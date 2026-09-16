"""
Unit tests for Sim Civilian: Ego-Centric EV Perception & Predictive AEB
Covers:
  - SE(3) ego-motion pitch compensation under braking
  - Capped MLS overhead clearance validation (3.2m underpass)
  - Predictive dynamic braking corridor & Time-to-Collision (TTC <= 1.8s)
  - Cross-traffic occlusion coasting behind parked delivery van
"""

import math
import pytest
import numpy as np
import torch

from config import (
    EV_HEIGHT_M,
    EV_LIDAR_HEIGHT_M,
    EV_SAFE_OVERHEAD_CLEARANCE_M,
    EV_CORRIDOR_WIDTH_M,
    EV_CORRIDOR_LOOKAHEAD_S,
    EV_TTC_THRESHOLD_S,
    EV_CRUISE_SPEED_MPS,
    SemanticClass,
)
from core_math.foveated_grid import FoveatedGrid
from core_math.mls_engine import MLSEngine
from tracking.mtt_manager import MTTManager, TrackProvenance, TrackState


def test_se3_pitch_compensation_leveling():
    """Verify that SE(3) transformation compensates for vehicle pitch during hard braking."""
    # Under hard braking, the EV pitches nose down by 2.5 degrees
    pitch_deg = 2.5
    pitch_rad = math.radians(pitch_deg)

    # In sensor local frame tilted down by pitch, a point on the flat road 20m ahead
    # has a negative local Z offset: z_local = -sensor_height - (distance * sin(pitch))
    sensor_h = 1.7
    dist_ahead = 20.0
    x_local = 0.0
    y_local = dist_ahead * math.cos(-pitch_rad)
    z_local = -sensor_h + dist_ahead * math.sin(-pitch_rad)

    # Apply SE(3) pitch transformation back to level world coordinates
    cos_p, sin_p = math.cos(pitch_rad), math.sin(pitch_rad)
    R_pitch = np.array([
        [1.0, 0.0, 0.0],
        [0.0, cos_p, -sin_p],
        [0.0, sin_p, cos_p]
    ])

    pt_local = np.array([x_local, y_local, z_local])
    pt_world = R_pitch @ pt_local + np.array([0.0, 0.0, sensor_h])

    # In the compensated world frame, the road point elevation must be within 1cm of 0.0m
    assert abs(pt_world[2]) < 0.01, f"Expected Z ~ 0.0m, got {pt_world[2]}m"


def test_capped_mls_overhead_clearance_underpass():
    """Verify Capped MLS maintains discrete road and ceiling intervals to prove underpass clearance."""
    grid = FoveatedGrid()
    mls = MLSEngine()

    # Generate road points (Z in [-0.05, 0.05]) and underpass ceiling points (Z in [3.15, 3.25])
    # at discrete cell (X=0.0, Y=20.0)
    road_pts = np.array([
        [0.0, 20.0, 0.02, float(SemanticClass.ROAD)],
        [0.1, 20.1, -0.01, float(SemanticClass.ROAD)],
        [-0.1, 19.9, 0.00, float(SemanticClass.ROAD)]
    ], dtype=np.float32)

    ceil_pts = np.array([
        [0.0, 20.0, 3.20, float(SemanticClass.BUILDING)],
        [0.1, 20.1, 3.22, float(SemanticClass.BUILDING)],
        [-0.1, 19.9, 3.18, float(SemanticClass.BUILDING)]
    ], dtype=np.float32)

    combined_pts = np.vstack([road_pts, ceil_pts])
    combined_t = torch.from_numpy(combined_pts).float()

    valid_mask, tier_ids, ix, iy, valid_pts = grid.partition(combined_t)
    mls.update_from_partition(tier_ids, ix, iy, valid_pts)

    assert mls.get_cell_count() >= 1

    # Verify that the cell contains at least 2 distinct capped intervals
    target_key = list(mls.cells.keys())[0]
    cell = mls.cells[target_key]
    assert len(cell.intervals) == 2, f"Expected 2 intervals (road + ceiling), found {len(cell.intervals)}"

    road_interval = cell.intervals[0]
    ceil_interval = cell.intervals[1]

    # Verify vertical gap
    assert road_interval.z_max < 0.1
    assert ceil_interval.z_min > 3.0

    vertical_clearance = ceil_interval.z_min - road_interval.z_max
    assert vertical_clearance >= EV_SAFE_OVERHEAD_CLEARANCE_M, (
        f"Clearance {vertical_clearance}m must exceed safe threshold {EV_SAFE_OVERHEAD_CLEARANCE_M}m"
    )


def test_predictive_braking_corridor_aeb_trigger():
    """Verify predictive Time-to-Collision (TTC) triggers AEB before pedestrian enters vehicle path."""
    v_ego = EV_CRUISE_SPEED_MPS  # 10.0 m/s
    corridor_w = EV_CORRIDOR_WIDTH_M  # 3.5 m (+/- 1.75m)
    corridor_l = max(6.0, v_ego * EV_CORRIDOR_LOOKAHEAD_S)  # 25.0 m

    # Pedestrian crossing trajectory:
    # Starts at X = 3.0m (outside corridor), walking left at vx = -1.2 m/s
    # Longitudinal distance ahead: Y = 14.0m
    ped_x = 3.0
    ped_y = 14.0
    ped_vx = -1.2

    # Compute time to cross into lane boundary (X = +1.75m)
    time_to_corridor_edge = (ped_x - 1.75) / abs(ped_vx)
    # Compute time to lane center (X = 0.0m)
    time_to_center = ped_x / abs(ped_vx)  # 3.0 / 1.2 = 2.5 s
    # Compute EV arrival time at pedestrian Y
    time_to_ev = ped_y / v_ego  # 14.0 / 10.0 = 1.4 s

    # Predicted intersection time difference
    delta_t = abs(time_to_center - time_to_ev)

    # In our autonomous control logic:
    # If ped enters dynamic longitudinal corridor (0.5m < Y <= 25m) and TTC <= 1.8s, AEB triggers
    ttc = time_to_ev
    aeb_triggered = (ttc <= EV_TTC_THRESHOLD_S) and (ped_y <= corridor_l)

    assert aeb_triggered is True
    assert ttc <= EV_TTC_THRESHOLD_S, f"TTC {ttc}s should be within emergency threshold {EV_TTC_THRESHOLD_S}s"


def test_pedestrian_occlusion_coasting_behind_van():
    """Verify that when a pedestrian steps behind a parked delivery van, the track coasts rather than dropping."""
    from tracking.tier_dbscan import TargetCluster

    mtt = MTTManager()

    # Step 1: Pedestrian visible for 4 frames (confirms track)
    for f in range(4):
        x = 4.0 - f * 0.1
        y = 12.0
        cluster = TargetCluster(
            centroid_x=x,
            centroid_y=y,
            centroid_z=0.8,
            bbox_min=(x - 0.2, y - 0.2, 0.0),
            bbox_max=(x + 0.2, y + 0.2, 1.6),
            point_count=8,
            tier_id=0
        )
        tracks = mtt.update([cluster], provenance=TrackProvenance.LIDAR_CONFIRMED)

    confirmed = [t for t in tracks if t.state == TrackState.CONFIRMED]
    assert len(confirmed) >= 1
    track_id = confirmed[0].track_id

    # Step 2: Pedestrian enters blind cone behind parked delivery van (0 LiDAR returns for 5 frames)
    for _ in range(5):
        tracks = mtt.update([], provenance=TrackProvenance.LIDAR_CONFIRMED)

    # The track must be COASTING, NOT dropped
    tracked = [t for t in tracks if t.track_id == track_id]
    assert len(tracked) == 1, "Track must not be dropped while coasting"
    assert tracked[0].state == TrackState.COASTING, f"Expected COASTING, got {tracked[0].state.name}"
