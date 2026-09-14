"""
Loop-Free 4-Tier Foveated Radial Grid Partitioning
Mathematical foundation based on Computational Geometry (de Berg Ch. 14) & PyTorch bucketize.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import torch

from config import (
    TIER_RADII,
    TIER_RESOLUTIONS,
    MAX_SENSOR_RANGE_M,
    ZERO_CROSSING_EPSILON,
)

@dataclass(frozen=True, slots=True)
class FoveatedCellKey:
    """Anti-aliased spatial cell key preventing cross-tier hash collisions."""
    tier_id: int
    ix: int
    iy: int

class FoveatedGrid:
    """
    Vectorized 4-tier foveated grid engine.
    Partitions 3D point clouds into concentric spatial resolution bands:
      Tier 0 (Fovea):      0m  - 10m  @ 5cm
      Tier 1 (Near-Field): 10m - 30m  @ 10cm
      Tier 2 (Mid-Field):  30m - 60m  @ 20cm
      Tier 3 (Far-Field):  60m - 100m @ 50cm
    """

    def __init__(
        self,
        tier_radii: Optional[List[float]] = None,
        tier_resolutions: Optional[List[float]] = None,
        device: str = "cpu"
    ):
        self.tier_radii_list = tier_radii or TIER_RADII
        self.tier_resolutions_list = tier_resolutions or TIER_RESOLUTIONS
        self.device = torch.device(device)

        # Pre-allocate parameter tensors
        self.tier_boundaries = torch.tensor(
            self.tier_radii_list, dtype=torch.float32, device=self.device
        )
        self.tier_resolutions = torch.tensor(
            self.tier_resolutions_list, dtype=torch.float32, device=self.device
        )
        self.num_tiers = len(self.tier_radii_list)

    def partition(
        self, points: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Vectorized loop-free partitioning of point clouds.

        Args:
            points: (N, 3) or (N, 4) float tensor of [X, Y, Z] or [X, Y, Z, SemanticID]

        Returns:
            valid_mask: (N,) boolean mask of points within max range
            tier_ids:   (M,) int64 tensor of tier index (0..num_tiers-1) for valid points
            ix:         (M,) int64 tensor of discrete X grid coordinates
            iy:         (M,) int64 tensor of discrete Y grid coordinates
            valid_pts:  (M, D) float tensor of valid points
        """
        if points.numel() == 0:
            empty_long = torch.empty(0, dtype=torch.long, device=points.device)
            empty_bool = torch.empty(0, dtype=torch.bool, device=points.device)
            return empty_bool, empty_long, empty_long, empty_long, points

        x = points[:, 0]
        y = points[:, 1]

        # 1. Zero-crossing stabilization guard
        # Prevents asymmetric rounding around (0, 0)
        x_clamped = torch.where(torch.abs(x) < ZERO_CROSSING_EPSILON, torch.zeros_like(x), x)
        y_clamped = torch.where(torch.abs(y) < ZERO_CROSSING_EPSILON, torch.zeros_like(y), y)

        # 2. Euclidean radial distance calculation
        r = torch.sqrt(x_clamped ** 2 + y_clamped ** 2)

        # Filter out out-of-range points (beyond Tier 4 outer boundary)
        valid_mask = r <= self.tier_radii_list[-1]
        if not valid_mask.any():
            empty_long = torch.empty(0, dtype=torch.long, device=points.device)
            return valid_mask, empty_long, empty_long, empty_long, points[valid_mask]

        r_valid = r[valid_mask]
        x_valid = x_clamped[valid_mask]
        y_valid = y_clamped[valid_mask]
        valid_pts = points[valid_mask]

        # 3. Vectorized tier allocation using torch.bucketize
        # Tier 0 for r in [0, 10], Tier 1 for r in (10, 30], etc.
        # right=False ensures r == 10.0 falls into Tier 1 (boundary inclusion)
        tier_ids = torch.bucketize(r_valid, self.tier_boundaries, right=False)
        tier_ids = torch.clamp(tier_ids, 0, self.num_tiers - 1)

        # 4. Discrete cell indexing based on per-tier resolution
        resolutions = self.tier_resolutions[tier_ids]
        ix = torch.floor(x_valid / resolutions).long()
        iy = torch.floor(y_valid / resolutions).long()

        return valid_mask, tier_ids, ix, iy, valid_pts

    def get_cell_center(self, key: FoveatedCellKey) -> Tuple[float, float, float]:
        """Returns the world-space (X, Y) center and cell resolution for a given key."""
        res = self.tier_resolutions_list[key.tier_id]
        cx = (key.ix + 0.5) * res
        cy = (key.iy + 0.5) * res
        return cx, cy, res
