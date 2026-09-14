"""
Tests for Multi-Target Tracking (MTT) Pipeline.
Validates Kalman filter convergence, Mahalanobis gating, and zero track swaps during target crossings.
"""

import pytest
import numpy as np

from tracking.kalman_tracker import KalmanTracker2D
from tracking.hungarian_associator import HungarianAssociator
from tracking.mtt_manager import MTTManager, TrackState
from tracking.tier_dbscan import TargetCluster

def test_kalman_filter_convergence():
    # Target moving along X axis at constant 2.0 m/s from X=0 to X=10
    dt = 0.05
    tracker = KalmanTracker2D(track_id=1, initial_x=0.0, initial_y=0.0, dt=dt)

    np.random.seed(42)
    true_x = 0.0
    true_vx = 2.0

    for step in range(50):  # 2.5 seconds of tracking
        true_x += true_vx * dt
        noise = np.random.normal(0.0, 0.03)
        meas = np.array([true_x + noise, 0.0])

        tracker.predict()
        tracker.update(meas)

    # Velocity estimate should converge close to 2.0 m/s
    est_vx = tracker.velocity_2d[0]
    assert pytest.approx(est_vx, abs=0.25) == 2.0
    assert pytest.approx(tracker.position_2d[0], abs=0.2) == true_x

def test_zero_track_swaps_during_crossing():
    """
    CRITICAL SIH TEST:
    Target A travels East to West: (-5, 0) -> (5, 0)
    Target B travels North to South: (0, -5) -> (0, 5)
    At t = 2.5s, both targets cross exactly at the village square (0, 0).
    The Hungarian algorithm and Mahalanobis gating MUST maintain their identity
    with ZERO identity swaps.
    """
    dt = 0.05
    manager = MTTManager(dt=dt)

    # Initial warmup positions at t = 0
    # Hostile A starts at (-4.0, 0.0), velocity = (+1.6 m/s, 0) -> reaches (0,0) at t=2.5s
    # Hostile B starts at (0.0, -4.0), velocity = (0, +1.6 m/s) -> reaches (0,0) at t=2.5s
    speed = 1.6
    steps = 100  # 5.0 seconds total

    track_id_a = None
    track_id_b = None

    for step in range(steps):
        t = step * dt
        # Positions:
        pos_a_x = -4.0 + speed * t
        pos_a_y = 0.0

        pos_b_x = 0.0
        pos_b_y = -4.0 + speed * t

        cluster_a = TargetCluster(
            centroid_x=pos_a_x, centroid_y=pos_a_y, centroid_z=0.0,
            bbox_min=(pos_a_x - 0.4, pos_a_y - 0.4, -0.9),
            bbox_max=(pos_a_x + 0.4, pos_a_y + 0.4, 0.9),
            point_count=25, tier_id=0
        )
        cluster_b = TargetCluster(
            centroid_x=pos_b_x, centroid_y=pos_b_y, centroid_z=0.0,
            bbox_min=(pos_b_x - 0.4, pos_b_y - 0.4, -0.9),
            bbox_max=(pos_b_x + 0.4, pos_b_y + 0.4, 0.9),
            point_count=25, tier_id=0
        )

        active = manager.update([cluster_a, cluster_b])

        if step == 10:  # After initial confirmation frames
            assert len(active) == 2
            # Identify which track ID belongs to A (moving East) and B (moving North)
            for trk in active:
                if trk.velocity_2d[0] > trk.velocity_2d[1]:
                    track_id_a = trk.track_id
                else:
                    track_id_b = trk.track_id

    # Verify that post-crossing (at t = 5.0s, step 99):
    # Track A is still Track A, and Track B is still Track B!
    final_tracks = {trk.track_id: trk for trk in manager.get_confirmed_tracks()}

    assert track_id_a in final_tracks
    assert track_id_b in final_tracks
    assert track_id_a != track_id_b

    # Track A should now be at positive X (+4.0), near Y=0
    assert final_tracks[track_id_a].position_3d[0] > 3.0
    assert abs(final_tracks[track_id_a].position_3d[1]) < 0.5

    # Track B should now be at positive Y (+4.0), near X=0
    assert final_tracks[track_id_b].position_3d[1] > 3.0
    assert abs(final_tracks[track_id_b].position_3d[0]) < 0.5

def test_wall_occlusion_coasting_and_reacquisition():
    """
    Validates that a confirmed track enters COASTING when occluded behind a wall
    and re-acquires without losing its track ID when emerging.
    """
    dt = 0.05
    manager = MTTManager(dt=dt)

    # 1. Warmup track for 5 frames
    for i in range(5):
        c = TargetCluster(
            centroid_x=float(i * 0.1), centroid_y=0.0, centroid_z=0.0,
            bbox_min=(0,0,0), bbox_max=(1,1,1), point_count=15, tier_id=0
        )
        active = manager.update([c])

    assert len(active) == 1
    orig_id = active[0].track_id
    assert active[0].state == TrackState.CONFIRMED

    # 2. Occlusion behind stone wall for 3 frames (no detections)
    for _ in range(3):
        active = manager.update([])

    # Track should be coasting, still alive!
    assert len(active) == 1
    assert active[0].track_id == orig_id
    assert active[0].state == TrackState.COASTING

    # 3. Target emerges from behind wall
    c_reappear = TargetCluster(
        centroid_x=0.8, centroid_y=0.0, centroid_z=0.0,
        bbox_min=(0,0,0), bbox_max=(1,1,1), point_count=15, tier_id=0
    )
    active = manager.update([c_reappear])

    # Should re-acquire with SAME track ID and return to CONFIRMED!
    assert len(active) == 1
    assert active[0].track_id == orig_id
    assert active[0].state == TrackState.CONFIRMED
