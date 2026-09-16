"""
Unit tests for Deep Learning Sparse CNN Module:
  - Spatial hash voxelization O(N) complexity & point restoration
  - Submanifold Sparse 3D Convolution & Sparse U-Net backbone
  - Semantic inference and hand-off into foveated grid
"""

import pytest
import numpy as np
import torch

from deep_learning.sparse_voxelizer import SparseVoxelizer
from deep_learning.sparse_cnn_backbone import SparseCNNBackbone, SubmanifoldSparseConv3d
from deep_learning.semantic_inference import SemanticLidarInference
from core_math.foveated_grid import FoveatedGrid
from config import SemanticClass


def test_sparse_voxelizer_hash_grouping():
    """Verify that O(N) spatial hashing accurately reduces points into unique voxels."""
    voxelizer = SparseVoxelizer(voxel_size_m=0.20)

    # Create synthetic points: 2000 random points within a 10m cube
    pts = np.random.uniform(-5.0, 5.0, size=(2000, 3)).astype(np.float32)
    # Add identical points to verify clustering
    pts[:100] = pts[100]

    voxel_data = voxelizer.voxelize(pts)

    assert voxel_data.num_points == 2000
    assert voxel_data.num_voxels < 2000
    assert voxel_data.voxel_coords.shape[0] == voxel_data.num_voxels
    assert voxel_data.inverse_indices.shape[0] == 2000

    # Devoxelization test
    dummy_preds = torch.arange(voxel_data.num_voxels, dtype=torch.int64)
    point_preds = voxelizer.devoxelize(dummy_preds, voxel_data.inverse_indices)
    assert point_preds.shape[0] == 2000
    # Duplicate points should map to identical voxel indices
    assert point_preds[0] == point_preds[100]


def test_submanifold_sparse_conv_invariance():
    """Verify Submanifold Sparse Convolution maintains exact spatial sparsity."""
    conv = SubmanifoldSparseConv3d(in_channels=16, out_channels=32)
    conv.eval()

    M = 50
    coords = torch.randint(0, 10, size=(M, 3), dtype=torch.int32)
    # Ensure uniqueness
    coords = torch.unique(coords, dim=0)
    M_unique = coords.shape[0]
    feats = torch.randn((M_unique, 16), dtype=torch.float32)

    with torch.no_grad():
        out_feats = conv(coords, feats)

    assert out_feats.shape == (M_unique, 32)
    assert not torch.isnan(out_feats).any()


def test_sparse_cnn_backbone_forward():
    """Verify Sparse CNN backbone outputs correct class logits."""
    model = SparseCNNBackbone(in_channels=4, num_classes=9)
    model.eval()

    M = 80
    coords = torch.randint(0, 15, size=(M, 3), dtype=torch.int32)
    coords = torch.unique(coords, dim=0)
    M_unique = coords.shape[0]
    feats = torch.randn((M_unique, 4), dtype=torch.float32)

    with torch.no_grad():
        logits = model(coords, feats)

    assert logits.shape == (M_unique, 9)
    assert not torch.isnan(logits).any()


def test_semantic_inference_and_foveated_handoff():
    """Verify end-to-end hand-off: Raw points -> Sparse CNN -> Foveated Grid bucketing."""
    inference_engine = SemanticLidarInference(voxel_size_m=0.25)
    foveated_grid = FoveatedGrid()

    # Generate 500 synthetic ground points and 50 vertical obstacle points
    ground_pts = np.random.uniform(-15.0, 15.0, size=(500, 3)).astype(np.float32)
    ground_pts[:, 2] = np.random.uniform(-0.05, 0.05, size=(500,)).astype(np.float32)

    obstacle_pts = np.random.uniform(5.0, 8.0, size=(50, 3)).astype(np.float32)
    obstacle_pts[:, 2] = np.random.uniform(1.5, 3.5, size=(50,)).astype(np.float32)

    raw_pts = np.vstack([ground_pts, obstacle_pts])

    # 1. Run inference
    pts_t, labels_t = inference_engine.process_and_handoff(raw_pts)

    assert pts_t.shape[0] == 550
    assert labels_t.shape[0] == 550

    # Combine into (N, 4) [X, Y, Z, SemanticClass]
    annotated_pts = torch.cat([pts_t, labels_t.unsqueeze(1).float()], dim=1)

    # 2. Hand-off into Foveated Grid
    valid_mask, tier_ids, ix, iy, valid_pts = foveated_grid.partition(annotated_pts)

    assert valid_pts.shape[0] == 550
    assert tier_ids.shape[0] == 550
    assert ix.shape[0] == 550
    assert iy.shape[0] == 550
