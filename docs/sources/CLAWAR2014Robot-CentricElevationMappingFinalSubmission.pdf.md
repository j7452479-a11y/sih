April 17, 2014 8:57 WSPC - Proceedings Trim Size: 9in x 6in ”CLAWAR 2014 Robot-Centric Elevation Mapping”
1
ROBOT-CENTRIC ELEVATION MAPPING WITH
UNCERTAINTY ESTIMATES
P. FANKHAUSER∗, M. BLOESCH, C. GEHRING, M. HUTTER and R. SIEGWART
Autonomous Systems Lab, ETH Zurich,
Zurich, 8092, Switzerland ∗E-mail: pfankhauser@ethz.ch
www.leggedrobotics.ethz.ch
This paper addresses the local terrain mapping process for an autonomous robot. Building upon an onboard range measurement sensor and an existing robot pose estimation, we formulate a novel elevation mapping method from a robot-centric perspective. This formulation can explicitly handle drift of the robot pose estimation which occurs for many autonomous robots. Our mapping approach fully incorporates the distance sensor measurement uncertainties and the six-dimensional pose covariance of the robot. We introduce a computationally efficient formulation of the map fusion process, which allows for mapping a terrain at high update rates. Finally, our approach is demonstrated on a quadrupedal robot walking over obstacles.
Keywords: Elevation Mapping; Terrain Estimation; Legged Robotics
1. Introduction
The ability to perceive and map an environment is an essential step to
allow robots to navigate in unstructured and unknown terrain. While a lot
of work has focused on obtaining a globally-consistent map,1 our focus lies
on retrieving a local map of the environment of the robot. We assume that a
global path is given by a human operator or another algorithm and that the
local map is used to plan the motion of the robot for a limited time horizon.
Given a robot equipped with i) a range sensor and ii) state estimation
capabilities, our task is to find a representation of the terrain that takes
the uncertainties of the range measurements and the state estimation into
account.
Since we are concerned with locally planning the robot’s motion over or
around obstacles, we are setting our focus on elevation mapping techniques,
which simplify the terrain as a two-dimensional surface. Early work on the
April 17, 2014 8:57 WSPC - Proceedings Trim Size: 9in x 6in ”CLAWAR 2014 Robot-Centric Elevation Mapping”
2
generation of elevation maps for autonomous legged robots was presented
by Herbert et. al.2 and Kweon et. al.3 Their approaches build on a grid map
in which each cell represents the height of the terrain in order to approxi-
mate the surface of the terrain. They use matching algorithms to find the
corresponding transformation between multiple scans to build a composite
elevation map, but they do not address the issues of error propagation as a
result of the remaining error after matching. Cremean et. al.4 developed an
approach to fuse range measurements with uncertainties into a height map.
When a range measurement is taken, cells that fall into the region of the
measurement are updated based on previously stored data and the uncer-
tainty of the measurement. Cells that do not receive measurement updates
are left unchanged. This approach relies on absolute position measurements
from GPS and is therefore unsuitable for our application. In the approach
presented by Belter et. al.,5 a local elevation map is used that surrounds
the robot and is moved along with its motion. While we use a similar setup,
their approach relies on a good pose tracking algorithm and does not ad-
dress the issue of a drifting pose estimation. Our approach is similar to the
work of Kleiner et. al.,6 where the elevation map is deteriorated based on
the motion of the robot. The uncertainty of the robot’s position and orien-
tation is reflected in the map by linearly growing the variance of the height
estimate based on the accumulated distance and angle. This approach con-
servatively merges an approximation of the pose uncertainty into the height
variance without taking the effect of in-plane uncertainty into account.
In contrast to related work, in which the elevation map is usually re-
lated to an inertial frame, we approach the elevation mapping from a robot-
centric perspective: Our main contribution is the formulation of a mapping
algorithm in which the elevation map is tightly coupled to the robot’s mo-
tion. This leads to the important result that our method is able to specifi-
cally incorporate drift of the pose estimation. As opposed to methods that
rely on matching new scans with the existing map, our formulation does not
require (but can incorporate) a feedback-loop from the map building pro-
cess to the state estimation. In Sec. 2, we formalize the elevation mapping
framework with the treatment of the sensor measurement uncertainties and
the six-dimensional pose covariance. Section 3 describes our implementa-
tion on an autonomous four-legged robot and presents the achieved results,
before we conclude in Sec. 4. While we emphasize the application for legged
robots, the presented approach is suitable for any robot that requires only
local knowledge about its surrounding in order to plan its motion.
April 17, 2014 8:57 WSPC - Proceedings Trim Size: 9in x 6in ”CLAWAR 2014 Robot-Centric Elevation Mapping”
3
2. Method
We formulate our elevation mapping algorithm from a robot-centric view:
Distance measurements are taken relative to the robot and when the robot
moves, the entire elevation map is updated with information about the mo-
tion of the robot. At any time, the robot-centric elevation map is an estimate
which the system has about the shape of the terrain from a local perspec-
tive. The region ahead of the robot has typically the highest precision as
it is constantly updated with new measurements from the forward-looking
distance sensor. On the other hand, regions which are out of the sensor’s
field of view (below or behind the robot) have decreased certainty due to
drift of the robot’s relative pose estimation.
In the following, we describe a method to obtain a robot-centric, local
elevation map which consist of a two-dimensional grid in which each cell
stores a height estimate ĥ and variance σ̂2 h.
2.1. Definitions
To describe the framework, we introduce three coordinate frames, namely
the Inertial frame I, the Sensor frame S, and the Map frame M (Fig. 1).
The inertial frame I is fixed to the environment and we assume that the real
terrain is stationary relative to this frame. The sensor frame S is attached
to the distance sensor and is related to the inertial frame I through the
translation rIS and rotation CIS . The transformation between the inertial
frame I and sensor frame S is obtained through the on-board state estima-
tion and characterized by the six-dimensional pose covariance matrix ΣP .
Finally, the elevation map frame M is defined through a relation to the
sensor frame S with translation rSM and rotation CSM , which are specified
by the user. We choose the rotation CSM such that the z-axis of the map
frame M and the inertial frame I remain always aligned (eIz = eMz ). The
last degree of freedom, which corresponds to the yaw angle ψ between I
and M (rotation around eIz), is chosen to match the yaw angle between I
and S.
2.2. Measurement Update
New measurements from the distance sensor are handled as points in space
and mapped to the elevation map. This results in a new height measurement
p̃ at a cell (x, y) in the height map. In the elevation map frameM , the height
measurements are approximated by a Gaussian probability distribution as
p̃ ∼ N (p, σ2 p) with mean p and variance σ2
p. A single measurement, given
![](https://lh3.googleusercontent.com/notebooklm/AKYWMX8xqnOAXUOSXzRmo3QycGK_-vBlKa2LdPPYo-gg-nSFjxU0zxR0wqABawasj9ndGjUaynxci90F0zb6RT739GWsbZ6ghK2mQZ9lDSkmurYDHDmkTefD02rpdmlRP2NMuOXQk6zz6g=w834-h452-v0)
April 17, 2014 8:57 WSPC - Proceedings Trim Size: 9in x 6in ”CLAWAR 2014 Robot-Centric Elevation Mapping”
4
**e **z
I
I **e **x
**r **IS
**r **SM
**r **SP
**r **MP
h
I
**e **z
M
M **e **
x
M
**e **z
S
S
P
**e **y
S
Fig. 1. Illustration of the coordinate frames used in the elevation mapping framework.
as the position SrSP in the sensor frame S, can be transformed to the
corresponding height measurement p with
p = P (
CT SM (q)SrSP − MrSM
)
, (1)
where the rotation between map frame and sensor frame CSM is parameter-
ized by the unit quaternion q. The projection matrix P = \[0 0 1\] maps the
three-dimensional measurement to the scalar height measurement p (in the
map frame M). To obtain the variance of the height measurement σ2 p, we
derive the Jacobians for the sensor measurement JS and the sensor frame
rotation Jq from (1) as
JS = ∂p
∂SrSP = PCT
SM (q) and Jq = ∂p
∂q = PCT
SMS r×
SP , (2)
where the superscript × is used to denote the skew-symmetric matrix of a
vector. The error propagation for the variance σ2 p is given as
σ2 p = JSΣSJ
T S + JqΣP,qJ
T q , (3)
where ΣS denotes the covariance matrix of the distance sensor model and
ΣP,q the covariance matrix of the sensor rotation. It is important to note,
that uncertainties of the position of the sensor ΣP,r do not need to be
taken into account in this step because of our choice for the definition of
the elevation map frame M (Sec. 2.1). Furthermore, an influence of the
uncertainty of the yaw-rotation of the sensor ψ (rotation around eIz) on the
measurement is excluded because of the use of the projection matrix P and
our definition of the map frame M .
The height measurement (p, σ2 p) is fused with the existing elevation map
estimation (ĥ, σ2 h) by means of a Kalman filter:4
ĥ+ = σ2 p ĥ
− + σ̂2−
h p̃
σ2 p + σ̂2−
h
, σ̂2+
h = σ̂2−
h σ2 p
σ̂2−
h + σ2 p
, (4)
![](https://lh3.googleusercontent.com/notebooklm/AKYWMX9m59Y9-my5qq7zs0ln6bQj2a8vqbUrAPq3nKOJ2dQLIR5nKB5UagncG1Rfk3_V-sjLLL5NaF5R1wXg7x27nS61FdrgIEzEPcm2LITMGY1sDjko8WPvOJvM6diWgIwKEMOzVO0HMg=w410-h174-v0)
April 17, 2014 8:57 WSPC - Proceedings Trim Size: 9in x 6in ”CLAWAR 2014 Robot-Centric Elevation Mapping”
5
where estimates before an update are denoted with a − superscript, respec-
tively with a + superscript if the update has already taken place.
If multiple measurements with different heights fall into the same cell
(as it is in the case of a vertical wall), we employ an update rule similarly
to the one presented by Kleiner et. al.6 Based on the Mahalanobis dis-
tance, the rule fuses the measurements for the highest elevation and drops
measurements that fall below a certain distance from the current estimate.
2.3. Model Update
As the elevation map frame M is defined in dependence of the motion of
the sensor/robot (Sec. 2.1), the elevation map data needs to be updated
whenever a motion of the robot relative to the inertial frame I has occurred.
This is necessary because the real terrain is stationary in the inertial frame
I and we want to approximate the terrain in the moving map frame M .
The mean ĥ and variance values σ̂2 h are updated according to the change
of the pose estimate of the robot. Ideally, the variance and mean of each
cell is updated depending on the increase of the uncertainty of the pose
estimation as well as on the estimates of the surrounding cells. However,
performing such an update for each cell of the map is computationally ex-
pensive. Instead, we extend the elevation map structure with information
about the variance in the horizontal directions, σ̂2 x and σ̂2
y for the x- and y-
directions, for each cell. Herewith, we can gather the full three-dimensional
uncertainty for each point of the elevation map, and postpone the compu-
tationally expensive fusion (Sec. 2.4) to the time when the map is needed
by the user or another algorithm.
Our goal is to derive the error propagation of the elevation map variances
\[σ̂2 x σ̂
2 y σ̂
2 h\] as a result of the change of the sensor pose covariance matrix
ΣP from time k − 1 to k. To this end, we analyze the effect of the pose
uncertainty onto the mapping from a fixed point in the inertial frame, IrIP ,
to its representation in the elevation map, M rk MP at timestep k:
Sr k SP = CT
IS(q k)
(
IrIP − Ir k IS
)
, Mrk MP = CT
SMSr k SP − MrSM . (5)
The Jacobians with respect to the sensor frame translation and rotation,
Jr and Jq, can be evaluated to
Jr = ∂ M rk MP
∂ I rk IS
= −CT SMCT
IS(q k) , (6)
Jq = ∂ M rk MP
∂qk = CT
SMCT IS(q
k)(IrIP − IrIS) × . (7)
April 17, 2014 8:57 WSPC - Proceedings Trim Size: 9in x 6in ”CLAWAR 2014 Robot-Centric Elevation Mapping”
6
Now, the map for time k is updated based on the difference of the pose
covariance matrices ΣP,r and ΣP,q from time k − 1 to k according to 

σ̂2 x
σ̂2 y
σ̂2 h

 =


σ̂2 x
σ̂2 y
σ̂2 h

+ diag (
Jr(Σ k P,r −Σk−1
P,r )JT r + Jq(Σ
k P,q −Σk−1
P,q )JT q
)
. (8)
The estimates of the mean height ĥ are kept unchanged as they still repre-
sent the best estimate of the mean. Note that while the change of full sensor
position covariance matrix ΣP,r is propagated on the elevation map vari-
ances, only the variances for the yaw-rotation ψ from the sensor rotation
covariance matrix ΣP,q (rotation around eIz = eMz ) are propagated. This is
complementary to the measurement update (Sec. 2.2), where the sensor po-
sition covariance and the sensor yaw-rotation variances are excluded from
the update step.
2.4. Map Fusion
Whenever required, we can transform the elevation map data structure
(ĥ, σ̂2 h, σ̂
2 x, σ̂
2 y) to the corresponding original representation (ĥ, σ̂2
h). This re-
quires to infer the mean ĥ and variance σ̂2 h based on the data from all
surrounding cells. We formulate the map fusion based on the rules for the
combination of standard deviations for multiple populations as
ĥ =
∑
n
wnĥn ∑
n
wn
, σ̂2 h =
∑
n
wn(σ̂ 2 h,n + ĥ2n)
∑
n
wn
− ĥ2. (9)
The weights wn for a cell n in the neighborhood of the cell of interest is
derived by considering the probability of cell n being positioned in the cell
of interest as
wn = (
Φx(dx + r
2 )− Φx(dx −
r
2 ) )(
Φy(dy + r
2 )− Φy(dy −
r
2 ) )
, (10)
where Φx and Φy denote the cumulative normal distribution with covariance
σx and σy, and dx and dy represent the distance of cell n to the cell being
updated. Variable r denotes the length of the cell side.
3. Results
We have implemented the presented elevation mapping method on the
quadruped robot StarlETH .7 The state estimation of the system is based on
the fusion of kinematic and inertial measurements as presented by Bloesch
et. al.8 It was shown that the position and the rotation around the gravity
![](https://lh3.googleusercontent.com/notebooklm/AKYWMX9jrA8m8WuK0urKayK_NUlFze774lSHiNXpDa6dZlcGd8XVUCxqIZKkzWqHEYxyEFUMcDawsoq1XiNOsk1uW6afeELG8YWsnagtUevE944qllHkT2Oa59Ib9WtTUiyldrEd_O0bmQ=w1280-h356-v0)
![](https://lh3.googleusercontent.com/notebooklm/AKYWMX-UkNhfA3-1_JLuZFCfSQZbbRGDA-eHjeikNYnBvUXIyCHEeom5In-KTKekCJLw8H0g46dK-nI6q1C_rKqlXHISeL8k8HNCnPNsBPO7w_xw_xkM6baxEZro1kGBwLPljGGMCyiY=w1280-h258-v0)
April 17, 2014 8:57 WSPC - Proceedings Trim Size: 9in x 6in ”CLAWAR 2014 Robot-Centric Elevation Mapping”
7
Fig. 2. The quadruped robot StarlETH 7 walks over obstacles (manually controlled) while the terrain is estimated with an elevation map.
Fig. 3. The images show the development from left to right for a region of the height map (marked in Fig. 2) as the robot scans the terrain and than moves away from it.
axis (yaw angle) are in general unobservable and are therefore subject to
drift. We attach a downward-facing PrimeSense Carmine 1.09 structured
light sensor in the front of the robot as distance sensor. We use a sensor
measurement model that was introduced by Nguyen et. al.,9 which models
the noise in depth and lateral direction as a function of the measurement
depth. The experimental setup is shown on the left of Fig. 2. We add obsta-
cles of different heights (7–150mm) and manually control the robot to walk
over the test field in a walking gait at a speed of ∼0.05m/s. The elevation
map is set to a size of 2.5×2.5m with a cell side length of 1 cm. The map
is updated with the measurements and the model estimates at 20Hz. For
the map fusion, the process requires ∼0.3 s to fuse the entire elevation map
(Intel Core i3, 2.60GHz), but generally, only a sub-map is required.
An estimated elevation map for our setup is shown on the right of Fig. 2a.
We conclude that the height information is well preserved when compared
to the real setup. Very few holes are included in the map, which is a result
of the high resolution of the sensor and the high frequency of the elevation
update. One can observe that the region in front of the robot is well cap-
tured with crisp edges, while regions far behind the robot tend to smooth
out with increased uncertainty. We illustrate this effect in Fig. 3, which
shows a close-up of the region marked in Fig. 2. The three images of Fig. 3
depict the development over time (from left to right) as the robot scans
this region and then moves away from it. One can observe that even un-
aA video demonstration is available at http://youtu.be/I9eP8GrMyNQ
April 17, 2014 8:57 WSPC - Proceedings Trim Size: 9in x 6in ”CLAWAR 2014 Robot-Centric Elevation Mapping”
8
der increased pose uncertainty of the robot, large flat regions remain at a
relatively low standard deviation. This is an important feature that can be
used for foothold selection in motion planning algorithms.
4. Summary and Future Work
We have presented a novel approach for elevation mapping that addresses
the problem of pose estimate drift as it occurs on many autonomous robots.
The presented method approaches the elevation map from a robot-centric
perceptive, meaning that new measurements are introduced into the map
at the precision of distance sensor and the estimation of the roll- and pitch
angle of the robot. Through motion of the robot, the data in the map
is updated based on the uncertainty estimates of the pose estimation of
the robot. This gives the robot at any point in time an estimate of the
terrain from its local perspective. We lower the computation burden of
the mapping procedure by splitting the method into the data collection
(measurement and model update) and the map fusion step. This enables
real-time elevation mapping with high update frequencies.
We are currently working on a more detailed evaluation and comparison
of the presented mapping method on different platforms.
This work was supported in part by the Swiss National Science Foundation (SNF) through project 200021 149427/1 and the National Centre of Competence in Research Robotics.
References
1. S. Thrun, Robotic mapping: A Survey, in Exploring artificial intelligence in
the new millennium, 2002. 2. M. Herbert, C. Caillas, E. Krotkov, I. Kweon and T. Kanade, Terrain mapping
for a roving planetary explorer, in ICRA, 1989. 3. S. Kweon and T. Kanade, IEEE Trans. Pattern Anal. Machine Intell. (1992). 4. L. Cremean and R. M. Murray, Uncertainty-based Sensor Fusion of Range
Data for Real-time Digital Elevation Mapping (RTDEM), in ICRA, 2005. 5. D. Belter, P. Labecki and P. Skrzypczyski, Estimating terrain elevation maps
from sparse and uncertain multi-sensor data, in ROBIO , 2012. 6. A. Kleiner and C. Dornhege, Journal of Field Robotics (2007). 7. M. Hutter, C. Gehring, M. Bloesch, M. A. Hoepflinger, C. D. Remy and
R. Siegwart, StarlETH: A compliant quadrupedal robot for fast, efficient, and versatile locomotion, in CLAWAR, 2012.
8. M. Bloesch, C. Gehring, P. Fankhauser, M. Hutter, M. A. Hoepflinger and R. Siegwart, State Estimation for Legged Robots on Unstable and Slippery Terrain, in IROS , 2013.
9. C. V. Nguyen, S. Izadi and D. Lovell, Modeling Kinect Sensor Noise for Im-proved 3D Reconstruction and Tracking, in 3DIMPVT , 2012.