# Case Study: From Manual Processes to Automated Operations

## The Problem

A construction consultancy was managing projects, stakeholders, and time tracking using **spreadsheets and manual Word documents**. This created:

- **Data inconsistency**: Contact details duplicated across project spreadsheets, quickly becoming outdated
- **No visibility**: Project managers couldn't see stage-level time overruns until it was too late
- **Manual reporting**: Generating a project directory or performance report required hours of copy-pasting
- **Document maintenance**: Updating dates across 50+ policy documents took half a day of manual editing

---

## The Solution

A **full-stack internal operations platform** was designed and built to digitise these workflows:

### 1. Centralised Project & Stakeholder Management

**Before**: Each project had its own spreadsheet with contact details copied in. Updating someone's phone number meant finding every spreadsheet they appeared in.

**After**: Contacts exist once in the system. Their involvement in specific projects is managed through a **directory junction table**. Updating a phone number propagates everywhere instantly.

**Technical implementation**:
- RESTful API with idempotent write operations
- Junction table pattern preventing data duplication
- Soft deletes protecting historical data

### 2. Real-Time Performance Analytics

**Before**: Project managers discovered time overruns at the end of a project stage, when it was too late to act.

**After**: Stage-level burn rate monitoring with an **80% early warning threshold** that flags at-risk projects before budgets are exceeded.

**Technical implementation**:
- Server-side analytics computed in the API layer for consistency
- Stage-by-stage breakdown aligned with RIBA Work Stages
- Executive portfolio view for directors showing all projects at a glance

### 3. Automated Document Processing

**Before**: Updating review dates across 50+ Word documents took approximately 3 hours of manual editing, with a high risk of human error and inconsistent formatting.

**After**: A Python automation script processes all documents in **under 30 seconds**, with built-in dry-run testing and automatic backups.

**Technical implementation**:
- Batch processing with backup-first safety
- Dry-run mode for testing before execution
- Handles paragraphs, tables, headers, and footers

### 4. Email-to-Task Workflow Automation

**Before**: Emails requiring action were manually read, interpreted, and converted into tasks — a process dependent on one person remembering to check their inbox.

**After**: A rule-based engine automatically extracts project references, determines priority, and routes tasks to the correct bucket.

**Technical implementation**:
- Deterministic rules (not AI) for reliability
- Pattern matching for project references
- Review bucket for unmatched emails (safety net)

---

## Results

| Metric | Before | After | Impact |
|--------|--------|-------|--------|
| Document date updates (50+ files) | ~3 hours | < 30 seconds | **99.7% time reduction** |
| Directory lookup | 10-15 minutes (find spreadsheet, check) | Instant (search & filter) | **Immediate access** |
| Time overrun detection | End of stage (reactive) | Real-time at 80% (proactive) | **Early risk intervention** |
| Report generation | 30-60 minutes (manual formatting) | One-click export (CSV/PDF) | **95% time reduction** |
| Contact data accuracy | Multiple outdated copies | Single source of truth | **100% consistency** |

---

## Key Engineering Decisions Made

1. **Chose relational modelling over document storage** — because data relationships (org → contact → project) are the core of the domain
2. **Implemented soft deletes instead of hard deletes** — because construction projects have audit requirements
3. **Put calculations in the backend, not the UI** — because multiple consumers need consistent numbers
4. **Used rules instead of AI for email processing** — because reliability matters more than intelligence for core workflows
5. **Set 80% risk threshold, not 100%** — because catching overruns at 100% is too late in construction

---

## Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Backend API | FastAPI (Python) | Async-capable, automatic OpenAPI docs, Pydantic validation |
| Frontend | Streamlit | Rapid internal tool development, native data display |
| Database | SQLAlchemy + SQLite | Portable for dev, swappable to PostgreSQL for prod |
| PDF Reports | ReportLab | Full layout control, A3 landscape support, branding |
| Document Processing | python-docx | Programmatic Word file manipulation |
| Analytics | Pandas + Plotly | Data aggregation and interactive visualisation |
| Testing | pytest + httpx | Fast, isolated API testing with TestClient |

---

## Skills Demonstrated

- **Python backend development** (FastAPI, SQLAlchemy, Pydantic)
- **REST API design** with proper HTTP semantics (GET/POST/PATCH/DELETE)
- **Relational data modelling** (one-to-many, junction tables, foreign keys)
- **Production-safe engineering** (soft deletes, idempotency, dev/prod separation)
- **Document automation** (PDF generation, batch Word processing)
- **Workflow automation** (email-to-task, rule-based routing)
- **Full-stack delivery** (backend + frontend + database + testing)
- **Systems thinking** (architecture decisions, trade-off analysis)
- **Debugging & root-cause analysis** (cross-layer issue resolution)
