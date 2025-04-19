# >>> file: app.py >>>
"""
UK Mock Spending Review – v2.1
- Three tabs: Tax, Spend, Results
- Fixed tab layout, uses BASELINE_RECEIPTS constant for total receipts
- Summary panels on Tax and Spend tabs
- Results tab: side-by-side stacked bars with separate legends, summary tables beneath
"""
import re
import pathlib
from collections import defaultdict

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from calc import (
    load_tax_table,
    load_spend_table,
    compute_tax_delta,
    compute_spend_delta,
    BASELINE_DEFICIT,
)

# Configuration
DATA_DIR = pathlib.Path(__file__).parent
OTHER_RECEIPTS = 310            # £bn residual
BASELINE_RECEIPTS = 1141        # £bn at baseline total receipts

st.set_page_config(page_title="UK Mock Spending Review", layout="wide")
st.title("💰 UK Mock Spending Review (v2.1)")

# Load baseline data
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
        f"<span style='background:{colour};color:#fff;"
        f"padding:2px 6px;border-radius:4px;font-size:0.9em'>{sign}{delta_surplus:.1f} bn</span>"
    )

def fmt_value(val: float, unit: str) -> str:
    u = unit.strip()
    if "ppt" in u or "%" in u:
        return f"{int(round(val))}%"
    if u.startswith("£"):
        return f"£{val:,.0f}"
    return f"{val:g}{u}"

# Grouping logic
def tax_group(name: str) -> str:
    n = name.lower()
    if any(x in n for x in ["income tax", "personal allowance", "basic‑rate limit"]): return "Income Tax & Thresholds"
    if "nics" in n: return "National Insurance"
    if "corporation" in n: return "Corporation Tax"
    if name.startswith("VAT"): return "VAT"
    if "cgt" in n: return "Capital Gains Tax"
    if "iht" in n: return "Inheritance Tax"
    if "ipt" in n: return "Insurance Premium Tax"
    if any(x in n for x in ["stamp","sdlt"]): return "Stamp Duty"
    if any(x in n for x in ["duty","levy","fuel","apd","vehicle"]): return "Duties & Environmental Taxes"
    return "Other taxes"

def spend_group(name: str) -> str:
    n = name.lower()
    if any(x in n for x in ["nhs","health","social care"]): return "Health & Care"
    if any(x in n for x in ["school","education","childcare","student","skills"]): return "Education & Skills"
    if "pension" in n: return "Pensions"
    if any(x in n for x in ["benefit","welfare","disability"]): return "Welfare & Benefits"
    if any(x in n for x in ["defence","security"]): return "Defence & Security"
    if any(x in n for x in ["transport","rail","roads"]): return "Transport"
    if any(x in n for x in ["environment","climate","agriculture"]): return "Environment & Agriculture"
    if any(x in n for x in ["culture","sport","housing","community","business","r&d","innovation"]): return "Economic & Community"
    if any(x in n for x in ["devolved","local","eu","cross‑cutting"]): return "Inter‑governmental & Other"
    return "Other programmes"

# Build grouped dicts
tax_groups = defaultdict(list)
for _, r in tax_df.iterrows(): tax_groups[tax_group(r['name'])].append(r)
spend_groups = defaultdict(list)
for _, r in spend_df.iterrows(): spend_groups[spend_group(r['name'])].append(r)

# Compute deltas & totals
tax_changes = {r['name']: st.session_state.get(f"tax_{r['name']}",0) for _,r in tax_df.iterrows()}
spend_changes = {r['name']: st.session_state.get(f"spend_{r['name']}",0)/100 for _,r in spend_df.iterrows()}
tax_delta = compute_tax_delta(tax_df, tax_changes)
spend_delta = compute_spend_delta(spend_df, spend_changes)
baseline_surplus = -BASELINE_DEFICIT
surplus_new = baseline_surplus + tax_delta - spend_delta

total_receipts_new = BASELINE_RECEIPTS + tax_delta
programme_spend_new = spend_df['baseline'].sum() + spend_delta

# Prepare category breakdown
tax_cat = {grp:sum(tax_changes[r['name']]*r['delta_per_unit'] for r in rows) for grp,rows in tax_groups.items()}
spend_cat = {grp:sum(spend_changes[r['name']]*r['baseline'] for r in rows) for grp,rows in spend_groups.items()}

# Tabs layout
tab_tax, tab_spend, tab_results = st.tabs(["Tax","Spend","Results"])

# --- Tax Tab
with tab_tax:
    st.header("Tax settings & summary")
    c1,c2 = st.columns([4,2])
    with c1:
        st.markdown("Revenue-raising moves improve surplus (green badge).")
        for grp,rows in tax_groups.items():
            with st.expander(grp):
                for r in rows:
                    key=f"tax_{r['name']}"; base,unit=r['baseline'],r['unit']
                    prev=st.slider(label=r['name'],min_value=int(r['min_change']),max_value=int(r['max_change']),value=tax_changes[r['name']],key=key,label_visibility="collapsed")
                    newv=base+prev
                    st.markdown(f"**{r['name']}**  <span style='color:grey'>{fmt_value(base,unit)}</span> → <span style='font-weight:700'>{fmt_value(newv,unit)}</span> {badge(prev*r['delta_per_unit'])}",unsafe_allow_html=True)
    with c2:
        st.metric("Total receipts",f"£{total_receipts_new:,.0f} bn",f"{tax_delta:+.1f}")
        st.metric("Programme spend",f"£{programme_spend_new:,.0f} bn",f"{-spend_delta:+.1f}")
        st.metric("Surplus (+) / Deficit (−)",f"£{surplus_new:,.0f} bn",f"{surplus_new-baseline_surplus:+.1f}",delta_color="normal")

# --- Spend Tab
with tab_spend:
    st.header("Spend settings & summary")
    c1,c2 = st.columns([4,2])
    with c1:
        st.markdown("Programme spend adjustments: cuts improve surplus (green badge).")
        for grp,rows in spend_groups.items():
            with st.expander(grp):
                for r in rows:
                    key=f"spend_{r['name']}"; base=r['baseline']
                    prev_pct=int(spend_changes[r['name']]*100)
                    prev=st.slider(label=r['name'],min_value=int(r['min_pct']),max_value=int(r['max_pct']),value=prev_pct,key=key,format="%d%%",label_visibility="collapsed")
                    newsp=base*(1+prev/100)
                    st.markdown(f"**{r['name']}**  <span style='color:grey'>£{base:,.0f} bn</span> → <span style='font-weight:700'>£{newsp:,.0f} bn</span> {badge(-(newsp-base))}",unsafe_allow_html=True)
    with c2:
        st.metric("Total receipts",f"£{total_receipts_new:,.0f} bn",f"{tax_delta:+.1f}")
        st.metric("Programme spend",f"£{programme_spend_new:,.0f} bn",f"{-spend_delta:+.1f}")
        st.metric("Surplus (+) / Deficit (−)",f"£{surplus_new:,.0f} bn",f"{surplus_new-baseline_surplus:+.1f}",delta_color="normal")

# --- Results Tab
with tab_results:
    st.header("Results Overview: Change by Category")
    col1,col2 = st.columns(2)
    with col1:
        st.subheader("Tax change by category")
        fig=go.Figure()
        for grp,val in tax_cat.items(): fig.add_trace(go.Bar(name=grp,x=["Tax"],y=[val]))
        fig.update_layout(barmode='stack',showlegend=True,xaxis=dict(visible=False),yaxis=dict(title='Δ £bn'))
        st.plotly_chart(fig,use_container_width=True)
    with col2:
        st.subheader("Spend change by category")
        fig2=go.Figure()
        for grp,val in spend_cat.items(): fig2.add_trace(go.Bar(name=grp,x=["Spend"],y=[val]))
        fig2.update_layout(barmode='stack',showlegend=True,xaxis=dict(visible=False),yaxis=dict(title='Δ £bn'))
        st.plotly_chart(fig2,use_container_width=True)
    t1,t2=st.columns(2)
    df1=pd.DataFrame([(g,v) for g,v in tax_cat.items()],columns=['Category','Δ £bn']).sort_values('Δ £bn',ascending=False)
    df2=pd.DataFrame([(g,v) for g,v in spend_cat.items()],columns=['Category','Δ £bn']).sort_values('Δ £bn',ascending=False)
    with t1: st.subheader('Tax summary'); st.table(df1)
    with t2: st.subheader('Spend summary'); st.table(df2)
    st.markdown(f"Baseline surplus: £{-BASELINE_DEFICIT:,.0f} bn → New surplus: £{surplus_new:,.0f} bn.")
# <<< end of app.py <<<
