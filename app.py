# >>> file: app.py >>>
"""
UK Mock Spending Review – v1.8
- Tabs: Tax, Spend, Results
- Tax/Spend tabs: grouped sliders with headers above
- Summary panel on Tax and Spend tabs
- Results tab: side-by-side stacked vertical bars with summaries
"""
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

# Config
DATA_DIR = pathlib.Path(__file__).parent
OTHER_RECEIPTS = 310  # £bn

st.set_page_config(page_title="UK Mock Spending Review", layout="wide")
st.title("💰 UK Mock Spending Review (v1.8)")

# Load data
try:
    tax_df = load_tax_table(DATA_DIR / "baseline_tax.csv")
    spend_df = load_spend_table(DATA_DIR / "baseline_spend.csv")
except FileNotFoundError as e:
    st.error(f"Missing CSV: {e.filename}")
    st.stop()

# Helpers
def badge(delta):
    colour = "#228B22" if delta>0 else "#C70039" if delta<0 else "#666"
    sign = "+" if delta>0 else ""
    return f"<span style='background:{colour};color:#fff;padding:2px 6px;border-radius:4px;font-size:0.9em'>{sign}{delta:.1f} bn</span>"

def fmt_value(val, unit):
    u = unit.strip()
    if 'ppt' in u or '%' in u: return f"{int(round(val))}%"
    if u.startswith('£'): return f"£{val:,.0f}"
    return f"{val:g}{u}"

# Grouping

def tax_group(n):
    n0=n.lower()
    if 'income tax' in n0 or 'personal allowance' in n0 or 'basic‑rate limit' in n0: return 'Income Tax & Thresholds'
    if 'nics' in n0: return 'National Insurance'
    if 'corporation' in n0: return 'Corporation Tax'
    if n.startswith('VAT'): return 'VAT'
    if 'cgt' in n0: return 'Capital Gains Tax'
    if 'iht' in n0: return 'Inheritance Tax'
    if 'ipt' in n0: return 'Insurance Premium Tax'
    if 'sdlt' in n0 or 'stamp' in n0: return 'Stamp Duty'
    if any(x in n0 for x in ['duty','levy','fuel','apd','vehicle']): return 'Duties & Environmental Taxes'
    return 'Other taxes'

def spend_group(n):
    n0=n.lower()
    if any(x in n0 for x in ['nhs','health','social care']): return 'Health & Care'
    if any(x in n0 for x in ['school','education','childcare','student','skills']): return 'Education & Skills'
    if 'pension' in n0: return 'Pensions'
    if any(x in n0 for x in ['benefit','welfare','disability']): return 'Welfare & Benefits'
    if any(x in n0 for x in ['defence','security']): return 'Defence & Security'
    if any(x in n0 for x in ['transport','rail','roads']): return 'Transport'
    if any(x in n0 for x in ['environment','climate','agriculture']): return 'Environment & Agriculture'
    if any(x in n0 for x in ['culture','sport','housing','community','business','r&d','innovation']): return 'Economic & Community'
    if any(x in n0 for x in ['devolved','local','eu','cross‑cutting']): return 'Inter‑governmental & Other'
    return 'Other programmes'

# Build groups
tax_groups=defaultdict(list)
for _,r in tax_df.iterrows(): tax_groups[tax_group(r['name'])].append(r)
spend_groups=defaultdict(list)
for _,r in spend_df.iterrows(): spend_groups[spend_group(r['name'])].append(r)

# Compute changes from session
changes_tax = {r['name']: st.session_state.get(f"tax_{r['name']}",0) for _,r in tax_df.iterrows()}
changes_spend = {r['name']: st.session_state.get(f"spend_{r['name']}",0)/100 for _,r in spend_df.iterrows()}
tax_delta=compute_tax_delta(tax_df,changes_tax)
spend_delta=compute_spend_delta(spend_df,changes_spend)
baseline_surplus=-BASELINE_DEFICIT
surplus_new=baseline_surplus+tax_delta-spend_delta
total_receipts=tax_df['baseline_receipts'].sum()+OTHER_RECEIPTS+tax_delta
programme_spend=spend_df['baseline'].sum()+spend_delta

# Tabs
tax_tab,spend_tab,results_tab=st.tabs(['Tax','Spend','Results'])

# Tax tab
with tax_tab:
    st.header('Tax settings & summary')
    c1,c2=st.columns([4,2])
    with c1:
        st.caption('Revenue-raising moves improve surplus (green badge).')
        for grp,rows in tax_groups.items():
            with st.expander(grp):
                for r in rows:
                    key=f"tax_{r['name']}"
                    base,unit=r['baseline'],r['unit']
                    prev=st.slider(label=r['name'],min_value=int(r['min_change']),max_value=int(r['max_change']),value=st.session_state.get(key,0),key=key,format='%d')
                    newv=base+prev
                    st.markdown(f"**{r['name']}**  <span style='color:grey'>{fmt_value(base,unit)}</span> → <span style='font-weight:700'>{fmt_value(newv,unit)}</span> {badge(prev*r['delta_per_unit'])}",unsafe_allow_html=True)
    with c2:
        st.metric('Total receipts',f'£{total_receipts:,.0f} bn',f'{tax_delta:+.1f}')
        st.metric('Programme spend',f'£{programme_spend:,.0f} bn',f'{-spend_delta:+.1f}')
        st.metric('Surplus (+) / Deficit (−)',f'£{surplus_new:,.0f} bn',f'{surplus_new-baseline_surplus:+.1f}',delta_color='normal')

# Spend tab
with spend_tab:
    st.header('Spend settings & summary')
    c1,c2=st.columns([4,2])
    with c1:
        st.caption('Programme spend adjustments: cuts improve the surplus (green badge).')
        for grp,rows in spend_groups.items():
            with st.expander(grp):
                for r in rows:
                    key=f"spend_{r['name']}"
                    base=r['baseline']
                    prev=st.slider(label=r['name'],min_value=int(r['min_pct']),max_value=int(r['max_pct']),value=int(st.session_state.get(key,0)*100),key=key,format='%d%%')
                    newsp=base*(1+prev/100)
                    st.markdown(f"**{r['name']}**  <span style='color:grey'>£{base:,.0f} bn</span> → <span style='font-weight:700'>£{newsp:,.0f} bn</span> {badge(-(newsp-base))}",unsafe_allow_html=True)
    with c2:
        st.metric('Total receipts',f'£{total_receipts:,.0f} bn',f'{tax_delta:+.1f}')
        st.metric('Programme spend',f'£{programme_spend:,.0f} bn',f'{-spend_delta:+.1f}')
        st.metric('Surplus (+) / Deficit (−)',f'£{surplus_new:,.0f} bn',f'{surplus_new-baseline_surplus:+.1f}',delta_color='normal')

# Results tab
with results_tab:
    st.header('Results Overview: Change by Category')
    chart1,chart2=st.columns(2)
    tax_cat={grp:sum(changes_tax[n]*r['delta_per_unit'] for r in rows) for grp,rows in tax_groups.items()}
    spend_cat={grp:sum(changes_spend[n]*r['baseline'] for r in rows) for grp,rows in spend_groups.items()}
    with chart1:
        st.subheader('Tax change by category')
        fig=go.Figure()
        for grp,val in tax_cat.items(): fig.add_trace(go.Bar(name=grp,x=[''],y=[val]))
        fig.update_layout(barmode='stack',showlegend=True,xaxis=dict(visible=False),yaxis=dict(title='Δ £bn'))
        st.plotly_chart(fig,use_container_width=True)
    with chart2:
        st.subheader('Spend change by category')
        fig2=go.Figure()
        for grp,val in spend_cat.items(): fig2.add_trace(go.Bar(name=grp,x=[''],y=[val]))
        fig2.update_layout(barmode='stack',showlegend=True,xaxis=dict(visible=False),yaxis=dict(title='Δ £bn'))
        st.plotly_chart(fig2,use_container_width=True)
    t1,t2=st.columns(2)
    df1=pd.DataFrame([(g,v) for g,v in tax_cat.items()],columns=['Category','Δ £bn']).sort_values('Δ £bn',ascending=False)
    df2=pd.DataFrame([(g,v) for g,v in spend_cat.items()],columns=['Category','Δ £bn']).sort_values('Δ £bn',ascending=False)
    with t1: st.subheader('Tax summary'); st.table(df1)
    with t2: st.subheader('Spend summary'); st.table(df2)
    st.markdown(f"Baseline surplus: £{baseline_surplus:,.0f} bn → New surplus: £{surplus_new:,.0f} bn.")
# <<< end of app.py <<<
