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
    Sliding temporal ring buffer.
    Maintains independent queues for UAV and UGV sweeps and emits matched pairs
    whose timestamps are within +/- 25ms.
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

        self.dropped_stale_count = 0
        self.emitted_pairs_count = 0

    def push(
        self, header: SIHHeader, points: np.ndarray
    ) -> Optional[SyncedFramePair]:
        """
        Inserts a new sensor sweep into the corresponding queue and checks
        for an available synchronized counterpart.
        """
        now_ts = header.timestamp

        if header.sensor_type == 1:
            self.uav_queue.append((header, points))
        elif header.sensor_type == 2:
            self.ugv_queue.append((header, points))
        else:
            return None

        # Purge stale frames from both queues
        self._purge_stale(now_ts)

        # Attempt to find best match
        return self._find_match()

    def _purge_stale(self, current_ts: float):
        """Purges frames older than the sliding temporal window."""
        while self.uav_queue and (current_ts - self.uav_queue[0][0].timestamp) > self.window_sec:
            self.uav_queue.popleft()
            self.dropped_stale_count += 1

        while self.ugv_queue and (current_ts - self.ugv_queue[0][0].timestamp) > self.window_sec:
            self.ugv_queue.popleft()
            self.dropped_stale_count += 1

    def _find_match(self) -> Optional[SyncedFramePair]:
        """Scans both queues to find the closest temporal match within tolerance."""
        if not self.uav_queue or not self.ugv_queue:
            return None

        best_diff = float("inf")
        best_uav_idx = -1
        best_ugv_idx = -1

        for u_idx, (u_hdr, _) in enumerate(self.uav_queue):
            for g_idx, (g_hdr, _) in enumerate(self.ugv_queue):
                # Match either by identical frame_id or within delta_t tolerance
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
            # Extract matched frames and clear up to matched index to prevent repeats
            u_hdr, u_pts = self.uav_queue[best_uav_idx]
            g_hdr, g_pts = self.ugv_queue[best_ugv_idx]

            # Pop elements up to the matched indices
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

        return None
