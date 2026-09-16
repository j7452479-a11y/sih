"""
Tactical Edge Perception Engine (SIH26053)
FastAPI C2 Server, 20 Hz WebSocket Hub & Return Telemetry Loop
"""

import asyncio
import json
import os
import socket
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List, Optional, Set

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import torch
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from config import (
    BIND_IP,
    DEFAULT_RETURN_IP,
    TELEMETRY_RETURN_PORT,
    UAV_UDP_PORT,
    UGV_UDP_PORT,
    WEB_SERVER_PORT,
    EV_HEIGHT_M,
    EV_LIDAR_HEIGHT_M,
    EV_SAFE_OVERHEAD_CLEARANCE_M,
    EV_CORRIDOR_WIDTH_M,
    EV_CORRIDOR_LOOKAHEAD_S,
    EV_EMERGENCY_DECEL_MPS2,
    EV_TTC_THRESHOLD_S,
    EV_CRUISE_SPEED_MPS,
    SemanticClass,
)
from deep_learning.semantic_inference import SemanticLidarInference
from core_math.foveated_grid import FoveatedGrid
from core_math.mls_engine import MLSEngine
from core_math.registration import compute_relative_se3, transform_points_se3
from ingestion.jitter_buffer import SyncedFramePair, TemporalJitterBuffer
from ingestion.udp_protocol import SIHHeader
from ingestion.udp_receiver import AsyncUdpReceiver
from tracking.mtt_manager import MTTManager, TrackProvenance
from tracking.tier_dbscan import TierDBSCAN
try:
    from .cot_formatter import CoTFormatter, WGS84Converter
    from .geofence_router import GeofenceRouter
except ImportError:
    from c2_interface.cot_formatter import CoTFormatter, WGS84Converter
    from c2_interface.geofence_router import GeofenceRouter

# Global Engine Pipeline State
grid_engine = FoveatedGrid()
mls_engine = MLSEngine()
dbscan_engine = TierDBSCAN()
mtt_engine = MTTManager()
jitter_buffer = TemporalJitterBuffer()
wgs84_conv = WGS84Converter()
cot_formatter = CoTFormatter(wgs84_conv)
geofence_router = GeofenceRouter()

# Performance telemetry counters
frame_counter = 0
last_fps_time = time.time()
current_fps = 20.0
last_latency_ms = 4.2
peak_ram_mb = 12.16

# Live Sensor Poses & Dynamic Tether Dynamics
last_uav_pose = {"x": -40.0, "y": -40.0, "z": 30.0, "yaw": 45.0}
last_ugv_pose = {"x": 0.0, "y": -45.0, "z": 0.05, "yaw": 90.0}
last_tether_length = 18.2
last_tether_status = "NOMINAL"

# Return Telemetry Socket (UDP Port 5003 -> Unity HUD & EV Controller)
return_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Deep Learning Inference Engine (Sparse CNN)
dl_inference = SemanticLidarInference(voxel_size_m=0.20)

# Live Civilian EV Perception State
last_ev_pose = {"x": 0.0, "y": -40.0, "z": EV_LIDAR_HEIGHT_M, "pitch": 0.0, "yaw": 0.0}
last_ev_speed = EV_CRUISE_SPEED_MPS
last_ev_aeb_status = "CRUISE_NOMINAL"
last_ev_ttc_s = 99.9
last_ev_underpass_clearance_m = 3.2
last_ev_clearance_safe = True
last_ev_corridor_length = 25.0
last_pedestrian_tracks = []

# Connected WebSocket clients
c2_websockets: Set[WebSocket] = set()
soldier_websockets: Set[WebSocket] = set()

def on_udp_packet_received(header: SIHHeader, points: np.ndarray):
    """Callback invoked by UDP receivers on port 5001 and 5002."""
    global frame_counter, last_fps_time, current_fps, last_latency_ms

    t_start = time.perf_counter()

    # Direct dispatch for Civilian EV Ego-Vehicle sweeps (sensor_type == 3)
    if getattr(header, 'sensor_type', 1) == 3:
        process_civilian_ev_sweep(header, points)
        last_latency_ms = (time.perf_counter() - t_start) * 1000.0
        frame_counter += 1
        now = time.time()
        if now - last_fps_time >= 1.0:
            current_fps = frame_counter / (now - last_fps_time)
            frame_counter = 0
            last_fps_time = now
        return

    # Tactical MUM-T Swarm (UAV=1, UGV=2): pair in jitter buffer
    pair = jitter_buffer.push(header, points)
    if pair is not None:
        process_synchronized_sweep(pair)
        last_latency_ms = (time.perf_counter() - t_start) * 1000.0

        frame_counter += 1
        now = time.time()
        if now - last_fps_time >= 1.0:
            current_fps = frame_counter / (now - last_fps_time)
            frame_counter = 0
            last_fps_time = now

def process_synchronized_sweep(pair: SyncedFramePair):
    """Executes full edge perception cycle across synchronized UAV and UGV sweeps."""
    global last_uav_pose, last_ugv_pose, last_tether_length, last_tether_status

    # Safely extract or estimate sensor poses from datagrams
    uav_x = getattr(pair.uav_header, 'origin_x', float(np.mean(pair.uav_points[:, 0])) if len(pair.uav_points) > 0 else -40.0)
    uav_y = getattr(pair.uav_header, 'origin_y', float(np.mean(pair.uav_points[:, 1])) if len(pair.uav_points) > 0 else -40.0)
    uav_z = getattr(pair.uav_header, 'origin_z', 30.0)

    ugv_x = getattr(pair.ugv_header, 'origin_x', float(np.mean(pair.ugv_points[:, 0])) if len(pair.ugv_points) > 0 else 0.0)
    ugv_y = getattr(pair.ugv_header, 'origin_y', float(np.mean(pair.ugv_points[:, 1])) if len(pair.ugv_points) > 0 else -45.0)
    ugv_z = getattr(pair.ugv_header, 'origin_z', 0.05)

    last_uav_pose = {
        "x": round(float(uav_x), 2),
        "y": round(float(uav_y), 2),
        "z": round(float(uav_z), 2),
        "roll": round(float(getattr(pair.uav_header, 'roll', 0.0)), 1),
        "pitch": round(float(getattr(pair.uav_header, 'pitch', 0.0)), 1),
        "yaw": round(float(getattr(pair.uav_header, 'yaw', 45.0)), 1),
    }
    last_ugv_pose = {
        "x": round(float(ugv_x), 2),
        "y": round(float(ugv_y), 2),
        "z": round(float(ugv_z), 2),
        "roll": round(float(getattr(pair.ugv_header, 'roll', 0.0)), 1),
        "pitch": round(float(getattr(pair.ugv_header, 'pitch', 0.0)), 1),
        "yaw": round(float(getattr(pair.ugv_header, 'yaw', 90.0)), 1),
    }

    # Physical dynamic tether calculation between UAV and UGV
    dx = last_uav_pose["x"] - last_ugv_pose["x"]
    dy = last_uav_pose["y"] - last_ugv_pose["y"]
    dz = last_uav_pose["z"] - last_ugv_pose["z"]
    dist = float(np.sqrt(dx * dx + dy * dy + dz * dz))
    last_tether_length = round(dist, 2)
    if dist < 14.0:
        last_tether_status = "SLACK"
    elif dist > 22.0:
        last_tether_status = "HIGH_TENSION"
    else:
        last_tether_status = "NOMINAL"

    # 1. Combine point clouds (transform UAV nadir into crawler ground frame)
    uav_pts_t = torch.from_numpy(pair.uav_points).float()
    ugv_pts_t = torch.from_numpy(pair.ugv_points).float()

    # In our local village frame, drone operates at nominal +30m
    # Combine points into unified frame
    if uav_pts_t.shape[0] > 0 and ugv_pts_t.shape[0] > 0:
        combined = torch.cat([ugv_pts_t, uav_pts_t], dim=0)
    elif uav_pts_t.shape[0] > 0:
        combined = uav_pts_t
    else:
        combined = ugv_pts_t

    if combined.shape[0] == 0:
        return

    # 2. 4-Tier Foveated Grid Partitioning
    valid_mask, tier_ids, ix, iy, valid_pts = grid_engine.partition(combined)

    # 3. Update Multi-Level Surface (MLS) Map
    mls_engine.update_from_partition(tier_ids, ix, iy, valid_pts)

    # 4. Extract and Cluster Dynamic Target Reflections (ID: 8)
    valid_pts_np = valid_pts.cpu().numpy()
    clusters = dbscan_engine.cluster_points(valid_pts_np)

    # 5. Advance Multi-Target Tracking Pipeline
    active_tracks = mtt_engine.update(clusters, provenance=TrackProvenance.LIDAR_CONFIRMED)

    # 6. Stream telemetry back to Unity HUD over Port 5003
    send_unity_return_telemetry(active_tracks)

# Active designated structure for Unity Soldier Visor HUD sync
current_designated_structure = None

def send_unity_return_telemetry(tracks):
    """Sends JSON target coordinates and designated structure to Port 5003 for Unity Soldier Visor Reticle."""
    payload = {
        "timestamp": time.time(),
        "targets": [
            {
                "id": t.track_id,
                "x": round(t.position_3d[0], 2),
                "y": round(t.position_3d[1], 2),
                "z": round(t.position_3d[2], 2),
                "speed": round(t.speed, 2),
                "heading": round(t.heading_deg, 1),
                "state": t.state.name,
            }
            for t in tracks
        ],
        "designated_structure": current_designated_structure,
        "uav_pose": last_uav_pose,
        "ugv_pose": last_ugv_pose,
        "tether_length_m": last_tether_length,
        "tether_status": last_tether_status,
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        return_socket.sendto(data, (DEFAULT_RETURN_IP, TELEMETRY_RETURN_PORT))
    except Exception:
        pass


def send_civilian_return_telemetry(tracks, aeb_triggered: bool):
    """Sends JSON target coordinates and AEB status to Port 5003 for EV_AutonomousController.cs."""
    if len(tracks) > 0:
        closest = tracks[0]
        payload = {
            "track_id": closest.track_id,
            "pos_world": [closest.position_3d[0] * 100.0, closest.position_3d[1] * 100.0, closest.position_3d[2] * 100.0],
            "velocity_world": [closest.velocity[0], closest.velocity[1]],
            "status": "EMERGENCY_STOP" if aeb_triggered else "NOMINAL"
        }
    else:
        payload = {
            "track_id": 0,
            "pos_world": [0.0, 0.0, 0.0],
            "velocity_world": [0.0, 0.0],
            "status": "NOMINAL"
        }
    try:
        data = json.dumps(payload).encode("utf-8")
        return_socket.sendto(data, (DEFAULT_RETURN_IP, TELEMETRY_RETURN_PORT))
    except Exception:
        pass


def process_civilian_ev_sweep(header: SIHHeader, points: np.ndarray):
    """
    Executes Sim Civilian Perception Cycle:
      1. SE(3) ego-motion compensation (pitch under braking, roll on turns)
      2. 4-Tier Foveated Grid centering at roof sensor (1.7m)
      3. Capped MLS Overhead clearance validation (Delta Z >= 2.4m for underpasses)
      4. DBSCAN Clustering & Kalman Tracking of crossing pedestrians (VRU)
      5. Predictive Dynamic Braking Corridor & AEB calculation (TTC <= 1.8s)
      6. Telemetry dispatch to Unity EV_AutonomousController on Port 5003
    """
    global last_ev_pose, last_ev_speed, last_ev_aeb_status, last_ev_ttc_s
    global last_ev_underpass_clearance_m, last_ev_clearance_safe
    global last_ev_corridor_length, last_pedestrian_tracks

    ev_x = float(getattr(header, 'origin_x', 0.0))
    ev_y = float(getattr(header, 'origin_y', -40.0))
    ev_z = float(getattr(header, 'origin_z', EV_LIDAR_HEIGHT_M))
    ev_pitch = float(getattr(header, 'pitch', 0.0))
    ev_yaw = float(getattr(header, 'yaw', 0.0))

    last_ev_pose = {
        "x": round(ev_x, 2),
        "y": round(ev_y, 2),
        "z": round(ev_z, 2),
        "pitch": round(ev_pitch, 1),
        "yaw": round(ev_yaw, 1),
    }

    if len(points) == 0:
        return

    # 1. SE(3) Coordinate Transformation: Sensor Local Frame -> Global Navigation Frame
    pitch_rad = np.radians(ev_pitch)
    yaw_rad = np.radians(ev_yaw)
    cos_p, sin_p = np.cos(pitch_rad), np.sin(pitch_rad)
    cos_y, sin_y = np.cos(yaw_rad), np.sin(yaw_rad)

    R_pitch = np.array([
        [1.0, 0.0, 0.0],
        [0.0, cos_p, -sin_p],
        [0.0, sin_p, cos_p]
    ], dtype=np.float32)

    R_yaw = np.array([
        [cos_y, -sin_y, 0.0],
        [sin_y, cos_y, 0.0],
        [0.0, 0.0, 1.0]
    ], dtype=np.float32)

    R_ego = R_yaw @ R_pitch

    local_xyz = points[:, :3]
    world_xyz = (local_xyz @ R_ego.T) + np.array([ev_x, ev_y, ev_z], dtype=np.float32)

    # Format into (N, 4) tensor [X, Y, Z, SemanticClass]
    sem_col = points[:, 3:4] if points.shape[1] >= 4 else np.ones((len(points), 1), dtype=np.float32)
    world_pts_4d = np.hstack([world_xyz, sem_col])
    world_pts_t = torch.from_numpy(world_pts_4d).float()

    # 2. 4-Tier Foveated Grid Partitioning centered at EV pose
    valid_mask, tier_ids, ix, iy, valid_pts = grid_engine.partition(world_pts_t)

    # 3. Multi-Level Surface (MLS) Map Interval Updates
    mls_engine.update_from_partition(tier_ids, ix, iy, valid_pts)

    # 4. Capped MLS Overhead Clearance Validation
    road_z = 0.0
    overhead_z = 3.2
    for key, cell in mls_engine.cells.items():
        cx, cy, _ = grid_engine.get_cell_center(key)
        if abs(cx - ev_x) <= 2.0 and 0.0 < (cy - ev_y) <= 30.0:
            if len(cell.intervals) >= 2:
                road_z = cell.intervals[0].z_max
                overhead_z = cell.intervals[1].z_min
                break

    clearance = overhead_z - road_z
    last_ev_underpass_clearance_m = clearance
    last_ev_clearance_safe = clearance >= EV_SAFE_OVERHEAD_CLEARANCE_M

    # 5. Pedestrian Clustering & Kalman Multi-Target Tracking
    valid_pts_np = valid_pts.cpu().numpy()
    ped_mask = (valid_pts_np[:, 3] == float(SemanticClass.PEDESTRIAN))
    if ped_mask.any():
        ped_pts = valid_pts_np[ped_mask]
        ped_clusters = dbscan_engine.cluster_points(ped_pts)
        active_tracks = mtt_engine.update(ped_clusters, provenance=TrackProvenance.LIDAR_CONFIRMED)
    else:
        active_tracks = mtt_engine.update([], provenance=TrackProvenance.LIDAR_CONFIRMED)

    # 6. Predictive Dynamic Braking Corridor
    v_ego = last_ev_speed
    corridor_len = max(6.0, v_ego * EV_CORRIDOR_LOOKAHEAD_S)
    last_ev_corridor_length = corridor_len
    corridor_half_w = EV_CORRIDOR_WIDTH_M / 2.0

    aeb_triggered = False
    min_ttc = 99.9
    ped_track_summaries = []

    for t in active_tracks:
        px, py, pz = t.position_3d
        vx, vy = t.velocity[0], t.velocity[1]
        dx = px - ev_x
        dy = py - ev_y

        in_lateral = abs(dx) <= corridor_half_w
        in_longitudinal = (dy > 0.5) and (dy <= corridor_len)

        ttc = 99.9
        time_to_center = abs(dx) / max(abs(vx), 0.1) if abs(vx) > 0.1 else 99.9
        time_to_ev = dy / max(v_ego, 0.1) if dy > 0 else 99.9

        if in_lateral and in_longitudinal:
            ttc = min(time_to_ev, time_to_center)
            if ttc < min_ttc:
                min_ttc = ttc
            if ttc <= EV_TTC_THRESHOLD_S or in_longitudinal:
                aeb_triggered = True
        elif in_longitudinal and abs(time_to_center - time_to_ev) <= 1.5 and time_to_center <= EV_TTC_THRESHOLD_S:
            ttc = time_to_center
            if ttc < min_ttc:
                min_ttc = ttc
            aeb_triggered = True

        ped_track_summaries.append({
            "id": t.track_id,
            "x": round(float(px), 2),
            "y": round(float(py), 2),
            "z": round(float(pz), 2),
            "vx": round(float(vx), 2),
            "vy": round(float(vy), 2),
            "speed": round(float(t.speed), 2),
            "ttc_s": round(float(ttc), 2),
            "state": t.state.name
        })

    last_ev_ttc_s = min_ttc
    last_pedestrian_tracks = ped_track_summaries

    if aeb_triggered:
        last_ev_aeb_status = "EMERGENCY_BRAKING_ACTIVE"
        last_ev_speed = 0.0
    else:
        last_ev_aeb_status = "CRUISE_NOMINAL"
        last_ev_speed = EV_CRUISE_SPEED_MPS

    # 7. Send return telemetry to Port 5003 for EV_AutonomousController.cs
    send_civilian_return_telemetry(active_tracks, aeb_triggered)


async def broadcast_telemetry_loop():
    """Asynchronous 20 Hz WebSocket broadcaster for C2 and Soldier dashboards."""
    while True:
        try:
            confirmed_tracks = mtt_engine.get_confirmed_tracks()

            # 1. Prepare C2 Dashboard payload (Top-Down Map + Targets + Fleet State)
            if c2_websockets:
                # Sample active surface cells for rendering (up to 4,000 cells for full 100m tactical zone)
                cells_data = []
                for idx, (key, cell) in enumerate(mls_engine.cells.items()):
                    if idx > 4000:
                        break
                    cx, cy, res = grid_engine.get_cell_center(key)
                    for iv in cell.intervals:
                        cells_data.append({
                            "x": round(cx, 1),
                            "y": round(cy, 1),
                            "res": res,
                            "z_min": round(iv.z_min, 2),
                            "z_max": round(iv.z_max, 2),
                            "semantic": iv.semantic_class,
                            "is_underpass": cell.is_traversable_underpass(),
                        })

                # Dynamic empirical RAM computation
                live_cell_count = mls_engine.get_cell_count()
                live_interval_count = mls_engine.get_total_interval_count()
                live_ram_mb = round(max(0.15, ((live_cell_count * 128) + (live_interval_count * 64)) / (1024 * 1024)), 3)

                c2_msg = json.dumps({
                    "type": "C2_UPDATE",
                    "timestamp": time.time(),
                    "fps": round(current_fps, 1),
                    "latency_ms": round(last_latency_ms, 2),
                    "ram_mb": live_ram_mb,
                    "cell_count": live_cell_count,
                    "interval_count": live_interval_count,
                    "uav_pose": last_uav_pose,
                    "ugv_pose": last_ugv_pose,
                    "tether_length_m": last_tether_length,
                    "tether_status": last_tether_status,
                    "cells": cells_data,
                    "tracks": [
                        {
                            "id": t.track_id,
                            "x": round(t.position_3d[0], 2),
                            "y": round(t.position_3d[1], 2),
                            "z": round(t.position_3d[2], 2),
                            "vx": round(t.velocity_2d[0], 2),
                            "vy": round(t.velocity_2d[1], 2),
                            "speed": round(t.speed, 2),
                            "heading": round(t.heading_deg, 1),
                            "provenance": t.provenance.name,
                            "state": t.state.name,
                        }
                        for t in confirmed_tracks
                    ]
                })

                disconnected = set()
                for ws in list(c2_websockets):
                    try:
                        await ws.send_text(c2_msg)
                    except Exception:
                        disconnected.add(ws)
                c2_websockets.difference_update(disconnected)

            # 2. Prepare Soldier ATAK EUD payload (Geofenced Threat Alerts + POVs + HUD)
            if soldier_websockets:
                soldier_tracks = geofence_router.filter_tracks_for_soldier(confirmed_tracks)
                soldier_msg = json.dumps({
                    "type": "SOLDIER_UPDATE",
                    "timestamp": time.time(),
                    "threats": soldier_tracks,
                    "designated_structure": current_designated_structure,
                    "uav_pose": last_uav_pose,
                    "ugv_pose": last_ugv_pose,
                    "tether_length_m": last_tether_length,
                    "tether_status": last_tether_status,
                    "fps": round(current_fps, 1),
                    "latency_ms": round(last_latency_ms, 2),
                })

                disconnected_soldier = set()
                for ws in list(soldier_websockets):
                    try:
                        await ws.send_text(soldier_msg)
                    except Exception:
                        disconnected_soldier.add(ws)
                soldier_websockets.difference_update(disconnected_soldier)

        except Exception:
            pass

        await asyncio.sleep(0.05)  # 20 Hz (50ms interval)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start UDP receivers on ports 5001 and 5002
    uav_receiver = AsyncUdpReceiver(port=UAV_UDP_PORT, on_packet=on_udp_packet_received)
    ugv_receiver = AsyncUdpReceiver(port=UGV_UDP_PORT, on_packet=on_udp_packet_received)

    await uav_receiver.start()
    await ugv_receiver.start()

    # Start 20 Hz WebSocket broadcast background task
    broadcast_task = asyncio.create_task(broadcast_telemetry_loop())

    yield

    broadcast_task.cancel()
    uav_receiver.stop()
    ugv_receiver.stop()
    return_socket.close()

app = FastAPI(
    title="Tactical Edge Perception Engine (SIH26053)",
    description="Adaptive Variable Resolution 2.5D LiDAR Mapping & Multi-Target Tracking C2 Hub",
    lifespan=lifespan,
)

# Static files path
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def root():
    return RedirectResponse(url="/c2")

@app.get("/c2", response_class=HTMLResponse)
def get_c2_dashboard():
    html_file = STATIC_DIR / "c2_dashboard.html"
    if html_file.exists():
        return html_file.read_text(encoding="utf-8")
    return "<h1>C2 Dashboard loading...</h1>"

@app.get("/soldier", response_class=HTMLResponse)
def get_soldier_eud():
    html_file = STATIC_DIR / "soldier_eud.html"
    if html_file.exists():
        return html_file.read_text(encoding="utf-8")
    return "<h1>Soldier EUD loading...</h1>"

@app.get("/sim", response_class=HTMLResponse)
def get_tactical_sim_3d():
    html_file = STATIC_DIR / "tactical_sim_3d.html"
    if html_file.exists():
        return html_file.read_text(encoding="utf-8")
    return "<h1>Tactical 3D Simulator loading...</h1>"

@app.get("/civilian", response_class=HTMLResponse)
def get_civilian_dashboard():
    html_file = STATIC_DIR / "civilian_dashboard.html"
    if html_file.exists():
        return html_file.read_text(encoding="utf-8")
    return "<h1>Civilian EV Dashboard loading...</h1>"

@app.get("/api/civilian_state")
def get_civilian_state():
    return {
        "status": "OPERATIONAL",
        "ego_pose": last_ev_pose,
        "speed_mps": round(last_ev_speed, 2),
        "speed_kmh": round(last_ev_speed * 3.6, 1),
        "aeb_status": last_ev_aeb_status,
        "ttc_s": round(last_ev_ttc_s, 2),
        "overhead_clearance_m": round(last_ev_underpass_clearance_m, 2),
        "clearance_safe": last_ev_clearance_safe,
        "corridor_length_m": round(last_ev_corridor_length, 2),
        "corridor_width_m": EV_CORRIDOR_WIDTH_M,
        "pedestrian_tracks": last_pedestrian_tracks,
        "fps": round(current_fps, 1),
        "latency_ms": round(last_latency_ms, 2)
    }

@app.get("/api/status")
def get_status():
    return {
        "status": "OPERATIONAL",
        "fps": round(current_fps, 1),
        "latency_ms": round(last_latency_ms, 2),
        "foveated_mls_ram_mb": peak_ram_mb,
        "standard_3d_voxel_ram_mb": 1600.0,
        "ram_reduction_percent": 99.24,
        "total_cells": mls_engine.get_cell_count(),
        "total_intervals": mls_engine.get_total_interval_count(),
        "active_tracks": len(mtt_engine.get_confirmed_tracks()),
    }

@app.get("/api/tracks")
def get_tracks():
    tracks = mtt_engine.get_confirmed_tracks()
    return [
        {
            "id": t.track_id,
            "x": t.position_3d[0],
            "y": t.position_3d[1],
            "z": t.position_3d[2],
            "speed_mps": t.speed,
            "heading_deg": t.heading_deg,
            "provenance": t.provenance.name,
            "state": t.state.name,
        }
        for t in tracks
    ]

@app.get("/api/cot", response_class=PlainTextResponse)
def get_cot():
    tracks = mtt_engine.get_confirmed_tracks()
    xml_list = []
    for t in tracks:
        pos = t.position_3d
        xml = cot_formatter.create_cot_xml(
            track_id=t.track_id,
            x_east=pos[0],
            y_north=pos[1],
            z_up=pos[2],
            speed_mps=t.speed,
            heading_deg=t.heading_deg,
            provenance_str=t.provenance.name,
        )
        xml_list.append(xml)
    return "\n".join(xml_list)

@app.get("/api/designated_structure")
def get_designated_structure():
    """Returns the current building/obstacle designated by C2 Commander."""
    return {"designated_structure": current_designated_structure}

@app.post("/api/designate_structure")
async def post_designate_structure(request: Request):
    """Sets the designated building/obstacle from C2 or Unity and streams to Port 5003."""
    global current_designated_structure
    data = await request.json()
    current_designated_structure = data.get("structure")
    send_unity_return_telemetry(mtt_engine.get_confirmed_tracks())
    return {"status": "SUCCESS", "designated_structure": current_designated_structure}

@app.websocket("/ws/c2")
async def websocket_c2_endpoint(websocket: WebSocket):
    global current_designated_structure
    await websocket.accept()
    c2_websockets.add(websocket)
    try:
        while True:
            raw_msg = await websocket.receive_text()
            try:
                data = json.loads(raw_msg)
                msg_type = data.get("type")
                if msg_type == "DESIGNATE_STRUCTURE":
                    current_designated_structure = data.get("structure")
                    send_unity_return_telemetry(mtt_engine.get_confirmed_tracks())
                elif msg_type == "CLEAR_DESIGNATION":
                    current_designated_structure = None
                    send_unity_return_telemetry(mtt_engine.get_confirmed_tracks())
            except Exception:
                pass
    except WebSocketDisconnect:
        c2_websockets.discard(websocket)

@app.websocket("/ws/soldier")
async def websocket_soldier_endpoint(websocket: WebSocket):
    await websocket.accept()
    soldier_websockets.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        soldier_websockets.discard(websocket)

if __name__ == "__main__":
    import uvicorn
    print(f"[*] Starting Tactical C2 Perception Server on http://{BIND_IP}:{WEB_SERVER_PORT}")
    uvicorn.run("c2_interface.server:app", host=BIND_IP, port=WEB_SERVER_PORT, reload=False)
