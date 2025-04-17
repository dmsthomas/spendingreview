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

OTHER_RECEIPTS = 310  # £bn – residual receipts so baseline totals £1 141 bn
DATA_DIR = pathlib.Path(__file__).parent

st.set_page_config(
    page_title="UK Mock Spending Review",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("\U0001F4B0  UK Mock Spending Review (v 1.1)")

# --- load data ------------------------------------------------------------
try:
    tax_df   = load_tax_table(DATA_DIR / "baseline_tax.csv")
    spend_df = load_spend_table(DATA_DIR / "baseline_spend.csv")
except FileNotFoundError as e:
    st.error(f"Missing CSV: {e.filename}")
    st.stop()

# --- Column layout: controls left, results right -------------------------
controls_col, results_col = st.columns([3, 2])

with controls_col:
    st.subheader("Tax levers")
    tax_changes = {}
    for idx, row in tax_df.iterrows():
        left, mid, right = st.columns([1, 4, 1], gap="small")
        baseline_label = f"{row['baseline']}{row['unit']}".replace(" ", "")
        with left:
            st.markdown(f"**{baseline_label}**")
        with mid:
            slider_val = st.slider(
                row["name"],
                int(row["min_change"]),
                int(row["max_change"]),
                0,
                key=f"tax_{idx}",
                label_visibility="collapsed",
            )
        with right:
            new_label = f"{row['baseline'] + slider_val}{row['unit']}".replace(" ", "")
            st.markdown(f"**{new_label}**")
        tax_changes[row["name"]] = slider_val

    st.subheader("Spending levers")
    spend_changes = {}
    for idx, row in spend_df.iterrows():
        left, mid, right = st.columns([1, 4, 1], gap="small")
        with left:
            st.markdown(f"**£{row['baseline']:.0f} bn**")
        with mid:
            pct_val = st.slider(
                row["name"],
                int(row["min_pct"]),
                int(row["max_pct"]),
                0,
                key=f"spend_{idx}",
                label_visibility="collapsed",
                format="%d%%",
            )
        with right:
            new_spend = row["baseline"] * (1 + pct_val / 100)
            st.markdown(f"**£{new_spend:.1f} bn**")
        spend_changes[row["name"]] = pct_val / 100  # store proportion

# --- calculations ---------------------------------------------------------

tax_delta   = compute_tax_delta(tax_df, tax_changes)
spend_delta = compute_spend_delta(spend_df, spend_changes)

deficit_new = BASELINE_DEFICIT - tax_delta + spend_delta

total_receipts_new     = tax_df["baseline_receipts"].sum() + OTHER_RECEIPTS + tax_delta
programme_spend_new    = spend_df["baseline"].sum() + spend_delta
managed_expenditure_new = programme_spend_new + 99  # debt interest

# --- results panel --------------------------------------------------------
with results_col:
    st.header("Results")
    st.metric("Total receipts (£bn)", f"{total_receipts_new:,.0f}", f"{tax_delta:+,.0f}")
    st.metric("Programme spend (£bn)", f"{programme_spend_new:,.0f}", f"{spend_delta:+,.0f}")
    st.metric(
        "Surplus / Deficit (£bn)",
        f"{deficit_new:,.0f}",
        f"{deficit_new - BASELINE_DEFICIT:+,.0f}",
        delta_color="inverse",
    )

    # optional waterfall chart
    import plotly.graph_objects as go
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Taxes Δ", x=["Taxes"], y=[-tax_delta]))
    fig.add_trace(go.Bar(name="Spend Δ", x=["Spending"], y=[spend_delta]))
    fig.update_layout(title="Contribution to deficit (– reduces deficit)")
    st.plotly_chart(fig, use_container_width=True)

st.caption("Data: HMRC ready‑reckoner Jan 2025; HMT PESA 2024.  Baseline deficit –£137 bn.")
