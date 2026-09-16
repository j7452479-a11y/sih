"""
SIH26053 - Sim Civilian: Ego-Centric Autonomous EV Simulation
Simulates 20 Hz automotive LiDAR point cloud streaming with:
  - 32-channel automotive beam geometry (-25 deg to +15 deg)
  - 15cm raised sidewalk curbs and 3.2m underpass ceiling structure
  - Parked delivery van casting radial horizontal occlusion shadow
  - Crossing pedestrian walking from behind the van into the EV path
  - Closed-loop UDP Port 5001 (Stream Out) and Port 5003 (AEB Telemetry In)
"""

import os
import sys
import time
import math
import struct
import socket
import argparse
from typing import Tuple, List
import numpy as np

from config import (
    UAV_UDP_PORT,
    TELEMETRY_RETURN_PORT,
    DEFAULT_RETURN_IP,
    EV_HEIGHT_M,
    EV_LIDAR_HEIGHT_M,
    EV_CRUISE_SPEED_MPS,
    EV_SAFE_OVERHEAD_CLEARANCE_M,
    SemanticClass,
)


class CivilianEVSimulator:
    """Deterministic 20 Hz Simulation of Autonomous EV & Urban Proving Ground."""

    def __init__(self, target_ip: str = DEFAULT_RETURN_IP, target_port: int = UAV_UDP_PORT):
        self.target_ip = target_ip
        self.target_port = target_port

        # Network Sockets
        self.tx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rx_socket.bind(("0.0.0.0", TELEMETRY_RETURN_PORT))
        self.rx_socket.setblocking(False)

        # Vehicle State
        self.ego_x = 0.0
        self.ego_y = -35.0
        self.ego_z = 0.15
        self.speed = EV_CRUISE_SPEED_MPS
        self.pitch_deg = 0.0
        self.yaw_deg = 0.0
        self.aeb_active = False

        # Urban Proving Ground Static Geometry
        # Underpass ceiling at Y in [15.0, 30.0], Z in [3.1, 3.3] (3.2m clearance)
        self.underpass_y_min = 15.0
        self.underpass_y_max = 30.0
        self.underpass_clearance_z = 3.2

        # Parked delivery van at (X=2.8, Y=5.0), Dimensions: DX=2.0, DY=5.0, DZ=2.4
        self.van_x = 2.6
        self.van_y = 5.0
        self.van_w = 1.8
        self.van_l = 4.8
        self.van_h = 2.4

        # Dynamic Crossing Pedestrian: steps out from behind the van
        self.ped_x = 4.0
        self.ped_y = 6.2
        self.ped_z = 0.9  # Center elevation
        self.ped_vx = -1.2  # Walking into the lane at 1.2 m/s
        self.ped_vy = 0.0

        self.frame_id = 0

    def step_physics(self, dt: float):
        """Advances vehicle and dynamic pedestrian trajectories."""
        # 1. Process inbound AEB controller telemetry
        try:
            while True:
                data, _ = self.rx_socket.recvfrom(2048)
                import json
                payload = json.loads(data.decode("utf-8"))
                if payload.get("status") == "EMERGENCY_STOP":
                    self.aeb_active = True
                elif payload.get("status") == "NOMINAL":
                    self.aeb_active = False
        except BlockingIOError:
            pass
        except Exception:
            pass

        # 2. Update Vehicle Velocity & Pitch under Braking
        if self.aeb_active:
            # Decelerate rapidly (6.5 m/s^2) and nose-down pitch
            self.speed = max(0.0, self.speed - 6.5 * dt)
            if self.speed > 0.1:
                self.pitch_deg = min(2.5, self.pitch_deg + 8.0 * dt)  # Nose dives under hard braking
            else:
                self.pitch_deg = max(0.0, self.pitch_deg - 5.0 * dt)  # Settles when stopped
        else:
            # Accelerate smoothly back to cruise speed
            self.speed = min(EV_CRUISE_SPEED_MPS, self.speed + 3.0 * dt)
            self.pitch_deg = max(0.0, self.pitch_deg - 5.0 * dt)

        # Move vehicle along Y-axis
        self.ego_y += self.speed * dt
        if self.ego_y > 45.0:
            self.ego_y = -35.0  # Loop track

        # 3. Update Crossing Pedestrian
        if self.ego_y < 12.0:
            self.ped_x += self.ped_vx * dt
            if self.ped_x < -3.5 or self.ped_x > 4.2:
                self.ped_vx = -self.ped_vx  # Reverse crossing path

    def generate_ego_lidar_frame(self) -> Tuple[np.ndarray, bool]:
        """
        Generates 32-channel automotive LiDAR point cloud.
        Checks for line-of-sight occlusion behind the parked delivery van.
        """
        points = []
        sensor_x = self.ego_x
        sensor_y = self.ego_y
        sensor_z = self.ego_z + EV_LIDAR_HEIGHT_M

        v_channels = 32
        h_beams = 64
        v_fov_min = math.radians(-25.0)
        v_fov_max = math.radians(15.0)

        # Check if pedestrian is occluded from sensor view by parked delivery van
        # Ray from (sensor_x, sensor_y) to (ped_x, ped_y)
        ped_occluded = False
        if self.van_y - self.van_l / 2.0 <= self.ped_y <= self.van_y + self.van_l / 2.0:
            # If sensor is upstream of van and ped is behind van lateral extent
            if sensor_y < self.van_y and self.ped_x > (self.van_x - self.van_w / 2.0):
                # Vector intersection check
                van_x_min = self.van_x - self.van_w / 2.0
                van_x_max = self.van_x + self.van_w / 2.0
                van_y_min = self.van_y - self.van_l / 2.0
                van_y_max = self.van_y + self.van_l / 2.0

                # Parametric ray check
                dx = self.ped_x - sensor_x
                dy = self.ped_y - sensor_y
                if dy > 0:
                    t_van = (self.van_y - sensor_y) / dy
                    ray_x_at_van = sensor_x + t_van * dx
                    if van_x_min <= ray_x_at_van <= van_x_max and t_van < 1.0:
                        ped_occluded = True

        for c in range(v_channels):
            pitch = v_fov_min + (v_fov_max - v_fov_min) * (c / (v_channels - 1))
            for b in range(h_beams):
                yaw = math.radians((b / h_beams) * 360.0 - 180.0)

                # Beam unit vector in sensor local frame
                vx = math.cos(pitch) * math.sin(yaw)
                vy = math.cos(pitch) * math.cos(yaw)
                vz = math.sin(pitch)

                # 1. Asphalt Road Intersection (Z = 0.0)
                if vz < -0.01:
                    t_road = -sensor_z / vz
                    if 0.5 < t_road < 60.0:
                        hx = vx * t_road
                        hy = vy * t_road
                        hz = -sensor_z
                        # Semantic 1: Road, 5: Curb at |X| >= 3.5m
                        sem = SemanticClass.CURB if abs(hx + sensor_x) >= 3.4 else SemanticClass.ROAD
                        intensity = int(max(10, min(255, (1.0 - t_road / 60.0) * 240)))
                        points.append([hx, hy, hz, float(sem), float(intensity)])

                # 2. Overhead Underpass Ceiling Intersection (Z = underpass_clearance_z)
                if vz > 0.05:
                    t_ceil = (self.underpass_clearance_z - sensor_z) / vz
                    if 1.0 < t_ceil < 40.0:
                        wy = sensor_y + vy * t_ceil
                        wx = sensor_x + vx * t_ceil
                        if self.underpass_y_min <= wy <= self.underpass_y_max and abs(wx) <= 4.5:
                            hx = vx * t_ceil
                            hy = vy * t_ceil
                            hz = vz * t_ceil
                            intensity = int(max(10, min(255, (1.0 - t_ceil / 40.0) * 200)))
                            points.append([hx, hy, hz, float(SemanticClass.BUILDING), float(intensity)])

        # 3. Parked Van Point Reflections
        dx_van = self.van_x - sensor_x
        dy_van = self.van_y - sensor_y
        dist_van = math.sqrt(dx_van * dx_van + dy_van * dy_van)
        if 2.0 < dist_van < 45.0:
            for _ in range(12):
                rx = np.random.uniform(-self.van_w / 2.0, self.van_w / 2.0)
                ry = np.random.uniform(-self.van_l / 2.0, self.van_l / 2.0)
                rz = np.random.uniform(0.3, self.van_h)
                points.append([dx_van + rx, dy_van + ry, rz - sensor_z, float(SemanticClass.VEHICLE), 200.0])

        # 4. Pedestrian Point Reflections (if not occluded behind the van)
        if not ped_occluded:
            dx_ped = self.ped_x - sensor_x
            dy_ped = self.ped_y - sensor_y
            dist_ped = math.sqrt(dx_ped * dx_ped + dy_ped * dy_ped)
            if 1.0 < dist_ped < 50.0:
                for _ in range(8):
                    rx = np.random.uniform(-0.25, 0.25)
                    ry = np.random.uniform(-0.25, 0.25)
                    rz = np.random.uniform(0.1, 1.7)
                    points.append([dx_ped + rx, dy_ped + ry, rz - sensor_z, float(SemanticClass.PEDESTRIAN), 220.0])

        if len(points) == 0:
            return np.zeros((0, 5), dtype=np.float32), ped_occluded

        pts_array = np.array(points, dtype=np.float32)
        # Cap packet points to 80 per packet to match UDP protocol standard
        if len(pts_array) > 80:
            indices = np.random.choice(len(pts_array), 80, replace=False)
            pts_array = pts_array[indices]

        return pts_array, ped_occluded

    def send_sih1_packet(self, points: np.ndarray):
        """Serializes point cloud to standard 40-byte header SIH1 datagram."""
        self.frame_id += 1
        unix_ts = time.time()
        num_points = len(points)

        sensor_type = 3  # 3 = CIVILIAN_EV_EGO
        reserved = 0

        # Header: Magic(4s) + Frame(I) + Ts(d) + Type(B) + Count(i) + OriginXYZ(3f) + RollPitchYaw(3f) + Reserved(I)
        # Pack to 40-byte binary header
        header_bytes = struct.pack(
            "!4sIdBiffffffI",
            b"SIH1",
            self.frame_id,
            unix_ts,
            sensor_type,
            num_points,
            float(self.ego_x),
            float(self.ego_y),
            float(self.ego_z + EV_LIDAR_HEIGHT_M),
            0.0,
            float(self.pitch_deg),
            float(self.yaw_deg),
            reserved
        )

        # 16-byte points: X(f) + Y(f) + Z(f) + Semantic(H) + Intensity(B) + ReturnIdx(B)
        point_records = bytearray()
        for i in range(num_points):
            pt = points[i]
            x, y, z = float(pt[0]), float(pt[1]), float(pt[2])
            sem = int(pt[3])
            intensity = int(pt[4]) if len(pt) >= 5 else 180
            ret_idx = 1
            point_records.extend(struct.pack("!fffHBB", x, y, z, sem, intensity, ret_idx))

        datagram = header_bytes + point_records
        try:
            self.tx_socket.sendto(datagram, (self.target_ip, self.target_port))
        except Exception:
            pass

    def close(self):
        self.tx_socket.close()
        self.rx_socket.close()


def run_simulation(duration_s: float = 60.0, fps: float = 20.0, verbose: bool = True):
    print("\n" + "=" * 80)
    print("   SIH26053 - SIM CIVILIAN: AUTONOMOUS EV URBAN PERCEPTION SIMULATOR")
    print("=" * 80)
    print(f" Target Endpoint:   UDP {DEFAULT_RETURN_IP}:{UAV_UDP_PORT} (Sensor Type: 3)")
    print(f" AEB Telemetry In: UDP 0.0.0.0:{TELEMETRY_RETURN_PORT}")
    print(f" Cruise Speed:      {EV_CRUISE_SPEED_MPS} m/s (36 km/h) | Underpass Clearance: 3.2m")
    print("=" * 80 + "\n")

    sim = CivilianEVSimulator()
    dt = 1.0 / fps
    total_frames = int(duration_s * fps) if duration_s > 0 else 999999

    try:
        for f in range(total_frames):
            t0 = time.perf_counter()

            sim.step_physics(dt)
            points, ped_occluded = sim.generate_ego_lidar_frame()
            sim.send_sih1_packet(points)

            if verbose and (f % 20 == 0):
                occl_str = "OCUSED_BEHIND_VAN" if ped_occluded else "LINE_OF_SIGHT"
                aeb_str = "BRAKING_ACTIVE [STOP]" if sim.aeb_active else "CRUISE_NOMINAL"
                print(f"[SimCivilian F{sim.frame_id:05d}] EV: Y={sim.ego_y:+05.1f}m | Speed: {sim.speed:04.1f}m/s | Pitch: {sim.pitch_deg:+04.1f}° | Ped: X={sim.ped_x:+04.1f}m ({occl_str}) | AEB: {aeb_str}")

            elapsed = time.perf_counter() - t0
            sleep_time = max(0.001, dt - elapsed)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n[*] Sim Civilian stopped by user.")
    finally:
        sim.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sim Civilian EV Simulator")
    parser.add_argument("--duration", type=float, default=60.0, help="Simulation duration (s), 0 for infinite")
    parser.add_argument("--fps", type=float, default=20.0, help="Simulation FPS")
    parser.add_argument("--quiet", action="store_true", help="Quiet mode")
    args = parser.parse_args()

    run_simulation(duration_s=args.duration, fps=args.fps, verbose=not args.quiet)
