# >>> file: app.py >>>
"""
UK Mock Spending Review – v1.10
- Tabs: Tax, Spend, Results
- Tax/Spend: grouped sliders with headers above sliders
- Spend sliders use container pattern to avoid bounce-to-max
- Summary panels on Tax/Spend tabs
- Results: side-by-side vertical stacked bars with separate legends, summary tables beneath
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

# Configuration
DATA_DIR = pathlib.Path(__file__).parent
OTHER_RECEIPTS = 310  # £bn residual
BASELINE_RECEIPTS = 1141  # £bn at baseline

st.set_page_config(page_title="UK Mock Spending Review", layout="wide")
st.title("💰 UK Mock Spending Review (v1.10)")

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
        f"<span style='background:{colour};color:#fff;"  \
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
    if any(x in n for x in ["income tax", "personal allowance", "basic‑rate limit"]):
        return "Income Tax & Thresholds"
    if "nics" in n:
        return "National Insurance"
    if "corporation" in n:
        return "Corporation Tax"
    if name.startswith("VAT"):
        return "VAT"
    if "cgt" in n:
        return "Capital Gains Tax"
    if "iht" in n:
        return "Inheritance Tax"
    if "ipt" in n:
        return "Insurance Premium Tax"
    if any(x in n for x in ["stamp", "sdlt"]):
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
    if any(x in n for x in ["benefit", "welfare", "disability"]):
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
tax_groups = defaultdict(list)
for _, row in tax_df.iterrows():
    tax_groups[tax_group(row["name"])].append(row)
spend_groups = defaultdict(list)
for _, row in spend_df.iterrows():
    spend_groups[spend_group(row["name"])].append(row)

# Compute changes from session
changes_tax = {r['name']: st.session_state.get(f"tax_{r['name']}", 0) for _, r in tax_df.iterrows()}
changes_spend = {r['name']: st.session_state.get(f"spend_{r['name']}", 0) / 100 for _, r in spend_df.iterrows()}

# Compute aggregate deltas and totals
tax_delta = compute_tax_delta(tax_df, changes_tax)
spend_delta = compute_spend_delta(spend_df, changes_spend)
baseline_surplus = -BASELINE_DEFICIT
surplus_new = baseline_surplus + tax_delta - spend_delta
total_receipts = BASELINE_RECEIPTS + tax_delta
programme_spend = spend_df['baseline'].sum() + spend_delta

# Aggregate by category for Results tab
tax_cat = {grp: sum(changes_tax[r['name']] * r['delta_per_unit'] for r in rows) for grp, rows in tax_groups.items()}
spend_cat = {grp: sum(changes_spend[r['name']] * r['baseline'] for r in rows) for grp, rows in spend_groups.items()}

# Tabs layout
tabs = st.tabs(["Tax", "Spend", "Results"])

# --- Tax tab
with tabs[0]:
    st.header("Tax settings & summary")
    col1, col2 = st.columns([4, 2])
    with col1:
        st.caption("Revenue-raising moves improve the surplus (green badge).")
        for grp, rows in tax_groups.items():
            with st.expander(grp, expanded=False):
                for r in rows:
                    key = f"tax_{r['name']}"
                    baseline, unit = r['baseline'], r['unit']
                    # Slider then header
                    container = st.container()
                    header_ph = container.empty()
                    slider_val = container.slider(
    label=r['name'],
    min_value=int(r['min_pct']),
    max_value=int(r['max_pct']),
    value=st.session_state.get(key, 0),
    key=key,
    format="%d%%",
    label_visibility="collapsed",
)  # slider control slider control --- Spend tab
with tabs[1]:
    st.header("Spend settings & summary")
    col1, col2 = st.columns([4, 2])
    with col1:
        st.caption("Programme spend adjustments: cuts improve the surplus (green badge).")
        for grp, rows in spend_groups.items():
            with st.expander(grp, expanded=False):
                for r in rows:
                    key = f"spend_{r['name']}"
                    baseline = r['baseline']
                    # Slider then header
                    container = st.container()
                    header_ph = container.empty()
                    slider_val = container.slider(
    label=r['name'],
    min_value=int(r['min_pct']), max_value=int(r['max_pct']),
    value=st.session_state.get(key, 0),
    key=key,
    format="%d%%",
    label_visibility="collapsed"
),
                        key=key,
                        format="%d%%",
                        label_visibility="collapsed"
                    )
                    newsp = baseline * (1 + slider_val / 100)
                    sup_delta = -(newsp - baseline)
                    header_ph.markdown(
                        f"**{r['name']}**  <span style='color:grey'>£{baseline:,.0f} bn</span> → "
                        f"<span style='font-weight:700'>£{newsp:,.0f} bn</span> {badge(sup_delta)}",
                        unsafe_allow_html=True,
                    )
    with col2:
        st.metric("Total receipts", f"£{total_receipts:,.0f} bn", f"{tax_delta:+.1f}")
        st.metric("Programme spend", f"£{programme_spend:,.0f} bn", f"{-spend_delta:+.1f}")
        st.metric(
            "Surplus (+) / Deficit (−)",
            f"£{surplus_new:,.0f} bn",
            f"{surplus_new - baseline_surplus:+.1f}",
            delta_color="normal"
        )

# --- Results tab
with tabs[2]:
    st.header("Results Overview: Change by Category")
    chart_col1, chart_col2 = st.columns(2, gap="large")
    with chart_col1:
        st.subheader("Tax change by category")
        fig_tax = go.Figure()
        for grp, val in tax_cat.items():
            fig_tax.add_trace(go.Bar(name=grp, x=["Tax"], y=[val]))
        fig_tax.update_layout(barmode='stack', showlegend=True, legend=dict(x=1.0, y=1.0), xaxis=dict(visible=False), yaxis=dict(title='Δ £bn'))
        st.plotly_chart(fig_tax, use_container_width=True)
    with chart_col2:
        st.subheader("Spend change by category")
        fig_spend = go.Figure()
        for grp, val in spend_cat.items():
            fig_spend.add_trace(go.Bar(name=grp, x=["Spend"], y=[val]))
        fig_spend.update_layout(barmode='stack', showlegend=True, legend=dict(x=1.0, y=1.0), xaxis=dict(visible=False), yaxis=dict(title='Δ £bn'))
        st.plotly_chart(fig_spend, use_container_width=True)
    table_col1, table_col2 = st.columns(2)
    df_tax = pd.DataFrame([(grp, val) for grp, val in tax_cat.items()], columns=['Category', 'Δ £bn']).sort_values('Δ £bn', ascending=False).reset_index(drop=True)
    df_spend = pd.DataFrame([(grp, val) for grp, val in spend_cat.items()], columns=['Category', 'Δ £bn']).sort_values('Δ £bn', ascending=False).reset_index(drop=True)
    with table_col1:
        st.subheader("Tax summary")
        st.table(df_tax)
    with table_col2:
        st.subheader("Spend summary")
        st.table(df_spend)

    st.markdown(f"Baseline surplus: £{baseline_surplus:,.0f} bn → New surplus: £{surplus_new:,.0f} bn.")
# <<< end of app.py <<<
