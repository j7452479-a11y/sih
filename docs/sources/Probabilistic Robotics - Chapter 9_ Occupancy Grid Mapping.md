# Chapter 9: Occupancy Grid Mapping
Probabilistic Robotics Authors: Sebastian Thrun, Wolfram Burgard, Dieter Fox
## 9.1 Introduction
Occupancy grid maps represent an environment as a discrete grid of binary random variables, where each cell is either free or occupied. Originally developed by Moravec and Elfes (1985), occupancy grid mapping addresses the problem of generating consistent spatial representations from noisy and uncertain range sensor data (such as LiDAR and sonar), without pre-defining explicit geometric features (lines, cylinders, planes).
---
## 9.2 The Occupancy Grid Mapping Algorithm
### 9.2.1 Problem Formulation & Grid Representation
- The environment map m is divided into a collection of grid cells: m = \\{m\_i\\} where each cell m\_i has a static binary state:
- m\_i = 1 (occupied)
- m\_i = 0 (free)
- The objective is to compute the posterior probability distribution over maps given a sequence of robot poses x\_{1:t} and range measurements z\_{1:t}: p(m \\mid z\_{1:t}, x\_{1:t})
- Due to the enormous dimensionality of the map space (2^{|m|} possible configurations), occupancy grid mapping decomposes the high-dimensional problem by assuming conditional independence between individual cells: p(m \\mid z\_{1:t}, x\_{1:t}) = \\prod\_i p(m\_i \\mid z\_{1:t}, x\_{1:t})
### 9.2.2 The Log-Odds Representation
To avoid numerical instability near probability values 0 and 1, probabilities are converted to log-odds ratios: l(m\_i) = \\log \\frac{p(m\_i)}{1 - p(m\_i)}
Conversely, probabilities can be recovered from the log-odds representation: p(m\_i) = 1 - \\frac{1}{1 + \\exp(l(m\_i))}
### 9.2.3 Binary Bayes Filter for Static States
Applying Bayes' rule under the Markov assumption yields the recursive update equation: l\_{t,i} = l\_{t-1,i} + \\text{inv\\\_sensor\\\_model}(m\_i, x\_t, z\_t) - l\_0 where:
- l\_{t,i} is the updated log-odds of cell m\_i at time t.
- l\_{t-1,i} is the previous log-odds of cell m\_i.
- l\_0 = \\log \\frac{p(m\_i = 1)}{p(m\_i = 0)} is the prior log-odds of occupancy (typically p(m\_i = 1) = 0.5 \\implies l\_0 = 0).
- \\text{inv\\\_sensor\\\_model}(m\_i, x\_t, z\_t) = \\log \\frac{p(m\_i \\mid z\_t, x\_t)}{1 - p(m\_i \\mid z\_t, x\_t)} is the inverse sensor measurement model.
### 9.2.4 Inverse Measurement Model for LiDAR / Range Finders
For a beam emitted from robot pose x\_t = (x, y, \\theta)^T at sensor angle \\theta + \\theta\_{\\text{beam}} measuring range z\_t^k:
1. Calculate the distance r and bearing \\phi from the sensor to the center of grid cell m\_i: r = \\sqrt{(x\_i - x)^2 + (y\_i - y)^2}, \\quad \\phi = \\text{atan2}(y\_i - y, x\_i - x) - \\theta
2. Find the beam k closest in angle to \\phi: k = \\arg\\min\_j |\\phi - \\theta\_j|
3. The inverse sensor model assigns occupancy probabilities based on range:
- ***Cell beyond beam range (*****r > \\min(z\_{\\max}, z\_t^k + \\alpha/2)***** or *****|\\phi - \\theta\_k| > \\beta/2*****):*** p(m\_i \\mid z\_t, x\_t) = p\_0 \\implies \\text{inv\\\_sensor\\\_model} = l\_0
- ***Cell on detected obstacle surface (*****|r - z\_t^k| \\le \\alpha/2*****):*** p(m\_i \\mid z\_t, x\_t) = p\_{\\text{occ}} > 0.5 \\implies \\text{inv\\\_sensor\\\_model} = l\_{\\text{occ}} > l\_0
- ***Cell in free line of sight (*****r < z\_t^k - \\alpha/2*****):*** p(m\_i \\mid z\_t, x\_t) = p\_{\\text{free}} < 0.5 \\implies \\text{inv\\\_sensor\\\_model} = l\_{\\text{free}} < l\_0 where \\alpha is the obstacle thickness parameter and \\beta is the sensor beam aperture.
---
## 9.3 Ray Casting & Efficient Grid Traversal
- In 2D and 2.5D/3D grids, ray tracing algorithms (such as Bresenham's line algorithm or Amanatides & Woo fast voxel traversal) trace rays from the sensor origin to each LiDAR return point.
- Cells along the ray before the hit point are updated with l\_{\\text{free}}.
- The cell containing the hit point is updated with l\_{\\text{occ}}.
---
## 9.4 Learning Inverse Measurement Models & Limitations
- ***Forward vs. Inverse Models***: Forward models p(z\_t \\mid m, x\_t) capture sensor physics directly; inverse models p(m\_i \\mid z\_t, x\_t) can be learned using neural networks or logistic regression from labeled laser scans.
- ***Key Limitations***:
- Independent cell assumption ignores correlations induced by occlusions and sensor beams spanning multiple cells.
- Robot poses x\_{1:t} are assumed known and error-free (in SLAM, uncertainty in pose must be integrated).
- Dynamic obstacles violate the static environment assumption, causing ghosting artifacts unless explicitly filtered.