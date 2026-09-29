"""
Temporal Jitter Buffer & Sensor Synchronization Module
Synchronizes asynchronous UAV and UGV LiDAR sweeps within a 50ms window.
"""

from collections import deque
from dataclasses import dataclass
from typing import Optional, List, Tuple
import numpy as np

from config import JITTER_BUFFER_WINDOW_MS, TEMPORAL_SYNC_TOLERANCE_MS
from .udp_protocol import SIHHeader

@dataclass
class SyncedFramePair:
    """Pair of synchronized UAV and UGV LiDAR sweeps ready for SE(3) fusion."""
    uav_header: SIHHeader
    uav_points: np.ndarray
    ugv_header: SIHHeader
    ugv_points: np.ndarray
    time_delta_ms: float

class TemporalJitterBuffer:
    """
    Sliding temporal ring buffer with chunk aggregation and adaptive sensor synchronization.
    Assembles multi-chunk packets per frame and emits synchronized pairs (or single-sensor sweeps
    when only one vehicle is operating) to ensure continuous 20 Hz perception.
    """

    def __init__(
        self,
        window_ms: float = JITTER_BUFFER_WINDOW_MS,
        sync_tolerance_ms: float = TEMPORAL_SYNC_TOLERANCE_MS,
    ):
        self.window_sec = window_ms / 1000.0
        self.sync_tolerance_sec = sync_tolerance_ms / 1000.0

        self.uav_queue: deque[Tuple[SIHHeader, np.ndarray]] = deque(maxlen=50)
        self.ugv_queue: deque[Tuple[SIHHeader, np.ndarray]] = deque(maxlen=50)

        # Chunk aggregation storage: (sensor_type, frame_id) -> {'header': SIHHeader, 'chunks': [np.ndarray]}
        self._pending_chunks = {}

        self.dropped_stale_count = 0
        self.emitted_pairs_count = 0

    def push_chunk(self, header: SIHHeader, points: np.ndarray) -> Optional[Tuple[SIHHeader, np.ndarray]]:
        """
        Aggregates multi-packet chunks belonging to the same sweep (identified by sensor_type and frame_id).
        Returns the completed (header, merged_points) when all chunks of a sweep have arrived.
        """
        key = (header.sensor_type, header.frame_id)
        completed_frame = None

        # Check if a new frame_id arrived for this sensor_type; if so, finalize the previous frame
        for prev_key in list(self._pending_chunks.keys()):
            if prev_key[0] == header.sensor_type and prev_key[1] != header.frame_id:
                prev = self._pending_chunks.pop(prev_key)
                merged = np.vstack(prev["chunks"]) if prev["chunks"] else np.empty((0, 4), dtype=np.float32)
                completed_frame = (prev["header"], merged)
                break

        if key not in self._pending_chunks:
            self._pending_chunks[key] = {
                "header": header,
                "chunks": [points] if len(points) > 0 else [],
            }
        else:
            if len(points) > 0:
                self._pending_chunks[key]["chunks"].append(points)
            self._pending_chunks[key]["header"] = header

        # If this chunk has fewer than 80 points (or 0), it is the final chunk of the sweep
        if len(points) < 80 and key in self._pending_chunks:
            curr = self._pending_chunks.pop(key)
            merged = np.vstack(curr["chunks"]) if curr["chunks"] else np.empty((0, 4), dtype=np.float32)
            return curr["header"], merged

        return completed_frame

    def push(
        self, header: SIHHeader, points: np.ndarray
    ) -> Optional[SyncedFramePair]:
        """
        Pushes a sweep into the queue (aggregating chunks if necessary) and checks
        for an available synchronized counterpart.
        """
        # 1. Aggregate chunks
        sweep = self.push_chunk(header, points)
        if sweep is None:
            return None

        full_header, full_points = sweep
        now_ts = full_header.timestamp

        if full_header.sensor_type == 1:
            self.uav_queue.append((full_header, full_points))
        elif full_header.sensor_type == 2:
            self.ugv_queue.append((full_header, full_points))
        else:
            return None

        # 2. Purge stale frames
        self._purge_stale(now_ts)

        # 3. Attempt to find best match or emit unpaired active sensor sweep
        return self._find_match(now_ts)

    def _purge_stale(self, current_ts: float):
        """Purges frames older than the sliding temporal window."""
        while self.uav_queue and (current_ts - self.uav_queue[0][0].timestamp) > self.window_sec:
            self.uav_queue.popleft()
            self.dropped_stale_count += 1

        while self.ugv_queue and (current_ts - self.ugv_queue[0][0].timestamp) > self.window_sec:
            self.ugv_queue.popleft()
            self.dropped_stale_count += 1

    def _find_match(self, current_ts: float) -> Optional[SyncedFramePair]:
        """
        Scans both queues to find the closest temporal match within tolerance.
        If only one vehicle is currently active or transmitting, emits its sweep
        so the perception mathematics engine never starves.
        """
        # Case A: Both queues have data -> synchronize and fuse
        if self.uav_queue and self.ugv_queue:
            best_diff = float("inf")
            best_uav_idx = -1
            best_ugv_idx = -1

            for u_idx, (u_hdr, _) in enumerate(self.uav_queue):
                for g_idx, (g_hdr, _) in enumerate(self.ugv_queue):
                    if u_hdr.frame_id == g_hdr.frame_id:
                        diff = abs(u_hdr.timestamp - g_hdr.timestamp)
                        best_diff = diff
                        best_uav_idx = u_idx
                        best_ugv_idx = g_idx
                        break

                    diff = abs(u_hdr.timestamp - g_hdr.timestamp)
                    if diff <= self.sync_tolerance_sec and diff < best_diff:
                        best_diff = diff
                        best_uav_idx = u_idx
                        best_ugv_idx = g_idx

                if best_uav_idx != -1 and self.uav_queue[best_uav_idx][0].frame_id == self.ugv_queue[best_ugv_idx][0].frame_id:
                    break

            if best_uav_idx != -1 and best_ugv_idx != -1:
                u_hdr, u_pts = self.uav_queue[best_uav_idx]
                g_hdr, g_pts = self.ugv_queue[best_ugv_idx]

                for _ in range(best_uav_idx + 1):
                    self.uav_queue.popleft()
                for _ in range(best_ugv_idx + 1):
                    self.ugv_queue.popleft()

                self.emitted_pairs_count += 1
                return SyncedFramePair(
                    uav_header=u_hdr,
                    uav_points=u_pts,
                    ugv_header=g_hdr,
                    ugv_points=g_pts,
                    time_delta_ms=best_diff * 1000.0,
                )

        # Case B: UAV has frames waiting and UGV is delayed past tolerance
        if self.uav_queue:
            u_hdr, u_pts = self.uav_queue[0]
            if (current_ts - u_hdr.timestamp) >= self.sync_tolerance_sec:
                self.uav_queue.popleft()
                self.emitted_pairs_count += 1
                return SyncedFramePair(
                    uav_header=u_hdr,
                    uav_points=u_pts,
                    ugv_header=None,
                    ugv_points=np.empty((0, 4), dtype=np.float32),
                    time_delta_ms=0.0,
                )

        # Case C: UGV has frames waiting and UAV is delayed past tolerance
        if self.ugv_queue:
            g_hdr, g_pts = self.ugv_queue[0]
            if (current_ts - g_hdr.timestamp) >= self.sync_tolerance_sec:
                self.ugv_queue.popleft()
                self.emitted_pairs_count += 1
                return SyncedFramePair(
                    uav_header=None,
                    uav_points=np.empty((0, 4), dtype=np.float32),
                    ugv_header=g_hdr,
                    ugv_points=g_pts,
                    time_delta_ms=0.0,
                )

        return None
