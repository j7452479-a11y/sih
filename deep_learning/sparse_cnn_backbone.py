"""
SIH26053 - Tactical Edge Perception Engine
Module: Sparse Convolutional Neural Network (Sparse CNN) Backbone
Mathematical Foundations:
  - Choy, C., Gwak, J., & Savarese, S. (2019). "4D Spatio-Temporal ConvNets: Minkowski Engine." CVPR.
  - Tang, H., et al. (2020). "Searching Efficient 3D Architectures with Sparse Point-Voxel Convolution." ECCV.
  - Qi, C. R., et al. (2017). "PointNet++: Deep Hierarchical Feature Learning on Point Sets." NeurIPS.
  - Submanifold Sparse Convolution preserves exact spatial sparsity: O(N) FLOPs vs dense O(N^3).
"""

from typing import Tuple, List, Dict
import torch
import torch.nn as nn
import torch.nn.functional as F


class SubmanifoldSparseConv3d(nn.Module):
    """
    Submanifold Sparse 3D Convolution layer operating on coordinate-feature pairs (Coords, Features).
    Kernel offsets evaluate only within existing occupied voxels to maintain strict O(N) sparsity.
    """

    def __init__(self, in_channels: int, out_channels: int, kernel_size: int = 3):
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.kernel_size = kernel_size

        # Define 3D kernel offsets (6-connected cross or 27-connected cube)
        # Using 7-kernel (center + 6 cardinal neighbors) for maximal edge-compute efficiency
        offsets = [
            (0, 0, 0),    # Center
            (1, 0, 0), (-1, 0, 0),  # +X, -X
            (0, 1, 0), (0, -1, 0),  # +Y, -Y
            (0, 0, 1), (0, 0, -1)   # +Z, -Z
        ]
        self.register_buffer("kernel_offsets", torch.tensor(offsets, dtype=torch.int32))
        self.num_offsets = len(offsets)

        # Learnable weight tensor: (num_offsets, in_channels, out_channels)
        self.weight = nn.Parameter(torch.empty(self.num_offsets, in_channels, out_channels))
        self.bias = nn.Parameter(torch.zeros(out_channels))
        nn.init.kaiming_uniform_(self.weight, a=5**0.5)

    def forward(self, coords: torch.Tensor, features: torch.Tensor) -> torch.Tensor:
        """
        Forward pass of Submanifold Sparse Convolution.

        Args:
            coords: (M, 3) int32 voxel coordinates
            features: (M, C_in) float32 features

        Returns:
            out_features: (M, C_out) float32 convolved features
        """
        M, C_in = features.shape
        device = features.device

        if M == 0:
            return torch.zeros((0, self.out_channels), device=device)

        # Center contribution (offset 0: (0,0,0))
        out_features = torch.matmul(features, self.weight[0]) + self.bias

        # Spatial Hash Map for fast O(1) coordinate lookup
        # Prime hash multipliers for 3D coordinates
        p1, p2, p3 = 73856093, 19349663, 83492791
        hash_keys = coords[:, 0].to(torch.int64) * p1 ^ coords[:, 1].to(torch.int64) * p2 ^ coords[:, 2].to(torch.int64) * p3

        # Sort coordinates for fast binary search / searchsorted indexing
        sorted_hashes, sort_indices = torch.sort(hash_keys)
        inv_sort_indices = torch.empty_like(sort_indices)
        inv_sort_indices[sort_indices] = torch.arange(M, device=device)

        # Evaluate neighbor contributions
        for k in range(1, self.num_offsets):
            offset = self.kernel_offsets[k]
            neighbor_coords = coords + offset

            # Compute neighbor hashes
            nbr_hashes = neighbor_coords[:, 0].to(torch.int64) * p1 ^ neighbor_coords[:, 1].to(torch.int64) * p2 ^ neighbor_coords[:, 2].to(torch.int64) * p3

            # Find matching hash positions via binary search
            candidate_indices = torch.searchsorted(sorted_hashes, nbr_hashes)
            candidate_indices = torch.clamp(candidate_indices, 0, M - 1)

            # Check exact match
            matched = (sorted_hashes[candidate_indices] == nbr_hashes)
            if matched.any():
                match_indices_in_orig = sort_indices[candidate_indices[matched]]
                source_indices = torch.nonzero(matched, as_tuple=True)[0]

                # Matrix multiplication for kernel offset k
                nbr_feats = features[match_indices_in_orig]
                transformed = torch.matmul(nbr_feats, self.weight[k])
                out_features[source_indices] += transformed

        return out_features


class SparseResidualBlock(nn.Module):
    """Residual Sparse Convolutional Block: F_out = ReLU(BatchNorm(Conv(ReLU(BatchNorm(Conv(F)))))) + F"""

    def __init__(self, channels: int):
        super().__init__()
        self.conv1 = SubmanifoldSparseConv3d(channels, channels)
        self.bn1 = nn.BatchNorm1d(channels)
        self.conv2 = SubmanifoldSparseConv3d(channels, channels)
        self.bn2 = nn.BatchNorm1d(channels)

    def forward(self, coords: torch.Tensor, features: torch.Tensor) -> torch.Tensor:
        residual = features
        x = self.conv1(coords, features)
        x = self.bn1(x)
        x = F.relu(x, inplace=True)
        x = self.conv2(coords, x)
        x = self.bn2(x)
        return F.relu(x + residual, inplace=True)


class SparseCNNBackbone(nn.Module):
    """
    Lightweight Sparse Convolutional Neural Network (Sparse U-Net).
    Optimized for SWaP-constrained edge platforms (NVIDIA Jetson Orin Nano).
    Processes sparse voxel features in O(N) complexity and outputs semantic classification logits.
    """

    def __init__(self, in_channels: int = 4, num_classes: int = 9):
        super().__init__()
        self.in_channels = in_channels
        self.num_classes = num_classes

        # Stem projection
        self.stem = nn.Sequential(
            nn.Linear(in_channels, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(inplace=True)
        )

        # Sparse Convolutional Encoders
        self.sparse_conv1 = SubmanifoldSparseConv3d(32, 32)
        self.res_block1 = SparseResidualBlock(32)

        self.transit1 = nn.Sequential(
            nn.Linear(32, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(inplace=True)
        )
        self.sparse_conv2 = SubmanifoldSparseConv3d(64, 64)
        self.res_block2 = SparseResidualBlock(64)

        # Bottleneck & Decoder
        self.decoder_transit = nn.Sequential(
            nn.Linear(64, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(inplace=True)
        )
        self.sparse_conv_dec = SubmanifoldSparseConv3d(32, 32)

        # Classification Head (per-voxel logits)
        self.classifier = nn.Sequential(
            nn.Linear(32, 32),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.1),
            nn.Linear(32, num_classes)
        )

    def forward(self, coords: torch.Tensor, features: torch.Tensor) -> torch.Tensor:
        """
        Args:
            coords: (M, 3) int32 voxel coordinates
            features: (M, in_channels) float32 input features

        Returns:
            logits: (M, num_classes) float32 classification logits
        """
        # 1. Stem
        x = self.stem(features)

        # 2. Stage 1 Sparse Convolutions (32 channels)
        x = self.sparse_conv1(coords, x)
        x = self.res_block1(coords, x)

        # 3. Stage 2 Sparse Convolutions (64 channels)
        x = self.transit1(x)
        x = self.sparse_conv2(coords, x)
        x = self.res_block2(coords, x)

        # 4. Decoder Stage
        x = self.decoder_transit(x)
        x = self.sparse_conv_dec(coords, x)

        # 5. Output Logits
        logits = self.classifier(x)
        return logits
