"""
Capped Multi-Level Surface (MLS) Representation with Void Carving
Mathematical foundation based on Multi-Level Surface Maps for Outdoor Terrain (Triebel, Pfaff, Burgard).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import torch
import numpy as np

from config import (
    MLS_MAX_INTERVALS,
    MLS_GAP_THRESHOLD_M,
    MLS_MERGE_THRESHOLD_M,
    VEHICLE_CLEARANCE_HEIGHT_M,
    SemanticClass,
)
from .foveated_grid import FoveatedCellKey

@dataclass
class MLSInterval:
    """Represents a single vertical elevation layer within a spatial cell column."""
    z_min: float
    z_max: float
    point_count: int = 1
    semantic_class: int = int(SemanticClass.GROUND)

    @property
    def thickness(self) -> float:
        return max(0.0, self.z_max - self.z_min)

    @property
    def mean_z(self) -> float:
        return 0.5 * (self.z_min + self.z_max)

    def contains(self, z: float, tolerance: float = MLS_MERGE_THRESHOLD_M) -> bool:
        return (self.z_min - tolerance) <= z <= (self.z_max + tolerance)

    def merge_point(self, z: float, semantic_id: int):
        self.z_min = min(self.z_min, z)
        self.z_max = max(self.z_max, z)
        self.point_count += 1
        # Target/Obstacle takes precedence if hit
        if semantic_id in (int(SemanticClass.TARGET), int(SemanticClass.OBSTACLE), int(SemanticClass.BRIDGE)):
            self.semantic_class = semantic_id

@dataclass
class MLSCell:
    """Represents a multi-level surface column with up to K intervals."""
    key: FoveatedCellKey
    intervals: List[MLSInterval] = field(default_factory=list)

    def add_point(
        self,
        z: float,
        semantic_id: int = int(SemanticClass.GROUND),
        max_intervals: int = MLS_MAX_INTERVALS,
        merge_threshold: float = MLS_MERGE_THRESHOLD_M,
        gap_threshold: float = MLS_GAP_THRESHOLD_M,
    ):
        """Inserts an elevation point, managing interval splitting and merging."""
        if not self.intervals:
            self.intervals.append(MLSInterval(z_min=z, z_max=z, point_count=1, semantic_class=semantic_id))
            return

        # 1. Check if point merges into any existing interval
        for interval in self.intervals:
            if interval.contains(z, tolerance=merge_threshold):
                old_min, old_max = interval.z_min, interval.z_max
                interval.merge_point(z, semantic_id)
                # Only consolidate if there are multiple intervals and bounds expanded
                if len(self.intervals) > 1 and (interval.z_min < old_min or interval.z_max > old_max):
                    self._consolidate_intervals(merge_threshold)
                return

        # 2. Point is outside all existing intervals by > merge_threshold
        # Add new interval
        self.intervals.append(MLSInterval(z_min=z, z_max=z, point_count=1, semantic_class=semantic_id))
        self.intervals.sort(key=lambda iv: iv.z_min)
        if len(self.intervals) > 1:
            self._consolidate_intervals(merge_threshold)

        # 3. If exceeding max_intervals (K=3), merge the two closest intervals
        while len(self.intervals) > max_intervals:
            min_gap_idx = 0
            min_gap = float("inf")
            for i in range(len(self.intervals) - 1):
                gap = self.intervals[i + 1].z_min - self.intervals[i].z_max
                if gap < min_gap:
                    min_gap = gap
                    min_gap_idx = i

            # Merge interval i and i+1
            iv_a = self.intervals[min_gap_idx]
            iv_b = self.intervals[min_gap_idx + 1]
            merged = MLSInterval(
                z_min=min(iv_a.z_min, iv_b.z_min),
                z_max=max(iv_a.z_max, iv_b.z_max),
                point_count=iv_a.point_count + iv_b.point_count,
                semantic_class=max(iv_a.semantic_class, iv_b.semantic_class)
            )
            self.intervals.pop(min_gap_idx + 1)
            self.intervals[min_gap_idx] = merged

    def _consolidate_intervals(self, merge_threshold: float):
        """Merges overlapping or adjacent intervals."""
        if len(self.intervals) <= 1:
            return
        self.intervals.sort(key=lambda iv: iv.z_min)
        consolidated: List[MLSInterval] = [self.intervals[0]]
        for curr in self.intervals[1:]:
            prev = consolidated[-1]
            if curr.z_min <= (prev.z_max + merge_threshold):
                prev.z_max = max(prev.z_max, curr.z_max)
                prev.point_count += curr.point_count
                prev.semantic_class = max(prev.semantic_class, curr.semantic_class)
            else:
                consolidated.append(curr)
        self.intervals = consolidated

    def get_traversable_voids(self) -> List[Tuple[float, float, float]]:
        """
        Returns all vertical void passages between layers:
        List of (void_bottom_z, void_top_z, clearance_height_m)
        """
        voids = []
        if len(self.intervals) < 2:
            return voids
        for i in range(len(self.intervals) - 1):
            bottom = self.intervals[i].z_max
            top = self.intervals[i + 1].z_min
            clearance = max(0.0, top - bottom)
            voids.append((bottom, top, clearance))
        return voids

    def is_traversable_underpass(self, required_clearance: float = VEHICLE_CLEARANCE_HEIGHT_M) -> bool:
        """
        Evaluates whether this cell is an open underpass.
        True if there is ground surface AND an overhead surface with clearance >= required_clearance.
        """
        for _, _, clearance in self.get_traversable_voids():
            if clearance >= required_clearance:
                return True
        return False

class MLSEngine:
    """Manages the sparse collection of multi-level surface cells across the 4 tiers."""

    def __init__(self):
        self.cells: Dict[FoveatedCellKey, MLSCell] = {}

    def clear(self):
        self.cells.clear()

    def update_from_partition(
        self,
        tier_ids: torch.Tensor,
        ix: torch.Tensor,
        iy: torch.Tensor,
        points: torch.Tensor,
    ):
        """
        Updates the MLS map with batch points from FoveatedGrid.partition().
        points: (N, 3) [x, y, z] or (N, 4) [x, y, z, semantic_id]
        """
        if points.numel() == 0:
            return

        has_semantic = points.shape[1] >= 4
        z_coords = points[:, 2].tolist()
        semantics = points[:, 3].long().tolist() if has_semantic else [0] * len(points)

        t_ids = tier_ids.tolist()
        ix_l = ix.tolist()
        iy_l = iy.tolist()

        cells = self.cells
        for t_id, x_idx, y_idx, z, sem in zip(t_ids, ix_l, iy_l, z_coords, semantics):
            key = FoveatedCellKey(t_id, x_idx, y_idx)
            cell = cells.get(key)
            if cell is None:
                cell = MLSCell(key=key)
                cells[key] = cell
            cell.add_point(z, sem)

    def get_traversable_corridors(
        self, required_clearance: float = VEHICLE_CLEARANCE_HEIGHT_M
    ) -> List[Tuple[FoveatedCellKey, float, float]]:
        """Returns all cells with confirmed open clearance (underpasses)."""
        corridors = []
        for key, cell in self.cells.items():
            for bottom, top, clearance in cell.get_traversable_voids():
                if clearance >= required_clearance:
                    corridors.append((key, bottom, clearance))
        return corridors

    def get_cell_count(self) -> int:
        return len(self.cells)

    def get_total_interval_count(self) -> int:
        return sum(len(c.intervals) for c in self.cells.values())
