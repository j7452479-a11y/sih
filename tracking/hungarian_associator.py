"""
Data Association using Mahalanobis Validation Gating & Hungarian Algorithm
Prevents identity swaps when targets intersect or cross paths.
"""

from typing import List, Tuple
import numpy as np
from scipy.optimize import linear_sum_assignment

from config import MAHALANOBIS_GATE_GAMMA
from .kalman_tracker import KalmanTracker2D

class HungarianAssociator:
    """
    Associates incoming detections to active tracks via Mahalanobis distance gating
    and optimal bipartite Hungarian matching.
    """

    def __init__(self, gate_gamma: float = MAHALANOBIS_GATE_GAMMA):
        self.gate_gamma = gate_gamma
        self.gate_penalty = 1e6

    def associate(
        self,
        tracks: List[KalmanTracker2D],
        detections: List[np.ndarray],  # List of [x, y] coordinates
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """
        Solves optimal track-to-detection matching.

        Args:
            tracks: List of active KalmanTracker2D objects (predicted state)
            detections: List of 2D detection coordinate arrays [x, y]

        Returns:
            matches: List of (track_index, detection_index)
            unmatched_tracks: List of track indices with no valid detection
            unmatched_detections: List of detection indices with no matching track
        """
        n_tracks = len(tracks)
        n_detections = len(detections)

        if n_tracks == 0:
            return [], [], list(range(n_detections))
        if n_detections == 0:
            return [], list(range(n_tracks)), []

        # Construct Cost Matrix (n_tracks, n_detections)
        cost_matrix = np.full((n_tracks, n_detections), self.gate_penalty, dtype=np.float64)

        for i, track in enumerate(tracks):
            s00 = track.P[0, 0] + track.R[0, 0]
            s01 = track.P[0, 1]
            s11 = track.P[1, 1] + track.R[1, 1]
            det = s00 * s11 - s01 * s01
            inv_det = 1.0 / det if abs(det) >= 1e-9 else 1e9
            i00 = s11 * inv_det
            i01 = -s01 * inv_det
            i11 = s00 * inv_det
            tx, ty = track.x[0], track.x[1]

            for j, det in enumerate(detections):
                dx = float(det[0] - tx)
                dy = float(det[1] - ty)
                d_m_sq = dx * (dx * i00 + dy * i01) + dy * (dx * i01 + dy * i11)
                if d_m_sq <= self.gate_gamma:
                    cost_matrix[i, j] = d_m_sq

        # Execute Hungarian (Munkres) assignment
        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        matches: List[Tuple[int, int]] = []
        matched_tracks = set()
        matched_detections = set()

        for r, c in zip(row_ind, col_ind):
            if cost_matrix[r, c] < self.gate_penalty:
                matches.append((r, c))
                matched_tracks.add(r)
                matched_detections.add(c)

        unmatched_tracks = [i for i in range(n_tracks) if i not in matched_tracks]
        unmatched_detections = [j for j in range(n_detections) if j not in matched_detections]

        return matches, unmatched_tracks, unmatched_detections
