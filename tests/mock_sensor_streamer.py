"""
Scaled Tactical Sensor Streamer & Stress Simulation (SIH26053)
Streams dense, high-frequency 20 Hz binary SIH1 UDP telemetry covering a full 100m x 100m tactical zone:
- 24 Normandy multi-story stone buildings
- 2 Bridge overpasses with open traversable underpass voids
- 6 Dynamic tactical combatants & fast vehicles with crossing routes and severe occlusions
- High-density dual-channel LiDAR point streams
"""

import argparse
import socket
import time
import math
import sys
from pathlib import Path
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    UAV_UDP_PORT,
    UGV_UDP_PORT,
    SemanticClass,
)
from ingestion.udp_protocol import pack_sih1_packet

def generate_scaled_tactical_environment():
    """Generates an extensive 100m x 100m realistic Normandy battlefield."""
    static_pts = []

    # 1. Main North-South Cobblestone Avenue (Y from -80 to +80, X in [-4, 4])
    for y in np.linspace(-80, 80, 80):
        for x in np.linspace(-4, 4, 9):
            static_pts.append([x, y, 0.05, int(SemanticClass.ROAD)])

    # 2. East-West Cross Streets at Y = -40, Y = 0, Y = +40
    for cross_y in [-40.0, 0.0, 40.0]:
        for x in np.linspace(-70, 70, 70):
            for dy in np.linspace(-3, 3, 7):
                static_pts.append([x, cross_y + dy, 0.05, int(SemanticClass.ROAD)])

    # 3. North Bridge Overpass at Y = +25m (Deck at Z = 5.2m, clearance beneath)
    for x in np.linspace(-6, 6, 13):
        for y in np.linspace(22, 28, 7):
            static_pts.append([x, y, 5.2, int(SemanticClass.BRIDGE)])

    # 4. South Bridge Overpass at Y = -35m (Deck at Z = 4.8m, clearance beneath)
    for x in np.linspace(-6, 6, 13):
        for y in np.linspace(-38, -32, 7):
            static_pts.append([x, y, 4.8, int(SemanticClass.BRIDGE)])

    # 5. Stone Wall Occlusion Barriers (SM_H_StoneWall_00A assets)
    # Wall A (Village Center Western Barrier)
    for y in np.linspace(-12, 12, 25):
        for z in np.linspace(0, 2.4, 5):
            static_pts.append([-10.0, y, z, int(SemanticClass.OBSTACLE)])

    # Wall B (Eastern Alley Barrier)
    for y in np.linspace(-15, 15, 25):
        for z in np.linspace(0, 2.4, 5):
            static_pts.append([12.0, y, z, int(SemanticClass.OBSTACLE)])

    # Wall C & D (Outer perimeter walls)
    for x in np.linspace(-35, -20, 16):
        for z in np.linspace(0, 2.0, 4):
            static_pts.append([x, 20.0, z, int(SemanticClass.OBSTACLE)])
            static_pts.append([x, -20.0, z, int(SemanticClass.OBSTACLE)])

    # 6. Village Buildings (32 Multi-Story Buildings)
    building_layouts = [
        # Sector NW (Close & Mid)
        (-25, 15, 12, 10, 6.5), (-45, 15, 10, 14, 7.0), (-25, 35, 14, 10, 5.5), (-50, 35, 12, 12, 8.0),
        (-18, 28, 8, 8, 5.0), (-38, 48, 10, 10, 6.0),
        # Sector NE (Close & Mid)
        (25, 15, 12, 10, 6.0), (45, 15, 10, 12, 7.5), (25, 35, 14, 10, 5.0), (50, 35, 12, 14, 8.0),
        (18, 28, 8, 8, 5.5), (38, 48, 10, 10, 6.5),
        # Sector SW (Close & Mid)
        (-25, -25, 12, 10, 6.0), (-45, -25, 10, 12, 7.0), (-25, -50, 14, 10, 5.5), (-50, -50, 12, 12, 7.5),
        (-18, -38, 8, 8, 4.5), (-38, -18, 10, 10, 6.0),
        # Sector SE (Close & Mid)
        (25, -25, 12, 10, 6.5), (45, -25, 10, 14, 7.0), (25, -50, 14, 10, 5.0), (50, -50, 12, 12, 8.0),
        (18, -38, 8, 8, 5.0), (38, -18, 10, 10, 6.5),
        # Far-Field Outposts (Tier 4, R > 60m)
        (-65, 0, 12, 12, 6.0), (65, 0, 12, 12, 6.0), (0, 65, 14, 10, 5.5), (0, -65, 14, 10, 5.5),
        (-60, 60, 10, 10, 5.0), (60, 60, 10, 10, 5.0), (-60, -60, 10, 10, 5.0), (60, -60, 10, 10, 5.0),
    ]

    for bx, by, bw, bl, bh in building_layouts:
        for x in np.linspace(bx - bw/2, bx + bw/2, 5):
            for y in np.linspace(by - bl/2, by + bl/2, 5):
                for z in np.linspace(0, bh, 4):
                    static_pts.append([x, y, z, int(SemanticClass.OBSTACLE)])

    # 7. Military Sandbag Checkpoints & Road Bunkers (4 Cardinal Entrances)
    for c_x, c_y in [(0, 30), (0, -30), (30, 0), (-30, 0)]:
        for dx in np.linspace(-3, 3, 5):
            for dy in np.linspace(-1.5, 1.5, 3):
                for dz in np.linspace(0, 1.8, 3):
                    static_pts.append([c_x + dx, c_y + dy, dz, int(SemanticClass.OBSTACLE)])

    # 8. Perimeter Watchtowers (4 Elevated Guard Platforms at Z = 6.0m)
    for wt_x, wt_y in [(-40, 40), (40, 40), (-40, -40), (40, -40)]:
        for dx in np.linspace(-2, 2, 3):
            for dy in np.linspace(-2, 2, 3):
                for dz in [0.0, 3.0, 6.0]:
                    static_pts.append([wt_x + dx, wt_y + dy, dz, int(SemanticClass.OBSTACLE)])

    # 9. Drainage Ditches / Culverts (Z < 0m)
    for y in np.linspace(-60, 60, 30):
        static_pts.append([5.5, y, -0.4, int(SemanticClass.GROUND)])
        static_pts.append([-5.5, y, -0.4, int(SemanticClass.GROUND)])

    return np.array(static_pts, dtype=np.float32)

def generate_target_cluster(cx: float, cy: float, cz: float, points_per_target: int = 24):
    """Generates a dense cluster of points around a combatant / vehicle with continuous vertical profile."""
    pts = []
    for dx in [-0.15, 0.15]:
        for dy in [-0.15, 0.15]:
            for dz in [0.3, 0.5, 0.7, 0.9, 1.1, 1.3]:
                pts.append([cx + dx, cy + dy, cz + dz, int(SemanticClass.TARGET)])
    return np.array(pts, dtype=np.float32)

def run_scaled_streamer(target_ip: str = "127.0.0.1", duration_sec: float = 0.0):
    uav_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ugv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    env_pts = generate_scaled_tactical_environment()
    frame_id = 1
    t_start = time.time()
    dt = 0.05  # 20 Hz

    print("======================================================================")
    print(f"[SCALED STRESS STREAMER] Broadcasting 20 Hz LiDAR to {target_ip}:")
    print(f"  -> Operational Envelope: 100m x 100m Tactical Village")
    print(f"  -> Total Environment Terrain Points: {len(env_pts)}")
    print(f"  -> Static Obstacles: 32 Buildings, 2 Bridges, 4 Bunkers, 4 Towers")
    print(f"  -> Dynamic Combatants: 8 Active Hostiles (Crossing + Tunnel + Air + Armor)")
    print(f"  -> UAV Port: {UAV_UDP_PORT} | UGV Port: {UGV_UDP_PORT}")
    print("======================================================================")
    print("Streaming at 20 Hz... Press Ctrl+C to stop.\n")

    try:
        while True:
            t = time.time() - t_start
            if duration_sec > 0 and t >= duration_sec:
                break

            # -------------------------------------------------------------
            # DYNAMIC THREAT TRAJECTORIES (8 TARGETS)
            # -------------------------------------------------------------
            # Hostile 1 (Alpha): Crossing East to West (-22m to +22m, Y = 0)
            h1_x = 22.0 * math.sin(0.45 * t)
            h1_y = 0.0
            h1_z = 0.0

            # Hostile 2 (Bravo): Crossing North to South (X = 0, Y = -22m to +22m)
            # Intersects Hostile 1 at origin
            h2_x = 0.0
            h2_y = 22.0 * math.cos(0.45 * t)
            h2_z = 0.0

            # Hostile 3 (Charlie - Tunnel Infiltrator):
            # Passes directly through the South Bridge underpass (Y = -35m)
            h3_x = 18.0 * math.sin(0.35 * t)
            h3_y = -35.0
            h3_z = 0.0  # Under the 4.8m bridge deck

            # Hostile 4 (Delta - Elevated Sniper on Ruins):
            # Moves along building balcony at Z = 3.6m
            h4_x = 20.0 + 8.0 * math.sin(0.3 * t)
            h4_y = 20.0
            h4_z = 3.6

            # Hostile 5 (Echo - Flanker Weaving Behind Wall A):
            # Moves behind the stone wall at X = -10m (causes intermittent occlusion)
            h5_x = -12.0
            h5_y = 15.0 * math.sin(0.5 * t)
            h5_z = 0.0

            # Hostile 6 (Foxtrot - Fast Armored Patrol Vehicle):
            # High-speed vehicle (8.5 m/s) circling outer perimeter road (Radius ~ 55m)
            vehicle_angle = 0.35 * t
            h6_x = 55.0 * math.cos(vehicle_angle)
            h6_y = 55.0 * math.sin(vehicle_angle)
            h6_z = 0.0

            # Hostile 7 (Golf - Airborne Recon Drone):
            # Elevated hostile aerial asset circling village airspace at Z = 8.5m
            drone_angle = 0.5 * t
            h7_x = 28.0 * math.cos(drone_angle)
            h7_y = 28.0 * math.sin(drone_angle)
            h7_z = 8.5

            # Hostile 8 (Hotel - Fast Cross-Road Interceptor / Technical):
            # Travels along North Cross-Street at Y = 40.0m (-50m to +50m)
            h8_x = 50.0 * math.sin(0.4 * t)
            h8_y = 40.0
            h8_z = 0.0

            # Generate target point clusters
            targets = [
                generate_target_cluster(h1_x, h1_y, h1_z),
                generate_target_cluster(h2_x, h2_y, h2_z),
                generate_target_cluster(h3_x, h3_y, h3_z),
                generate_target_cluster(h4_x, h4_y, h4_z),
                generate_target_cluster(h5_x, h5_y, h5_z),
                generate_target_cluster(h6_x, h6_y, h6_z),
                generate_target_cluster(h7_x, h7_y, h7_z),
                generate_target_cluster(h8_x, h8_y, h8_z),
            ]
            all_target_pts = np.vstack(targets)

            # High-channel LiDAR samples from static environment
            # UAV 64-channel scan sample
            uav_sample = env_pts[np.random.choice(len(env_pts), min(128, len(env_pts)), replace=False)]
            # UGV 32-channel scan sample
            ugv_sample = env_pts[np.random.choice(len(env_pts), min(64, len(env_pts)), replace=False)]

            uav_pts = np.vstack([uav_sample, all_target_pts])
            ugv_pts = np.vstack([ugv_sample, all_target_pts])

            # Pack binary datagrams
            timestamp = time.time()
            uav_data = pack_sih1_packet(frame_id, timestamp, 1, uav_pts)
            ugv_data = pack_sih1_packet(frame_id, timestamp + 0.005, 2, ugv_pts)

            # Transmit
            uav_sock.sendto(uav_data, (target_ip, UAV_UDP_PORT))
            ugv_sock.sendto(ugv_data, (target_ip, UGV_UDP_PORT))

            frame_id += 1
            time.sleep(dt)

    except KeyboardInterrupt:
        print("\n[SCALED STRESS STREAMER] Stopped.")
    finally:
        uav_sock.close()
        ugv_sock.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default="127.0.0.1", help="Target IP for UDP datagrams")
    parser.add_argument("--duration", type=float, default=0.0, help="Run duration in seconds (0 = infinite)")
    args = parser.parse_args()
    run_scaled_streamer(args.ip, args.duration)
