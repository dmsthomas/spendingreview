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

st.title("💰  UK Mock Spending Review (v 1.3)")

# ── load data ──────────────────────────────────────────────────────────────
try:
    tax_df   = load_tax_table(DATA_DIR / "baseline_tax.csv")
    spend_df = load_spend_table(DATA_DIR / "baseline_spend.csv")
except FileNotFoundError as e:
    st.error(f"Missing CSV file → {e.filename}")
    st.stop()

# ── helper functions ───────────────────────────────────────────────────────

def surplus_badge(delta: float) -> str:
    """Return HTML badge: green if increases surplus, red if reduces."""
    colour = "#228B22" if delta > 0 else "#C70039" if delta < 0 else "#666"
    sign = "+" if delta > 0 else ""  # minus shown by format
    return (
        f"<span style='background:{colour};color:white;padding:2px 6px;border-radius:4px;"
        f"font-size:0.9em'>{sign}{delta:.1f} bn</span>"
    )

# ── layout ────────────────────────────────────────────────────────────────
controls_col, results_col = st.columns([4, 2], gap="large")

with controls_col:
    st.subheader("Taxes")
    tax_changes = {}
    for idx, row in tax_df.iterrows():
        container = st.container()
        baseline_val = row["baseline"]
        unit = row["unit"].strip()
        min_delta, max_delta = int(row["min_change"]), int(row["max_change"])

        # header line
        header_cols = container.columns([6, 1])
        header_cols[0].markdown(
            f"**{row['name']}**   <span style='color:grey'>{baseline_val}{unit}</span> → "
            f"<span id='new_{idx}' style='font-weight:700'></span>",
            unsafe_allow_html=True,
        )

        # slider + compute new value
        delta_units = container.slider(
            label="", min_value=min_delta, max_value=max_delta, value=0,
            key=f"tax_{idx}", label_visibility="collapsed",
        )
        new_val = baseline_val + delta_units
        # javascript to update the span (Streamlit hack via components)
        container.markdown(
            f"<script>var el=document.getElementById('new_{idx}');"
            f"if(el){{el.textContent='{new_val}{unit}';}}</script>",
            unsafe_allow_html=True,
        )

        # surplus change badge (revenue ↑ => surplus ↑)
        receipts_delta = delta_units * row["delta_per_unit"]
        surplus_delta  = receipts_delta  # sign preserved
        header_cols[1].markdown(surplus_badge(surplus_delta), unsafe_allow_html=True)

        tax_changes[row["name"]] = delta_units

    st.subheader("Spending")
    spend_changes = {}
    for idx, row in spend_df.iterrows():
        container = st.container()
        baseline_spend = row["baseline"]
        min_pct, max_pct = int(row["min_pct"]), int(row["max_pct"])

        header_cols = container.columns([6, 1])
        header_cols[0].markdown(
            f"**{row['name']}**   <span style='color:grey'>£{baseline_spend:.0f}bn</span> → "
            f"<span id='snew_{idx}' style='font-weight:700'></span>",
            unsafe_allow_html=True,
        )

        pct_change = container.slider(
            label="", min_value=min_pct, max_value=max_pct, value=0,
            key=f"spend_{idx}", label_visibility="collapsed", format="%d%%",
        )
        new_spend = baseline_spend * (1 + pct_change / 100)
        container.markdown(
            f"<script>var el=document.getElementById('snew_{idx}');"
            f"if(el){{el.textContent='£{new_spend:.1f}bn';}}</script>",
            unsafe_allow_html=True,
        )

        spend_delta_bn = new_spend - baseline_spend
        surplus_delta  = -spend_delta_bn  # spend cut → surplus ↑
        header_cols[1].markdown(surplus_badge(surplus_delta), unsafe_allow_html=True)

        spend_changes[row["name"]] = pct_change / 100

# ── calculations ──────────────────────────────────────────────────────────

tax_delta   = compute_tax_delta(tax_df, tax_changes)
spend_delta = compute_spend_delta(spend_df, spend_changes)

deficit_new = BASELINE_DEFICIT - tax_delta + spend_delta
surplus_new = -deficit_new
surplus_base = -BASELINE_DEFICIT

total_receipts_new  = tax_df["baseline_receipts"].sum() + OTHER_RECEIPTS + tax_delta
programme_spend_new = spend_df["baseline"].sum() + spend_delta
managed_exp_new     = programme_spend_new + 99

# ── results panel ─────────────────────────────────────────────────────────
with results_col:
    st.header("Headline numbers")
    st.metric("Total receipts", f"£{total_receipts_new:,.0f} bn", f"{tax_delta:+,.1f}")
    st.metric("Programme spend", f"£{programme_spend_new:,.0f} bn", f"{spend_delta:+,.1f}")
    st.metric(
        "Surplus (+) / Deficit (−)",
        f"£{surplus_new:,.0f} bn",
        f"{surplus_new - surplus_base:+,.1f}",
        delta_color="normal",
    )

    import plotly.graph_objects as go
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Taxes", x=["Taxes"], y=[tax_delta]))
    fig.add_trace(go.Bar(name="Spending", x=["Spending"], y=[-spend_delta]))
    fig.update_layout(title="Contribution to surplus (positive = improves)")
    st.plotly_chart(fig, use_container_width=True)

st.caption("Badges show impact on **surplus** (green = improves, red = worsens). Baseline surplus is –£137 bn.")
