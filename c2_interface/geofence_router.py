"""
Dynamic Threat Geofencing & Bandwidth Router
Applies distance-based rate limiting to prevent front-line radio saturation.
"""

import time
from typing import Dict, List, Optional, Tuple
import numpy as np

from config import (
    THREAT_GEOFENCE_RADIUS_M,
    NEAR_FIELD_STREAM_RATE_HZ,
    FAR_FIELD_STREAM_RATE_HZ,
)
from tracking.mtt_manager import TrackedTarget

class GeofenceRouter:
    """
    Filters target telemetry based on soldier engagement perimeter:
    - Within 50m: Stream at full 20 Hz rate (critical weapons engagement zone)
    - Beyond 50m: Rate-limited to 0.5 Hz (1 update every 2 sec, < 2 KB/s bandwidth)
    """

    def __init__(
        self,
        geofence_radius: float = THREAT_GEOFENCE_RADIUS_M,
        near_rate_hz: float = NEAR_FIELD_STREAM_RATE_HZ,
        far_rate_hz: float = FAR_FIELD_STREAM_RATE_HZ,
    ):
        self.geofence_radius = geofence_radius
        self.near_interval_sec = 1.0 / near_rate_hz
        self.far_interval_sec = 1.0 / far_rate_hz
        self.last_sent_timestamps: Dict[int, float] = {}

    def filter_tracks_for_soldier(
        self, tracks: List[TrackedTarget], soldier_pos: Tuple[float, float] = (0.0, 0.0)
    ) -> List[Dict]:
        """
        Returns filtered list of tracks ready for soldier EUD transmission,
        annotated with threat alerts if inside the 50m danger ring.
        """
        now = time.time()
        emitted = []
        sx, sy = soldier_pos

        for track in tracks:
            tx, ty, tz = track.position_3d
            dist = float(np.sqrt((tx - sx) ** 2 + (ty - sy) ** 2))
            inside_perimeter = dist <= self.geofence_radius

            # Rate-limiting check
            required_interval = self.near_interval_sec if inside_perimeter else self.far_interval_sec
            last_ts = self.last_sent_timestamps.get(track.track_id, 0.0)

            if (now - last_ts) >= required_interval:
                self.last_sent_timestamps[track.track_id] = now
                vx, vy = track.velocity_2d

                emitted.append({
                    "track_id": track.track_id,
                    "x": round(tx, 2),
                    "y": round(ty, 2),
                    "z": round(tz, 2),
                    "distance_m": round(dist, 1),
                    "speed_mps": round(track.speed, 2),
                    "heading_deg": round(track.heading_deg, 1),
                    "inside_50m": inside_perimeter,
                    "state": track.state.name,
                    "provenance": track.provenance.name,
                })

        return emitted
