"""
Reports Page — Export project data as CSV and PDF.
"""

import streamlit as st
import requests

API_BASE = "http://localhost:8000/api/v1"

st.set_page_config(page_title="Reports", page_icon="📄", layout="wide")
st.title("📄 Report Generation")
st.markdown("Generate and download project reports in CSV and PDF formats.")

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
                st.subheader(f"Reports for: {selected['name']}")

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("##### 📊 Analytics Reports")
                    st.markdown("Stage-level performance breakdown with burn rates and risk indicators.")

                    if st.button("📥 Download Analytics CSV"):
                        csv_resp = requests.get(
                            f"{API_BASE}/reports/analytics/{selected['id']}/csv",
                            timeout=10
                        )
                        if csv_resp.status_code == 200:
                            st.download_button(
                                "💾 Save CSV",
                                data=csv_resp.content,
                                file_name=f"{selected['job_number']}_analytics.csv",
                                mime="text/csv",
                            )
                        else:
                            st.error("Failed to generate CSV")

                    if st.button("📥 Download Analytics PDF"):
                        pdf_resp = requests.get(
                            f"{API_BASE}/reports/analytics/{selected['id']}/pdf",
                            timeout=10
                        )
                        if pdf_resp.status_code == 200:
                            st.download_button(
                                "💾 Save PDF",
                                data=pdf_resp.content,
                                file_name=f"{selected['job_number']}_report.pdf",
                                mime="application/pdf",
                            )
                        else:
                            st.error("Failed to generate PDF")

                with col2:
                    st.markdown("##### 👥 Directory Reports")
                    st.markdown("Project stakeholder directory with contact details and roles.")

                    if st.button("📥 Download Directory CSV"):
                        csv_resp = requests.get(
                            f"{API_BASE}/reports/directory/{selected['id']}/csv",
                            timeout=10
                        )
                        if csv_resp.status_code == 200:
                            st.download_button(
                                "💾 Save Directory CSV",
                                data=csv_resp.content,
                                file_name=f"{selected['job_number']}_directory.csv",
                                mime="text/csv",
                            )
                        else:
                            st.error("Failed to generate CSV")
        else:
            st.info("No projects found.")
except requests.exceptions.ConnectionError:
    st.warning("⚠️ Cannot connect to the API. Start the backend first.")
