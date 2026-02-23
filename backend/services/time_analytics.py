"""
Time Tracking Analytics Service.

Reusable calculations for burn rate analysis, risk detection,
and portfolio-level performance metrics.
"""

RISK_THRESHOLD_PERCENT = 80.0


def calculate_burn_rate(allocated: float, used: float) -> float:
    """Calculate percentage of allocated hours consumed."""
    if allocated <= 0:
        return 0.0
    return round((used / allocated) * 100, 1)


def classify_risk(burn_percentage: float) -> str:
    """
    Classify risk: On Track (< 80%), At Risk (80-100%), Overrun (> 100%).
    80% threshold gives managers time to act before budget is exceeded.
    """
    if burn_percentage > 100:
        return "Overrun"
    elif burn_percentage >= RISK_THRESHOLD_PERCENT:
        return "At Risk"
    return "On Track"


def compute_stage_metrics(allocations: dict, actuals: dict) -> list:
    """Compute per-stage metrics combining allocations and actuals."""
    all_stages = sorted(set(list(allocations.keys()) + list(actuals.keys())))
    metrics = []
    for stage in all_stages:
        allocated = allocations.get(stage, 0)
        used = actuals.get(stage, 0)
        burn_pct = calculate_burn_rate(allocated, used)
        risk = classify_risk(burn_pct)
        metrics.append({
            "stage": stage,
            "allocated_hours": allocated,
            "used_hours": used,
            "remaining_hours": round(allocated - used, 1),
            "burn_percentage": burn_pct,
            "risk_status": risk,
            "is_at_risk": risk in ("At Risk", "Overrun"),
            "is_overrun": risk == "Overrun",
        })
    return metrics


def compute_portfolio_risk(project_metrics: list) -> dict:
    """Compute portfolio-wide risk summary."""
    at_risk, overrun, on_track = [], [], []
    for proj in project_metrics:
        burn = proj.get("overall_burn_percentage", 0)
        name = proj.get("project_name", "Unknown")
        if burn > 100:
            overrun.append(name)
        elif burn >= RISK_THRESHOLD_PERCENT:
            at_risk.append(name)
        else:
            on_track.append(name)
    return {
        "total_projects": len(project_metrics),
        "on_track_count": len(on_track),
        "at_risk_count": len(at_risk),
        "overrun_count": len(overrun),
        "at_risk_projects": at_risk,
        "overrun_projects": overrun,
    }
