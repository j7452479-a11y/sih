# Chapter 6: Estimation for Kinematic Models
Estimation with Applications to Tracking and Navigation: Theory, Algorithms and Software Authors: Yaakov Bar-Shalom, X. Rong Li, Thiagalingam Kirubarajan
## 6.1 Introduction
Kinematic models describe the motion of a target (position, velocity, acceleration) without considering the forces causing the motion. In target tracking and state estimation from sensors like LiDAR and radar, choosing an appropriate kinematic state model and corresponding process noise covariance Q is fundamental for Kalman filtering.
---
## 6.2 Continuous-Time Models for Target Kinematics
Continuous-time target motion is represented by stochastic differential equations: \\dot{x}(t) = F x(t) + G \\tilde{w}(t) where:
- x(t) is the continuous state vector (e.g., position, velocity, acceleration).
- F is the system dynamic matrix.
- G is the process noise gain matrix.
- \\tilde{w}(t) is zero-mean continuous white Gaussian noise with power spectral density (PSD) \\tilde{q}: E\[\\tilde{w}(t)\\tilde{w}(\\tau)'\] = \\tilde{q} \\delta(t - \\tau)
### 6.2.1 White Noise Acceleration Model (Nearly Constant Velocity / CV)
- State vector (1D): x = \[p, \\dot{p}\]^T = \[x, \\dot{x}\]^T
- Acceleration is modeled as pure continuous white noise: \\ddot{p}(t) = \\tilde{w}(t).
- Continuous system matrices: F = \\begin{bmatrix} 0 & 1 \\\\ 0 & 0 \\end{bmatrix}, \\quad G = \\begin{bmatrix} 0 \\\\ 1 \\end{bmatrix}
- Suitable for non-maneuvering targets or targets with mild, random accelerations.
### 6.2.2 Wiener-Sequence Acceleration Model (Nearly Constant Acceleration / CA)
- State vector (1D): x = \[p, \\dot{p}, \\ddot{p}\]^T
- Jerk (derivative of acceleration) is modeled as continuous white noise: \\dddot{p}(t) = \\tilde{w}(t).
- Continuous system matrices: F = \\begin{bmatrix} 0 & 1 & 0 \\\\ 0 & 0 & 1 \\\\ 0 & 0 & 0 \\end{bmatrix}, \\quad G = \\begin{bmatrix} 0 \\\\ 0 \\\\ 1 \\end{bmatrix}
- Suitable for targets undergoing sustained or gradual acceleration changes.
### 6.2.3 Singer Model (First-Order Gauss-Markov Acceleration Model)
- Acceleration is modeled as a first-order stationary Gauss-Markov process with auto-correlation R\_a(\\tau) = \\sigma\_a^2 e^{-\\alpha |\\tau|}, where \\alpha = 1/\\tau\_m is the reciprocal of the maneuver time constant \\tau\_m: \\dot{a}(t) = -\\alpha a(t) + \\tilde{w}(t)
- Power spectral density: \\tilde{q} = 2 \\alpha \\sigma\_a^2.
- Transition matrix incorporates the exponential decay e^{-\\alpha T}.
---
## 6.3 Discrete-Time Models for Target Kinematics
For discrete measurement intervals T = t\_{k+1} - t\_k, the discrete-time state equation is: x\_{k+1} = F\_k x\_k + v\_k where F\_k = e^{F T} and v\_k is a discrete zero-mean white Gaussian sequence with covariance matrix Q\_k.
### 6.3.1 Discrete White Noise Acceleration (DWNA) Model / Constant Velocity (CV)
State vector: x\_k = \[x, \\dot{x}\]^T
- State transition matrix: F = \\begin{bmatrix} 1 & T \\\\ 0 & 1 \\end{bmatrix}
- Discrete process noise covariance (piecewise constant acceleration / discrete white noise): Q = \\begin{bmatrix} \\frac{1}{4}T^4 & \\frac{1}{2}T^3 \\\\ \\frac{1}{2}T^3 & T^2 \\end{bmatrix} \\sigma\_v^2 where \\sigma\_v^2 is the variance of the acceleration increment over sampling period T.
### 6.3.2 Continuous White Noise Acceleration (CWNA) Discretized
When discretizing the continuous white noise acceleration model over sampling interval T: Q = \\int\_0^T e^{F(T-\\tau)} G \\tilde{q} G^T e^{F^T(T-\\tau)} d\\tau = \\begin{bmatrix} \\frac{1}{3}T^3 & \\frac{1}{2}T^2 \\\\ \\frac{1}{2}T^2 & T \\end{bmatrix} \\tilde{q} where \\tilde{q} is the continuous-time process noise PSD (units: \\text{m}^2/\\text{s}^3).
### 6.3.3 Discretized Nearly Constant Acceleration (CA) Model
State vector: x\_k = \[x, \\dot{x}, \\ddot{x}\]^T
- State transition matrix: F = \\begin{bmatrix} 1 & T & \\frac{1}{2}T^2 \\\\ 0 & 1 & T \\\\ 0 & 0 & 1 \\end{bmatrix}
- Discretized Continuous Wiener Sequence Acceleration process noise covariance: Q = \\begin{bmatrix} \\frac{1}{20}T^5 & \\frac{1}{8}T^4 & \\frac{1}{6}T^3 \\\\ \\frac{1}{8}T^4 & \\frac{1}{3}T^3 & \\frac{1}{2}T^2 \\\\ \\frac{1}{6}T^3 & \\frac{1}{2}T^2 & T \\end{bmatrix} \\tilde{q} where \\tilde{q} is the continuous-time jerk PSD (units: \\text{m}^2/\\text{s}^5).
---
## 6.4 Measurement Models & Coordinate Transformations
LiDAR and radar sensors provide measurements in polar/spherical coordinates (range r, azimuth \\theta, elevation \\phi) or directly in 3D Cartesian coordinates (x, y, z).
### 6.4.1 Cartesian vs. Sensor Coordinates
- If tracking in Cartesian coordinates with range-bearing sensors: x = r \\cos \\theta, \\quad y = r \\sin \\theta
- Standard Extended Kalman Filter (EKF) uses non-linear measurement function h(x).
- Converted Measurement Kalman Filter (CMKF): converts measurements to Cartesian coordinates before filtering: z\_{k} = \[r\_m \\cos \\theta\_m, r\_m \\sin \\theta\_m\]^T
- Unbiased Converted Measurements (UCM): corrects for the transformation bias E\[z\_k - x\_k\] that arises due to non-linear polar-to-Cartesian trigonometric conversions in noisy conditions.
---
## 6.5 Practical Implementation for LiDAR Tracking & State Estimation
1. ***Model Selection***:
- For high-frequency ground vehicle or mobile robot tracking using LiDAR, the constant velocity (CV / DWNA or CWNA) model is standard due to small T (10\\text{--}100\\text{ ms}).
- When significant maneuvers or terrain-induced slope changes occur, CA or interacting multiple model (IMM) filters are preferred.
2. ***Tuning Process Noise (*****Q*****)***:
- Q must balance filter responsiveness and noise smoothing.
- For CWNA, \\tilde{q} \\approx a\_{\\max}^2 / 3 or tuned based on maximum expected vehicle acceleration over the update cycle.
3. ***Application to Point Cloud Tracking***:
- Cluster centroids or bounding box positions are tracked using the state vector \[x, \\dot{x}, y, \\dot{y}, z, \\dot{z}\]^T with block-diagonal F and Q across coordinates.