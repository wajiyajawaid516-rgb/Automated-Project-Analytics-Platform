"""
Analytics Page — Time tracking performance dashboard.

Shows stage-level burn rates, risk indicators,
and portfolio-level executive summary.
"""

import streamlit as st
import requests
import plotly.graph_objects as go

API_BASE = "http://localhost:8000/api/v1"
RISK_THRESHOLD = 80

st.set_page_config(page_title="Analytics", page_icon="📊", layout="wide")
st.title("📊 Performance Analytics")

# ---------------------------------------------------------------------------
# Portfolio Summary
# ---------------------------------------------------------------------------
st.subheader("📌 Portfolio Overview")

try:
    summary_resp = requests.get(f"{API_BASE}/analytics/portfolio", timeout=5)
    if summary_resp.status_code == 200:
        summary = summary_resp.json()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Projects", summary["total_projects"])
        with col2:
            st.metric("Active Projects", summary["active_projects"])
        with col3:
            st.metric("At Risk", summary["projects_at_risk"], delta_color="inverse")
        with col4:
            st.metric("Overrun", summary["projects_overrun"], delta_color="inverse")

        # Show at-risk and overrun project names
        if summary["at_risk_project_names"]:
            st.warning(f"⚠️ **At Risk:** {', '.join(summary['at_risk_project_names'])}")
        if summary["overrun_project_names"]:
            st.error(f"🔴 **Overrun:** {', '.join(summary['overrun_project_names'])}")

except requests.exceptions.ConnectionError:
    st.warning("⚠️ Cannot connect to the API.")
    st.stop()

# ---------------------------------------------------------------------------
# Project-Level Analysis
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("📋 Project Performance")

try:
    projects_resp = requests.get(f"{API_BASE}/projects", timeout=5)
    if projects_resp.status_code == 200:
        projects = projects_resp.json()
        selected = st.selectbox(
            "Select Project",
            options=projects,
            format_func=lambda p: f"{p['job_number']} — {p['name']}",
        )

        if selected:
            perf_resp = requests.get(
                f"{API_BASE}/analytics/project/{selected['id']}", timeout=5
            )

            if perf_resp.status_code == 200:
                perf = perf_resp.json()

                # Project KPIs
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Allocated", f"{perf['total_allocated_hours']:.0f}h")
                with col2:
                    st.metric("Total Used", f"{perf['total_used_hours']:.0f}h")
                with col3:
                    burn_delta = f"{perf['overall_burn_percentage']:.1f}%"
                    st.metric("Overall Burn Rate", burn_delta)
                with col4:
                    st.metric("Stages At Risk", perf['stages_at_risk'], delta_color="inverse")

                st.markdown("---")

                # Stage-level table
                st.markdown("##### Stage-by-Stage Breakdown")

                stages = perf.get("stage_details", [])
                if stages:
                    # Build visual table
                    for stage in stages:
                        burn = stage["burn_percentage"]
                        if stage["is_overrun"]:
                            colour = "🔴"
                            bg = "background-color: #ffcccc;"
                        elif stage["is_at_risk"]:
                            colour = "🟡"
                            bg = "background-color: #fff3cd;"
                        else:
                            colour = "🟢"
                            bg = ""

                        cols = st.columns([3, 1.5, 1.5, 1.5, 1.5, 1])
                        with cols[0]:
                            st.markdown(f"{colour} **{stage['stage']}**")
                        with cols[1]:
                            st.markdown(f"Allocated: **{stage['allocated_hours']:.0f}h**")
                        with cols[2]:
                            st.markdown(f"Used: **{stage['used_hours']:.0f}h**")
                        with cols[3]:
                            st.markdown(f"Remaining: **{stage['remaining_hours']:.1f}h**")
                        with cols[4]:
                            st.markdown(f"Burn: **{burn:.1f}%**")
                        with cols[5]:
                            risk_label = "OVERRUN" if stage["is_overrun"] else ("AT RISK" if stage["is_at_risk"] else "OK")
                            st.markdown(f"**{risk_label}**")

                # Burn rate chart
                st.markdown("---")
                st.markdown("##### Burn Rate Visualisation")

                if stages:
                    fig = go.Figure()

                    stage_names = [s["stage"].split(" - ")[0] for s in stages]
                    burn_rates = [s["burn_percentage"] for s in stages]
                    colors = [
                        "#e74c3c" if s["is_overrun"]
                        else "#f39c12" if s["is_at_risk"]
                        else "#2ecc71"
                        for s in stages
                    ]

                    fig.add_trace(go.Bar(
                        x=stage_names,
                        y=burn_rates,
                        marker_color=colors,
                        text=[f"{b:.0f}%" for b in burn_rates],
                        textposition="outside",
                    ))

                    fig.add_hline(
                        y=RISK_THRESHOLD,
                        line_dash="dash",
                        line_color="orange",
                        annotation_text=f"Risk Threshold ({RISK_THRESHOLD}%)",
                    )

                    fig.update_layout(
                        title="Stage Burn Rates",
                        xaxis_title="RIBA Stage",
                        yaxis_title="Burn Rate (%)",
                        yaxis=dict(range=[0, max(max(burn_rates) * 1.2, 110)]),
                        height=400,
                        template="plotly_white",
                    )

                    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Error loading analytics: {e}")
