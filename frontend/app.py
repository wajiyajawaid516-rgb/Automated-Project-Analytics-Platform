"""
Business Operations Platform — Main Application.

Streamlit-based internal dashboard for managing construction
projects, stakeholder directories, and performance analytics.
"""

import streamlit as st

st.set_page_config(
    page_title="Business Operations Platform",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.title("🏗️ Business Ops")
st.sidebar.markdown("---")
st.sidebar.markdown("""
**Navigation**
- 📋 Projects
- 👥 Directory  
- 📊 Analytics
- 📄 Reports
""")
st.sidebar.markdown("---")
st.sidebar.caption("v1.0.0 | Internal Use Only")

# ---------------------------------------------------------------------------
# Home Page
# ---------------------------------------------------------------------------
st.title("🏗️ Business Operations Platform")
st.markdown("#### Project Management • Stakeholder Directory • Performance Analytics")

st.markdown("---")

# KPI Cards
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="Active Projects", value="4", delta="1 new this month")
with col2:
    st.metric(label="Total Stakeholders", value="8", delta="2 added")
with col3:
    st.metric(label="Projects At Risk", value="2", delta="1", delta_color="inverse")
with col4:
    st.metric(label="Hours Utilisation", value="78.5%", delta="-2.1%")

st.markdown("---")

# Quick Overview
st.subheader("📌 Quick Overview")

col_left, col_right = st.columns(2)

with col_left:
    st.markdown("##### Recent Activity")
    st.info("📋 **Cardiff Waterfront** — Stage 3 spatial coordination in progress (90% burn rate)")
    st.warning("⚠️ **Penarth School** — Stage 4 technical design has exceeded budget (107.5%)")
    st.success("✅ **Newport Office** — All stages on track")

with col_right:
    st.markdown("##### System Status")
    st.markdown("""
    | Component | Status |
    |-----------|--------|
    | Backend API | 🟢 Healthy |
    | Database | 🟢 Connected |
    | Report Engine | 🟢 Available |
    | Analytics | 🟢 Running |
    """)

st.markdown("---")

st.markdown("""
### About This System

This platform digitises manual construction project management workflows, replacing 
spreadsheet-based tracking with a structured, relational system. It provides:

- **Real-time visibility** into project performance at each RIBA stage
- **Stakeholder management** across multiple projects without data duplication
- **Automated reporting** with branded PDF exports
- **Risk detection** that flags overruns before it's too late

Built with **Python**, **FastAPI**, **Streamlit**, and **SQLAlchemy**.
""")
