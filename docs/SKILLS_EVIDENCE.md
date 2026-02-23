# Skills Evidence & Competency Mapping

This document maps the technical and professional skills demonstrated in this project to **UK Skilled Worker visa-relevant roles**. Each skill is backed by concrete evidence from the codebase.

---

## Technical Skills

### 1. Python Backend Development
**Evidence**: `backend/main.py`, `backend/api/routes/*.py`, `backend/services/*.py`
- Production-grade FastAPI application with modular route registration
- Dependency injection for database sessions
- Error handling with appropriate HTTP status codes
- Pydantic models for request/response validation

**Relevant roles**: Software Engineer, Backend Developer, API Engineer

---

### 2. REST API Design
**Evidence**: `backend/api/routes/projects.py`, `directory.py`, `time_entries.py`
- Proper HTTP method usage (GET for reads, POST for creates, PATCH for updates, DELETE for archives)
- Query parameter filtering with validation
- Consistent error responses (400, 404, 409)
- Versioned API paths (`/api/v1/...`)

**Relevant roles**: API Engineer, Integration Engineer, Software Engineer

---

### 3. Relational Data Modelling
**Evidence**: `backend/api/models/database.py`
- One-to-many relationships (Organisation → Contacts, Project → TimeEntries)
- Junction table pattern (ProjectDirectory linking Projects and Contacts)
- Enum-based domain modelling (RIBA stages, project status, contact roles)
- Foreign key constraints with referential integrity

**Relevant roles**: Data Engineer, Database Developer, Analytics Engineer

---

### 4. Production-Safe Engineering
**Evidence**: Throughout codebase
- Soft deletes (`is_active` flag on all models)
- Idempotent write operations (duplicate prevention)
- Input validation (Pydantic schemas with constraints)
- Dev/Prod environment separation
- Backup-first document processing

**Relevant roles**: Platform Engineer, Reliability Engineer, DevOps Engineer

---

### 5. Document Automation
**Evidence**: `backend/services/document_automation.py`, `automation/document_updater.py`
- Programmatic PDF generation with ReportLab
- Batch Word document processing with python-docx
- Dynamic table layouts and company branding
- CLI interface with dry-run safety mode

**Relevant roles**: Automation Engineer, Process Improvement Analyst

---

### 6. Workflow Automation
**Evidence**: `backend/services/workflow_engine.py`
- Rule-based email-to-task conversion
- Pattern matching for project references
- Priority classification from keywords
- Batch processing with structured results

**Relevant roles**: Automation Engineer, Systems Analyst, Digital Transformation

---

### 7. Analytics & Business Intelligence
**Evidence**: `backend/api/routes/time_entries.py`, `frontend/pages/3_📊_Analytics.py`
- Stage-level burn rate computation
- Risk detection with configurable thresholds
- Executive portfolio summary
- Interactive Plotly visualisations

**Relevant roles**: BI Developer, Data Analyst, Reporting Analyst

---

### 8. Frontend Development (Internal Tools)
**Evidence**: `frontend/app.py`, `frontend/pages/*.py`
- Multi-page Streamlit application
- CRUD forms with validation
- Data tables with filtering
- Interactive dashboard with KPI metrics

**Relevant roles**: Full-Stack Developer, Internal Tools Engineer

---

### 9. Testing & Quality Assurance
**Evidence**: `backend/tests/*.py`
- Unit tests for business logic
- Integration tests for API endpoints
- Edge case testing (duplicates, not found, invalid input)
- Isolated test database setup/teardown

**Relevant roles**: Software Engineer, QA Engineer

---

## Professional Competencies

### Ownership & Autonomy
- Designed system architecture independently
- Made trade-off decisions (rules vs AI, soft vs hard deletes)
- Managed full development lifecycle (design → build → test → document)

### Systems Thinking
- Understood how changes in one layer affect others
- Designed data flows, not just individual scripts
- Considered future extensibility in every decision

### Business Impact Focus
- Built features that directly reduce manual work hours
- Designed analytics that enable proactive risk management
- Translated business requirements into technical solutions

### Production Discipline
- Never hard-delete data
- Test before deploy (dry-run modes)
- Validate inputs at every boundary
- Document decisions for future maintainers

---

## Role Mapping

| Skill Cluster | Target Roles |
|--------------|-------------|
| Python + FastAPI + API Design | Software Engineer, Backend Developer |
| Data Modelling + SQL | Data Engineer, Analytics Engineer |
| Full-Stack (Backend + UI) | Full-Stack Developer, Product Engineer |
| Automation + Process Improvement | Automation Engineer, Digital Transformation |
| Systems Design + Architecture | Solutions Engineer, Platform Engineer |
| Internal Tools + Business Logic | Internal Tools Engineer, Systems Developer |

All of these roles appear on the [UK Skilled Worker visa eligible occupations list](https://www.gov.uk/government/publications/skilled-worker-visa-eligible-occupations).
