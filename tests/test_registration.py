"""
Tests for Closed-Form SE(3) Coordinate Registration (Barfoot Ch. 7).
"""

import pytest
import torch
import math

from core_math.registration import compute_relative_se3, transform_points_se3

def test_se3_relative_transformation():
    # Crawler at origin facing North (0 deg yaw)
    r_W_WC = torch.tensor([0.0, 0.0, 0.0], dtype=torch.float32)
    C_WC = torch.eye(3, dtype=torch.float32)

    # Drone at (X=10, Y=20, Z=30) facing North
    r_W_WD = torch.tensor([10.0, 20.0, 30.0], dtype=torch.float32)
    C_WD = torch.eye(3, dtype=torch.float32)

    C_CD, r_C_CD = compute_relative_se3(r_W_WC, C_WC, r_W_WD, C_WD)

    # Relative rotation should be identity
    assert torch.allclose(C_CD, torch.eye(3), atol=1e-5)
    # Relative translation should be (10, 20, 30)
    assert torch.allclose(r_C_CD, torch.tensor([10.0, 20.0, 30.0]), atol=1e-5)

    # Transform a drone point [0, 0, -10] (point 10m below drone in drone body frame)
    drone_pts = torch.tensor([[0.0, 0.0, -10.0]], dtype=torch.float32)
    crawler_pts = transform_points_se3(drone_pts, C_CD, r_C_CD)

    # In crawler frame, point should be at [10, 20, 20]
    expected = torch.tensor([[10.0, 20.0, 20.0]], dtype=torch.float32)
    assert torch.allclose(crawler_pts, expected, atol=1e-5)

def test_se3_with_rotation():
    # Crawler rotated 90 deg yaw around Z
    # Rot matrix for +90 deg: [ [0, -1, 0], [1, 0, 0], [0, 0, 1] ]
    C_WC = torch.tensor([
        [0.0, -1.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0]
    ], dtype=torch.float32)
    r_W_WC = torch.tensor([5.0, 0.0, 0.0], dtype=torch.float32)

    # Drone at world [5, 10, 0] with identity rotation
    r_W_WD = torch.tensor([5.0, 10.0, 0.0], dtype=torch.float32)
    C_WD = torch.eye(3, dtype=torch.float32)

    C_CD, r_C_CD = compute_relative_se3(r_W_WC, C_WC, r_W_WD, C_WD)

    # Point at drone origin [0, 0, 0]
    p_D = torch.tensor([[0.0, 0.0, 0.0]], dtype=torch.float32)
    p_C = transform_points_se3(p_D, C_CD, r_C_CD)

    # Drone is at world (5, 10, 0).
    # Crawler is at world (5, 0, 0) facing +Y (North).
    # In crawler frame, drone is 10m directly forward along Crawler's +X axis!
    # Let's verify: C_WC^T * ( [5, 10, 0] - [5, 0, 0] ) = [ [0, 1, 0], [-1, 0, 0], [0, 0, 1] ] * [0, 10, 0]^T = [10, 0, 0]
    expected = torch.tensor([[10.0, 0.0, 0.0]], dtype=torch.float32)
    assert torch.allclose(p_C, expected, atol=1e-4)
