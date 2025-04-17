# >>> file: app.py >>>
"""UK Mock Spending Review – v1.5 (fixed slider default)
Tax and Spend on separate tabs, grouped in expanders, with
headers showing baseline → new and surplus badges above each slider.
"""
import pathlib
from collections import defaultdict

import pandas as pd
import streamlit as st
from calc import (
    load_tax_table,
    load_spend_table,
    compute_tax_delta,
    compute_spend_delta,
    BASELINE_DEFICIT,
)

# Configuration
DATA_DIR = pathlib.Path(__file__).parent
OTHER_RECEIPTS = 310  # £bn residual so receipts sum to £1,141 bn

st.set_page_config(page_title="UK Mock Spending Review", layout="wide")
st.title("💰 UK Mock Spending Review (v1.5)")

# Load data
try:
    tax_df = load_tax_table(DATA_DIR / "baseline_tax.csv")
    spend_df = load_spend_table(DATA_DIR / "baseline_spend.csv")
except FileNotFoundError as e:
    st.error(f"Missing CSV file: {e.filename}")
    st.stop()

# Helper functions
def badge(delta_surplus: float) -> str:
    colour = "#228B22" if delta_surplus > 0 else "#C70039" if delta_surplus < 0 else "#666"
    sign = "+" if delta_surplus > 0 else ""
    return (
        f"<span style='background:{colour};color:#fff;padding:2px 6px;"
        f"border-radius:4px;font-size:0.9em'>{sign}{delta_surplus:.1f} bn</span>"
    )

def fmt_value(val: float, unit: str) -> str:
    unit = unit.strip()
    if "ppt" in unit:
        return f"{int(round(val))}%"
    if unit.startswith("£"):
        return f"{unit}{int(round(val))}"
    return f"{val:g}{unit}"

# Grouping functions
def tax_group(name: str) -> str:
    n = name.lower()
    if any(x in n for x in ["income tax", "personal allowance", "basic‑rate limit"]):
        return "Income Tax & Thresholds"
    if "nics" in n:
        return "National Insurance"
    if "corporation" in n:
        return "Corporation Tax"
    if name.startswith("VAT"):
        return "VAT"
    if any(x in n for x in ["capital gains", "cgt"]):
        return "Capital Gains Tax"
    if any(x in n for x in ["inheritance", "iht"]):
        return "Inheritance Tax"
    if "ipt" in n:
        return "Insurance Premium Tax"
    if any(x in n for x in ["stamp", "sdlt"]):
        return "Stamp Duty"
    if any(x in n for x in ["duty", "levy", "fuel", "apd", "vehicle"]):
        return "Duties & Environmental Taxes"
    return "Other taxes"

def spend_group(name: str) -> str:
    n = name.lower()
    if any(x in n for x in ["nhs", "health", "social care"]):
        return "Health & Care"
    if any(x in n for x in ["school", "education", "childcare", "student", "skills"]):
        return "Education & Skills"
    if "pension" in n:
        return "Pensions"
    if any(x in n for x in ["universal credit", "benefit", "welfare", "disability"]):
        return "Welfare & Benefits"
    if any(x in n for x in ["defence", "security"]):
        return "Defence & Security"
    if any(x in n for x in ["transport", "rail", "roads"]):
        return "Transport"
    if any(x in n for x in ["environment", "climate", "agriculture"]):
        return "Environment & Agriculture"
    if any(x in n for x in ["culture", "sport", "housing", "community", "business", "r&d", "innovation"]):
        return "Economic & Community"
    if any(x in n for x in ["devolved", "local", "eu", "cross‑cutting"]):
        return "Inter‑governmental & Other"
    return "Other programmes"

# Build groups
tax_groups = defaultdict(list)
for _, row in tax_df.iterrows():
    tax_groups[tax_group(row["name"])].append(row)

spend_groups = defaultdict(list)
for _, row in spend_df.iterrows():
    spend_groups[spend_group(row["name"])].append(row)

# UI Layout
controls_col, results_col = st.columns([4, 2], gap="large")
with controls_col:
    tax_tab, spend_tab = st.tabs(["Tax", "Spend"])

    # TAX TAB
    with tax_tab:
        st.caption("Revenue‑raising moves improve the surplus (green badge).")
        for group_name in sorted(tax_groups):
            with st.expander(group_name, expanded=False):
                for row in tax_groups[group_name]:
                    slider_key = f"tax_{row['name']}"
                    container = st.container()
                    header_ph = container.empty()
                    baseline = row["baseline"]
                    unit_raw = row["unit"].strip()
                    min_d = int(row["min_change"])
                    max_d = int(row["max_change"])

                    # Slider (default zero)
                    delta_units = container.slider(
                        "", 
                        min_d, max_d,
                        value=st.session_state.get(slider_key, 0),
                        key=slider_key,
                        label_visibility="collapsed"
                    )

                    # Header above slider
                    new_val = baseline + delta_units
                    surplus_delta = delta_units * row["delta_per_unit"]
                    header_ph.markdown(
                        f"**{row['name']}**   " \
                        f"<span style='color:grey'>{fmt_value(baseline, unit_raw)}</span> → " \
                        f"<span style='font-weight:700'>{fmt_value(new_val, unit_raw)}</span> " + badge(surplus_delta),
                        unsafe_allow_html=True,
                    )

    # SPEND TAB
    with spend_tab:
        st.caption("Programme spend adjustments: cuts improve surplus (green badge).")
        for group_name in sorted(spend_groups):
            with st.expander(group_name, expanded=False):
                for row in spend_groups[group_name]:
                    slider_key = f"spend_{row['name']}"
                    container = st.container()
                    header_ph = container.empty()
                    baseline = row["baseline"]
                    min_pct = int(row["min_pct"])
                    max_pct = int(row["max_pct"])

                    # Slider (default zero)
                    pct_change = container.slider(
                        "",
                        min_pct, max_pct,
                        value=st.session_state.get(slider_key, 0),
                        key=slider_key,
                        format="%d%%",
                        label_visibility="collapsed"
                    )

                    # Header above slider
                    new_spend = baseline * (1 + pct_change / 100)
                    surplus_delta = -(new_spend - baseline)
                    header_ph.markdown(
                        f"**{row['name']}**   " \
                        f"<span style='color:grey'>£{baseline:.0f}bn</span> → " \
                        f"<span style='font-weight:700'>£{new_spend:.0f}bn</span> " + badge(surplus_delta),
                        unsafe_allow_html=True,
                    )

# Calculations
tax_changes = {row['name']: st.session_state.get(f"tax_{row['name']}", 0)
               for _, row in tax_df.iterrows()}
spend_changes = {row['name']: st.session_state.get(f"spend_{row['name']}", 0) / 100
                 for _, row in spend_df.iterrows()}

tax_delta = compute_tax_delta(tax_df, tax_changes)
spend_delta = compute_spend_delta(spend_df, spend_changes)
baseline_surplus = -BASELINE_DEFICIT
surplus_new = baseline_surplus + tax_delta - spend_delta

total_receipts_new = tax_df["baseline_receipts"].sum() + OTHER_RECEIPTS + tax_delta
programme_spend_new = spend_df["baseline"].sum() + spend_delta

# Results panel
with results_col:
    st.header("Headline")
    st.metric("Total receipts", f"£{total_receipts_new:,.0f} bn", f"{tax_delta:+.1f}")
    st.metric("Programme spend", f"£{programme_spend_new:,.0f} bn", f"{-spend_delta:+.1f}")
    st.metric(
        "Surplus (+) / Deficit (−)",
        f"£{surplus_new:,.0f} bn",
        f"{surplus_new - baseline_surplus:+.1f}",
        delta_color="normal"
    )

    import plotly.graph_objects as go
    fig = go.Figure([
        go.Bar(name="Taxes", x=["Taxes"], y=[tax_delta]),
        go.Bar(name="Spending", x=["Spending"], y=[-spend_delta]),
    ])
    fig.update_layout(title="Contribution to surplus (positive = improves)")
    st.plotly_chart(fig, use_container_width=True)

st.caption("Badges show impact on **surplus** (green up, red down). Baseline surplus −£137 bn.")
# <<< end of app.py <<<
