import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import time
import numpy as np
from ingestion.jitter_buffer import TemporalJitterBuffer
from ingestion.udp_protocol import pack_sih1_packet, unpack_sih1_packet
from tracking.tier_dbscan import TierDBSCAN
from tracking.mtt_manager import MTTManager

def test_continuous_jitter_and_coasting_pipeline():
    jb = TemporalJitterBuffer()
    dbscan = TierDBSCAN()
    mtt = MTTManager(max_misses=50)

    confirmed_seen = False
    coasting_seen = False

    for f in range(1, 16):
        ts = time.time()
        
        # 80 points
        uav = np.zeros((80, 4), dtype=np.float32)
        # Alpha always visible
        uav[:8, :3] = [-10.0, 5.0, 1.0] + np.random.normal(0, 0.05, (8, 3))
        uav[:8, 3] = 8.0
        
        # Bravo visible only in frames 1-4 and 12-15 (occluded in frames 5-11 behind wall)
        if f <= 4 or f >= 12:
            uav[8:16, :3] = [5.0, -14.0, 1.0] + np.random.normal(0, 0.05, (8, 3))
            uav[8:16, 3] = 8.0
            
        ugv = np.copy(uav)
        
        pkt_u = pack_sih1_packet(f, ts, 1, uav)
        pkt_g = pack_sih1_packet(f, ts + 0.002, 2, ugv)
        
        h_u, pts_u = unpack_sih1_packet(pkt_u)
        h_g, pts_g = unpack_sih1_packet(pkt_g)
        
        jb.push(h_u, pts_u)
        pair = jb.push(h_g, pts_g)
        
        if pair:
            comb = np.vstack([pair.uav_points, pair.ugv_points])
            clusters = dbscan.cluster_points(comb)
            tracks = mtt.update(clusters)
            states = [t.state.name for t in tracks]
            if "CONFIRMED" in states:
                confirmed_seen = True
            if "COASTING" in states:
                coasting_seen = True

    assert confirmed_seen, "Should have confirmed tracks before occlusion"
    assert coasting_seen, "Bravo should enter COASTING when occluded behind wall"
