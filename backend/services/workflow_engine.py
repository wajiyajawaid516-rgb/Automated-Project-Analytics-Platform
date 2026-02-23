"""
Workflow Engine — Email-to-Task Processing.

Demonstrates rule-based automation that converts unstructured
input (emails) into structured work items (tasks).

Architecture Decision:
    Rule-based logic is used instead of AI/LLM because:
    - Business rules are deterministic (not probabilistic)
    - The system must be reliable for daily operations
    - AI can be added LATER as an optional fallback for edge cases
    - This approach has zero API costs and zero latency
"""

import re
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class TaskItem:
    """A structured task extracted from an email."""
    title: str
    project_reference: Optional[str] = None
    priority: str = "Normal"
    assigned_bucket: str = "Inbox"
    source_email: str = ""
    extracted_date: Optional[str] = None
    notes: str = ""


@dataclass
class ProcessingResult:
    """Result of processing an email through the workflow engine."""
    success: bool
    tasks_created: List[TaskItem] = field(default_factory=list)
    review_required: bool = False
    reason: str = ""


class EmailTaskConverter:
    """
    Converts incoming emails into structured tasks using rule-based logic.

    Design Decisions:
    1. Rules are explicit and auditable (no black-box AI)
    2. Emails that don't match any rule go to a "Review" bucket
    3. The system is designed to be extended with new rules easily
    4. AI/LLM can be added as a fallback for unmatched emails later
    """

    # Project reference patterns (e.g., PRJ-2024-001)
    PROJECT_PATTERN = re.compile(r'PRJ-\d{4}-\d{3}', re.IGNORECASE)

    # Priority keywords
    HIGH_PRIORITY_KEYWORDS = ['urgent', 'asap', 'critical', 'immediately', 'deadline']
    LOW_PRIORITY_KEYWORDS = ['fyi', 'for your information', 'no rush', 'when you can']

    # Task-indicating keywords
    TASK_KEYWORDS = ['please', 'can you', 'could you', 'need to', 'action required',
                     'follow up', 'review', 'approve', 'submit', 'update', 'check']

    def __init__(self, routing_rules: Optional[Dict] = None):
        """
        Args:
            routing_rules: Optional mapping of project references to
                          Planner buckets. If None, uses default routing.
        """
        self.routing_rules = routing_rules or {}

    def process_email(self, subject: str, body: str, sender: str) -> ProcessingResult:
        """
        Process a single email and extract tasks.

        Flow:
        1. Extract project reference (if any)
        2. Determine priority from keywords
        3. Check if email contains actionable content
        4. Route to appropriate bucket
        5. If unclear, flag for manual review
        """
        # Step 1: Extract project reference
        project_ref = self._extract_project_reference(subject + " " + body)

        # Step 2: Determine priority
        priority = self._determine_priority(subject + " " + body)

        # Step 3: Check for actionable content
        is_actionable = self._is_actionable(subject + " " + body)

        if not is_actionable:
            return ProcessingResult(
                success=True,
                review_required=False,
                reason="Email does not appear to contain actionable tasks"
            )

        # Step 4: Create task
        task = TaskItem(
            title=self._clean_subject(subject),
            project_reference=project_ref,
            priority=priority,
            assigned_bucket=self._route_to_bucket(project_ref),
            source_email=sender,
            extracted_date=datetime.now().strftime("%Y-%m-%d"),
            notes=self._extract_key_sentences(body),
        )

        # Step 5: Flag for review if no project reference found
        review_needed = project_ref is None

        return ProcessingResult(
            success=True,
            tasks_created=[task],
            review_required=review_needed,
            reason="Task created" + (" (no project reference found — review recommended)" if review_needed else ""),
        )

    def process_batch(self, emails: List[Dict]) -> List[ProcessingResult]:
        """Process multiple emails. Returns results in same order."""
        return [
            self.process_email(
                e.get("subject", ""),
                e.get("body", ""),
                e.get("sender", ""),
            )
            for e in emails
        ]

    def _extract_project_reference(self, text: str) -> Optional[str]:
        """Extract PRJ-XXXX-XXX pattern from text."""
        match = self.PROJECT_PATTERN.search(text)
        return match.group(0).upper() if match else None

    def _determine_priority(self, text: str) -> str:
        """Determine priority based on keyword presence."""
        text_lower = text.lower()
        if any(kw in text_lower for kw in self.HIGH_PRIORITY_KEYWORDS):
            return "High"
        if any(kw in text_lower for kw in self.LOW_PRIORITY_KEYWORDS):
            return "Low"
        return "Normal"

    def _is_actionable(self, text: str) -> bool:
        """Check if text contains task-indicating keywords."""
        text_lower = text.lower()
        return any(kw in text_lower for kw in self.TASK_KEYWORDS)

    def _clean_subject(self, subject: str) -> str:
        """Remove Re:/Fwd: prefixes and clean up subject line."""
        cleaned = re.sub(r'^(RE:|FWD?:|FW:)\s*', '', subject, flags=re.IGNORECASE).strip()
        return cleaned or "Untitled Task"

    def _route_to_bucket(self, project_ref: Optional[str]) -> str:
        """Route task to the correct bucket based on project reference."""
        if project_ref and project_ref in self.routing_rules:
            return self.routing_rules[project_ref]
        return "Review" if project_ref is None else "General"

    def _extract_key_sentences(self, body: str, max_sentences: int = 3) -> str:
        """Extract the most relevant sentences from email body."""
        sentences = re.split(r'[.!?]+', body)
        relevant = [s.strip() for s in sentences if self._is_actionable(s)]
        return ". ".join(relevant[:max_sentences]) if relevant else ""


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    converter = EmailTaskConverter(
        routing_rules={
            "PRJ-2024-001": "Cardiff Waterfront",
            "PRJ-2024-002": "Penarth School",
            "PRJ-2024-003": "Newport Office",
        }
    )

    result = converter.process_email(
        subject="RE: PRJ-2024-001 — Please review the latest drawings",
        body="Hi team, can you please review the updated structural drawings for the Cardiff Waterfront project? We need approval by Friday.",
        sender="d.patel@example.com",
    )

    print(f"Success: {result.success}")
    print(f"Review needed: {result.review_required}")
    for task in result.tasks_created:
        print(f"Task: {task.title}")
        print(f"  Project: {task.project_reference}")
        print(f"  Priority: {task.priority}")
        print(f"  Bucket: {task.assigned_bucket}")
