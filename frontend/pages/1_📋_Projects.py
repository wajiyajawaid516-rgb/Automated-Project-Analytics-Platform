"""
Projects Page — Manage construction projects.

Provides CRUD operations with project filtering by status and RIBA stage.
"""

import streamlit as st
import requests
import pandas as pd

API_BASE = "http://localhost:8000/api/v1"

st.set_page_config(page_title="Projects", page_icon="📋", layout="wide")
st.title("📋 Project Management")
st.markdown("View and manage all construction projects.")

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
col1, col2, col3 = st.columns(3)
with col1:
    status_filter = st.selectbox("Status", ["All", "Active", "On Hold", "Completed", "Archived"])
with col2:
    stage_filter = st.selectbox("RIBA Stage", [
        "All", "0 - Strategic Definition", "1 - Preparation & Briefing",
        "2 - Concept Design", "3 - Spatial Coordination",
        "4 - Technical Design", "5 - Manufacturing & Construction",
        "6 - Handover", "7 - Use"
    ])
with col3:
    st.write("")  # Spacer

# ---------------------------------------------------------------------------
# Fetch Projects
# ---------------------------------------------------------------------------
try:
    params = {}
    if status_filter != "All":
        params["status"] = status_filter
    if stage_filter != "All":
        params["stage"] = stage_filter

    response = requests.get(f"{API_BASE}/projects", params=params, timeout=5)

    if response.status_code == 200:
        projects = response.json()

        if projects:
            df = pd.DataFrame(projects)
            display_cols = ["job_number", "name", "current_stage", "status"]
            available_cols = [c for c in display_cols if c in df.columns]

            st.dataframe(
                df[available_cols],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "job_number": st.column_config.TextColumn("Job Number", width="small"),
                    "name": st.column_config.TextColumn("Project Name", width="large"),
                    "current_stage": st.column_config.TextColumn("RIBA Stage", width="medium"),
                    "status": st.column_config.TextColumn("Status", width="small"),
                },
            )

            # Project detail view
            st.markdown("---")
            selected_project = st.selectbox(
                "Select a project to view details",
                options=projects,
                format_func=lambda p: f"{p['job_number']} — {p['name']}",
            )

            if selected_project:
                st.subheader(f"📋 {selected_project['name']}")
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"**Job Number:** {selected_project['job_number']}")
                    st.markdown(f"**RIBA Stage:** {selected_project.get('current_stage', 'N/A')}")
                    st.markdown(f"**Status:** {selected_project.get('status', 'N/A')}")
                with col_b:
                    st.markdown(f"**Description:** {selected_project.get('description', 'No description')}")
                    st.markdown(f"**Start Date:** {selected_project.get('start_date', 'N/A')}")
                    st.markdown(f"**Target Completion:** {selected_project.get('target_completion', 'N/A')}")
        else:
            st.info("No projects found matching the selected filters.")
    else:
        st.error(f"Failed to fetch projects (HTTP {response.status_code})")

except requests.exceptions.ConnectionError:
    st.warning("⚠️ Cannot connect to the API. Make sure the backend is running: `uvicorn backend.main:app --reload`")
except Exception as e:
    st.error(f"Error: {e}")

# ---------------------------------------------------------------------------
# Add New Project
# ---------------------------------------------------------------------------
st.markdown("---")
with st.expander("➕ Add New Project"):
    with st.form("new_project_form"):
        new_job = st.text_input("Job Number", placeholder="PRJ-2025-001")
        new_name = st.text_input("Project Name", placeholder="Project name")
        new_desc = st.text_area("Description", placeholder="Brief project description")
        new_stage = st.selectbox("Starting RIBA Stage", [
            "0 - Strategic Definition", "1 - Preparation & Briefing",
            "2 - Concept Design", "3 - Spatial Coordination",
            "4 - Technical Design", "5 - Manufacturing & Construction",
            "6 - Handover", "7 - Use"
        ])
        submitted = st.form_submit_button("Create Project")

        if submitted and new_job and new_name:
            try:
                resp = requests.post(f"{API_BASE}/projects", json={
                    "job_number": new_job,
                    "name": new_name,
                    "description": new_desc,
                    "current_stage": new_stage,
                }, timeout=5)
                if resp.status_code == 201:
                    st.success(f"✅ Project '{new_name}' created successfully!")
                    st.rerun()
                elif resp.status_code == 409:
                    st.warning(f"⚠️ A project with job number '{new_job}' already exists.")
                else:
                    st.error(f"Failed to create project: {resp.text}")
            except requests.exceptions.ConnectionError:
                st.warning("Cannot connect to the API.")
