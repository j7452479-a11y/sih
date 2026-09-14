# State Estimation for Robotics (Timothy D. Barfoot)
## Chapter 7: 3D Kinematics, Lie Groups, and Pose Estimation
---
### 1. Introduction and Notation Conventions
In three-dimensional state estimation and robotic mapping, rigid-body transformations must be represented without singularities or coordinate ambiguities. Let \\mathcal{F}\_A and \\mathcal{F}\_B denote two right-handed reference frames:
- \\mathbf{r}\_A^{P} denotes the position vector of point P expressed in frame \\mathcal{F}\_A.
- \\mathbf{r}\_A^{BA} denotes the vector from the origin of frame \\mathcal{F}\_A to the origin of frame \\mathcal{F}\_B, resolved in frame \\mathcal{F}\_A.
- C\_{AB} \\in SO(3) denotes the Direction Cosine Matrix (rotation matrix) that transforms vectors from frame \\mathcal{F}\_B to frame \\mathcal{F}\_A: \\mathbf{v}\_A = C\_{AB} \\mathbf{v}\_B
---
### 2. The Special Orthogonal Group SO(3)
2.1 Definition and Lie Group Structure
The Special Orthogonal Group SO(3) represents 3D rotations: SO(3) = \\left\\{ C \\in \\mathbb{R}^{3 \\times 3} \\mid C^T C = I\_{3 \\times 3}, \\; \\det(C) = +1 \\right\\}
2.2 Lie Algebra \\mathfrak{so}(3) and the Skew-Symmetric Operator
The Lie algebra \\mathfrak{so}(3) associated with SO(3) is the tangent space at the identity element, characterized by 3 \\times 3 skew-symmetric matrices. For a vector \\boldsymbol{\\phi} = \[\\phi\_1, \\phi\_2, \\phi\_3\]^T \\in \\mathbb{R}^3, the cross-product (hat/wedge) operator (\\cdot)^\\wedge maps \\mathbb{R}^3 \\to \\mathfrak{so}(3): \\boldsymbol{\\phi}^\\wedge = \\begin{bmatrix} 0 & -\\phi\_3 & \\phi\_2 \\\\ \\phi\_3 & 0 & -\\phi\_1 \\\\ -\\phi\_2 & \\phi\_1 & 0 \\end{bmatrix} Property: \\boldsymbol{\\phi}^\\wedge \\mathbf{v} = \\boldsymbol{\\phi} \\times \\mathbf{v} for any \\mathbf{v} \\in \\mathbb{R}^3. The inverse (vee) operator (\\cdot)^\\vee recovers the vector from the matrix: (\\boldsymbol{\\phi}^\\wedge)^\\vee = \\boldsymbol{\\phi}.
2.3 Matrix Exponential and Rodrigues' Formula
The exponential map \\exp: \\mathfrak{so}(3) \\to SO(3) is defined by the infinite matrix series: \\exp(\\boldsymbol{\\phi}^\\wedge) = \\sum\_{n=0}^{\\infty} \\frac{(\\boldsymbol{\\phi}^\\wedge)^n}{n!} Using the identity (\\boldsymbol{\\phi}^\\wedge)^3 = -\\phi^2 \\boldsymbol{\\phi}^\\wedge, where \\phi = \\|\\boldsymbol{\\phi}\\| = \\sqrt{\\boldsymbol{\\phi}^T \\boldsymbol{\\phi}} is the rotation angle and \\mathbf{a} = \\boldsymbol{\\phi} / \\phi is the unit axis of rotation, the series collapses into ***Rodrigues' formula***: \\exp(\\boldsymbol{\\phi}^\\wedge) = I + \\frac{\\sin \\phi}{\\phi} \\boldsymbol{\\phi}^\\wedge + \\frac{1 - \\cos \\phi}{\\phi^2} (\\boldsymbol{\\phi}^\\wedge)^2
2.4 Matrix Logarithm
The logarithm map \\ln: SO(3) \\to \\mathfrak{so}(3) computes the inverse mapping: \\phi = \\arccos\\left(\\frac{\\text{tr}(C) - 1}{2}\\right) \\ln(C)^\\vee = \\boldsymbol{\\phi} = \\frac{\\phi}{2 \\sin \\phi} \\begin{bmatrix} C\_{32} - C\_{23} \\\\ C\_{13} - C\_{31} \\\\ C\_{21} - C\_{12} \\end{bmatrix} For small angles (\\phi \\to 0), \\ln(C)^\\vee \\approx \\frac{1}{2}(C - C^T)^\\vee.
2.5 Left and Right Jacobians of SO(3)
The derivative of a rotation with respect to its vector parameterization defines the left Jacobian J\_\\ell(\\boldsymbol{\\phi}): J\_\\ell(\\boldsymbol{\\phi}) = \\frac{\\sin \\phi}{\\phi} I + \\left(1 - \\frac{\\sin \\phi}{\\phi}\\right) \\mathbf{a}\\mathbf{a}^T + \\frac{1 - \\cos \\phi}{\\phi} \\mathbf{a}^\\wedge The inverse left Jacobian is: J\_\\ell(\\boldsymbol{\\phi})^{-1} = \\frac{\\phi}{2} \\cot\\left(\\frac{\\phi}{2}\\right) I + \\left(1 - \\frac{\\phi}{2} \\cot\\left(\\frac{\\phi}{2}\\right)\\right) \\mathbf{a}\\mathbf{a}^T - \\frac{\\phi}{2} \\mathbf{a}^\\wedge The right Jacobian satisfies J\_r(\\boldsymbol{\\phi}) = J\_\\ell(-\\boldsymbol{\\phi}) = J\_\\ell(\\boldsymbol{\\phi})^T.
---
### 3. The Special Euclidean Group SE(3)
3.1 Definition and Homogeneous Coordinates
The Special Euclidean Group SE(3) defines rigid body motions (rotations and translations) in 3D: SE(3) = \\left\\{ T = \\begin{bmatrix} C & \\mathbf{r} \\\\ \\mathbf{0}^T & 1 \\end{bmatrix} \\in \\mathbb{R}^{4 \\times 4} \\;\\middle|\\; C \\in SO(3), \\; \\mathbf{r} \\in \\mathbb{R}^3 \\right\\} Group inverse: T^{-1} = \\begin{bmatrix} C^T & -C^T \\mathbf{r} \\\\ \\mathbf{0}^T & 1 \\end{bmatrix}
3.2 Lie Algebra \\mathfrak{se}(3)
The Lie algebra \\mathfrak{se}(3) is parameterized by a 6-vector of generalized coordinates \\boldsymbol{\\xi} = \\begin{bmatrix} \\boldsymbol{\\rho} \\\\ \\boldsymbol{\\phi} \\end{bmatrix} \\in \\mathbb{R}^6, where \\boldsymbol{\\rho} \\in \\mathbb{R}^3 corresponds to translation/coupling and \\boldsymbol{\\phi} \\in \\mathbb{R}^3 to rotation: \\boldsymbol{\\xi}^\\wedge = \\begin{bmatrix} \\boldsymbol{\\phi}^\\wedge & \\boldsymbol{\\rho} \\\\ \\mathbf{0}^T & 0 \\end{bmatrix} \\in \\mathfrak{se}(3)
3.3 Exponential and Logarithmic Maps for SE(3)
The exponential map \\exp: \\mathfrak{se}(3) \\to SE(3) is given in closed form by: \\exp(\\boldsymbol{\\xi}^\\wedge) = \\begin{bmatrix} \\exp(\\boldsymbol{\\phi}^\\wedge) & J\_\\ell(\\boldsymbol{\\phi}) \\boldsymbol{\\rho} \\\\ \\mathbf{0}^T & 1 \\end{bmatrix} where J\_\\ell(\\boldsymbol{\\phi}) is the left Jacobian of SO(3).
The logarithm map \\ln: SE(3) \\to \\mathfrak{se}(3) is: \\ln(T)^\\vee = \\boldsymbol{\\xi} = \\begin{bmatrix} \\boldsymbol{\\rho} \\\\ \\boldsymbol{\\phi} \\end{bmatrix} = \\begin{bmatrix} J\_\\ell(\\boldsymbol{\\phi})^{-1} \\mathbf{r} \\\\ \\ln(C)^\\vee \\end{bmatrix}
3.4 Adjoint Representation \\text{Ad}(T)
The adjoint operator \\mathcal{T} = \\text{Ad}(T) \\in \\mathbb{R}^{6 \\times 6} linearly transforms tangent vectors between coordinate frames: \\mathcal{T} = \\text{Ad}(T) = \\begin{bmatrix} C & \\mathbf{r}^\\wedge C \\\\ \\mathbf{0}\_{3 \\times 3} & C \\end{bmatrix} Fundamental identity: T \\boldsymbol{\\xi}^\\wedge T^{-1} = (\\mathcal{T} \\boldsymbol{\\xi})^\\wedge
The curly-wedge operator (\\cdot)^\\curlywedge for \\boldsymbol{\\xi} = \[\\boldsymbol{\\rho}^T, \\boldsymbol{\\phi}^T\]^T is: \\boldsymbol{\\xi}^\\curlywedge = \\begin{bmatrix} \\boldsymbol{\\phi}^\\wedge & \\boldsymbol{\\rho}^\\wedge \\\\ \\mathbf{0}\_{3 \\times 3} & \\boldsymbol{\\phi}^\\wedge \\end{bmatrix} \\in \\mathbb{R}^{6 \\times 6}
---
### 4. Drone-to-Crawler Multi-Perspective Coordinate Alignment
4.1 System Geometry and Reference Frames
Consider a cooperative robotic system comprising:
1. An aerial drone \\mathcal{F}\_D providing top-down oblique LiDAR scanning.
2. A ground crawler \\mathcal{F}\_C providing horizontal LiDAR terrain sweeps.
3. A shared inertial world frame \\mathcal{F}\_W.
Let the world-referenced poses of the drone and crawler be: T\_{WD} = \\begin{bmatrix} C\_{WD} & \\mathbf{r}\_W^{WD} \\\\ \\mathbf{0}^T & 1 \\end{bmatrix}, \\quad T\_{WC} = \\begin{bmatrix} C\_{WC} & \\mathbf{r}\_W^{WC} \\\\ \\mathbf{0}^T & 1 \\end{bmatrix}
4.2 Exact Relative SE(3) Transformation Matrix
To align aerial drone measurements directly into the crawler's reference frame: T\_{CD} = T\_{WC}^{-1} T\_{WD} = \\begin{bmatrix} C\_{WC}^T & -C\_{WC}^T \\mathbf{r}\_W^{WC} \\\\ \\mathbf{0}^T & 1 \\end{bmatrix} \\begin{bmatrix} C\_{WD} & \\mathbf{r}\_W^{WD} \\\\ \\mathbf{0}^T & 1 \\end{bmatrix} Evaluating block multiplication yields the exact closed-form matrix: T\_{CD} = \\begin{bmatrix} C\_{WC}^T C\_{WD} & C\_{WC}^T (\\mathbf{r}\_W^{WD} - \\mathbf{r}\_W^{WC}) \\\\ \\mathbf{0}^T & 1 \\end{bmatrix} = \\begin{bmatrix} C\_{CD} & \\mathbf{r}\_C^{CD} \\\\ \\mathbf{0}^T & 1 \\end{bmatrix} where:
- Relative rotation matrix: C\_{CD} = C\_{WC}^T C\_{WD}
- Relative translation vector: \\mathbf{r}\_C^{CD} = C\_{WC}^T (\\mathbf{r}\_W^{WD} - \\mathbf{r}\_W^{WC}) (the baseline vector expressed in crawler body coordinates).
4.3 Direct 3D Point Cloud Transformation
For any LiDAR point \\mathbf{p}\_D = \[x\_D, y\_D, z\_D\]^T captured by the drone: \\begin{bmatrix} \\mathbf{p}\_C \\\\ 1 \\end{bmatrix} = T\_{CD} \\begin{bmatrix} \\mathbf{p}\_D \\\\ 1 \\end{bmatrix} \\implies \\mathbf{p}\_C = C\_{CD} \\mathbf{p}\_D + \\mathbf{r}\_C^{CD}
---
### 5. Linearized Kinematics and Covariance Propagation
5.1 Perturbation Scheme on SE(3)
Under small pose perturbations \\delta\\boldsymbol{\\xi} = \[\\delta\\boldsymbol{\\rho}^T, \\delta\\boldsymbol{\\phi}^T\]^T \\in \\mathbb{R}^6: T \\approx \\exp(\\delta\\boldsymbol{\\xi}^\\wedge) \\bar{T} \\approx (I + \\delta\\boldsymbol{\\xi}^\\wedge) \\bar{T} The perturbed point transformation is: \\mathbf{p}\_C + \\delta\\mathbf{p}\_C = (\\bar{C}\_{CD} + \\delta\\boldsymbol{\\phi}^\\wedge \\bar{C}\_{CD})\\mathbf{p}\_D + \\bar{\\mathbf{r}}\_C^{CD} + \\delta\\boldsymbol{\\rho} \\delta\\mathbf{p}\_C = \\delta\\boldsymbol{\\rho} - (\\bar{C}\_{CD}\\mathbf{p}\_D)^\\wedge \\delta\\boldsymbol{\\phi} = \\begin{bmatrix} I\_3 & -(\\bar{C}\_{CD}\\mathbf{p}\_D)^\\wedge \\end{bmatrix} \\begin{bmatrix} \\delta\\boldsymbol{\\rho} \\\\ \\delta\\boldsymbol{\\phi} \\end{bmatrix} The measurement Jacobian with respect to the relative pose perturbation is: G = \\frac{\\partial \\mathbf{p}\_C}{\\partial \\delta\\boldsymbol{\\xi}\_{CD}} = \\begin{bmatrix} I\_3 & -(\\mathbf{p}\_C - \\mathbf{r}\_C^{CD})^\\wedge \\end{bmatrix}
5.2 Sensor Uncertainty and Covariance Transformation
Let \\Sigma\_D \\in \\mathbb{R}^{3 \\times 3} be the heteroscedastic range uncertainty covariance of the drone LiDAR measurement \\mathbf{p}\_D. Under transformation T\_{CD}, the propagated spatial covariance in the crawler frame is: \\Sigma\_C = C\_{CD} \\Sigma\_D C\_{CD}^T + G \\Sigma\_{\\text{pose}} G^T where \\Sigma\_{\\text{pose}} \\in \\mathbb{R}^{6 \\times 6} is the full uncertainty covariance of the relative pose estimate T\_{CD}.
---
### 6. Summary for LiDAR Fusion Pipelines
- ***SE(3) Coordinate Invariance***: The Lie-algebraic parameterization guarantees singularity-free alignment over all roll/pitch/yaw angles.
- ***Drone-to-Crawler Co-Registration***: Enables seamless projection of drone elevation measurements onto the crawler's multi-level surface patches.
- ***Adjoint Transformation***: Provides exact propagation of velocity, process noise, and spatial uncertainties between platforms.