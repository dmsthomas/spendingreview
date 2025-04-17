# >>> file: app.py >>>
"""Streamlit app – v1.5
• Two tabs (Tax / Spend) with grouped sliders in expanders
• Header shows baseline → new and surplus badge *above* each slider
• Slider values persist via Streamlit’s own session_state keys, so no double‑drag glitch
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

DATA_DIR = pathlib.Path(__file__).parent
OTHER_RECEIPTS = 310  # residual so baseline receipts = 1 141 bn

st.set_page_config(page_title="UK Mock Spending Review", layout="wide")
st.title("\U0001F4B0  UK Mock Spending Review (v 1.5)")

# ── Load snapshots ────────────────────────────────────────────────────────
try:
    tax_df   = load_tax_table(DATA_DIR / "baseline_tax.csv")
    spend_df = load_spend_table(DATA_DIR / "baseline_spend.csv")
except FileNotFoundError as e:
    st.error(f"Missing CSV: {e.filename}")
    st.stop()

# ── Helpers ───────────────────────────────────────────────────────────────

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

# ── Grouping rules (same heuristic as before) ─────────────────────────────

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
    if "capital gains" in n or "cgt" in n:
        return "Capital Gains Tax"
    if "inheritance" in n or "iht" in n:
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

# Build grouped dicts

tax_groups   = defaultdict(list)
for _, row in tax_df.iterrows():
    tax_groups[tax_group(row["name"])].append(row)

spend_groups = defaultdict(list)
for _, row in spend_df.iterrows():
    spend_groups[spend_group(row["name"])].append(row)

# ── UI Layout ─────────────────────────────────────────────────────────────
controls_col, results_col = st.columns([4, 2], gap="large")

with controls_col:
    tax_tab, spend_tab = st.tabs(["Tax", "Spend"])

    # ================= TAX TAB =================
    with tax_tab:
        st.caption("Revenue‑raising moves improve the surplus (green badge).")
        for gname in sorted(tax_groups):
            with st.expander(gname, expanded=False):
                for row in tax_groups[gname]:
                    baseline = row["baseline"]
                    unit_raw = row["unit"].strip()
                    min_d, max_d = int(row["min_change"]), int(row["max_change"])
                    slider_key = f"tax_{row['name']}"

                    container = st.container()
                    header_ph = container.empty()

                    # Slider – relies on Streamlit to persist its own value
                    delta_units = container.slider(
                        "", min_d, max_d,
                        value=st.session_state.get(slider_key, 0),
                        key=slider_key,
                        label_visibility="collapsed",
                    ),
                        key=slider_key, label_visibility="collapsed",                              
                    )
                    )

                    # Header using current slider value
                    new_val = baseline + delta_units
                    surplus_delta = delta_units * row["delta_per_unit"]
                    header_ph.markdown(
                        f"**{row['name']}**   <span style='color:grey'>{fmt_value(baseline, unit_raw)}</span> → "
                        f"<span style='font-weight:700'>{fmt_value(new_val, unit_raw)}</span>  " + badge(surplus_delta),
                        unsafe_allow_html=True,
                    )

    # ================= SPEND TAB =================
    with spend_tab:
        st.caption("Cuts improve the surplus (green badge).")
        for gname in sorted(spend_groups):
            with st.expander(gname, expanded=False):
                for row in spend_groups[gname]:
                    baseline = row["baseline"]
                    min_pct, max_pct = int(row["min_pct"]), int(row["max_pct"])
                    slider_key = f"spend_{row['name']}"

                    container = st.container()
                    header_ph = container.empty()

                    pct_change = container.slider(
                        "", min_value=min_pct, max_value=max_pct,
                        value=int(st.session_state.get(slider_key, 0)*100),
                        key=slider_key,
                        format="%d%%",
                        label_visibility="collapsed",
                    ),
                        key=slider_key, format="%d%%", label_visibility="collapsed",                              
                    )
                    )

                    new_spend = baseline * (1 + pct_change/100)
                    surplus_delta = -(new_spend - baseline)
                    header_ph.markdown(
                        f"**{row['name']}**   <span style='color:grey'>£{baseline:.0f}bn</span> → "
                        f"<span style='font-weight:700'>£{new_spend:.0f}bn</span>  " + badge(surplus_delta),
                        unsafe_allow_html=True,
                    )

# ── Calculations ──────────────────────────────────────────────────────────
# Build change dicts directly from slider keys

tax_changes = {
    row["name"]: st.session_state[f"tax_{row['name']}"]
    for _, row in tax_df.iterrows()
}
spend_changes = {
    row["name"]: st.session_state[f"spend_{row['name']}"] / 100
    for _, row in spend_df.iterrows()
}

tax_delta   = compute_tax_delta(tax_df, tax_changes)
spend_delta = compute_spend_delta(spend_df, spend_changes)

baseline_surplus = -BASELINE_DEFICIT
surplus_new      = baseline_surplus + tax_delta - spend_delta

total_receipts_new  = tax_df["baseline_receipts"].sum() + OTHER_RECEIPTS + tax_delta
programme_spend_new = spend_df["baseline"].sum() + spend_delta

# ── Results Panel ─────────────────────────────────────────────────────────
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

st.caption("Badges show impact on **surplus** (green = up, red = down). Baseline surplus −£137 bn.")
# <<< end of app.py <<<
