# Architecture & Design Decisions

This document explains the **why** behind every major technical decision in the Business Operations Platform — not just what was built, but the reasoning that drove each choice. This level of architectural thinking is what separates task execution from system ownership.

---

## 1. System Architecture: Three-Layer Separation

### Decision
Separate the system into three distinct layers:
- **Frontend** (Streamlit) — UI and user interaction
- **Backend** (FastAPI) — Business logic and API
- **Database** (SQLAlchemy/SQLite) — Data persistence

### Reasoning
Any layer can be **replaced independently** without rewriting the system:
- Streamlit could be swapped for React → backend stays the same
- SQLite could be swapped for PostgreSQL → API stays the same
- FastAPI could be swapped for Django → frontend stays the same

This is how systems are built in consultancies, banks, and tech firms. The **tools change**, but the **architectural thinking** transfers directly.

### Evidence
```
Frontend (Streamlit) → HTTP Requests → Backend (FastAPI) → ORM → Database (SQLite)
```
No layer directly accesses another layer's internals.

---

## 2. Data Model: Relational with Junction Tables

### Decision
Use a **relational model** with explicit junction tables instead of embedding or duplicating data.

### Schema
```
Organisations ──(1:many)── Contacts
Projects ──(1:many via ProjectDirectory)── Contacts
Projects ──(1:many)── StageAllocations
Projects ──(1:many)── TimeEntries
```

### Why Not Duplicate?
In many tutorial projects, contact details are copied into each project. This creates:
- **Data inconsistency**: One project has an old phone number, another has the new one
- **Update nightmares**: Changing an email requires updating N project records
- **Wasted storage**: Same data stored multiple times

Our approach:
- A contact exists **once** in the system
- Their **role per project** is stored in the `ProjectDirectory` junction table
- Updating a contact's details propagates **everywhere automatically**

This mirrors how enterprise CRM and ERP systems handle stakeholder relationships.

---

## 3. Soft Deletes: Never Lose Data

### Decision
All delete operations set `is_active = False` instead of removing records.

### Reasoning
In a production system managing real construction projects:
- **Audit trails** require historical records
- **Accidental deletions** must be reversible
- **Linked records** (time entries, financial data) become orphaned if parent records are hard-deleted
- **Regulatory compliance** may require data retention

### Implementation
```python
# Every model has:
is_active = Column(Boolean, default=True)

# Every query defaults to:
query.filter(Model.is_active == True)

# Delete endpoint:
project.is_active = False  # NOT db.delete(project)
```

### Trade-off
This means the database grows over time. In a real production system, we would add a scheduled archive process for records older than N years. But for active operations, the safety benefit far outweighs the storage cost.

---

## 4. Idempotent Operations: Prevent Duplicates

### Decision
Write operations check for existing records before creating new ones.

### The Problem
Without idempotency:
- Double-clicking "Add Contact" creates two identical directory entries
- Re-running a data import doubles the dataset
- Network retries create phantom records

### The Solution
```python
# Before creating a directory entry:
existing = db.query(ProjectDirectory).filter(
    ProjectDirectory.project_id == project_id,
    ProjectDirectory.contact_id == contact_id,
    ProjectDirectory.role == role,
    ProjectDirectory.is_active == True,
).first()

if existing:
    return existing  # Return existing, don't create duplicate
```

This is **critical for data integrity** in multi-user environments and is a pattern used in every serious production system.

---

## 5. Risk Detection: 80% Threshold

### Decision
Flag projects as "At Risk" when stage burn rate reaches **80%**, not 100%.

### Reasoning
In construction project management:
- Catching an overrun at **100% is too late** — the budget is already gone
- An **80% early warning** gives project managers 1-2 weeks to:
  - Reallocate resources
  - Negotiate scope changes
  - Escalate to directors

This threshold is based on how real construction cost control works.

### Implementation
```python
RISK_THRESHOLD = 80.0  # percent

if burn_percentage > 100:
    status = "Overrun"
elif burn_percentage >= RISK_THRESHOLD:
    status = "At Risk"
else:
    status = "On Track"
```

### Why Not Configurable?
We initially considered making this a UI slider. However:
- Different users would set different thresholds, making reports inconsistent
- The 80% threshold is an **industry-informed business decision**, not a UI preference
- It's configurable in code (single constant), not in the UI

---

## 6. Backend-First Calculations

### Decision
All business calculations (burn rates, risk flags, portfolio summaries) happen in the **API layer**, not in the frontend.

### Reasoning
- **Consistency**: All consumers (Streamlit, reports, exports) get the same numbers
- **Testability**: Analytics logic has unit tests independent of UI
- **Performance**: Server-side aggregation is faster than sending all raw data to the client
- **Security**: Business logic isn't exposed in client-side code

### Example
```python
# API endpoint computes burn rate:
GET /api/v1/analytics/project/1 → { "overall_burn_percentage": 85.3 }

# Frontend simply displays it — no calculation needed
st.metric("Burn Rate", f"{perf['overall_burn_percentage']}%")
```

---

## 7. Rule-Based Workflow Over AI

### Decision
Email-to-task automation uses **deterministic rules**, not LLM/AI.

### Reasoning
- Business email routing rules are **deterministic** (if project reference exists, route to that bucket)
- LLMs are **probabilistic** — they might route incorrectly
- Rule-based logic has **zero API cost** and zero latency
- It's **auditable** — you can trace exactly why a task was created
- AI can be added **later** as an optional fallback for unmatched emails

### Architecture Decision Record
```
Title: Email-to-Task Processing Engine
Status: Implemented
Context: Need to convert incoming emails into structured tasks
Decision: Use rule-based pattern matching (regex + keywords)
Rationale: Reliability > intelligence for core business workflow
Future: Add LLM fallback for emails that don't match any rule
```

This represents **mature engineering judgement** — knowing when AI is the right tool and when it isn't.

---

## 8. Dev → Production Workflow

### Decision
All new features and database changes are developed and tested in a **dev environment** before being deployed to production.

### Reasoning
- Production data is **real and valuable** — breaking it has real consequences
- Schema changes can be **destructive** — adding/removing columns on live data is risky
- New features need **testing with realistic data** before users see them

### Implementation
- Dev: SQLite local database with seed data
- Prod: Configurable connection string (PostgreSQL in production)
- Feature flags: New features can be toggled without redeployment

---

## Summary

Every decision in this system was made with **production safety**, **data integrity**, and **maintainability** in mind. These are not academic choices — they come from building and operating a live system where mistakes have real consequences.

The tools may change (Streamlit → React, SQLite → PostgreSQL, FastAPI → Django), but the **thinking transfers directly** to any engineering role.
