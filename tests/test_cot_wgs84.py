"""
Tests for WGS84 Geodesy & MIL-STD-2525 Cursor-on-Target (CoT) Serializer.
Validates sub-5mm geodetic precision and XML schema adherence.
"""

import pytest
import xml.etree.ElementTree as ET

from c2_interface.cot_formatter import WGS84Converter, CoTFormatter
from config import DATUM_LAT_0, DATUM_LON_0, DATUM_HAE_0

def test_wgs84_round_trip_precision():
    converter = WGS84Converter()

    # Test offsets up to 1000m East, 1000m North, 50m Up
    test_offsets = [
        (0.0, 0.0, 0.0),
        (10.5, -25.2, 3.5),
        (100.0, 100.0, 10.0),
        (-500.0, 750.0, -15.0),
        (1000.0, -1000.0, 45.0),
    ]

    for x_orig, y_orig, z_orig in test_offsets:
        lat, lon, hae = converter.cartesian_to_geodetic(x_orig, y_orig, z_orig)
        x_rec, y_rec, z_rec = converter.geodetic_to_cartesian(lat, lon, hae)

        # Round-trip error must be sub-millimeter (< 0.001 m)
        assert abs(x_rec - x_orig) < 0.001, f"X round-trip error: {abs(x_rec - x_orig)}"
        assert abs(y_rec - y_orig) < 0.001, f"Y round-trip error: {abs(y_rec - y_orig)}"
        assert abs(z_rec - z_orig) < 0.001, f"Z round-trip error: {abs(z_rec - z_orig)}"

def test_cot_xml_structure_and_schema():
    formatter = CoTFormatter()

    xml_str = formatter.create_cot_xml(
        track_id=1,
        x_east=25.0,
        y_north=50.0,
        z_up=2.0,
        speed_mps=1.8,
        heading_deg=45.0,
        provenance_str="LIDAR_CONFIRMED"
    )

    # Must parse as valid XML
    root = ET.fromstring(xml_str)

    assert root.tag == "event"
    assert root.attrib["version"] == "2.0"
    assert root.attrib["uid"] == "HOSTILE-01"
    assert root.attrib["type"] == "a-h-G-U-C"
    assert root.attrib["how"] == "m-g"

    # Point element
    pt = root.find("point")
    assert pt is not None
    assert float(pt.attrib["lat"]) > 49.0
    assert float(pt.attrib["lon"]) < 0.0

    # Detail element
    detail = root.find("detail")
    assert detail is not None
    contact = detail.find("contact")
    assert contact is not None
    assert contact.attrib["callsign"] == "HOSTILE-01"

    track = detail.find("track")
    assert track is not None
    assert float(track.attrib["speed"]) == 1.8
    assert float(track.attrib["course"]) == 45.0
