"""
Database models and setup for the Business Operations Platform.

Uses SQLAlchemy ORM with SQLite for development.
Designed to be swappable to PostgreSQL for production environments.

Architecture Decision:
    - Relational model with clear one-to-many relationships
    - Soft deletes (is_active flag) to protect data integrity
    - Separation of Organisations, Contacts, Projects, and Time Entries
    - Junction table (ProjectDirectory) to avoid data duplication
"""

import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean,
    DateTime, ForeignKey, Text, Enum as SQLEnum
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import enum


# ---------------------------------------------------------------------------
# Database Configuration
# ---------------------------------------------------------------------------
DATABASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..")
DATABASE_URL = f"sqlite:///{os.path.join(DATABASE_DIR, 'business_ops.db')}"

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency injection for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Enums — RIBA Work Stages (UK Construction Industry Standard)
# ---------------------------------------------------------------------------
class RIBAStage(str, enum.Enum):
    """
    RIBA Plan of Work stages — the UK standard for organising the process
    of briefing, designing, constructing, and operating building projects.
    """
    STAGE_0 = "0 - Strategic Definition"
    STAGE_1 = "1 - Preparation & Briefing"
    STAGE_2 = "2 - Concept Design"
    STAGE_3 = "3 - Spatial Coordination"
    STAGE_4 = "4 - Technical Design"
    STAGE_5 = "5 - Manufacturing & Construction"
    STAGE_6 = "6 - Handover"
    STAGE_7 = "7 - Use"


class ProjectStatus(str, enum.Enum):
    ACTIVE = "Active"
    ON_HOLD = "On Hold"
    COMPLETED = "Completed"
    ARCHIVED = "Archived"


class ContactRole(str, enum.Enum):
    """Roles a contact can hold within a project directory."""
    CLIENT = "Client"
    ARCHITECT = "Architect"
    ENGINEER = "Engineer"
    QUANTITY_SURVEYOR = "Quantity Surveyor"
    PROJECT_MANAGER = "Project Manager"
    CONTRACTOR = "Contractor"
    CONSULTANT = "Consultant"
    SUB_CONTRACTOR = "Sub-Contractor"
    SUPPLIER = "Supplier"
    OTHER = "Other"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class Organisation(Base):
    """
    Represents a company or firm.
    A single organisation can have many contacts and be involved in many projects.
    """
    __tablename__ = "organisations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    address_line_1 = Column(String(255))
    address_line_2 = Column(String(255))
    city = Column(String(100))
    postcode = Column(String(20))
    country = Column(String(100), default="United Kingdom")
    phone = Column(String(50))
    email = Column(String(255))
    website = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    contacts = relationship("Contact", back_populates="organisation", lazy="selectin")

    def __repr__(self):
        return f"<Organisation(id={self.id}, name='{self.name}')>"


class Contact(Base):
    """
    Represents an individual person linked to an organisation.
    Contacts exist independently of projects — their project roles
    are managed through the ProjectDirectory junction table.

    Design Decision:
        Contacts are NOT duplicated per project. A single contact record
        is linked to multiple projects via ProjectDirectory entries.
        This ensures global updates (e.g. phone number change) propagate
        everywhere automatically.
    """
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    job_title = Column(String(255))
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organisation = relationship("Organisation", back_populates="contacts")
    directory_entries = relationship("ProjectDirectory", back_populates="contact", lazy="selectin")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<Contact(id={self.id}, name='{self.full_name}')>"


class Project(Base):
    """
    Represents a construction or engineering project.
    Each project has a unique job number, a current RIBA stage,
    and allocated hours per stage for time tracking.

    Design Decision:
        The project holds the 'current_stage' as a denormalised field
        for quick filtering. The full stage history is tracked through
        TimeEntry records, allowing retrospective analysis.
    """
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    job_number = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    client_organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=True)
    current_stage = Column(SQLEnum(RIBAStage), default=RIBAStage.STAGE_0)
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.ACTIVE)
    start_date = Column(DateTime)
    target_completion = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client_organisation = relationship("Organisation", foreign_keys=[client_organisation_id])
    directory_entries = relationship("ProjectDirectory", back_populates="project", lazy="selectin")
    time_entries = relationship("TimeEntry", back_populates="project", lazy="selectin")
    stage_allocations = relationship("StageAllocation", back_populates="project", lazy="selectin")

    def __repr__(self):
        return f"<Project(id={self.id}, job='{self.job_number}', name='{self.name}')>"


class ProjectDirectory(Base):
    """
    Junction table: links a Contact to a Project with a specific role.

    Design Decision:
        This is the key architectural choice — instead of duplicating contact
        data per project, we create a lightweight link. This means:
        - Updating a contact's phone number updates it everywhere
        - A contact can have different roles in different projects
        - We can query "all projects this person is involved in" efficiently

    This mirrors how enterprise CRM systems handle stakeholder relationships.
    """
    __tablename__ = "project_directory"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False)
    role = Column(SQLEnum(ContactRole), default=ContactRole.OTHER)
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    added_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="directory_entries")
    contact = relationship("Contact", back_populates="directory_entries")

    def __repr__(self):
        return f"<ProjectDirectory(project={self.project_id}, contact={self.contact_id}, role='{self.role}')>"


class StageAllocation(Base):
    """
    Defines how many hours are allocated to each RIBA stage for a project.
    Used as the baseline for burn rate and risk calculations.

    Design Decision:
        Separated from the Project model to allow per-stage budgeting.
        This enables stage-level performance tracking rather than just
        project-level totals, which is how real construction firms
        monitor cost and time.
    """
    __tablename__ = "stage_allocations"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    stage = Column(SQLEnum(RIBAStage), nullable=False)
    allocated_hours = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)

    # Relationships
    project = relationship("Project", back_populates="stage_allocations")

    def __repr__(self):
        return f"<StageAllocation(project={self.project_id}, stage='{self.stage}', hours={self.allocated_hours})>"


class TimeEntry(Base):
    """
    Records actual time spent on a project at a specific RIBA stage.
    Comparable to time tracking entries from tools like Clockify.

    Design Decision:
        Each entry records the stage at the time of logging, not the
        project's current stage. This allows accurate historical analysis
        even when projects move through stages.
    """
    __tablename__ = "time_entries"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    stage = Column(SQLEnum(RIBAStage), nullable=False)
    hours = Column(Float, nullable=False)
    description = Column(Text)
    logged_by = Column(String(255))
    logged_date = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationships
    project = relationship("Project", back_populates="time_entries")

    def __repr__(self):
        return f"<TimeEntry(project={self.project_id}, stage='{self.stage}', hours={self.hours})>"


# ---------------------------------------------------------------------------
# Database Initialisation
# ---------------------------------------------------------------------------
def init_db():
    """Create all tables. Safe to call multiple times."""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully.")


def seed_sample_data():
    """
    Populate the database with realistic sample data for demonstration.
    All data is fictional — no real company or personal information.
    """
    db = SessionLocal()

    try:
        # Check if data already exists
        if db.query(Organisation).count() > 0:
            print("ℹ️  Sample data already exists. Skipping seed.")
            return

        # --- Organisations (fictional) ---
        orgs = [
            Organisation(
                name="Thornfield Associates",
                address_line_1="14 Cathedral Road",
                city="Cardiff",
                postcode="CF11 9LJ",
                phone="+44 29 2000 1234",
                email="info@thornfield.example.com",
                website="https://thornfield.example.com",
            ),
            Organisation(
                name="Westbury Engineering Ltd",
                address_line_1="7 King Edward VII Avenue",
                city="Cardiff",
                postcode="CF10 3NB",
                phone="+44 29 2000 5678",
                email="hello@westbury-eng.example.com",
            ),
            Organisation(
                name="Bridgeway Construction",
                address_line_1="Unit 3, Atlantic Wharf",
                city="Cardiff",
                postcode="CF10 4AW",
                phone="+44 29 2000 9012",
                email="projects@bridgeway.example.com",
            ),
            Organisation(
                name="Severn Architects",
                address_line_1="22 Churchill Way",
                city="Cardiff",
                postcode="CF10 2DY",
                email="studio@severnarch.example.com",
            ),
            Organisation(
                name="Millennium Surveyors",
                address_line_1="5 Bute Crescent",
                city="Cardiff",
                postcode="CF10 5AN",
                email="qs@millennium-qs.example.com",
            ),
        ]
        db.add_all(orgs)
        db.flush()

        # --- Contacts (fictional) ---
        contacts = [
            Contact(first_name="James", last_name="Morton", email="j.morton@thornfield.example.com", job_title="Managing Director", organisation_id=orgs[0].id),
            Contact(first_name="Sarah", last_name="Chen", email="s.chen@thornfield.example.com", job_title="Senior Project Manager", organisation_id=orgs[0].id),
            Contact(first_name="David", last_name="Patel", email="d.patel@westbury-eng.example.com", job_title="Lead Structural Engineer", organisation_id=orgs[1].id),
            Contact(first_name="Emma", last_name="Williams", email="e.williams@bridgeway.example.com", job_title="Contracts Manager", organisation_id=orgs[2].id),
            Contact(first_name="Michael", last_name="O'Brien", email="m.obrien@severnarch.example.com", job_title="Principal Architect", organisation_id=orgs[3].id),
            Contact(first_name="Lisa", last_name="Roberts", email="l.roberts@millennium-qs.example.com", job_title="Quantity Surveyor", organisation_id=orgs[4].id),
            Contact(first_name="Tom", last_name="Hughes", email="t.hughes@bridgeway.example.com", job_title="Site Manager", organisation_id=orgs[2].id),
            Contact(first_name="Rachel", last_name="Davies", email="r.davies@westbury-eng.example.com", job_title="MEP Engineer", organisation_id=orgs[1].id),
        ]
        db.add_all(contacts)
        db.flush()

        # --- Projects (fictional) ---
        projects = [
            Project(
                job_number="PRJ-2024-001",
                name="Cardiff Waterfront Mixed-Use Development",
                description="A mixed-use development comprising 120 residential units, ground-floor retail, and public realm improvements along the waterfront.",
                client_organisation_id=orgs[0].id,
                current_stage=RIBAStage.STAGE_3,
                status=ProjectStatus.ACTIVE,
                start_date=datetime(2024, 3, 15),
                target_completion=datetime(2026, 9, 30),
            ),
            Project(
                job_number="PRJ-2024-002",
                name="Penarth School Extension",
                description="Two-storey extension to an existing primary school including new classrooms, a sports hall, and accessible facilities.",
                client_organisation_id=orgs[1].id,
                current_stage=RIBAStage.STAGE_4,
                status=ProjectStatus.ACTIVE,
                start_date=datetime(2024, 1, 10),
                target_completion=datetime(2025, 8, 15),
            ),
            Project(
                job_number="PRJ-2024-003",
                name="Newport Office Refurbishment",
                description="Full interior refurbishment of a 3-storey Grade B office building including MEP upgrades and sustainability improvements.",
                client_organisation_id=orgs[2].id,
                current_stage=RIBAStage.STAGE_5,
                status=ProjectStatus.ACTIVE,
                start_date=datetime(2023, 11, 1),
                target_completion=datetime(2025, 4, 30),
            ),
            Project(
                job_number="PRJ-2023-010",
                name="Swansea Marina Pavilion",
                description="New-build coastal pavilion with café, public toilets, and visitor information centre.",
                client_organisation_id=orgs[3].id,
                current_stage=RIBAStage.STAGE_6,
                status=ProjectStatus.ACTIVE,
                start_date=datetime(2023, 6, 1),
                target_completion=datetime(2025, 2, 28),
            ),
            Project(
                job_number="PRJ-2023-008",
                name="Bristol Residential Conversion",
                description="Conversion of a former warehouse into 24 residential apartments with communal amenity space.",
                client_organisation_id=orgs[0].id,
                current_stage=RIBAStage.STAGE_7,
                status=ProjectStatus.COMPLETED,
                start_date=datetime(2022, 9, 1),
                target_completion=datetime(2024, 12, 31),
            ),
        ]
        db.add_all(projects)
        db.flush()

        # --- Project Directory Entries ---
        directory_entries = [
            # Cardiff Waterfront
            ProjectDirectory(project_id=projects[0].id, contact_id=contacts[0].id, role=ContactRole.CLIENT, notes="Primary client contact"),
            ProjectDirectory(project_id=projects[0].id, contact_id=contacts[1].id, role=ContactRole.PROJECT_MANAGER),
            ProjectDirectory(project_id=projects[0].id, contact_id=contacts[2].id, role=ContactRole.ENGINEER, notes="Structural package lead"),
            ProjectDirectory(project_id=projects[0].id, contact_id=contacts[4].id, role=ContactRole.ARCHITECT),
            ProjectDirectory(project_id=projects[0].id, contact_id=contacts[5].id, role=ContactRole.QUANTITY_SURVEYOR),
            # Penarth School
            ProjectDirectory(project_id=projects[1].id, contact_id=contacts[2].id, role=ContactRole.ENGINEER),
            ProjectDirectory(project_id=projects[1].id, contact_id=contacts[7].id, role=ContactRole.ENGINEER, notes="MEP design"),
            ProjectDirectory(project_id=projects[1].id, contact_id=contacts[4].id, role=ContactRole.ARCHITECT),
            # Newport Office
            ProjectDirectory(project_id=projects[2].id, contact_id=contacts[3].id, role=ContactRole.CONTRACTOR),
            ProjectDirectory(project_id=projects[2].id, contact_id=contacts[6].id, role=ContactRole.CONTRACTOR, notes="On-site supervisor"),
            ProjectDirectory(project_id=projects[2].id, contact_id=contacts[7].id, role=ContactRole.ENGINEER),
            # Swansea Marina
            ProjectDirectory(project_id=projects[3].id, contact_id=contacts[4].id, role=ContactRole.ARCHITECT, notes="Lead designer"),
            ProjectDirectory(project_id=projects[3].id, contact_id=contacts[5].id, role=ContactRole.QUANTITY_SURVEYOR),
        ]
        db.add_all(directory_entries)
        db.flush()

        # --- Stage Allocations (hours budgeted per RIBA stage) ---
        allocations_data = [
            # Cardiff Waterfront — large project, more hours
            (projects[0].id, RIBAStage.STAGE_0, 40),
            (projects[0].id, RIBAStage.STAGE_1, 80),
            (projects[0].id, RIBAStage.STAGE_2, 200),
            (projects[0].id, RIBAStage.STAGE_3, 300),
            (projects[0].id, RIBAStage.STAGE_4, 400),
            (projects[0].id, RIBAStage.STAGE_5, 100),
            # Penarth School
            (projects[1].id, RIBAStage.STAGE_0, 20),
            (projects[1].id, RIBAStage.STAGE_1, 40),
            (projects[1].id, RIBAStage.STAGE_2, 100),
            (projects[1].id, RIBAStage.STAGE_3, 150),
            (projects[1].id, RIBAStage.STAGE_4, 200),
            # Newport Office
            (projects[2].id, RIBAStage.STAGE_0, 15),
            (projects[2].id, RIBAStage.STAGE_1, 30),
            (projects[2].id, RIBAStage.STAGE_2, 80),
            (projects[2].id, RIBAStage.STAGE_3, 120),
            (projects[2].id, RIBAStage.STAGE_4, 180),
            (projects[2].id, RIBAStage.STAGE_5, 60),
            # Swansea Marina
            (projects[3].id, RIBAStage.STAGE_0, 10),
            (projects[3].id, RIBAStage.STAGE_1, 25),
            (projects[3].id, RIBAStage.STAGE_2, 60),
            (projects[3].id, RIBAStage.STAGE_3, 100),
            (projects[3].id, RIBAStage.STAGE_4, 140),
            (projects[3].id, RIBAStage.STAGE_5, 50),
            (projects[3].id, RIBAStage.STAGE_6, 30),
        ]
        for proj_id, stage, hours in allocations_data:
            db.add(StageAllocation(project_id=proj_id, stage=stage, allocated_hours=hours))
        db.flush()

        # --- Time Entries (simulating real usage patterns) ---
        time_data = [
            # Cardiff Waterfront — Stage 3 is at risk (high burn rate)
            (projects[0].id, RIBAStage.STAGE_0, 38, "Strategic briefing and site analysis", "Sarah Chen"),
            (projects[0].id, RIBAStage.STAGE_1, 75, "Client requirements and feasibility", "Sarah Chen"),
            (projects[0].id, RIBAStage.STAGE_2, 190, "Concept design development", "Michael O'Brien"),
            (projects[0].id, RIBAStage.STAGE_3, 270, "Spatial coordination — ongoing", "David Patel"),  # 90% burn = AT RISK

            # Penarth School — Stage 4 is over budget
            (projects[1].id, RIBAStage.STAGE_0, 18, "Initial briefing", "Sarah Chen"),
            (projects[1].id, RIBAStage.STAGE_1, 42, "Design brief finalisation", "Sarah Chen"),
            (projects[1].id, RIBAStage.STAGE_2, 95, "Concept sketches and options", "Michael O'Brien"),
            (projects[1].id, RIBAStage.STAGE_3, 140, "Coordination drawings", "David Patel"),
            (projects[1].id, RIBAStage.STAGE_4, 215, "Technical design — OVERRUN", "Rachel Davies"),  # 107.5% = OVERRUN

            # Newport Office — healthy
            (projects[2].id, RIBAStage.STAGE_0, 12, "Initial survey and assessment", "Tom Hughes"),
            (projects[2].id, RIBAStage.STAGE_1, 25, "Scope definition", "Emma Williams"),
            (projects[2].id, RIBAStage.STAGE_2, 60, "Interior layout options", "Michael O'Brien"),
            (projects[2].id, RIBAStage.STAGE_3, 90, "MEP coordination", "Rachel Davies"),
            (projects[2].id, RIBAStage.STAGE_4, 150, "Technical specifications", "Rachel Davies"),
            (projects[2].id, RIBAStage.STAGE_5, 35, "Construction phase — ongoing", "Tom Hughes"),

            # Swansea Marina — Stage 6 at risk
            (projects[3].id, RIBAStage.STAGE_0, 9, "Site appraisal", "Michael O'Brien"),
            (projects[3].id, RIBAStage.STAGE_1, 22, "Planning brief", "Michael O'Brien"),
            (projects[3].id, RIBAStage.STAGE_2, 55, "Design concept", "Michael O'Brien"),
            (projects[3].id, RIBAStage.STAGE_3, 85, "Detail design", "David Patel"),
            (projects[3].id, RIBAStage.STAGE_4, 130, "Technical package", "David Patel"),
            (projects[3].id, RIBAStage.STAGE_5, 48, "Build phase", "Tom Hughes"),
            (projects[3].id, RIBAStage.STAGE_6, 26, "Handover snagging — ongoing", "Tom Hughes"),  # 87% = AT RISK
        ]
        for proj_id, stage, hours, desc, person in time_data:
            db.add(TimeEntry(
                project_id=proj_id, stage=stage, hours=hours,
                description=desc, logged_by=person
            ))

        db.commit()
        print("✅ Sample data seeded successfully.")
        print(f"   → {len(orgs)} organisations")
        print(f"   → {len(contacts)} contacts")
        print(f"   → {len(projects)} projects")
        print(f"   → {len(directory_entries)} directory entries")
        print(f"   → {len(allocations_data)} stage allocations")
        print(f"   → {len(time_data)} time entries")

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding data: {e}")
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Run directly to initialise and seed
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("🔧 Initialising Business Operations Platform database...")
    init_db()
    seed_sample_data()
