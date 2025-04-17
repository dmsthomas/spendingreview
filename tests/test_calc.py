import pandas as pd
from calc import compute_tax_delta, compute_spend_delta


def test_compute_tax_delta():
    df = pd.DataFrame([
        {"name": "VAT", "delta_per_unit": 8.5},
        {"name": "CT", "delta_per_unit": 3.6},
    ])
    changes = {"VAT": 2, "CT": -1}  # +2 ppt VAT, -1 ppt CT
    assert abs(compute_tax_delta(df, changes) - (2 * 8.5 - 1 * 3.6)) < 1e-6


def test_compute_spend_delta():
    df = pd.DataFrame([
        {"name": "NHS", "baseline": 192},
        {"name": "Defence", "baseline": 57},
    ])
    changes = {"NHS": 0.1, "Defence": -0.2}  # +10%, -20%
    expected = 0.1 * 192 - 0.2 * 57
    assert abs(compute_spend_delta(df, changes) - expected) < 1e-6
