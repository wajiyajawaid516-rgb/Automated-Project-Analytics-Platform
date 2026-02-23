"""
Directory Page — Stakeholder management per project.
"""

import streamlit as st
import requests

API_BASE = "http://localhost:8000/api/v1"

st.set_page_config(page_title="Directory", page_icon="👥", layout="wide")
st.title("👥 Project Directory")
st.markdown("Manage stakeholders and contacts for each project.")

# Fetch projects for dropdown
try:
    resp = requests.get(f"{API_BASE}/projects", timeout=5)
    if resp.status_code == 200:
        projects = resp.json()
        if projects:
            selected = st.selectbox(
                "Select Project",
                options=projects,
                format_func=lambda p: f"{p['job_number']} — {p['name']}",
            )

            if selected:
                st.markdown("---")
                st.subheader(f"Directory: {selected['name']}")

                # Fetch directory
                dir_resp = requests.get(
                    f"{API_BASE}/projects/{selected['id']}/directory", timeout=5
                )

                if dir_resp.status_code == 200:
                    entries = dir_resp.json()
                    if entries:
                        for entry in entries:
                            contact = entry.get("contact", {})
                            org = contact.get("organisation", {}) if contact else {}
                            col1, col2, col3, col4 = st.columns([2, 2, 1.5, 1.5])
                            with col1:
                                name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}" if contact else "Unknown"
                                st.markdown(f"**{name}**")
                                st.caption(contact.get("job_title", "") if contact else "")
                            with col2:
                                st.markdown(org.get("name", "No organisation") if org else "No organisation")
                            with col3:
                                role = entry.get("role", "Other")
                                st.markdown(f"🏷️ {role}")
                            with col4:
                                email = contact.get("email", "") if contact else ""
                                if email:
                                    st.markdown(f"📧 {email}")
                            st.markdown("---")
                    else:
                        st.info("No contacts assigned to this project yet.")

                # Add contact to project
                with st.expander("➕ Add Contact to Project"):
                    contacts_resp = requests.get(f"{API_BASE}/contacts", timeout=5)
                    if contacts_resp.status_code == 200:
                        contacts = contacts_resp.json()
                        if contacts:
                            contact_sel = st.selectbox(
                                "Select Contact",
                                options=contacts,
                                format_func=lambda c: f"{c['first_name']} {c['last_name']} ({c.get('job_title', 'N/A')})",
                            )
                            role = st.selectbox("Role", [
                                "Client", "Architect", "Engineer", "Quantity Surveyor",
                                "Project Manager", "Contractor", "Consultant",
                                "Sub-Contractor", "Supplier", "Other"
                            ])
                            notes = st.text_input("Notes (optional)")

                            if st.button("Add to Directory"):
                                add_resp = requests.post(
                                    f"{API_BASE}/projects/{selected['id']}/directory",
                                    json={
                                        "project_id": selected["id"],
                                        "contact_id": contact_sel["id"],
                                        "role": role,
                                        "notes": notes,
                                    }, timeout=5
                                )
                                if add_resp.status_code == 201:
                                    st.success("✅ Contact added to project directory!")
                                    st.rerun()
                                else:
                                    st.error(f"Failed: {add_resp.text}")
        else:
            st.info("No projects found. Create a project first.")
    else:
        st.error("Failed to fetch projects.")
except requests.exceptions.ConnectionError:
    st.warning("⚠️ Cannot connect to the API. Start the backend first.")
