"""Streamlit app – grouped sliders & tabbed layout
   v1.4 – tax and spend separated into tabs; sliders grouped in expanders.
"""
import pathlib
import pandas as pd
import streamlit as st

from calc import (
    load_tax_table,
    load_spend_table,
    compute_tax_delta,
    compute_spend_delta,
    BASELINE_DEFICIT,
)

DATA_DIR = pathlib.Path(__file__).parent
OTHER_RECEIPTS = 310  # £bn residual so baseline receipts sum to 1 141 bn

st.set_page_config(page_title="UK Mock Spending Review", layout="wide")
st.title("\U0001F4B0  UK Mock Spending Review (v 1.4)")

# ─────────────────────── Load baseline tables ─────────────────────────────
try:
    tax_df   = load_tax_table(DATA_DIR / "baseline_tax.csv")
    spend_df = load_spend_table(DATA_DIR / "baseline_spend.csv")
except FileNotFoundError as e:
    st.error(f"Missing CSV file → {e.filename}")
    st.stop()

# ─────────────────────── Helper functions ────────────────────────────────

def badge(delta_surplus: float) -> str:
    colour = "#228B22" if delta_surplus > 0 else "#C70039" if delta_surplus < 0 else "#666"
    sign   = "+" if delta_surplus > 0 else ""
    return (
        f"<span style='background:{colour};color:#fff;padding:2px 6px;border-radius:4px;"
        f"font-size:0.9em'>{sign}{delta_surplus:.1f} bn</span>"
    )

def fmt_value(val: float, unit: str) -> str:
    unit = unit.strip()
    if "ppt" in unit:
        return f"{int(round(val))}%"
    if unit.startswith("£"):
        return f"{unit}{int(round(val))}"
    return f"{val:g}{unit}"

# ─────────────────────── Grouping rules ───────────────────────────────────

def tax_group(name: str) -> str:
    n = name.lower()
    if "income tax" in n or "personal allowance" in n or "basic‑rate limit" in n:
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
    if "stamp" in n or "sdlt" in n:
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
    if any(x in n for x in ["pension"]):
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

# Build grouped dictionaries
from collections import defaultdict

tax_groups   = defaultdict(list)
for _, row in tax_df.iterrows():
    tax_groups[tax_group(row["name"])].append(row)

spend_groups = defaultdict(list)
for _, row in spend_df.iterrows():
    spend_groups[spend_group(row["name"])].append(row)

# Storage for deltas
st.session_state.setdefault("tax_changes", {})
st.session_state.setdefault("spend_changes", {})

# ─────────────────────── UI: Tabs & Expanders ─────────────────────────────
controls_col, results_col = st.columns([4, 2], gap="large")

with controls_col:
    tabs = st.tabs(["Tax", "Spend"])

    # -------- TAX TAB --------
    with tabs[0]:
        st.caption("Adjust tax parameters. Revenue‑raising moves improve the surplus (green badge).")
        for group_name in sorted(tax_groups):
            with st.expander(group_name, expanded=False):
                for row in tax_groups[group_name]:
                    baseline = row["baseline"]
                    unit_raw = row["unit"].strip()
                    min_d, max_d = int(row["min_change"]), int(row["max_change"])

                    # Slider first (returns latest value)
                    delta_units = st.slider(
                        row["name"], min_d, max_d,
                        value=st.session_state["tax_changes"].get(row["name"], 0),
                        key=f"tax_{row['name']}", help=f"Baseline {baseline}{unit_raw}"
                    )
                    st.session_state["tax_changes"][row["name"]] = delta_units

                    new_val       = baseline + delta_units
                    surplus_delta = delta_units * row["delta_per_unit"]
                    baseline_txt  = fmt_value(baseline, unit_raw)
                    new_txt       = fmt_value(new_val, unit_raw)

                    cols = st.columns([6,1])
                    cols[0].markdown(
                        f"<span style='color:grey'>{baseline_txt}</span> → "
                        f"<span style='font-weight:700'>{new_txt}</span>",
                        unsafe_allow_html=True,
                    )
                    cols[1].markdown(badge(surplus_delta), unsafe_allow_html=True)

    # -------- SPEND TAB --------
    with tabs[1]:
        st.caption("Adjust programme spend. Cuts improve the surplus (green badge).")
        for group_name in sorted(spend_groups):
            with st.expander(group_name, expanded=False):
                for row in spend_groups[group_name]:
                    baseline = row["baseline"]
                    min_pct, max_pct = int(row["min_pct"]), int(row["max_pct"])

                    pct_change = st.slider(
                        row["name"], min_pct, max_pct,
                        value=int(st.session_state["spend_changes"].get(row["name"], 0)*100),
                        key=f"spend_{row['name']}", format="%d%%", help=f"Baseline £{baseline:.0f}bn"
                    )
                    st.session_state["spend_changes"][row["name"]] = pct_change/100

                    new_spend     = baseline * (1 + pct_change/100)
                    surplus_delta = -(new_spend - baseline)
                    cols = st.columns([6,1])
                    cols[0].markdown(
                        f"<span style='color:grey'>£{baseline:.0f}bn</span> → "
                        f"<span style='font-weight:700'>£{new_spend:.0f}bn</span>",
                        unsafe_allow_html=True,
                    )
                    cols[1].markdown(badge(surplus_delta), unsafe_allow_html=True)

# ─────────────────────── Calculations ─────────────────────────────────────

tax_delta   = compute_tax_delta(tax_df, st.session_state["tax_changes"])
spend_delta = compute_spend_delta(spend_df, st.session_state["spend_changes"])

baseline_surplus = -BASELINE_DEFICIT  # -137 bn
surplus_new      = baseline_surplus + tax_delta - spend_delta

total_receipts_new  = tax_df["baseline_receipts"].sum() + OTHER_RECEIPTS + tax_delta
programme_spend_new = spend_df["baseline"].sum() + spend_delta

# ─────────────────────── Results panel ────────────────────────────────────
with results_col:
    st.header("Headline")
    st.metric("Total receipts", f"£{total_receipts_new:,.0f} bn", f"{tax_delta:+,.1f}")
    st.metric("Programme spend", f"£{programme_spend_new:,.0f} bn", f"{-spend_delta:+,.1f}")
    st.metric(
        "Surplus (+) / Deficit (−)", f"£{surplus_new:,.0f} bn",
        f"{surplus_new - baseline_surplus:+,.1f}", delta_color="normal",
    )

    import plotly.graph_objects as go
    fig = go.Figure([
        go.Bar(name="Taxes", x=["Taxes"], y=[tax_delta]),
        go.Bar(name="Spending", x=["Spending"], y=[-spend_delta]),
    ])
    fig.update_layout(title="Contribution to surplus (positive = improves)")
    st.plotly_chart(fig, use_container_width=True)

st.caption("Badges show change to **surplus** (green = up, red = down). Baseline surplus −£137 bn.")
