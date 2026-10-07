import pytest
from ai_engine.flags import compute_flag


@pytest.mark.parametrize('value', [float('nan'), float('inf'), float('-inf')])
def test_nonfinite_values_are_not_normal(value):
    assert compute_flag('Glucose', value, 'mg/dL', 70, 100) == 'UNKNOWN'


def test_incompatible_unit_is_not_compared_to_reference():
    assert compute_flag('HbA1c', 6, 'unrecognized-unit', None, None) == 'UNKNOWN'


def test_missing_unit_does_not_assume_table_unit():
    assert compute_flag('HbA1c', 6, None, None, None) == 'UNKNOWN'


def test_reversed_reference_range_is_unknown():
    assert compute_flag('synthetic', 5, 'u', 10, 1) == 'UNKNOWN'


@pytest.mark.parametrize('value,expected', [(1, 'LOW'), (2, 'NORMAL'), (4, 'NORMAL'), (5, 'HIGH')])
def test_document_boundaries(value, expected):
    assert compute_flag('synthetic', value, 'u', 2, 4) == expected
