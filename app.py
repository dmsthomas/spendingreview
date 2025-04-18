# >>> file: app.py >>>
"""UK Mock Spending Review – v1.6
• Tabs: Tax, Spend, Results
• Tax/Spend tabs: grouped sliders with baseline → new and surplus badges
• Results tab: vertical stacked bars side by side, summary tables underneath
"""
import pathlib
from collections import defaultdict

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from calc import (
    load_tax_table,
    load_spend_table,
    compute_tax_delta,
    compute_spend_delta,
    BASELINE_DEFICIT,
)

# Config
DATA_DIR = pathlib.Path(__file__).parent
OTHER_RECEIPTS = 310  # £bn residual so receipts sum to £1,141 bn

st.set_page_config(page_title="UK Mock Spending Review", layout="wide")
st.title("💰 UK Mock Spending Review (v1.6)")

# Load baseline data
try:
    tax_df = load_tax_table(DATA_DIR / "baseline_tax.csv")
    spend_df = load_spend_table(DATA_DIR / "baseline_spend.csv")
except FileNotFoundError as e:
    st.error(f"Missing CSV: {e.filename}")
    st.stop()

# Helper functions
def badge(delta_surplus: float) -> str:
    colour = "#228B22" if delta_surplus > 0 else "#C70039" if delta_surplus < 0 else "#666"
    sign = "+" if delta_surplus > 0 else ""
    return f"<span style='background:{colour};color:#fff;padding:2px 6px;border-radius:4px;font-size:0.9em'>{sign}{delta_surplus:.1f}bn</span>"

def fmt_value(val: float, unit: str) -> str:
    unit = unit.strip()
    if "ppt" in unit:
        return f"{int(round(val))}%"
    if unit.startswith("£"):
        return f"{unit}{int(round(val))}"
    return f"{val:g}{unit}"

# Grouping logic (same as v1.5)
def tax_group(name: str) -> str:
    n = name.lower()
    if any(x in n for x in ["income tax", "personal allowance", "basic‑rate limit"]): return "Income Tax & Thresholds"
    if "nics" in n: return "National Insurance"
    if "corporation" in n: return "Corporation Tax"
    if name.startswith("VAT"): return "VAT"
    if any(x in n for x in ["capital gains", "cgt"]): return "Capital Gains Tax"
    if any(x in n for x in ["inheritance", "iht"]): return "Inheritance Tax"
    if "ipt" in n: return "Insurance Premium Tax"
    if any(x in n for x in ["stamp", "sdlt"]): return "Stamp Duty"
    if any(x in n for x in ["duty", "levy", "fuel", "apd", "vehicle"]): return "Duties & Environmental Taxes"
    return "Other taxes"

def spend_group(name: str) -> str:
    n = name.lower()
    if any(x in n for x in ["nhs", "health", "social care"]): return "Health & Care"
    if any(x in n for x in ["school", "education", "childcare", "student", "skills"]): return "Education & Skills"
    if "pension" in n: return "Pensions"
    if any(x in n for x in ["universal credit", "benefit", "welfare", "disability"]): return "Welfare & Benefits"
    if any(x in n for x in ["defence", "security"]): return "Defence & Security"
    if any(x in n for x in ["transport", "rail", "roads"]): return "Transport"
    if any(x in n for x in ["environment", "climate", "agriculture"]): return "Environment & Agriculture"
    if any(x in n for x in ["culture", "sport", "housing", "community", "business", "r&d", "innovation"]): return "Economic & Community"
    if any(x in n for x in ["devolved", "local", "eu", "cross‑cutting"]): return "Inter‑governmental & Other"
    return "Other programmes"

# Build grouped dicts
tax_groups = defaultdict(list)
for _, r in tax_df.iterrows(): tax_groups[tax_group(r["name"])].append(r)
spend_groups = defaultdict(list)
for _, r in spend_df.iterrows(): spend_groups[spend_group(r["name"])].append(r)

# Tabs layout
tabs = st.tabs(["Tax", "Spend", "Results"])

# --- TAX tab
with tabs[0]:
    st.caption("Revenue-raising moves improve surplus (green badge).")
    for grp, rows in tax_groups.items():
        with st.expander(grp, expanded=False):
            for r in rows:
                key = f"tax_{r['name']}"
                baseline = r['baseline']; unit = r['unit']
                min_d, max_d = int(r['min_change']), int(r['max_change'])
                # slider
                delta = st.slider("", min_d, max_d, value=st.session_state.get(key, 0), key=key, label_visibility="collapsed")
                # header
                newv = baseline + delta
                sup_delta = delta * r['delta_per_unit']
                st.markdown(f"**{r['name']}**  <span style='color:grey'>{fmt_value(baseline,unit)}</span> → <span style='font-weight:700'>{fmt_value(newv,unit)}</span> {badge(sup_delta)}", unsafe_allow_html=True)

# --- SPEND tab
with tabs[1]:
    st.caption("Programme spend adjustments: cuts improve surplus (green badge).")
    for grp, rows in spend_groups.items():
        with st.expander(grp, expanded=False):
            for r in rows:
                key = f"spend_{r['name']}"
                baseline = r['baseline']
                min_p, max_p = int(r['min_pct']), int(r['max_pct'])
                # slider
                pct = st.slider("", min_p, max_p, value=st.session_state.get(key, 0), key=key, format="%d%%", label_visibility="collapsed")
                # header
                newsp = baseline * (1 + pct/100)
                sup_delta = -(newsp - baseline)
                st.markdown(f"**{r['name']}**  <span style='color:grey'>£{baseline:.0f}bn</span> → <span style='font-weight:700'>£{newsp:.0f}bn</span> {badge(sup_delta)}", unsafe_allow_html=True)

# Collect changes
tax_changes = {r['name']: st.session_state.get(f"tax_{r['name']}", 0) for _, r in tax_df.iterrows()}
spend_changes = {r['name']: st.session_state.get(f"spend_{r['name']}", 0)/100 for _, r in spend_df.iterrows()}

tax_delta = compute_tax_delta(tax_df, tax_changes)
spend_delta = compute_spend_delta(spend_df, spend_changes)
baseline_surplus = -BASELINE_DEFICIT
surplus_new = baseline_surplus + tax_delta - spend_delta

# --- RESULTS tab
with tabs[2]:
    st.header("Results Overview: Change by Category")
    # Aggregate category deltas
tax_cat = {grp: sum(st.session_state.get(f"tax_{r['name']}",0)*r['delta_per_unit'] for r in rows) for grp,rows in tax_groups.items()}
spend_cat = {grp: sum((st.session_state.get(f"spend_{r['name']}",0)/100)*r['baseline'] for r in rows) for grp,rows in spend_groups.items()}

    # Side-by-side charts
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.subheader("Tax change by category")
        fig1 = go.Figure()
        for grp, val in tax_cat.items():
            fig1.add_trace(go.Bar(name=grp, x=["Tax"], y=[val]))
        fig1.update_layout(barmode='stack', showlegend=True, xaxis={'visible':False})
        st.plotly_chart(fig1, use_container_width=True)
    with chart_col2:
        st.subheader("Spend change by category")
        fig2 = go.Figure()
        for grp, val in spend_cat.items():
            fig2.add_trace(go.Bar(name=grp, x=["Spend"], y=[-val]))
        fig2.update_layout(barmode='stack', showlegend=True, xaxis={'visible':False})
        st.plotly_chart(fig2, use_container_width=True)

    # Summary tables
    table_col1, table_col2 = st.columns(2)
    df_tax = pd.DataFrame([{'Category':grp,'Δ £bn':v} for grp,v in tax_cat.items()])
    df_spend = pd.DataFrame([{'Category':grp,'Δ £bn':-v} for grp,v in spend_cat.items()])
    with table_col1:
        st.table(df_tax.sort_values('Δ £bn', ascending=False).reset_index(drop=True))
    with table_col2:
        st.table(df_spend.sort_values('Δ £bn', ascending=False).reset_index(drop=True))

st.caption(f"Baseline surplus: £{baseline_surplus:,.0f}bn → New surplus: £{surplus_new:,.0f}bn.")
# <<< end of app.py <<<
