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
OTHER_RECEIPTS = 310  # £bn so baseline totals £1 141 bn

st.set_page_config(page_title="UK Mock Spending Review", layout="wide")
st.title("💰  UK Mock Spending Review (v 1.3.1)")

# ── load tables ───────────────────────────────────────────────────────────
try:
    tax_df   = load_tax_table(DATA_DIR / "baseline_tax.csv")
    spend_df = load_spend_table(DATA_DIR / "baseline_spend.csv")
except FileNotFoundError as e:
    st.error(f"Missing CSV: {e.filename}")
    st.stop()

# ── helper ────────────────────────────────────────────────────────────────

def badge(delta: float) -> str:
    colour = "#228B22" if delta > 0 else "#C70039" if delta < 0 else "#666"
    sign   = "+" if delta > 0 else ""  # minus shown by fmt
    return (
        f"<span style='background:{colour};color:#fff;padding:2px 6px;border-radius:4px;" 
        f"font-size:0.9em'>{sign}{delta:.1f} bn</span>"
    )

# ── layout ────────────────────────────────────────────────────────────────
controls_col, results_col = st.columns([4, 2], gap="large")

with controls_col:
    st.subheader("Taxes")
    tax_changes = {}
    for idx, row in tax_df.iterrows():
        baseline = row["baseline"]
        unit     = row["unit"].strip()
        min_d, max_d = int(row["min_change"]), int(row["max_change"])

        # slider first so we know new value on rerun
        delta_units = st.slider(
            label=row["name"], min_value=min_d, max_value=max_d, value=0,
            key=f"tax_{idx}", help=f"Baseline {baseline}{unit}",
        )
        new_val = baseline + delta_units

        # header with baseline -> new
        header_cols = st.columns([6, 1])
        header_cols[0].markdown(
            f"**{row['name']}**   <span style='color:grey'>{baseline:g}{unit}</span> → "
            f"<span style='font-weight:700'>{new_val:g}{unit}</span>",
            unsafe_allow_html=True,
        )

        surplus_delta = delta_units * row["delta_per_unit"]
        header_cols[1].markdown(badge(surplus_delta), unsafe_allow_html=True)
        tax_changes[row["name"]] = delta_units

    st.subheader("Spending")
    spend_changes = {}
    for idx, row in spend_df.iterrows():
        baseline = row["baseline"]
        min_pct, max_pct = int(row["min_pct"]), int(row["max_pct"])
        pct_change = st.slider(
            label=row["name"], min_value=min_pct, max_value=max_pct, value=0,
            key=f"spend_{idx}", format="%d%%", help=f"Baseline £{baseline:.0f}bn",
        )
        new_spend = baseline * (1 + pct_change/100)

        header_cols = st.columns([6,1])
        header_cols[0].markdown(
            f"**{row['name']}**   <span style='color:grey'>£{baseline:.0f}bn</span> → "
            f"<span style='font-weight:700'>£{new_spend:.1f}bn</span>",
            unsafe_allow_html=True,
        )
        surplus_delta = -(new_spend - baseline)
        header_cols[1].markdown(badge(surplus_delta), unsafe_allow_html=True)
        spend_changes[row["name"]] = pct_change/100

# ── calculations ──────────────────────────────────────────────────────────

tax_delta   = compute_tax_delta(tax_df, tax_changes)
spend_delta = compute_spend_delta(spend_df, spend_changes)

surplus_base = -BASELINE_DEFICIT
surplus_new  = surplus_base + tax_delta - spend_delta

total_receipts_new  = tax_df["baseline_receipts"].sum() + OTHER_RECEIPTS + tax_delta
programme_spend_new = spend_df["baseline"].sum() + spend_delta

# ── results panel ─────────────────────────────────────────────────────────
with results_col:
    st.header("Headline numbers")
    st.metric("Total receipts", f"£{total_receipts_new:,.0f} bn", f"{tax_delta:+,.1f}")
    st.metric("Programme spend", f"£{programme_spend_new:,.0f} bn", f"{-spend_delta:+,.1f}")
    st.metric(
        "Surplus (+) / Deficit (−)",
        f"£{surplus_new:,.0f} bn",
        f"{surplus_new - surplus_base:+,.1f}",
        delta_color="normal",
    )

    import plotly.graph_objects as go
    fig = go.Figure([
        go.Bar(name="Taxes", x=["Taxes"], y=[tax_delta]),
        go.Bar(name="Spending", x=["Spending"], y=[-spend_delta]),
    ])
    fig.update_layout(title="Contribution to surplus (positive = improves)")
    st.plotly_chart(fig, use_container_width=True)

st.caption("Badges show impact on **surplus** (green = up, red = down). Baseline surplus –£137 bn.")
