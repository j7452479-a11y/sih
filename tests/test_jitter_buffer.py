"""
Tests for UDP Protocol & Temporal Jitter Buffer.
Validates binary packing/unpacking, frame synchronization, and drop of stale packets.
"""

import pytest
import numpy as np

from ingestion.udp_protocol import pack_sih1_packet, unpack_sih1_packet, SIHHeader
from ingestion.jitter_buffer import TemporalJitterBuffer
from config import SemanticClass

def test_sih1_binary_pack_unpack_roundtrip():
    # 100 random points with coordinates and semantics
    n_pts = 100
    pts = np.random.uniform(-50.0, 50.0, (n_pts, 4)).astype(np.float32)
    pts[:, 3] = np.random.choice([0, 1, 2, 3, 8], n_pts)

    frame_id = 42
    timestamp = 1726310000.123456
    sensor_type = 1

    packet_bytes = pack_sih1_packet(frame_id, timestamp, sensor_type, pts)
    header, unpacked_pts = unpack_sih1_packet(packet_bytes)

    assert header.magic == b"SIH1"
    assert header.frame_id == frame_id
    assert pytest.approx(header.timestamp, abs=1e-5) == timestamp
    assert header.sensor_type == sensor_type
    assert header.point_count == n_pts

    assert unpacked_pts.shape == (n_pts, 4)
    # Check coordinates within float32 precision
    assert np.allclose(unpacked_pts[:, :3], pts[:, :3], atol=1e-5)
    assert np.array_equal(unpacked_pts[:, 3], pts[:, 3])

def test_jitter_buffer_synchronization():
    buf = TemporalJitterBuffer(window_ms=50.0, sync_tolerance_ms=25.0)

    t0 = 100.000
    pts = np.zeros((10, 4), dtype=np.float32)

    # 1. UAV packet arrives at t0
    hdr_uav = SIHHeader(magic=b"SIH1", frame_id=1, timestamp=t0, sensor_type=1, point_count=10)
    res1 = buf.push(hdr_uav, pts)
    assert res1 is None  # Waiting for UGV match

    # 2. UGV packet arrives at t0 + 15ms (within 25ms tolerance)
    hdr_ugv = SIHHeader(magic=b"SIH1", frame_id=1, timestamp=t0 + 0.015, sensor_type=2, point_count=10)
    res2 = buf.push(hdr_ugv, pts)

    # Must emit matched pair!
    assert res2 is not None
    assert res2.uav_header.frame_id == 1
    assert res2.ugv_header.frame_id == 1
    assert pytest.approx(res2.time_delta_ms, abs=1e-2) == 15.0

def test_jitter_buffer_drops_stale_packets():
    buf = TemporalJitterBuffer(window_ms=50.0, sync_tolerance_ms=25.0)
    pts = np.zeros((10, 4), dtype=np.float32)

    # UAV packet at t = 100.0
    hdr_uav_old = SIHHeader(magic=b"SIH1", frame_id=1, timestamp=100.0, sensor_type=1, point_count=10)
    buf.push(hdr_uav_old, pts)

    # UAV packet at t = 100.100 (100ms later -> exceeds 50ms window)
    hdr_uav_new = SIHHeader(magic=b"SIH1", frame_id=3, timestamp=100.100, sensor_type=1, point_count=10)
    buf.push(hdr_uav_new, pts)

    # Old packet should have been purged
    assert buf.dropped_stale_count >= 1

    # UGV packet arrives for t = 100.090 (matches the new UAV frame)
    hdr_ugv = SIHHeader(magic=b"SIH1", frame_id=3, timestamp=100.090, sensor_type=2, point_count=10)
    pair = buf.push(hdr_ugv, pts)

    assert pair is not None
    assert pair.uav_header.frame_id == 3
    assert pair.ugv_header.frame_id == 3
