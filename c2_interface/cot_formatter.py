"""
WGS84 Local Tangent Plane Geodesy & MIL-STD-2525 Cursor-on-Target (CoT) Serializer
Converts local Cartesian coordinates into Geodetic Lat/Lon/HAE and standard ATAK XML.
"""

import math
from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional
import xml.etree.ElementTree as ET

from config import (
    DATUM_LAT_0,
    DATUM_LON_0,
    DATUM_HAE_0,
    WGS84_SEMI_MAJOR_AXIS_A,
    WGS84_FIRST_ECCENTRICITY_SQ_E2,
)

class WGS84Converter:
    """
    High-precision Local Tangent Plane (LTP) projection to WGS84 Geodetic coordinates.
    Computes exact prime vertical N(phi) and meridional M(phi) radii of curvature.
    """

    def __init__(
        self,
        lat_0: float = DATUM_LAT_0,
        lon_0: float = DATUM_LON_0,
        hae_0: float = DATUM_HAE_0,
    ):
        self.lat_0 = lat_0
        self.lon_0 = lon_0
        self.hae_0 = hae_0

        # Anchor in radians
        self.phi_0 = math.radians(lat_0)
        self.lambda_0 = math.radians(lon_0)

        # Radii of curvature at anchor latitude
        sin_phi = math.sin(self.phi_0)
        e2 = WGS84_FIRST_ECCENTRICITY_SQ_E2
        a = WGS84_SEMI_MAJOR_AXIS_A

        denom = math.sqrt(1.0 - (e2 * (sin_phi ** 2)))
        self.N_phi = a / denom
        self.M_phi = (a * (1.0 - e2)) / (denom ** 3)

    def cartesian_to_geodetic(
        self, x_east: float, y_north: float, z_up: float = 0.0
    ) -> Tuple[float, float, float]:
        """
        Converts local Cartesian offsets (meters) to Geodetic Latitude, Longitude, and HAE altitude.

        Args:
            x_east:  Displacement East in meters (+X)
            y_north: Displacement North in meters (+Y)
            z_up:    Displacement Up in meters (+Z)

        Returns:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            hae: Height Above Ellipsoid in meters
        """
        d_phi = y_north / self.M_phi
        lat = math.degrees(self.phi_0 + d_phi)

        d_lambda = x_east / (self.N_phi * math.cos(self.phi_0))
        lon = math.degrees(self.lambda_0 + d_lambda)

        hae = self.hae_0 + z_up
        return lat, lon, hae

    def geodetic_to_cartesian(
        self, lat: float, lon: float, hae: float
    ) -> Tuple[float, float, float]:
        """Inverse conversion from Geodetic Lat/Lon/HAE back to local Cartesian (meters)."""
        d_phi = math.radians(lat) - self.phi_0
        y_north = d_phi * self.M_phi

        d_lambda = math.radians(lon) - self.lambda_0
        x_east = d_lambda * (self.N_phi * math.cos(self.phi_0))

        z_up = hae - self.hae_0
        return x_east, y_north, z_up

class CoTFormatter:
    """Serializes tracked tactical targets into MIL-STD-2525 Cursor-on-Target XML."""

    def __init__(self, converter: Optional[WGS84Converter] = None):
        self.converter = converter or WGS84Converter()

    def create_cot_xml(
        self,
        track_id: int,
        x_east: float,
        y_north: float,
        z_up: float,
        speed_mps: float,
        heading_deg: float,
        provenance_str: str = "LIDAR_CONFIRMED",
        stale_duration_sec: float = 5.0,
    ) -> str:
        """
        Formats track telemetry into valid Cursor-on-Target XML.
        CoT Type: 'a-h-G-U-C' represents Atom - Hostile - Ground - Unit - Combatant.
        """
        now = datetime.now(timezone.utc)
        stale = now + timedelta(seconds=stale_duration_sec)

        time_fmt = "%Y-%m-%dT%H:%M:%SZ"
        time_str = now.strftime(time_fmt)
        stale_str = stale.strftime(time_fmt)

        lat, lon, hae = self.converter.cartesian_to_geodetic(x_east, y_north, z_up)
        uid = f"HOSTILE-{track_id:02d}"

        event = ET.Element("event", {
            "version": "2.0",
            "uid": uid,
            "type": "a-h-G-U-C",
            "time": time_str,
            "start": time_str,
            "stale": stale_str,
            "how": "m-g",
        })

        ET.SubElement(event, "point", {
            "lat": f"{lat:.7f}",
            "lon": f"{lon:.7f}",
            "hae": f"{hae:.2f}",
            "ce": "1.5",
            "le": "1.0",
        })

        detail = ET.SubElement(event, "detail")
        ET.SubElement(detail, "contact", {"callsign": uid})
        ET.SubElement(detail, "track", {
            "course": f"{heading_deg:.1f}",
            "speed": f"{speed_mps:.2f}",
        })
        remarks = ET.SubElement(detail, "remarks")
        remarks.text = f"Provenance: {provenance_str} | Speed: {speed_mps:.1f}m/s | Hdg: {heading_deg:.0f}deg"

        return ET.tostring(event, encoding="utf-8", xml_declaration=True).decode("utf-8")
