"""
Spline Path Generator for UAV, UGV, and Crossing Hostiles
Calculates 3D Bezier and catmull-rom spline control points for Unreal Engine.
"""

from dataclasses import dataclass
from typing import List, Tuple
import json

@dataclass
class SplinePoint:
    index: int
    x_m: float
    y_m: float
    z_m: float

    def to_ue_cm(self) -> Tuple[float, float, float]:
        return (self.x_m * 100.0, self.y_m * 100.0, self.z_m * 100.0)

def generate_uav_flight_spline() -> List[SplinePoint]:
    """Generates 30m altitude aerial spline with sweeping turns over Normandy village."""
    coords = [
        (-40.0, -40.0, 30.0),
        (-20.0, -30.0, 30.0),
        (0.0, -10.0, 30.0),
        (10.0, 10.0, 30.0),
        (0.0, 30.0, 30.0),
        (-20.0, 40.0, 30.0),
        (-40.0, 20.0, 30.0),
        (-40.0, -40.0, 30.0),
    ]
    return [SplinePoint(i, pt[0], pt[1], pt[2]) for i, pt in enumerate(coords)]

def generate_ugv_road_spline() -> List[SplinePoint]:
    """Generates road spline along cobblestone road, passing directly under the 5m bridge."""
    coords = [
        (0.0, -45.0, 0.05),
        (0.0, -25.0, 0.05),
        (0.0, -5.0, 0.05),
        (0.0, 15.0, 0.05),   # Underpass beneath bridge at Y=15m
        (0.0, 35.0, 0.05),
        (0.0, 45.0, 0.05),
    ]
    return [SplinePoint(i, pt[0], pt[1], pt[2]) for i, pt in enumerate(coords)]

def generate_hostile_crossing_splines() -> Tuple[List[SplinePoint], List[SplinePoint]]:
    """
    Generates two intersecting splines:
    Hostile A: East to West across square (-18m to +18m)
    Hostile B: North to South across square, passing behind stone wall at X = -10m
    """
    hostile_a = [
        SplinePoint(0, -18.0, 0.0, 0.0),
        SplinePoint(1, -8.0, 0.0, 0.0),
        SplinePoint(2, 0.0, 0.0, 0.0),   # Crossing intersection
        SplinePoint(3, 8.0, 0.0, 0.0),
        SplinePoint(4, 18.0, 0.0, 0.0),
    ]

    hostile_b = [
        SplinePoint(0, 0.0, -18.0, 0.0),
        SplinePoint(1, 0.0, -8.0, 0.0),
        SplinePoint(2, 0.0, 0.0, 0.0),   # Crossing intersection
        SplinePoint(3, -10.0, 8.0, 0.0), # Occlusion detour behind SM_H_StoneWall_00A
        SplinePoint(4, 0.0, 18.0, 0.0),
    ]
    return hostile_a, hostile_b

def export_splines_json(output_path: str = "ue5_splines.json"):
    uav = [p.to_ue_cm() for p in generate_uav_flight_spline()]
    ugv = [p.to_ue_cm() for p in generate_ugv_road_spline()]
    h_a, h_b = generate_hostile_crossing_splines()

    data = {
        "UAV_FlightSpline_CM": uav,
        "UGV_RoadSpline_CM": ugv,
        "HostileA_CrossingSpline_CM": [p.to_ue_cm() for p in h_a],
        "HostileB_CrossingSpline_CM": [p.to_ue_cm() for p in h_b],
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Exported Unreal Engine Spline coordinates (cm) to {output_path}")

if __name__ == "__main__":
    export_splines_json()
