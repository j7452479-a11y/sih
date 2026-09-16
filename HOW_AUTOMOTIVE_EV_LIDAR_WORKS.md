# How Automotive LiDAR Works on an Electric Vehicle (EV)
### Comprehensive Scientific & Engineering Specification | SIH26053

---

## 1. Executive Summary & Core Physical Paradigm Shift

When transitioning perception from an aerial unmanned aerial vehicle (UAV) to an ego-centric ground electric vehicle (EV), the fundamental physics of the sensor data undergo an absolute paradigm shift.

| Dimension | Aerial Drone LiDAR (MUM-T UAV) | Automotive EV LiDAR (Ground Ego-Vehicle) |
| :--- | :--- | :--- |
| **Vantage Point** | Aerial / Oblique / Nadir ($+30\text{ m}$ to $+100\text{ m}$ AGL) | Strictly Ego-Centric Horizon ($+0.5\text{ m}$ to $+2.0\text{ m}$) |
| **Top-Down Access** | Native (Sensor is physically in the sky) | **Zero Access** (No aerial camera exists; ground-only) |
| **Incidence Angle on Ground** | Steep ($\theta_{\text{inc}} \approx 0^\circ$–$30^\circ$ to normal) | **Grazing Angle** ($\theta_{\text{inc}} \ge 88^\circ$, grazing $\psi \le 2^\circ$) |
| **Ground Return Pattern** | Uniform planar grid | **Non-linear expanding concentric ellipses / hyperbolas** |
| **Occlusion Profile** | Narrow vertical shadows behind structures | **Massive radial horizontal shadow cones** |
| **Ego-Dynamics Impact** | Yaw/Roll flight drift | **Suspension pitch dive ($-2^\circ$ to $-3.5^\circ$) under AEB braking** |
| **Overhead Structures** | Seen from above (roofs, bridge decks) | **Seen from underneath (tunnels, bridge ceiling clearances)** |
| **Perception Processing** | 2.5D Elevation Maps / Octrees | **Spherical Range Images ($H \times W$) / Sparse Voxel Convolutions** |

---

## 2. Sensor Placement & Asymmetric Beam Geometry

### 2.1 Physical Sensor Mounting Locations on an EV
1. **Roof Sensor Pod ($Z = 1.7\text{ m}$–$2.2\text{ m}$):**
   - Mounted centrally above the windshield header.
   - Provides unobstructed long-range forward detection ($150\text{ m}$–$250\text{ m}$).
   - Representative hardware: **Hesai AT128 / FT120**, **Luminar Iris ($1550\text{ nm}$)**, **Innovusion Falcon**.
2. **Bumper / Grille Pods ($Z = 0.5\text{ m}$–$0.7\text{ m}$):**
   - Solid-state flash LiDARs integrated into the front bumper.
   - Fills the near-field ground blind-zone ($0\text{ m}$–$3\text{ m}$) for road debris, potholes, and low curbs.

```
       Roof LiDAR (+1.8m)
          [==] <---------------- Horizontal FoV: 120°, Vertical: -25° to +15°
         /    \
        /  EV  \
   ===+==========+===
  [O]              [O]   <--- Front Bumper LiDAR (+0.5m)
-------------------------------------------------------------- (Asphalt Road Z = 0m)
```

### 2.2 Asymmetric Vertical Beam Distribution (Foveated ROI)
Unlike aerial sensors that distribute laser pulses uniformly, automotive LiDAR concentrates laser beams where threats appear:
- **Region of Interest (Horizon, $\phi \in [-2^\circ, +2^\circ]$):** High angular resolution ($0.1^\circ$). Enables detection of distant vehicles and pedestrians at $100\text{ m}$–$200\text{ m}$.
- **Road Surface Channels ($\phi \in [-3^\circ, -25^\circ]$):** Coarser angular resolution ($0.5^\circ$–$1.5^\circ$). Strikes the asphalt between $1.5\text{ m}$ and $30\text{ m}$ in front of the vehicle.
- **Overhead Channels ($\phi \in [+2^\circ, +15^\circ]$):** Sparse channels to detect overhead traffic lights, gantry signs, and bridge underpass ceilings.

---

## 3. Grazing-Angle Reflection Physics on Asphalt

### 3.1 Non-Linear Ground Return Distribution
Let an automotive LiDAR be mounted at height $h = 1.8\text{ m}$ above a planar asphalt roadway. For a laser channel tilted downward at pitch angle $\alpha_i < 0$:

$$d_i = \frac{h}{\tan(-\alpha_i)}$$

Because the laser beam strikes the asphalt at shallow grazing angles ($\psi \le 2^\circ$), a tiny change in elevation angle $\Delta \alpha$ creates an enormous leap in distance along the road:

$$\frac{\partial d}{\partial \alpha} = \frac{h}{\sin^2(-\alpha)}$$

At $\alpha = -1.0^\circ$ ($0.01745\text{ rad}$):
$$d = \frac{1.8}{\tan(1^\circ)} \approx 103.1\text{ m}$$
$$\frac{\partial d}{\partial \alpha} \approx \frac{1.8}{(0.01745)^2} \approx 5,910\text{ m/rad} \approx 103.1\text{ m per degree}$$

**Physical Result:**
- At $0\text{ m}$ to $10\text{ m}$, ground returns form dense, tight concentric arcs.
- Beyond $30\text{ m}$, ground returns stretch into sparse, widely separated hyperbolic rings.
- Asphalt reflectivity at grazing angles drops sharply due to specular forward scattering, leaving low-intensity retro-returns except on retroreflective road paint and road signs.

---

## 4. Radial Occlusion Shadows ("Blind Cones")

Photons propagate in straight lines. When a solid object (e.g., a parked delivery van of width $w=2.0\text{ m}$ and height $h=2.4\text{ m}$) sits at distance $d_0 = 12.0\text{ m}$:

$$\mathcal{S}_{\text{cone}} = \left\{ \mathbf{p} = (x, y, z) \;\middle|\; \exists \lambda \in (0, 1) \text{ s.t. } \lambda \mathbf{p} + (1-\lambda)\mathbf{p}_{\text{lidar}} \in \mathcal{V}_{\text{obstacle}} \right\}$$

```
                   Parked Van (Occluder)
 LiDAR [EV]  =================> [  VAN  ]
   (0,0)                           \     \
                                    \     \  Radial Occlusion Shadow Cone (Blind Zone)
                                     \     \  Zero returns reach the road
                                      \     \
                                       v     v
                                     [Pedestrian Emerges Here!]
```

### Automotive Safety Consequence:
An autonomous EV **cannot see through or behind** the delivery van. If a pedestrian (Vulnerable Road User, VRU) walks across the street from behind the van, they are completely invisible until they step outside the occlusion cone. The perception engine must:
1. Identify the boundary of the occlusion shadow.
2. Flag the high-risk edge as an **Emergence Zone**.
3. Dynamically coast kinematic track states using Kalman filters until direct line-of-sight is established.

---

## 5. Vehicle Dynamic Pitch Compensation under Braking ($SE(3)$)

When an autonomous EV detects a pedestrian and executes Automatic Emergency Braking (AEB) with deceleration $a = -7.5\text{ m/s}^2$:
- Load transfers forward onto the front suspension struts.
- The vehicle pitches nose-down by $\Delta \theta_{\text{pitch}} \in [-2.0^\circ, -3.5^\circ]$.

### The Uncompensated Catastrophe:
If the LiDAR point cloud is processed without pitch compensation:
- A horizontal beam at $0^\circ$ now strikes the road at $d = \frac{1.8\text{ m}}{\tan(2.5^\circ)} \approx 41.2\text{ m}$.
- The perception system misinterprets flat road asphalt as a vertical wall rising in front of the vehicle, creating false-positive phantom braking loops!

### The Mathematical Solution:
The EV's onboard 6-DOF IMU measures suspension pitch rate at 200 Hz. The perception engine applies an instantaneous $SE(3)$ transformation to rotate every raw point back into the gravity-aligned inertial frame:

$$\mathbf{p}_{\text{corrected}} = \mathbf{R}_y(-\Delta \theta_{\text{pitch}}) \cdot \mathbf{R}_x(-\Delta \phi_{\text{roll}}) \cdot \mathbf{p}_{\text{raw}} + \mathbf{t}_{\text{suspension}}$$

$$\begin{bmatrix} X' \\ Y' \\ Z' \\ 1 \end{bmatrix} = \begin{bmatrix} 1 & 0 & 0 & 0 \\ 0 & \cos\theta & -\sin\theta & 0 \\ 0 & \sin\theta & \cos\theta & \Delta z \\ 0 & 0 & 0 & 1 \end{bmatrix} \begin{bmatrix} X \\ Y \\ Z \\ 1 \end{bmatrix}$$

---

## 6. Native Spherical Range-View (Range Image 2D Projection)

High-performance automotive edge computers (e.g., NVIDIA DRIVE Orin Nano, Xavier) avoid allocating gigabytes for dense 3D voxel grids ($O(N^3)$). Instead, modern automotive perception backbones (RangeNet++, SalsaNext, LaserNet) project raw laser returns onto a **2D Cylindrical / Spherical Range Image**:

$$u = \left\lfloor \frac{\text{atan2}(y, x) - \theta_{\min}}{\Delta \theta} \right\rfloor \in [0, W-1]$$

$$v = \left\lfloor \frac{\arcsin(z / r) - \phi_{\min}}{\Delta \phi} \right\rfloor \in [0, H-1]$$

Where:
- $H = 32$ or $64$ (number of vertical laser rings).
- $W = 64$ to $1024$ (horizontal angular discretization steps).
- Pixel values store a multi-channel feature tensor: $[R, X, Y, Z, \text{Intensity}]$.

```
Row 31 (+15°) | [Sky / Overhead Sign / Underpass Deck]
      ...     | [Distant Vehicles / Horizon at 100m]
Row 16 (  0°) | [Pedestrians / Obstacles at Eye Level]
      ...     | [Near-field Asphalt Road Grazing Arcs]
Row  0 (-25°) | [Front Bumper Ground Returns]
              +---------------------------------------------
              Col 0 (-60° Left)            Col 63 (+60° Right)
```

Standard, highly optimized 2D convolutions run directly on this image matrix at $>60\text{ FPS}$ with sub-$15\text{ ms}$ latency and under $15\text{ MB}$ of memory.

---

## 7. Longitudinal Clearance Verification (Capped MLS)

When an EV approaches an underpass, tunnel, or parking structure, it must decide whether the vehicle can pass underneath safely.

### The 2D Occupancy Grid Failure:
A 2D occupancy grid collapses all $Z$-points into a flat 2D cell. The ceiling deck of the underpass at $Z = 3.2\text{ m}$ is projected onto the ground, marking the road as permanently occupied (blocked).

### The Capped MLS Solution:
The Capped Multi-Level Surface (MLS) engine divides space into vertical columns where each cell stores a list of non-overlapping solid intervals $[z_{\min}, z_{\max}]$:
- Interval 0 (Road surface): $[0.0\text{ m}, 0.15\text{ m}]$
- Free traversable headroom: $(0.15\text{ m}, 3.20\text{ m})$
- Interval 1 (Underpass concrete deck): $[3.20\text{ m}, 4.00\text{ m}]$

$$\text{Headroom Clearance} = Z_{\text{ceiling, min}} - Z_{\text{vehicle\_roof}} = 3.20\text{ m} - 1.60\text{ m} = +1.60\text{ m}$$
$$\text{Safety Threshold} = +0.80\text{ m} \implies \text{STATUS: PASS TRAVERSABLE}$$

---

## 8. Dynamic Braking Corridor & Time-to-Collision (TTC)

The EV maintains a dynamic swept braking corridor projected along its forward trajectory:

$$\mathcal{C}(t) = \left\{ (x, y) \;\middle|\; |x| \le \frac{W_{\text{corridor}}}{2} = 1.75\text{ m}, \quad 0 \le y \le d_{\text{lookahead}} \right\}$$

$$d_{\text{lookahead}} = v_{\text{ego}} \cdot t_{\text{lookahead}} + \frac{v_{\text{ego}}^2}{2 |a_{\max}|}$$

At $v_{\text{ego}} = 10.0\text{ m/s}$ ($36\text{ km/h}$), $t_{\text{lookahead}} = 1.8\text{ s}$, and $a_{\max} = -7.5\text{ m/s}^2$:
$$d_{\text{lookahead}} = 10.0 \times 1.8 + \frac{100}{15.0} = 18.0 + 6.67 = 24.67\text{ m} \approx 25.0\text{ m}$$

When an obstacle enters this corridor at distance $d_{\text{target}}$ with relative closing velocity $v_{\text{rel}}$:
$$\tau_{\text{TTC}} = \frac{d_{\text{target}}}{v_{\text{rel}}}$$

- If $\tau_{\text{TTC}} > 3.0\text{ s}$: Cruise Nominal (Green corridor).
- If $1.8\text{ s} < \tau_{\text{TTC}} \le 3.0\text{ s}$: Predictive Warning (Amber corridor).
- If $\tau_{\text{TTC}} \le 1.8\text{ s}$: **Automatic Emergency Braking (AEB Engage - Red corridor, full deceleration).**

---

## 9. Conclusion

By grounding the EV simulation strictly in these physical principles, the system eliminates unrealistic top-down views, accurately demonstrates grazing angle point density, models realistic radial occlusion cones, compensates for dynamic suspension dive, and validates safe overhead clearances using Capped MLS.
