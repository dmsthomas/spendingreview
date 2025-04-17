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
OTHER_RECEIPTS = 310  # £bn residual so receipts total £1 141 bn

st.set_page_config(page_title="UK Mock Spending Review", layout="wide")
st.title("💰  UK Mock Spending Review (v 1.3.2)")

# ── load CSVs ─────────────────────────────────────────────────────────────
try:
    tax_df   = load_tax_table(DATA_DIR / "baseline_tax.csv")
    spend_df = load_spend_table(DATA_DIR / "baseline_spend.csv")
except FileNotFoundError as e:
    st.error(f"Missing CSV → {e.filename}")
    st.stop()

# ── helper ────────────────────────────────────────────────────────────────

def make_badge(delta_surplus: float) -> str:
    colour = "#228B22" if delta_surplus > 0 else "#C70039" if delta_surplus < 0 else "#666"
    sign   = "+" if delta_surplus > 0 else ""  # minus displayed automatically
    return (
        f"<span style='background:{colour};color:#fff;padding:2px 6px;border-radius:4px;" 
        f"font-size:0.9em'>{sign}{delta_surplus:.1f} bn</span>"
    )

# ── layout ────────────────────────────────────────────────────────────────
controls_col, results_col = st.columns([4, 2], gap="large")

with controls_col:
    st.subheader("Taxes")
    tax_changes = {}
    for idx, row in tax_df.iterrows():
        baseline   = row["baseline"]
        unit       = row["unit"].strip()
        min_d, max_d = int(row["min_change"]), int(row["max_change"])

        container = st.container()
        header_ph = container.empty()  # placeholder for header line
        delta_units = container.slider(
            label="", min_value=min_d, max_value=max_d, value=0,
            key=f"tax_{idx}", label_visibility="collapsed",
        )
        new_val = baseline + delta_units
        surplus_delta = delta_units * row["delta_per_unit"]  # revenue ↑ -> surplus ↑
        header_ph.markdown(
            f"**{row['name']}**   <span style='color:grey'>{baseline:g}{unit}</span> → "
            f"<span style='font-weight:700'>{new_val:g}{unit}</span>  " + make_badge(surplus_delta),
            unsafe_allow_html=True,
        )
        tax_changes[row["name"]] = delta_units

    st.subheader("Spending")
    spend_changes = {}
    for idx, row in spend_df.iterrows():
        baseline = row["baseline"]
        min_pct, max_pct = int(row["min_pct"]), int(row["max_pct"])

        container = st.container()
        header_ph = container.empty()
        pct_change = container.slider(
            label="", min_value=min_pct, max_value=max_pct, value=0,
            key=f"spend_{idx}", format="%d%%", label_visibility="collapsed",
        )
        new_spend = baseline * (1 + pct_change/100)
        surplus_delta = -(new_spend - baseline)  # spend ↑ => surplus ↓
        header_ph.markdown(
            f"**{row['name']}**   <span style='color:grey'>£{baseline:.0f}bn</span> → "
            f"<span style='font-weight:700'>£{new_spend:.1f}bn</span>  " + make_badge(surplus_delta),
            unsafe_allow_html=True,
        )
        spend_changes[row["name"]] = pct_change/100

# ── calculations ──────────────────────────────────────────────────────────

tax_delta   = compute_tax_delta(tax_df, tax_changes)
spend_delta = compute_spend_delta(spend_df, spend_changes)

baseline_surplus = -BASELINE_DEFICIT  # baseline is negative
surplus_new      = baseline_surplus + tax_delta - spend_delta

total_receipts_new  = tax_df["baseline_receipts"].sum() + OTHER_RECEIPTS + tax_delta
programme_spend_new = spend_df["baseline"].sum() + spend_delta

# ── results ───────────────────────────────────────────────────────────────
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

st.caption("Badges show change to **surplus** (green = up, red = down). Baseline surplus −£137 bn.")
