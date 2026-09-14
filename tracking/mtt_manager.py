"""
Multi-Target Tracking Lifecycle State Machine & Provenance Manager
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple
import numpy as np

from config import (
    TRACK_DT,
    TRACK_CONFIRMATION_HITS,
    TRACK_COAST_MAX_MISSES,
)
from .kalman_tracker import KalmanTracker2D
from .hungarian_associator import HungarianAssociator
from .tier_dbscan import TargetCluster

class TrackState(Enum):
    TENTATIVE = auto()
    CONFIRMED = auto()
    COASTING = auto()
    DEAD = auto()

class TrackProvenance(Enum):
    LIDAR_CONFIRMED = 1
    UWB_SYNTHETIC = 2
    FUSED = 3

@dataclass
class TrackedTarget:
    """Represents a discrete tracked object with full kinematic history."""
    track_id: int
    tracker: KalmanTracker2D
    state: TrackState = TrackState.TENTATIVE
    provenance: TrackProvenance = TrackProvenance.LIDAR_CONFIRMED
    hit_count: int = 1
    miss_count: int = 0
    age_frames: int = 1
    point_count: int = 0
    tier_id: int = 0

    @property
    def position_3d(self) -> Tuple[float, float, float]:
        pos2d = self.tracker.position_2d
        return float(pos2d[0]), float(pos2d[1]), float(self.tracker.z)

    @property
    def velocity_2d(self) -> Tuple[float, float]:
        v2d = self.tracker.velocity_2d
        return float(v2d[0]), float(v2d[1])

    @property
    def speed(self) -> float:
        return self.tracker.speed

    @property
    def heading_deg(self) -> float:
        rad = self.tracker.heading_rad
        deg = float(np.degrees(rad))
        return (deg + 360.0) % 360.0

class MTTManager:
    """Coordinates detection association, Kalman filtering, and lifecycle state management."""

    def __init__(
        self,
        dt: float = TRACK_DT,
        confirmation_hits: int = TRACK_CONFIRMATION_HITS,
        max_misses: int = TRACK_COAST_MAX_MISSES,
    ):
        self.dt = dt
        self.confirmation_hits = confirmation_hits
        self.max_misses = max_misses
        self.associator = HungarianAssociator()
        self.tracks: Dict[int, TrackedTarget] = {}
        self.next_track_id = 1

    def update(
        self,
        clusters: List[TargetCluster],
        provenance: TrackProvenance = TrackProvenance.LIDAR_CONFIRMED,
    ) -> List[TrackedTarget]:
        """
        Executes one full cycle of the MTT pipeline:
        1. Predict active tracks
        2. Associate detections via Hungarian matching
        3. Update matched tracks, advance coasting tracks, spawn tentative tracks
        4. Purge dead tracks
        """
        active_tracks = list(self.tracks.values())

        # 1. Prediction step for all tracks
        for track in active_tracks:
            track.tracker.predict(self.dt)
            track.age_frames += 1

        # Extract 2D positions from clusters
        detections = [c.position_2d for c in clusters]
        track_objects = [t.tracker for t in active_tracks]

        # 2. Hungarian Data Association with Mahalanobis Gating
        matches, unmatched_tracks_idx, unmatched_dets_idx = self.associator.associate(
            track_objects, detections
        )

        # 3. Update Matched Tracks
        for t_idx, d_idx in matches:
            track = active_tracks[t_idx]
            cluster = clusters[d_idx]

            track.tracker.update(cluster.position_2d, z_elev=cluster.centroid_z)
            track.hit_count += 1
            track.miss_count = 0
            track.point_count = cluster.point_count
            track.tier_id = cluster.tier_id

            # Promote from Tentative to Confirmed
            if track.state == TrackState.TENTATIVE and track.hit_count >= self.confirmation_hits:
                track.state = TrackState.CONFIRMED
            elif track.state == TrackState.COASTING:
                track.state = TrackState.CONFIRMED

            # Update Provenance
            if track.provenance != provenance:
                track.provenance = TrackProvenance.FUSED
            else:
                track.provenance = provenance

        # 4. Handle Unmatched Tracks (Coasting or Dead)
        for t_idx in unmatched_tracks_idx:
            track = active_tracks[t_idx]
            track.miss_count += 1

            if track.state == TrackState.CONFIRMED:
                track.state = TrackState.COASTING

            if track.miss_count > self.max_misses or (track.state == TrackState.TENTATIVE and track.miss_count > 1):
                track.state = TrackState.DEAD

        # 5. Spawn New Tentative Tracks for Unmatched Detections
        used_ids = set(self.tracks.keys())
        for d_idx in unmatched_dets_idx:
            cluster = clusters[d_idx]
            new_id = 1
            while new_id in used_ids and new_id < 100:
                new_id += 1
            if new_id in used_ids:
                new_id = ((self.next_track_id - 1) % 99) + 1
                self.next_track_id += 1
            used_ids.add(new_id)

            tracker = KalmanTracker2D(
                track_id=new_id,
                initial_x=cluster.centroid_x,
                initial_y=cluster.centroid_y,
                initial_z=cluster.centroid_z,
                dt=self.dt,
            )
            self.tracks[new_id] = TrackedTarget(
                track_id=new_id,
                tracker=tracker,
                state=TrackState.TENTATIVE,
                provenance=provenance,
                hit_count=1,
                miss_count=0,
                age_frames=1,
                point_count=cluster.point_count,
                tier_id=cluster.tier_id,
            )

        # 6. Purge Dead Tracks
        dead_ids = [tid for tid, trk in self.tracks.items() if trk.state == TrackState.DEAD]
        for tid in dead_ids:
            del self.tracks[tid]

        # Return all active tracks (both Confirmed and Coasting)
        return [trk for trk in self.tracks.values() if trk.state in (TrackState.CONFIRMED, TrackState.COASTING)]

    def get_confirmed_tracks(self) -> List[TrackedTarget]:
        return [trk for trk in self.tracks.values() if trk.state == TrackState.CONFIRMED]
