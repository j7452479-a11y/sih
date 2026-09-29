"""
Binary SIH1 Protocol Packer & Unpacker
High-throughput struct and numpy deserialization for LiDAR telemetry.
"""

import struct
from dataclasses import dataclass
from typing import Tuple, Optional
import numpy as np

from config import UDP_MAGIC_BYTES, SemanticClass

@dataclass
class SIHHeader:
    magic: bytes
    frame_id: int
    timestamp: float
    sensor_type: int  # 1 = UAV, 2 = UGV, 3 = Ego EV
    point_count: int
    checksum: int = 0
    origin_x: float = 0.0
    origin_y: float = 0.0
    origin_z: float = 0.0
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0

# Fast NumPy structured dtype for 16-byte point payload
POINT_DTYPE = np.dtype([
    ("x", "<f4"),
    ("y", "<f4"),
    ("z", "<f4"),
    ("semantic", "u1"),
    ("pad0", "u1"),
    ("pad1", "u1"),
    ("pad2", "u1"),
])

def unpack_sih1_packet(data: bytes) -> Tuple[SIHHeader, np.ndarray]:
    """
    Unpacks raw binary UDP datagram into SIHHeader and (N, 4) float32 numpy array:
    Columns: [x, y, z, semantic_class].
    Supports:
      - 49-byte SIH2 header (with 6-DOF origin & Euler angles)
      - 25-byte SIH1 header
      - 21-byte legacy header
    """
    if len(data) < 21:
        raise ValueError(f"Datagram length {len(data)} is too small for SIH header")

    ox = oy = oz = roll = pitch = yaw = 0.0

    # Check for SIH2 extended 49-byte header
    if len(data) >= 49 and data[:4] == b"SIH2":
        magic, frame_id, timestamp, sensor_type, point_count, checksum, ox, oy, oz, roll, pitch, yaw = struct.unpack_from(
            "<4sIdBII6f", data, 0
        )
        payload_offset = 49
    # Check for standard 25-byte SIH1 header
    elif len(data) >= 25 and data[:4] == UDP_MAGIC_BYTES:
        magic, frame_id, timestamp, sensor_type, point_count, checksum = struct.unpack_from("<4sIdBII", data, 0)
        payload_offset = 25
    else:
        # Legacy 21-byte format
        frame_id, timestamp, sensor_type, point_count, checksum = struct.unpack_from("<IdBII", data, 0)
        magic = UDP_MAGIC_BYTES
        payload_offset = 21

    header = SIHHeader(
        magic=magic,
        frame_id=frame_id,
        timestamp=timestamp,
        sensor_type=sensor_type,
        point_count=point_count,
        checksum=checksum,
        origin_x=float(ox),
        origin_y=float(oy),
        origin_z=float(oz),
        roll=float(roll),
        pitch=float(pitch),
        yaw=float(yaw),
    )

    expected_payload_bytes = point_count * 16
    available_bytes = len(data) - payload_offset
    if available_bytes < expected_payload_bytes:
        # Gracefully handle truncated packets
        actual_points = available_bytes // 16
    else:
        actual_points = point_count

    if actual_points == 0:
        return header, np.empty((0, 4), dtype=np.float32)

    # Zero-copy fast array deserialization
    raw_records = np.frombuffer(
        data, dtype=POINT_DTYPE, count=actual_points, offset=payload_offset
    )

    # Build (N, 4) float32 array: [x, y, z, semantic]
    points = np.empty((actual_points, 4), dtype=np.float32)
    points[:, 0] = raw_records["x"]
    points[:, 1] = raw_records["y"]
    points[:, 2] = raw_records["z"]
    points[:, 3] = raw_records["semantic"].astype(np.float32)

    return header, points

def pack_sih1_packet(
    frame_id: int,
    timestamp: float,
    sensor_type: int,
    points: np.ndarray,  # (N, 3) or (N, 4)
    checksum: int = 0,
    pose: Optional[Tuple[float, float, float, float, float, float]] = None,
) -> bytes:
    """
    Packs point cloud into binary datagram:
    If pose is provided: 49-byte SIH2 header [4sIdBII6f] + N*16B
    If pose is None: 25-byte SIH1 header [4sIdBII] + N*16B
    """
    point_count = len(points)
    if pose is not None:
        ox, oy, oz, roll, pitch, yaw = pose
        header_bytes = struct.pack(
            "<4sIdBII6f",
            b"SIH2",
            frame_id,
            timestamp,
            sensor_type,
            point_count,
            checksum,
            float(ox),
            float(oy),
            float(oz),
            float(roll),
            float(pitch),
            float(yaw),
        )
    else:
        header_bytes = struct.pack(
            "<4sIdBII",
            UDP_MAGIC_BYTES,
            frame_id,
            timestamp,
            sensor_type,
            point_count,
            checksum,
        )

    if point_count == 0:
        return header_bytes

    records = np.zeros(point_count, dtype=POINT_DTYPE)
    records["x"] = points[:, 0].astype(np.float32)
    records["y"] = points[:, 1].astype(np.float32)
    records["z"] = points[:, 2].astype(np.float32)
    if points.shape[1] >= 4:
        records["semantic"] = points[:, 3].astype(np.uint8)
    else:
        records["semantic"] = int(SemanticClass.GROUND)

    return header_bytes + records.tobytes()
