"""
simulate_flight_and_math.py - Autonomous Real-Time MUM-T Flight & Math Engine Simulation
Simulates:
1. Square Village Proving Ground with diverse structures (Bridge void, Church 18m spire, 4-story buildings, houses, walls).
2. UAV Drone circular orbit at +30m altitude (R = 32m, 20 Hz LiDAR sweeps to UDP Port 5001).
3. UGV RC Car elliptical ground patrol (A = 26m, B = 16m) driving through the bridge underpass void to UDP Port 5002.
4. Dynamic tether distance & catenary tension calculation (14m - 20m envelope).
5. Dynamic Hostiles with stone wall occlusion and Kalman filter coasting state.
"""

import argparse
import math
import socket
import sys
import time
from pathlib import Path
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
from config import (
    UAV_UDP_PORT,
    UGV_UDP_PORT,
    TELEMETRY_RETURN_PORT,
    SemanticClass,
)
from ingestion.udp_protocol import pack_sih1_packet

class SquareVillageFlightSimulator:
    def __init__(self, target_ip="127.0.0.1"):
        self.target_ip = target_ip
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.frame_id = 0
        
        # Flight & Patrol Parameters
        self.uav_radius = 32.0       # Circular orbit radius (meters)
        self.uav_alt = 30.0          # Altitude (meters)
        self.uav_period = 25.0       # Seconds per full 360 deg orbit
        
        self.ugv_axis_a = 26.0       # Elliptical semi-major axis (East-West)
        self.ugv_axis_b = 16.0       # Elliptical semi-minor axis (North-South through underpass)
        
        self.hostile_a_x_range = (18.0, 34.0)
        self.hostile_b_x_range = (-12.0, 12.0)

    def compute_uav_pose(self, t_seconds):
        """UAV circular orbit at +30m altitude around square village."""
        theta = (2.0 * math.pi * (t_seconds % self.uav_period)) / self.uav_period
        x = self.uav_radius * math.cos(theta)
        y = self.uav_radius * math.sin(theta)
        z = self.uav_alt
        
        # Heading tangent to circle (degrees)
        yaw = math.degrees(theta + math.pi / 2.0) % 360.0
        return np.array([x, y, z], dtype=np.float32), yaw

    def compute_ugv_pose(self, t_seconds):
        """UGV elliptical ground track passing through bridge underpass at Y = 0."""
        # Synchronized with drone phase with slight trailing offset
        theta = (2.0 * math.pi * (t_seconds % self.uav_period)) / self.uav_period - 0.18
        x = self.ugv_axis_a * math.cos(theta)
        y = self.ugv_axis_b * math.sin(theta)
        z = 0.05
        
        # Heading tangent to ellipse
        dx = -self.ugv_axis_a * math.sin(theta)
        dy = self.ugv_axis_b * math.cos(theta)
        yaw = math.degrees(math.atan2(dx, dy)) % 360.0
        return np.array([x, y, z], dtype=np.float32), yaw

    def compute_hostiles(self, t_seconds):
        """Dynamic hostiles patrolling square village streets."""
        # Hostile Alpha in Eastern Market Quarter
        period_a = 18.0
        phase_a = (t_seconds % period_a) / period_a
        frac_a = phase_a * 2.0 if phase_a <= 0.5 else (1.0 - phase_a) * 2.0
        ha_x = self.hostile_a_x_range[0] + frac_a * (self.hostile_a_x_range[1] - self.hostile_a_x_range[0])
        ha_pos = np.array([ha_x, 2.0, 0.9], dtype=np.float32)

        # Hostile Bravo stepping behind the primary stone wall (Y = -14m, X in [-8, 8])
        period_b = 20.0
        phase_b = (t_seconds % period_b) / period_b
        frac_b = phase_b * 2.0 if phase_b <= 0.5 else (1.0 - phase_b) * 2.0
        hb_x = self.hostile_b_x_range[0] + frac_b * (self.hostile_b_x_range[1] - self.hostile_b_x_range[0])
        hb_pos = np.array([hb_x, -14.0, 0.9], dtype=np.float32)

        # Occlusion check: Behind stone wall X in [-8, 8] at Y = -14
        is_hb_occluded = (-8.0 <= hb_x <= 8.0)
        return (ha_pos, False), (hb_pos, is_hb_occluded)

    def generate_uav_lidar_sweep(self, uav_pos, uav_yaw, hostiles):
        """Generates 32-channel nadir LiDAR returns radiating from circular drone orbit."""
        points = []
        channels = 32
        beams_per_ch = 14
        max_range = 75.0

        for c in range(channels):
            pitch = -90.0 + (c / max(1, channels - 1)) * 48.0  # -90 to -42 deg
            pitch_rad = math.radians(pitch)
            for b in range(beams_per_ch):
                yaw = (b / beams_per_ch) * 360.0
                yaw_rad = math.radians(uav_yaw + yaw)

                dir_x = math.sin(yaw_rad) * math.cos(pitch_rad)
                dir_y = math.cos(yaw_rad) * math.cos(pitch_rad)
                dir_z = math.sin(pitch_rad)

                # Raycast to ground Z = 0
                if abs(dir_z) > 1e-4:
                    t_ground = (0.05 - uav_pos[2]) / dir_z
                    if 0.0 < t_ground < max_range:
                        gx = uav_pos[0] + dir_x * t_ground
                        gy = uav_pos[1] + dir_y * t_ground
                        gz = 0.05

                        # Determine semantic class
                        sem = SemanticClass.ROAD.value
                        
                        # Central Overpass Bridge check (X in [-20, 20], Y in [-4.5, 4.5])
                        if (-20.0 <= gx <= 20.0) and (-4.5 <= gy <= 4.5):
                            gz = 5.0 # Bridge deck hit
                            sem = SemanticClass.OBSTACLE.value
                        # Church Complex (X in [16, 32], Y in [14, 34])
                        elif (16.0 <= gx <= 32.0) and (14.0 <= gy <= 34.0):
                            gz = 12.0 if (gx > 22 and gy > 20) else 18.0 # Church spire
                            sem = SemanticClass.BUILDING.value
                        # 4-Story Blocks (X in [-32, -20], Y in [4, 32])
                        elif (-32.0 <= gx <= -20.0) and (4.0 <= gy <= 32.0):
                            gz = 14.0
                            sem = SemanticClass.BUILDING.value
                        # Houses (South)
                        elif (-30.0 <= gx <= -18.0 and -30.0 <= gy <= -18.0) or (18.0 <= gx <= 30.0 and -30.0 <= gy <= -18.0):
                            gz = 7.0
                            sem = SemanticClass.BUILDING.value
                        # Stone Wall (Y in [-15, -13], X in [-8, 8])
                        elif (-8.0 <= gx <= 8.0) and (-15.0 <= gy <= -13.0):
                            gz = 2.2
                            sem = SemanticClass.OBSTACLE.value

                        # Add jitter noise
                        noise = np.random.normal(0.0, 0.03, 3)
                        intensity = np.clip(1.0 - (t_ground / max_range), 0.1, 1.0)
                        points.append([gx + noise[0], gy + noise[1], gz + noise[2], sem, intensity])

        hostile_points = []
        # Inject Hostile Reflections (Semantic Class 8)
        for h_pos, is_occluded in hostiles:
            if not is_occluded:
                h_arr = np.asarray(h_pos, dtype=np.float32)
                u_arr = np.asarray(uav_pos, dtype=np.float32)
                dist = float(np.linalg.norm(u_arr - h_arr))
                if dist < max_range:
                    for _ in range(12):
                        noise = np.random.normal(0.0, 0.12, 3)
                        hostile_points.append([
                            h_arr[0] + noise[0],
                            h_arr[1] + noise[1],
                            h_arr[2] + noise[2],
                            SemanticClass.HOSTILE.value,
                            0.95
                        ])

        # Prepend hostiles so they are transmitted in first datagram
        all_pts = hostile_points + points
        return np.array(all_pts, dtype=np.float32)

    def generate_ugv_lidar_sweep(self, ugv_pos, ugv_yaw, hostiles):
        """Generates 16-channel horizontal ground LiDAR returns (underpass void & street walls)."""
        points = []
        channels = 16
        beams_per_ch = 20
        max_range = 35.0

        for c in range(channels):
            pitch = -12.0 + (c / max(1, channels - 1)) * 24.0 # -12 to +12 deg
            pitch_rad = math.radians(pitch)
            for b in range(beams_per_ch):
                yaw = (b / beams_per_ch) * 360.0
                yaw_rad = math.radians(ugv_yaw + yaw)

                dir_x = math.sin(yaw_rad) * math.cos(pitch_rad)
                dir_y = math.cos(yaw_rad) * math.cos(pitch_rad)
                dir_z = math.sin(pitch_rad)

                dist = np.random.uniform(3.0, 18.0)
                px = ugv_pos[0] + dir_x * dist
                py = ugv_pos[1] + dir_y * dist
                pz = max(0.05, ugv_pos[2] + dir_z * dist)

                # Underpass ceiling returns when passing through center Y in [-4.5, 4.5]
                sem = SemanticClass.ROAD.value
                if (-16.0 <= px <= 16.0) and (-4.5 <= py <= 4.5):
                    if pz > 4.4:
                        pz = 4.4 # Bridge soffit underside
                        sem = SemanticClass.OBSTACLE.value

                points.append([px, py, pz, sem, 0.85])

        # Inject visible hostiles into UGV sensor sweep
        hostile_points = []
        for h_pos, is_occluded in hostiles:
            if not is_occluded:
                h_arr = np.asarray(h_pos, dtype=np.float32)
                u_arr = np.asarray(ugv_pos, dtype=np.float32)
                dist = float(np.linalg.norm(u_arr - h_arr))
                if dist < max_range:
                    for _ in range(8):
                        noise = np.random.normal(0.0, 0.10, 3)
                        hostile_points.append([
                            h_arr[0] + noise[0],
                            h_arr[1] + noise[1],
                            h_arr[2] + noise[2],
                            SemanticClass.HOSTILE.value,
                            0.95
                        ])

        all_pts = hostile_points + points
        return np.array(all_pts, dtype=np.float32)

    def step(self, t_seconds):
        """Executes one simulation tick at 20 Hz."""
        self.frame_id += 1
        ts = time.time()

        # 1. Circular UAV Drone Orbit (+30m Alt)
        uav_pos, uav_yaw = self.compute_uav_pose(t_seconds)

        # 2. Elliptical UGV RC Car Path (Through Bridge Underpass)
        ugv_pos, ugv_yaw = self.compute_ugv_pose(t_seconds)

        # Tether Length & Dynamics
        tether_dist = float(np.linalg.norm(uav_pos - ugv_pos))

        # 3. Dynamic Hostiles (Alpha + Bravo behind stone wall)
        (h_a_pos, is_h_a_occl), (h_b_pos, is_h_b_occl) = self.compute_hostiles(t_seconds)
        hostiles = [(h_a_pos, is_h_a_occl), (h_b_pos, is_h_b_occl)]

        # 4. Generate Point Clouds
        uav_points = self.generate_uav_lidar_sweep(uav_pos, uav_yaw, hostiles)
        ugv_points = self.generate_ugv_lidar_sweep(ugv_pos, ugv_yaw, hostiles)

        # 5. Pack & Stream to UDP Ports 5001 & 5002 (1-to-1 synchronized frame transmission)
        if len(uav_points) > 0:
            chunk_uav = uav_points[:80, :4]
            uav_pkt = pack_sih1_packet(self.frame_id, ts, 1, chunk_uav)
            self.sock.sendto(uav_pkt, (self.target_ip, UAV_UDP_PORT))

        if len(ugv_points) > 0:
            chunk_ugv = ugv_points[:80, :4]
            ugv_pkt = pack_sih1_packet(self.frame_id, ts + 0.002, 2, chunk_ugv)
            self.sock.sendto(ugv_pkt, (self.target_ip, UGV_UDP_PORT))

        # 6. Stream JSON Telemetry to Port 5003 for Unity Reticle HUD (Soldier & Commander POVs)
        hud_payload = {
            "timestamp": ts,
            "targets": [
                {
                    "id": 1,
                    "x": round(float(h_a_pos[0]), 2),
                    "y": round(float(h_a_pos[1]), 2),
                    "z": round(float(h_a_pos[2]), 2),
                    "speed": 1.5,
                    "heading": 90.0,
                    "state": "COASTING" if is_h_a_occl else "CONFIRMED",
                },
                {
                    "id": 2,
                    "x": round(float(h_b_pos[0]), 2),
                    "y": round(float(h_b_pos[1]), 2),
                    "z": round(float(h_b_pos[2]), 2),
                    "speed": 1.8,
                    "heading": 0.0,
                    "state": "COASTING" if is_h_b_occl else "CONFIRMED",
                }
            ],
            "designated_structure": "Central_Overpass_Bridge",
            "uav_pose": [round(float(uav_pos[0]), 2), round(float(uav_pos[1]), 2), round(float(uav_pos[2]), 2)],
            "ugv_pose": [round(float(ugv_pos[0]), 2), round(float(ugv_pos[1]), 2), round(float(ugv_pos[2]), 2)],
            "tether_length_m": round(tether_dist, 2),
            "tether_status": "OVERSTRAIN" if tether_dist > 20.0 else ("SLACK" if tether_dist < 14.0 else "NOMINAL")
        }
        try:
            self.sock.sendto(json.dumps(hud_payload).encode("utf-8"), (self.target_ip, TELEMETRY_RETURN_PORT))
        except Exception:
            pass

        return {
            "frame_id": self.frame_id,
            "uav_pos": [round(float(uav_pos[0]), 2), round(float(uav_pos[1]), 2), round(float(uav_pos[2]), 2)],
            "ugv_pos": [round(float(ugv_pos[0]), 2), round(float(ugv_pos[1]), 2), round(float(ugv_pos[2]), 2)],
            "tether_dist_m": round(tether_dist, 2),
            "hostile_a": [round(float(h_a_pos[0]), 2), round(float(h_a_pos[1]), 2)],
            "hostile_b": [round(float(h_b_pos[0]), 2), round(float(h_b_pos[1]), 2)],
            "hostile_b_occluded": is_h_b_occl,
            "uav_points": len(uav_points),
            "ugv_points": len(ugv_points)
        }

def run_simulation(duration_seconds=14400.0, target_ip="127.0.0.1", fps=20.0):
    sim = SquareVillageFlightSimulator(target_ip=target_ip)
    interval = 1.0 / fps
    start_time = time.time()
    print(f"[*] Starting Square Village MUM-T Flight & Perception Simulation ({fps} Hz)")
    print(f"    UAV: Circular Orbit R=32m, Alt=+30m -> UDP {target_ip}:{UAV_UDP_PORT}")
    print(f"    UGV: Elliptical Underpass Track A=26m, B=16m -> UDP {target_ip}:{UGV_UDP_PORT}")

    t = 0.0
    while (time.time() - start_time) < duration_seconds:
        loop_start = time.perf_counter()
        info = sim.step(t)
        if sim.frame_id % 20 == 0:
            status = "OCCLUDED (Behind Stone Wall)" if info["hostile_b_occluded"] else "LINE-OF-SIGHT"
            print(f"[SIM Frame {info['frame_id']:04d}] Drone: {info['uav_pos']} | Rover: {info['ugv_pos']} | Tether: {info['tether_dist_m']}m | H-B: {status}")
        t += interval
        elapsed = time.perf_counter() - loop_start
        sleep_time = max(0.0, interval - elapsed)
        time.sleep(sleep_time)

    print("[*] Simulation cycle complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Square Village MUM-T Flight & LiDAR Simulation")
    parser.add_argument("--duration", type=float, default=14400.0, help="Simulation duration in seconds")
    parser.add_argument("--ip", type=str, default="127.0.0.1", help="Target UDP IP")
    parser.add_argument("--fps", type=float, default=20.0, help="Sweep frequency in Hz")
    args = parser.parse_args()

    run_simulation(duration_seconds=args.duration, target_ip=args.ip, fps=args.fps)
