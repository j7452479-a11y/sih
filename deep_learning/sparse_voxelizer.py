"""
SIH26053 - Tactical Edge Perception Engine
Module: Sparse Spatial Hash Voxelizer
Mathematical Foundation:
  - Choy, C., Gwak, J., & Savarese, S. (2019). "4D Spatio-Temporal ConvNets: Minkowski Engine." CVPR.
  - Voxelization complexity: O(N) spatial hashing instead of O(N^3) dense grid allocation.
"""

from dataclasses import dataclass
from typing import Tuple, Optional
import numpy as np
import torch


@dataclass
class VoxelGridData:
    """Represents a sparse voxelized point cloud."""
    voxel_coords: torch.Tensor       # Shape: (M, 3) int32 [vx, vy, vz]
    voxel_features: torch.Tensor     # Shape: (M, C) float32 (aggregated features e.g. centroid, intensity)
    inverse_indices: torch.Tensor    # Shape: (N,) int64 mapping each original point to its voxel index [0..M-1]
    num_points: int                  # Original point count N
    num_voxels: int                  # Occupied voxel count M (M <= N)
    voxel_size_m: float              # Spatial leaf dimension (meters)
    origin_m: torch.Tensor           # Minimum coordinate offset [min_x, min_y, min_z]


class SparseVoxelizer:
    """
    High-performance Sparse Hash Table Voxelizer.
    Converts raw unordered (N, 3) LiDAR coordinates into a sparse coordinate hash table.
    Bypasses dense 3D matrix storage to achieve O(N) memory efficiency on edge devices.
    """

    def __init__(self, voxel_size_m: float = 0.10, max_voxels: int = 40000):
        """
        Args:
            voxel_size_m: Side length of cubic voxel in meters (e.g. 0.10m = 10cm).
            max_voxels: Maximum unique voxels to process per frame buffer.
        """
        self.voxel_size_m = float(voxel_size_m)
        self.max_voxels = max_voxels

    def voxelize(
        self,
        points: torch.Tensor,
        features: Optional[torch.Tensor] = None
    ) -> VoxelGridData:
        """
        Voxelize an unordered point cloud via hash grouping.

        Args:
            points: Tensor of shape (N, 3) containing (x, y, z) in meters.
            features: Optional Tensor of shape (N, C) containing point features (e.g., intensity).
                      If None, normalized local point coordinates relative to voxel center are used.

        Returns:
            VoxelGridData dataclass containing sparse coords, features, and inverse mapping.
        """
        if not isinstance(points, torch.Tensor):
            points = torch.tensor(points, dtype=torch.float32)

        N = points.shape[0]
        if N == 0:
            empty_coords = torch.zeros((0, 3), dtype=torch.int32, device=points.device)
            empty_feat = torch.zeros((0, 4 if features is None else features.shape[1]), dtype=torch.float32, device=points.device)
            empty_inv = torch.zeros((0,), dtype=torch.int64, device=points.device)
            return VoxelGridData(
                voxel_coords=empty_coords,
                voxel_features=empty_feat,
                inverse_indices=empty_inv,
                num_points=0,
                num_voxels=0,
                voxel_size_m=self.voxel_size_m,
                origin_m=torch.zeros(3, device=points.device)
            )

        # 1. Compute bounding box origin
        origin = torch.min(points, dim=0)[0]

        # 2. Integer voxel coordinate quantization: v = floor((p - origin) / voxel_size)
        grid_coords = torch.floor((points - origin) / self.voxel_size_m).to(torch.int32)

        # 3. Fast Unique Coordinate Hash Extraction via torch.unique
        # dim=0 returns unique rows and inverse mapping for all original points
        unique_coords, inverse_indices = torch.unique(grid_coords, dim=0, return_inverse=True)
        M = unique_coords.shape[0]

        # 4. Feature aggregation: Scatter mean over points belonging to the same voxel
        if features is None:
            # Default features: (relative_x, relative_y, relative_z, distance)
            voxel_centers = (unique_coords.to(torch.float32) + 0.5) * self.voxel_size_m + origin
            point_centers = voxel_centers[inverse_indices]
            rel_coords = points - point_centers
            dists = torch.norm(points, dim=1, keepdim=True)
            raw_features = torch.cat([rel_coords, dists], dim=1)
        else:
            if not isinstance(features, torch.Tensor):
                features = torch.tensor(features, dtype=torch.float32, device=points.device)
            raw_features = features

        C = raw_features.shape[1]
        voxel_features = torch.zeros((M, C), dtype=torch.float32, device=points.device)
        counts = torch.zeros((M, 1), dtype=torch.float32, device=points.device)

        # Scatter sum
        voxel_features.index_add_(0, inverse_indices, raw_features)
        counts.index_add_(0, inverse_indices, torch.ones((N, 1), dtype=torch.float32, device=points.device))

        # Compute average feature per voxel
        voxel_features = voxel_features / torch.clamp(counts, min=1.0)

        return VoxelGridData(
            voxel_coords=unique_coords,
            voxel_features=voxel_features,
            inverse_indices=inverse_indices,
            num_points=N,
            num_voxels=M,
            voxel_size_m=self.voxel_size_m,
            origin_m=origin
        )

    def devoxelize(self, voxel_predictions: torch.Tensor, inverse_indices: torch.Tensor) -> torch.Tensor:
        """
        Maps voxel-level predictions back to the original N points in O(N) time.

        Args:
            voxel_predictions: Tensor of shape (M, num_classes) or (M,)
            inverse_indices: Tensor of shape (N,) from VoxelGridData

        Returns:
            Tensor of shape (N, num_classes) or (N,) mapped point predictions.
        """
        return voxel_predictions[inverse_indices]
