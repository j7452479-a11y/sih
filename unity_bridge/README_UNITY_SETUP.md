# SIH26053 - MUM-T Tactical Edge Perception Engine: Unity Proving Ground Setup Guide

This guide details the native **Unity 6 Tactical Proving Ground** and perception bridge. The entire simulation runs in Unity 6, providing deterministic 20 Hz multi-threaded LiDAR raycasting, circular drone flight, elliptical tethered UGV traversal, and screen-space military reticles in Commander and Soldier POVs.

---

## 1. Quick Automated Setup (One Command)

To automatically compile the full square tactical village scene in headless batchmode:
```bash
python unity_bridge/unity_automation.py --build
```
This builds `Assets/Scenes/TacticalProvingGround.unity` containing the entire 46-structure village, church spire, bridge underpass, NavMesh, hostiles, drone, and cameras.

To open the project in Unity Editor:
```bash
python unity_bridge/unity_automation.py --open
```

---

## 2. Scene Architecture: Square Tactical Village Layout

The scene is constructed within a 110m × 110m square perimeter with cobblestone avenues:

| Structure | Dimensions $(L \times W \times H)$ | Position $(X, Y, Z)$ | Layer | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Square Ground** | $110\text{m} \times 0.3\text{m} \times 110\text{m}$ | $(0, -0.15\text{m}, 0)$ | `Road` | Flat dark grey cobblestone base with perimeter walls. |
| **Central Overpass Bridge** | $40\text{m} \times 1.2\text{m} \times 9\text{m}$ | $(0, 5.0\text{m}, 0)$ | `Obstacle` | **Underpass Void:** Clearance of $4.4\text{m}$ below bridge deck for UGV traversal. |
| **Gothic Church + Spire** | $14\text{m} \times 10\text{m} \times 22\text{m}$ (Spire apex: $18\text{m}$) | $(25\text{m}, 5\text{m}, 25\text{m})$ | `Building` | Tests high-altitude vertical interval boundaries and z-axis partitioning. |
| **4-Story High-Rise Blocks** | $14\text{m} \times 14\text{m} \times 12\text{m}$ | $(-26\text{m}, 7\text{m}, 26\text{m})$ | `Building` | High-rise urban canyon and occlusion. |
| **Commercial & Storehouses**| $10\text{m} \times 10.5\text{m} \times 8\text{m}$ | $(-14\text{m}, 5.25\text{m}, 34\text{m})$ | `Building` | Multi-story industrial structures. |
| **Residential Houses & Barns** | $12\text{m} \times 7\text{m} \times 10\text{m}$ | $(-25\text{m}, 3.5\text{m}, -25\text{m})$ | `Building` | Low-rise residential quarter. |
| **Primary Stone Occlusion Wall**| $16\text{m} \times 2.5\text{m} \times 0.8\text{m}$ | $(0, 1.25\text{m}, -14\text{m})$ | `Obstacle` | Target Bravo walks behind this to test Kalman filter coasting. |
| **Perimeter Watchtowers** | $4.5\text{m} \times 8\text{m} \times 4.5\text{m}$ | $(\pm 44\text{m}, 4\text{m}, \pm 44\text{m})$ | `Obstacle` | Elevated corner outposts. |
| **Cardinal Bunkers** | $6\text{m} \times 2\text{m} \times 3.5\text{m}$ | Cardinal entrances | `Obstacle` | Sandbag fortifications. |

---

## 3. Autonomous MUM-T Kinematics

### A. UAV Drone (Circular Flight Path & Nadir LiDAR)
- **Orbit Parameters:** Radius $R = 32\text{m}$, Altitude $= +30\text{m}$ AGL, speed $14^\circ/\text{s}$ ($\sim 25\text{s}$ orbit).
- **LiDAR Matrix:** 16 channels × 20 beams/channel, $-90^\circ$ to $-32^\circ$ pitch, $360^\circ$ continuous azimuth downward conical scan.
- **Port:** Streams binary SIH1 point clouds to UDP `127.0.0.1:5001`.

### B. UGV Tethered RC Car (Elliptical Ground Track & Underpass Patrol)
- **Elliptical Parameters:** Semi-major axis $A = 26\text{m}$, semi-minor axis $B = 16\text{m}$, passing directly through the central bridge underpass void ($Z = 0$).
- **Dynamic Catenary Tether:** Connects circular drone to elliptical RC car; monitors tension envelope (14m–20m).
- **Port:** Streams binary SIH1 point clouds to UDP `127.0.0.1:5002`.

---

## 4. Multi-POV Camera Controller & AR Reticle HUD

### Camera Sockets & Hotkeys
- **`[1]` Soldier AR Visor POV:** First-person ground view looking from South entrance into village square and underpass. Displays AR tactical crosshair, compass tape, underpass clearance gauge, and MIL-STD-2525 diamond reticles.
- **`[2]` UAV Aerial Chase POV:** Third-person trailing chase camera behind the drone.
- **`[3]` UGV Rover Dash POV:** Hood bumper camera speeding through the village underpass.
- **`[4]` Commander Tactical POV:** Elevated high-angle command perspective showing the entire square village, drone orbit, and hostile tracks.
- **`Space`:** Instant toggle between Soldier Visor and Commander Overview.

### Threat Reticle Features (`ThreatReticleManager.cs`)
- Listens on UDP Port `5003` for backend JSON telemetry.
- Fallback autonomous scene tracker when offline.
- MIL-STD-2525 Diamond box over hostiles:
  - `[LOCKED - LOS]` in Red when in direct line-of-sight.
  - `[COASTING - OCCLUDED]` in Tactical Amber when walking behind the stone wall.
  - Euclidean Range ($m$), Speed ($m/s$), and Target ID tags.
- On-screen interactive bottom dock buttons for clicking between POVs.

---

## 5. Running the Complete System

1. **Start the Python Perception Hub:**
   ```bash
   python -m uvicorn c2_interface.server:app --host 0.0.0.0 --port 8000
   ```
2. **Launch Unity Simulation:**
   Open `SIH_TacticalSim` in Unity 6 and press **Play** (or run `python unity_bridge/unity_automation.py --open`).
3. **Open Web Dashboards:**
   - Soldier Visor HUD: `http://localhost:8000/static/soldier_eud.html`
   - Commander C2 Radar: `http://localhost:8000/static/c2_dashboard.html`
   - 3D WebGL Proving Ground: `http://localhost:8000/static/tactical_sim_3d.html`
