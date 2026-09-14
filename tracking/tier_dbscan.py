"""
Tier-Adaptive Density-Based Spatial Clustering (DBSCAN)
Clusters sparse LiDAR target reflections using spatial tier resolution.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
import numpy as np
import torch
from scipy.spatial import cKDTree, KDTree

from config import (
    TIER_RADII,
    TIER_DBSCAN_EPSILONS,
    DBSCAN_MIN_POINTS,
    SemanticClass,
)

@dataclass
class TargetCluster:
    """Represents a clustered physical obstacle or hostile combatant."""
    centroid_x: float
    centroid_y: float
    centroid_z: float
    bbox_min: Tuple[float, float, float]
    bbox_max: Tuple[float, float, float]
    point_count: int
    tier_id: int

    @property
    def position_2d(self) -> np.ndarray:
        return np.array([self.centroid_x, self.centroid_y], dtype=np.float64)

class TierDBSCAN:
    """
    Tier-aware DBSCAN clustering engine.
    Adapts epsilon search radius according to the sensor's radial distance tier.
    """

    def __init__(
        self,
        tier_radii: Optional[List[float]] = None,
        tier_epsilons: Optional[List[float]] = None,
        min_samples: int = DBSCAN_MIN_POINTS,
    ):
        self.tier_radii = tier_radii or TIER_RADII
        self.tier_epsilons = tier_epsilons or TIER_DBSCAN_EPSILONS
        self.min_samples = min_samples

    def get_epsilon_for_distance(self, r: float) -> float:
        """Determines clustering epsilon based on radial distance."""
        for i, radius in enumerate(self.tier_radii):
            if r <= radius:
                return self.tier_epsilons[i]
        return self.tier_epsilons[-1]

    def cluster_points(
        self, points: np.ndarray, target_semantic_id: int = int(SemanticClass.TARGET)
    ) -> List[TargetCluster]:
        """
        Extracts and clusters target points.

        Args:
            points: (N, 3) [x, y, z] or (N, 4) [x, y, z, semantic_id]

        Returns:
            clusters: List of TargetCluster objects
        """
        if len(points) == 0:
            return []

        # Filter by semantic class if present
        if points.shape[1] >= 4:
            target_mask = points[:, 3] == target_semantic_id
            pts = points[target_mask, :3]
        else:
            pts = points[:, :3]

        if len(pts) < self.min_samples:
            return []

        # Vectorized Tier-Adaptive KD-Tree query
        r_xy = np.sqrt(pts[:, 0]**2 + pts[:, 1]**2)
        eps_arr = np.array([self.get_epsilon_for_distance(float(r)) for r in r_xy], dtype=np.float64)

        tree = cKDTree(pts)
        all_neighbors = tree.query_ball_point(pts, r=eps_arr)

        visited = set()
        clusters: List[TargetCluster] = []

        for i in range(len(pts)):
            if i in visited:
                continue
            nbrs = all_neighbors[i]
            if len(nbrs) < self.min_samples:
                continue

            visited.add(i)
            members = [i]
            q = [n for n in nbrs if n not in visited]
            visited.update(q)
            members.extend(q)

            head = 0
            while head < len(q):
                curr = q[head]
                head += 1
                curr_nbrs = all_neighbors[curr]
                if len(curr_nbrs) >= self.min_samples:
                    new_nodes = [n for n in curr_nbrs if n not in visited]
                    visited.update(new_nodes)
                    q.extend(new_nodes)
                    members.extend(new_nodes)

            c_pts = pts[members]
            if len(c_pts) < self.min_samples:
                continue

            cx, cy, cz = np.mean(c_pts, axis=0)
            b_min = tuple(np.min(c_pts, axis=0))
            b_max = tuple(np.max(c_pts, axis=0))

            dist_r = float(np.sqrt(cx**2 + cy**2))
            tier_id = 0
            for t_idx, radius in enumerate(self.tier_radii):
                if dist_r <= radius:
                    tier_id = t_idx
                    break

            clusters.append(TargetCluster(
                centroid_x=float(cx),
                centroid_y=float(cy),
                centroid_z=float(cz),
                bbox_min=(float(b_min[0]), float(b_min[1]), float(b_min[2])),
                bbox_max=(float(b_max[0]), float(b_max[1]), float(b_max[2])),
                point_count=len(c_pts),
                tier_id=tier_id
            ))

        return clusters
