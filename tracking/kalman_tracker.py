"""
2D Constant Velocity (CV) Kalman Filter
Mathematical foundation based on Estimation with Applications to Tracking and Navigation (Bar-Shalom Ch. 6)
and Multivariate Kalman Filters (Labbe Ch. 6, 8).
"""

from typing import Tuple, Optional
import numpy as np

from config import (
    TRACK_DT,
    CWNA_PROCESS_NOISE_Q,
    MEASUREMENT_NOISE_STD_M,
    MAHALANOBIS_GATE_GAMMA,
)

class KalmanTracker2D:
    """
    Tracks target kinematics (x, y, vx, vy) using a 2D Constant Velocity model
    with Bar-Shalom Continuous White Noise Acceleration (CWNA) process noise.
    """

    def __init__(
        self,
        track_id: int,
        initial_x: float,
        initial_y: float,
        initial_z: float = 0.0,
        dt: float = TRACK_DT,
        q_var: float = CWNA_PROCESS_NOISE_Q,
        meas_std: float = MEASUREMENT_NOISE_STD_M,
    ):
        self.track_id = track_id
        self.dt = dt
        self.z = initial_z  # Altitude maintained as smooth elevation

        # State vector: [x, y, vx, vy]^T
        self.x = np.array([initial_x, initial_y, 0.0, 0.0], dtype=np.float64)

        # State covariance P (initial position variance small, velocity variance larger)
        self.P = np.diag([0.25, 0.25, 4.0, 4.0]).astype(np.float64)

        # State Transition Matrix F
        self.F = np.array([
            [1.0, 0.0, self.dt, 0.0],
            [0.0, 1.0, 0.0, self.dt],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ], dtype=np.float64)

        # Measurement Matrix H (observing x and y positions)
        self.H = np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
        ], dtype=np.float64)

        # Measurement Noise Covariance R
        r_var = meas_std ** 2
        self.R = np.diag([r_var, r_var]).astype(np.float64)

        # CWNA Process Noise Covariance Matrix Q (Bar-Shalom Eq. 6.2.2-1)
        dt2 = (self.dt ** 2) / 2.0
        dt3 = (self.dt ** 3) / 3.0
        self.Q = q_var * np.array([
            [dt3, 0.0, dt2, 0.0],
            [0.0, dt3, 0.0, dt2],
            [dt2, 0.0, self.dt, 0.0],
            [0.0, dt2, 0.0, self.dt],
        ], dtype=np.float64)

        # Innovation cache
        self.last_innovation = np.zeros(2, dtype=np.float64)
        self.last_S = np.eye(2, dtype=np.float64)

    def predict(self, dt: Optional[float] = None):
        """Advances state prediction x_k|k-1 = F * x and P_k|k-1 = F * P * F^T + Q."""
        if dt is not None and dt != self.dt:
            self.dt = dt
            self.F[0, 2] = dt
            self.F[1, 3] = dt

        self.x = self.F @ self.x
        self.P = (self.F @ self.P @ self.F.T) + self.Q
        # Ensure numerical symmetry
        self.P = 0.5 * (self.P + self.P.T)

    def compute_mahalanobis_sq(self, measurement: np.ndarray) -> float:
        """
        Computes the squared Mahalanobis distance d_M^2 = y^T * S^-1 * y
        between the predicted position and an incoming measurement [x, y].
        Uses closed-form analytical 2x2 inverse for sub-millisecond execution.
        """
        dx = float(measurement[0] - self.x[0])
        dy = float(measurement[1] - self.x[1])
        s00 = self.P[0, 0] + self.R[0, 0]
        s01 = self.P[0, 1]
        s11 = self.P[1, 1] + self.R[1, 1]
        det = s00 * s11 - s01 * s01
        if abs(det) < 1e-9:
            return 1e6
        inv_det = 1.0 / det
        return float((dx * (dx * s11 - dy * s01) + dy * (-dx * s01 + dy * s00)) * inv_det)

    def update(self, measurement: np.ndarray, z_elev: Optional[float] = None):
        """
        Updates filter with validated measurement [x, y].
        """
        if z_elev is not None:
            # Low-pass filter for smooth vertical altitude
            self.z = 0.8 * self.z + 0.2 * z_elev

        y = np.array([measurement[0] - self.x[0], measurement[1] - self.x[1]], dtype=np.float64)
        s00 = self.P[0, 0] + self.R[0, 0]
        s01 = self.P[0, 1]
        s11 = self.P[1, 1] + self.R[1, 1]
        det = s00 * s11 - s01 * s01
        inv_det = 1.0 / det if abs(det) >= 1e-9 else 1e9

        # S_inv = [[s11, -s01], [-s01, s00]] * inv_det
        P0 = self.P[:, 0]
        P1 = self.P[:, 1]
        K = np.empty((4, 2), dtype=np.float64)
        K[:, 0] = (P0 * s11 - P1 * s01) * inv_det
        K[:, 1] = (-P0 * s01 + P1 * s00) * inv_det

        self.x = self.x + (K @ y)
        I_KH = np.eye(4, dtype=np.float64)
        I_KH[:, 0] -= K[:, 0]
        I_KH[:, 1] -= K[:, 1]

        # Joseph form covariance update for numerical stability
        self.P = (I_KH @ self.P @ I_KH.T) + (K @ self.R @ K.T)
        self.P = 0.5 * (self.P + self.P.T)

        self.last_innovation = y
        self.last_S = np.array([[s00, s01], [s01, s11]], dtype=np.float64)

    @property
    def position_2d(self) -> np.ndarray:
        return self.x[:2]

    @property
    def velocity_2d(self) -> np.ndarray:
        return self.x[2:4]

    @property
    def speed(self) -> float:
        return float(np.linalg.norm(self.velocity_2d))

    @property
    def heading_rad(self) -> float:
        vx, vy = self.x[2], self.x[3]
        return float(np.arctan2(vy, vx))
