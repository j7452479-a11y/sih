"""
Closed-Form Relative SE(3) Coordinate Registration
Mathematical foundation based on State Estimation for Robotics (Barfoot Ch. 7).
"""

from typing import Tuple
import torch

def compute_relative_se3(
    r_W_WC: torch.Tensor,
    C_WC: torch.Tensor,
    r_W_WD: torch.Tensor,
    C_WD: torch.Tensor,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Computes the exact closed-form relative transformation T_CD = T_WC^-1 * T_WD
    aligning drone measurements directly into the crawler's reference frame.

    Args:
        r_W_WC: (3,) position of Crawler in World frame [X, Y, Z]
        C_WC:   (3, 3) rotation matrix of Crawler in World frame
        r_W_WD: (3,) position of Drone in World frame [X, Y, Z]
        C_WD:   (3, 3) rotation matrix of Drone in World frame

    Returns:
        C_CD:   (3, 3) relative rotation matrix
        r_C_CD: (3,) relative translation vector in Crawler frame
    """
    # Inverse rotation of crawler C_CW = C_WC^T
    C_CW = C_WC.transpose(-1, -2)

    # Relative rotation C_CD = C_CW * C_WD
    C_CD = torch.matmul(C_CW, C_WD)

    # Relative translation r_C_CD = C_CW * (r_W_WD - r_W_WC)
    delta_pos = r_W_WD - r_W_WC
    r_C_CD = torch.matmul(C_CW, delta_pos.unsqueeze(-1)).squeeze(-1)

    return C_CD, r_C_CD

def transform_points_se3(
    points: torch.Tensor,
    C_CD: torch.Tensor,
    r_C_CD: torch.Tensor,
) -> torch.Tensor:
    """
    Vectorized transformation of point cloud P_D into Crawler frame P_C:
    p_C = C_CD * p_D + r_C_CD

    Args:
        points: (N, 3) or (N, D) points where first 3 columns are (X, Y, Z)
        C_CD:   (3, 3) relative rotation matrix
        r_C_CD: (3,) relative translation vector

    Returns:
        transformed: (N, D) points transformed into Crawler coordinate frame
    """
    if points.numel() == 0:
        return points

    xyz = points[:, :3]
    # P_C = (P_D * C_CD^T) + r_C_CD
    transformed_xyz = torch.matmul(xyz, C_CD.transpose(-1, -2)) + r_C_CD

    if points.shape[1] > 3:
        # Preserve semantic IDs and other extra channels
        return torch.cat([transformed_xyz, points[:, 3:]], dim=-1)
    return transformed_xyz
