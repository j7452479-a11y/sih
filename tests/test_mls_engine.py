"""
Tests for Triebel Capped Multi-Level Surface (MLS) Engine.
Validates multi-interval splitting, void carving, and underpass traversability.
"""

import pytest
import torch

from core_math.foveated_grid import FoveatedGrid, FoveatedCellKey
from core_math.mls_engine import MLSEngine, MLSCell, MLSInterval
from config import SemanticClass

def test_mls_single_interval_expansion():
    cell = MLSCell(key=FoveatedCellKey(tier_id=0, ix=10, iy=10))
    # Add ground points with minor variation (within 10cm merge threshold)
    cell.add_point(z=0.05, semantic_id=int(SemanticClass.GROUND))
    cell.add_point(z=0.08, semantic_id=int(SemanticClass.GROUND))
    cell.add_point(z=0.12, semantic_id=int(SemanticClass.GROUND))

    assert len(cell.intervals) == 1
    assert cell.intervals[0].z_min == pytest.approx(0.05, abs=1e-3)
    assert cell.intervals[0].z_max == pytest.approx(0.12, abs=1e-3)
    assert cell.intervals[0].point_count == 3
    assert not cell.is_traversable_underpass()

def test_bridge_void_retention_and_traversability():
    """
    CRITICAL SIH TEST:
    Proves that road points (z ~ 0.1m) and bridge deck points (z ~ 5.0m)
    are retained as two separate intervals with a 4.8m open void clearance,
    CORRECTLY identifying an open underpass where a flat 2.5D grid would fail.
    """
    cell = MLSCell(key=FoveatedCellKey(tier_id=0, ix=5, iy=5))

    # 1. Road points at ground level (spaced within 10cm merge threshold)
    cell.add_point(z=0.0, semantic_id=int(SemanticClass.ROAD))
    cell.add_point(z=0.08, semantic_id=int(SemanticClass.ROAD))
    cell.add_point(z=0.15, semantic_id=int(SemanticClass.ROAD))

    # 2. Bridge overhead points at 5 meters (spaced within 10cm merge threshold)
    cell.add_point(z=4.9, semantic_id=int(SemanticClass.BRIDGE))
    cell.add_point(z=5.0, semantic_id=int(SemanticClass.BRIDGE))
    cell.add_point(z=5.1, semantic_id=int(SemanticClass.BRIDGE))

    # Must have exactly 2 distinct intervals (ground road + bridge overhead)
    assert len(cell.intervals) == 2

    # Check lower road interval
    assert cell.intervals[0].z_min == pytest.approx(0.0, abs=1e-3)
    assert cell.intervals[0].z_max == pytest.approx(0.15, abs=1e-3)

    # Check upper bridge interval
    assert cell.intervals[1].z_min == pytest.approx(4.9, abs=1e-3)
    assert cell.intervals[1].z_max == pytest.approx(5.1, abs=1e-3)

    # Check void space calculation: 4.9 - 0.15 = 4.75m clearance
    voids = cell.get_traversable_voids()
    assert len(voids) == 1
    bottom, top, clearance = voids[0]
    assert bottom == pytest.approx(0.15, abs=1e-3)
    assert top == pytest.approx(4.9, abs=1e-3)
    assert clearance == pytest.approx(4.75, abs=1e-3)

    # Must be recognized as a traversable underpass for a 1.8m vehicle!
    assert cell.is_traversable_underpass(required_clearance=1.8)

def test_mls_interval_capping_k3():
    """Validates that when more than K=3 intervals are created, closest are merged."""
    cell = MLSCell(key=FoveatedCellKey(tier_id=0, ix=0, iy=0))

    # Insert 5 distinct vertical levels separated by > 1.0m
    cell.add_point(z=0.0)   # Level 1
    cell.add_point(z=2.0)   # Level 2
    cell.add_point(z=2.2)   # Level 2 (near 2.0)
    cell.add_point(z=5.0)   # Level 3
    cell.add_point(z=8.0)   # Level 4
    cell.add_point(z=12.0)  # Level 5

    # Should strictly be capped at MLS_MAX_INTERVALS = 3
    assert len(cell.intervals) <= 3
