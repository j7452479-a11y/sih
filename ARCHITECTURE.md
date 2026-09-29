# System Architecture Specification

## Tactical Edge Perception Engine & Civilian EV Simulation (SIH26053)

---

## 1. System Philosophy & Edge Constraints

The system addresses the fundamental dilemma of real-time robotic perception: **High Spatial Fidelity vs. Extreme Edge Compute Constraints (SWaP)**.

Deploying dense 3D voxel grids over a $100\text{ m} \times 100\text{ m} \times 20\text{ m}$ perimeter at $5\text{ cm}$ resolution yields:
$$\frac{100}{0.05} \times \frac{100}{0.05} \times \frac{20}{0.05} = 2000 \times 2000 \times 400 = 1.6 \times 10^9 \text{ voxels}$$

At 1 byte per voxel, this demands **$1.6\text{ GB}$ of RAM per frame** and $>32\text{ GB/s}$ of continuous memory bandwidth at $20\text{ Hz}$.

### The Mathematical Solution: 4-Tier Foveated MLS
By leveraging concentric foveation and Capped Multi-Level Surface intervals ($K=3$), memory requirements collapse to **$12.16\text{ MB}$ ($>99.24\%$ reduction)** while preserving vertical bridge underpasses and high-altitude spires.

```
       [UAV Nadir LiDAR: UDP 5001]           [UGV Horizontal LiDAR: UDP 5002]
                    \                                    /
                     v                                  v
         +------------------------------------------------------+
         |     TEMPORAL JITTER RING BUFFER (ingestion/)         |
         |    - Window: 50ms | Max Frame Delta |dt| <= 25ms     |
         +------------------------------------------------------+
                                    |
                                    v
         +------------------------------------------------------+
         |        SE(3) POSE GRAPH REGISTRATION (core_math/)     |
         |         T_CD = Inv(T_WC) * T_WD (Barfoot Ch. 7)      |
         +------------------------------------------------------+
                                    |
                                    v
         +------------------------------------------------------+
         |     4-TIER CONCENTRIC FOVEATED PARTITIONING          |
         |   Tier 1 (0-10m): 5cm  | Tier 2 (10-30m): 10cm       |
         |   Tier 3 (30-60m): 20cm| Tier 4 (60-100m): 50cm      |
         +------------------------------------------------------+
                                    |
                                    v
         +------------------------------------------------------+
         |        MULTI-LEVEL SURFACE (MLS) ENGINE              |
         |  - Triebel et al. Vertical Clustering                |
         |  - Gap Threshold: 1.0m | Max Intervals: K=3          |
         |  - 4.5m Bridge Underpass Void Preserved              |
         +------------------------------------------------------+
                                    |
                                    v
         +------------------------------------------------------+
         |      MULTI-TARGET TRACKING & OCCLUSION COASTING      |
         |  - Tier-Adaptive DBSCAN Dynamic Target Extraction    |
         |  - 2D Constant Velocity (CWNA) Kalman Filter         |
         |  - Hungarian Bipartite Matcher (Mahalanobis gate)    |
         |  - 200-Frame Occlusion Coasting (Stone Wall Defense) |
         +------------------------------------------------------+
                                    |
                    +---------------+---------------+
                    |                               |
                    v                               v
    +------------------------------+  +-------------------------------+
    |  C2 TELEMETRY & AR HUD HUB   |  |   DEFENSE C4ISR STANDARDS     |
    |  - UDP 5003 Target Streamer  |  |  - WGS-84 Ellipsoidal Geodesy |
    |  - 20 Hz WebSocket Server    |  |  - Cursor-on-Target (CoT) XML |
    |  - Commander Radar (/c2)     |  |  - MIL-STD-2525 Symbology     |
    |  - Soldier ATAK EUD (/soldier|  +-------------------------------+
    +------------------------------+
```

---

## 2. Dual Operational Domains

### Domain A: Military Manned-Unmanned Teaming (MUM-T)
- **Airborne Reconnaissance:** UAV orbiting in a $R=32\text{ m}$ circle at $+30\text{ m}$ nadir angle, mapping rooftops and perimeter walls.
- **Underpass Infiltration:** Tethered ground rover traversing an elliptical path ($A=26\text{ m}, B=16\text{ m}$) under a $4.5\text{ m}$ clearance bridge.
- **Hostile Interception:** Multi-target Kalman tracking locking onto dynamic combatants, with 200-frame predictive coasting when line-of-sight is interrupted by $2.2\text{ m}$ stone walls.

### Domain B: Autonomous Civilian Electric Vehicle (EV)
- **Sensor Geometry:** Dual-tier automotive LiDAR comprising a roof-mounted long-range scanner ($Z=1.8\text{ m}$, 120° FOV, 200m range) and front bumper obstacle scanner ($Z=0.5\text{ m}$, near-field ground clearance).
- **Asymmetric Vertical Pitch:** Foveated vertical region of interest focused on the horizon ($\phi \in [-2^\circ, +2^\circ]$) with grazing-angle compensation for road asphalt reflection.
- **Active Safety & Collision Avoidance:** Time-to-Collision (TTC) predictive emergency braking guarding against suddenly crossing pedestrians.

---

## 3. Detailed Specifications Directory
For comprehensive mathematical equations, algorithm proofs, and test protocols, refer to:
- [MASTER_TACTICAL_PERCEPTION_ENGINE_SPECIFICATION.md](file:///b:/sih/MASTER_TACTICAL_PERCEPTION_ENGINE_SPECIFICATION.md)
- [PROJECT_MASTER_PLAN.md](file:///b:/sih/PROJECT_MASTER_PLAN.md)
- [HOW_AUTOMOTIVE_EV_LIDAR_WORKS.md](file:///b:/sih/HOW_AUTOMOTIVE_EV_LIDAR_WORKS.md)
- [MULTI_SCREEN_SIMULATION_SYSTEM_SPECIFICATION.md](file:///b:/sih/docs/MULTI_SCREEN_SIMULATION_SYSTEM_SPECIFICATION.md)
