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

OTHER_RECEIPTS = 310  # £bn residual so baseline totals £1 141 bn
DATA_DIR = pathlib.Path(__file__).parent

st.set_page_config(page_title="UK Mock Spending Review", layout="wide")

st.title("\U0001F4B0  UK Mock Spending Review (v 1.2)")

# ── load data ──────────────────────────────────────────────────────────────
try:
    tax_df   = load_tax_table(DATA_DIR / "baseline_tax.csv")
    spend_df = load_spend_table(DATA_DIR / "baseline_spend.csv")
except FileNotFoundError as e:
    st.error(f"Missing CSV file → {e.filename}")
    st.stop()

# ── helper functions ───────────────────────────────────────────────────────

def make_delta_badge(value: float) -> str:
    """Return coloured HTML badge string for £bn delta."""
    colour = "#228B22" if value < 0 else "#C70039" if value > 0 else "#333"
    sign   = "+" if value > 0 else ""  # minus handled by formatting
    return f"<span style='background:{colour};color:white;padding:2px 6px;border-radius:4px;font-size:0.9em'>{sign}{value:.1f} bn</span>"

# ── page layout ────────────────────────────────────────────────────────────
controls_col, results_col = st.columns([4, 2], gap="large")

with controls_col:
    st.subheader("Taxes")
    tax_changes = {}
    for idx, row in tax_df.iterrows():
        st.markdown(f"**{row['name']}**")
        left, mid, new, badge = st.columns([1, 4, 1, 1], gap="small")

        unit = row["unit"].replace(" ", "")
        baseline_val = row["baseline"]
        min_delta, max_delta = int(row["min_change"]), int(row["max_change"])

        with left:
            st.markdown(f"<span style='color:grey'>{baseline_val}{unit}</span>", unsafe_allow_html=True)
        with mid:
            delta_units = st.slider(
                label="", min_value=min_delta, max_value=max_delta, value=0,
                key=f"tax_{idx}",
                label_visibility="collapsed",
            )
        new_val = baseline_val + delta_units
        with new:
            st.markdown(f"**{new_val}{unit}**")

        receipts_delta = delta_units * row["delta_per_unit"]
        with badge:
            st.markdown(make_delta_badge(-receipts_delta), unsafe_allow_html=True)

        tax_changes[row["name"]] = delta_units  # store Δ units

    st.subheader("Spending")
    spend_changes = {}
    for idx, row in spend_df.iterrows():
        st.markdown(f"**{row['name']}**")
        left, mid, new, badge = st.columns([1, 4, 1, 1], gap="small")

        baseline_spend = row["baseline"]
        min_pct, max_pct = int(row["min_pct"]), int(row["max_pct"])

        with left:
            st.markdown(f"<span style='color:grey'>£{baseline_spend:.0f} bn</span>", unsafe_allow_html=True)
        with mid:
            pct_change = st.slider(
                label="", min_value=min_pct, max_value=max_pct, value=0,
                key=f"spend_{idx}", label_visibility="collapsed", format="%d%%",
            )
        new_spend = baseline_spend * (1 + pct_change / 100)
        with new:
            st.markdown(f"**£{new_spend:.1f} bn**")

        spend_delta_bn = new_spend - baseline_spend
        with badge:
            st.markdown(make_delta_badge(spend_delta_bn), unsafe_allow_html=True)

        spend_changes[row["name"]] = pct_change / 100  # store as proportion

# ── calculations ───────────────────────────────────────────────────────────

tax_delta   = compute_tax_delta(tax_df, tax_changes)
spend_delta = compute_spend_delta(spend_df, spend_changes)

deficit_new = BASELINE_DEFICIT - tax_delta + spend_delta

total_receipts_new  = tax_df["baseline_receipts"].sum() + OTHER_RECEIPTS + tax_delta
programme_spend_new = spend_df["baseline"].sum() + spend_delta
managed_exp_new     = programme_spend_new + 99

# ── results panel ─────────────────────────────────────────────────────────
with results_col:
    st.header("Headline numbers")
    st.metric("Total receipts", f"£{total_receipts_new:,.0f} bn", f"{tax_delta:+,.1f}")
    st.metric("Programme spend", f"£{programme_spend_new:,.0f} bn", f"{spend_delta:+,.1f}")
    st.metric(
        "Surplus / Deficit", f"£{deficit_new:,.0f} bn",
        f"{deficit_new-BASELINE_DEFICIT:+,.1f}", delta_color="inverse",
    )

    # quick waterfall
    import plotly.graph_objects as go
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Tax", x=["Taxes"], y=[-tax_delta]))
    fig.add_trace(go.Bar(name="Spend", x=["Spending"], y=[spend_delta]))
    fig.update_layout(title="Contribution to deficit (– reduces deficit)")
    st.plotly_chart(fig, use_container_width=True)

st.caption("Baseline deficit –£137 bn.  Green badge = deficit falls.  Red = rises.")
