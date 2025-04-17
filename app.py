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

st.set_page_config(
    page_title="UK Mock Spending Review",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("\U0001F4B0  UK Mock Spending Review (v 1.0)")

DATA_DIR = pathlib.Path(__file__).parent

# --- Load baseline tables -------------------------------------------------
try:
    tax_df = load_tax_table(DATA_DIR / "baseline_tax.csv")
    spend_df = load_spend_table(DATA_DIR / "baseline_spend.csv")
except FileNotFoundError as e:
    st.error(
        f"CSV not found: {e.filename}.\n"
        "Make sure baseline_tax.csv and baseline_spend.csv sit next to app.py "
        "(download them from your Google Sheet)."
    )
    st.stop()

# --- Build UI -------------------------------------------------------------
with st.expander("ℹ️ Instructions", expanded=True):
    st.markdown(
        "Move the sliders to change tax rates (in percentage‑points or £/unit) "
        "and spending programmes (percentage up/down). "
        "The live panel on the right shows the impact on the deficit relative "
        "to the £137 bn 2024‑25 baseline."
    )

# Split the page into two columns: controls left, results right
controls_col, results_col = st.columns([3, 2])

with controls_col:
    st.header("Tax levers")
    tax_changes = {}
    for idx, row in tax_df.iterrows():
        tax_changes[row["name"]] = st.slider(
            row["name"],
            int(row["min_change"]),
            int(row["max_change"]),
            0,
            key=f"tax_{idx}",
            help=f"Each step = {row['unit']}. Baseline {row['baseline']}{row['unit']}.",
        )

    st.header("Spending levers")
    spend_changes = {}
    for idx, row in spend_df.iterrows():
        spend_changes[row["name"]] = st.slider(
            row["name"],
            int(row["min_pct"]),
            int(row["max_pct"]),
            0,
            key=f"spend_{idx}",
            format="%d%%",
            help=f"Baseline £{row['baseline']:.1f} bn",
        ) / 100  # convert to proportion

# --- Calculations ---------------------------------------------------------

tax_delta   = compute_tax_delta(tax_df, tax_changes)
spend_delta = compute_spend_delta(spend_df, spend_changes)

deficit_new = BASELINE_DEFICIT - tax_delta + spend_delta

total_receipts_new = tax_df["baseline_receipts"].sum() + 310 + tax_delta
programme_spend_new = spend_df["baseline"].sum() + spend_delta
managed_expenditure_new = programme_spend_new + 99  # debt interest

# --- Results panel --------------------------------------------------------
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

    st.caption("Baseline deficit is –£137 bn (OBR 2024‑25).")

# Waterfall chart (optional) – simple text fallback for now
def _render_waterfall():
    import plotly.graph_objects as go

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Taxes", x=["Taxes"], y=[-tax_delta]))
    fig.add_trace(go.Bar(name="Spending", x=["Spending"], y=[spend_delta]))
    fig.update_layout(title="Contribution to Deficit (– reduces deficit)")
    st.plotly_chart(fig, use_container_width=True)

_render_waterfall()

# --- Footer ---------------------------------------------------------------
st.write("---")
st.caption(
    "Data sources: HMRC *Direct effects of illustrative tax changes* (Jan 2025); "
    "HM Treasury *PESA 2024* out‑turn 2024‑25.  Calculations static unless "
    "noted; large moves may be non‑linear.  © 2025 David Thomas."
)
