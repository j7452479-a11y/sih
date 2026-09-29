"""
Tactical Edge Perception Engine (SIH26053)
Master Configuration Module
"""

import math
from enum import IntEnum

# ==============================================================================
# 1. 4-Tier Foveated Grid Parameters
# ==============================================================================
# Radial boundary thresholds in meters [Tier 1, Tier 2, Tier 3, Tier 4]
TIER_RADII = [10.0, 30.0, 60.0, 100.0]

# Spatial resolution (grid cell size) per tier in meters
TIER_RESOLUTIONS = [0.05, 0.10, 0.20, 0.50]

# Maximum sensor operational range
MAX_SENSOR_RANGE_M = 100.0

# Numerical clamp for zero-crossing coordinate stability
ZERO_CROSSING_EPSILON = 1e-6

# ==============================================================================
# 2. Multi-Level Surface (MLS) Parameters (Triebel et al.)
# ==============================================================================
# Maximum number of vertical surface intervals per (tier, ix, iy) cell
MLS_MAX_INTERVALS = 3

# Minimum vertical clearance gap to split into a new layer (e.g. bridge vs road)
MLS_GAP_THRESHOLD_M = 1.0

# Vertical merging distance tolerance for contiguous points
MLS_MERGE_THRESHOLD_M = 0.10

# Default clearance height for traversability evaluation
VEHICLE_CLEARANCE_HEIGHT_M = 1.8

# ==============================================================================
# 3. Multi-Target Tracking (MTT) & Kinematics (Bar-Shalom / Labbe)
# ==============================================================================
# Expected pipeline update rate (20 Hz)
TRACK_UPDATE_RATE_HZ = 20.0
TRACK_DT = 1.0 / TRACK_UPDATE_RATE_HZ  # 0.05 seconds

# Maximum plausible hostile acceleration (m/s^2) for CWNA process noise
HOSTILE_MAX_ACCEL_MPS2 = 2.0
CWNA_PROCESS_NOISE_Q = (HOSTILE_MAX_ACCEL_MPS2 ** 2) / 3.0  # ~1.333

# Measurement noise standard deviation (meters)
MEASUREMENT_NOISE_STD_M = 0.15

# Chi-squared 2-DOF Mahalanobis validation gate (99% confidence threshold)
MAHALANOBIS_GATE_GAMMA = 9.21

# Track confirmation and coasting thresholds
TRACK_CONFIRMATION_HITS = 3
TRACK_COAST_MAX_MISSES = 200  # 200 frames @ 20 Hz = 10.0 s before purge (covers stone wall occlusion)

# Tier-adaptive DBSCAN clustering epsilons
TIER_DBSCAN_EPSILONS = [0.25, 0.40, 0.80, 1.20]
DBSCAN_MIN_POINTS = 3

# ==============================================================================
# 4. Networking, Synchronization & UDP Protocol
# ==============================================================================
# Bind IP: 0.0.0.0 accepts both localhost (127.0.0.1) and LAN (192.168.x.x)
BIND_IP = "0.0.0.0"

# Target IP for return telemetry (editable for Single-PC vs Dual-PC)
DEFAULT_RETURN_IP = "127.0.0.1"

# Port assignments
UAV_UDP_PORT = 5001               # Inbound UAV point cloud stream
UGV_UDP_PORT = 5002               # Inbound UGV point cloud stream
TELEMETRY_RETURN_PORT = 5003      # Outbound HUD / target coordinates to Unity HUD
CIVILIAN_TELEMETRY_PORT = 5004    # Dedicated return telemetry for Civilian EV controller
WEB_SERVER_PORT = 8000            # FastAPI REST & WebSocket hub

# Binary UDP Header constants
UDP_MAGIC_BYTES = b"SIH1"
HEADER_SIZE_BYTES = 21
POINT_RECORD_SIZE_BYTES = 16

# Temporal Jitter Buffer limits (milliseconds)
JITTER_BUFFER_WINDOW_MS = 50.0
TEMPORAL_SYNC_TOLERANCE_MS = 25.0

# ==============================================================================
# 5. Semantic Classification Schema
# ==============================================================================
class SemanticClass(IntEnum):
    GROUND = 0
    ROAD = 1
    OBSTACLE = 2
    BRIDGE = 3
    BUILDING = 4
    CURB = 5
    VEHICLE = 6
    PEDESTRIAN = 8
    VRU = 8
    HOSTILE = 8
    TARGET = 8

# ==============================================================================
# 5b. Civilian Autonomous EV & Safety Corridor Parameters
# ==============================================================================
EV_HEIGHT_M = 1.6                   # Vehicle roof height
EV_LIDAR_HEIGHT_M = 1.7             # Roof-mounted sensor position
EV_SAFE_OVERHEAD_CLEARANCE_M = 2.4  # Minimum clearance required for underpasses/garages
EV_LANE_WIDTH_M = 3.2               # Standard urban lane width
EV_CORRIDOR_WIDTH_M = 3.5           # Safety braking corridor lateral envelope
EV_CORRIDOR_LOOKAHEAD_S = 2.5       # Longitudinal lookahead horizon in seconds
EV_EMERGENCY_DECEL_MPS2 = 6.5       # Max braking deceleration (m/s^2)
EV_TTC_THRESHOLD_S = 1.8            # Time-to-Collision (TTC) threshold for AEB trigger
EV_CRUISE_SPEED_MPS = 10.0          # Target cruising speed (36 km/h)

# ==============================================================================
# 6. Geodetic Datum & Local Tangent Plane (Normandy Village)
# ==============================================================================
# Anchor coordinates for Local Tangent Plane projection
DATUM_LAT_0 = 49.34000000         # Degrees North
DATUM_LON_0 = -0.85000000         # Degrees East
DATUM_HAE_0 = 25.0                # Height Above Ellipsoid (meters)

# WGS84 Reference Ellipsoid Constants
WGS84_SEMI_MAJOR_AXIS_A = 6378137.0                   # meters
WGS84_FLATTENING_F = 1.0 / 298.257223563
WGS84_FIRST_ECCENTRICITY_SQ_E2 = (2.0 * WGS84_FLATTENING_F) - (WGS84_FLATTENING_F ** 2)

# Dynamic threat geofencing threshold
THREAT_GEOFENCE_RADIUS_M = 50.0
NEAR_FIELD_STREAM_RATE_HZ = 20.0
FAR_FIELD_STREAM_RATE_HZ = 0.5

# ==============================================================================
# 7. Watchdog Heartbeat & Real-Time Synchronization
# ==============================================================================
HEARTBEAT_UDP_PORT = 5005
WATCHDOG_TIMEOUT_SEC = 0.50         # 500ms strict hardware safe-stop threshold
HEARTBEAT_INTERVAL_SEC = 0.05       # 20 Hz broadcast
HARDWARE_SERIAL_PORT = None         # Optional serial port (e.g. 'COM3' or '/dev/ttyUSB0')
