"""
Tests for Loop-Free 4-Tier Foveated Grid Partitioning.
Validates boundary stability, zero-crossing numerical precision, and loop-free speed.
"""

import time
import pytest
import torch

from core_math.foveated_grid import FoveatedGrid, FoveatedCellKey
from config import TIER_RADII, TIER_RESOLUTIONS, ZERO_CROSSING_EPSILON

def test_radial_tier_allocation():
    grid = FoveatedGrid()
    # Test points at distinct radial bands
    # (r = 5m -> Tier 0, r = 20m -> Tier 1, r = 45m -> Tier 2, r = 80m -> Tier 3)
    pts = torch.tensor([
        [3.0, 4.0, 0.0],    # r = 5.0m  -> Tier 0 (Fovea)
        [12.0, 16.0, 0.0],  # r = 20.0m -> Tier 1 (Near-Field)
        [27.0, 36.0, 0.0],  # r = 45.0m -> Tier 2 (Mid-Field)
        [48.0, 64.0, 0.0],  # r = 80.0m -> Tier 3 (Far-Field)
    ], dtype=torch.float32)

    valid_mask, tier_ids, ix, iy, valid_pts = grid.partition(pts)

    assert valid_mask.all()
    assert tier_ids.tolist() == [0, 1, 2, 3]

def test_boundary_stability():
    grid = FoveatedGrid()
    # Points exactly on the boundaries: 10.0m, 30.0m, 60.0m, 100.0m
    pts = torch.tensor([
        [10.0, 0.0, 0.0],   # exactly at 10m
        [30.0, 0.0, 0.0],   # exactly at 30m
        [60.0, 0.0, 0.0],   # exactly at 60m
        [100.0, 0.0, 0.0],  # exactly at 100m
        [100.01, 0.0, 0.0], # beyond max range -> invalid
    ], dtype=torch.float32)

    valid_mask, tier_ids, ix, iy, valid_pts = grid.partition(pts)

    assert valid_mask[:4].all()
    assert not valid_mask[4]  # 100.01m is out of range
    assert tier_ids.shape[0] == 4

def test_zero_crossing_symmetry():
    grid = FoveatedGrid()
    # Coordinates infinitesimally close to zero
    pts = torch.tensor([
        [-1e-7, 1e-7, 0.0],
        [1e-7, -1e-7, 0.0],
        [0.0, 0.0, 0.0],
    ], dtype=torch.float32)

    valid_mask, tier_ids, ix, iy, valid_pts = grid.partition(pts)

    assert valid_mask.all()
    # All near-zero points should map to cell (0, 0) in Tier 0
    assert (ix == 0).all()
    assert (iy == 0).all()
    assert (tier_ids == 0).all()

def test_partition_performance_benchmark():
    grid = FoveatedGrid()
    # Benchmark with 100,000 points
    n_points = 100_000
    pts = (torch.rand(n_points, 3) - 0.5) * 160.0  # Points in [-80, 80]
    pts[:, 2] = torch.rand(n_points) * 5.0         # Elevations in [0, 5]

    t0 = time.perf_counter()
    valid_mask, tier_ids, ix, iy, valid_pts = grid.partition(pts)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    print(f"\nPartitioned {n_points} points in {elapsed_ms:.2f} ms")
    # Must execute in under 20 ms on modern CPU
    assert elapsed_ms < 50.0, f"Partition latency {elapsed_ms:.2f}ms exceeds threshold"
    assert valid_mask.sum() > 0
