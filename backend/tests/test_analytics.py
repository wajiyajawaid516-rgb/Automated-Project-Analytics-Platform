"""
Tests for analytics and time tracking logic.
"""

import pytest
from backend.services.time_analytics import (
    calculate_burn_rate, classify_risk,
    compute_stage_metrics, compute_portfolio_risk,
)


class TestBurnRate:
    def test_normal_burn_rate(self):
        assert calculate_burn_rate(100, 50) == 50.0

    def test_zero_allocation(self):
        assert calculate_burn_rate(0, 50) == 0.0

    def test_full_utilisation(self):
        assert calculate_burn_rate(100, 100) == 100.0

    def test_overrun(self):
        assert calculate_burn_rate(100, 120) == 120.0


class TestRiskClassification:
    def test_on_track(self):
        assert classify_risk(50.0) == "On Track"

    def test_at_risk_boundary(self):
        assert classify_risk(80.0) == "At Risk"

    def test_at_risk(self):
        assert classify_risk(90.0) == "At Risk"

    def test_overrun_boundary(self):
        assert classify_risk(100.1) == "Overrun"

    def test_overrun(self):
        assert classify_risk(150.0) == "Overrun"


class TestStageMetrics:
    def test_compute_metrics(self):
        allocations = {"Stage 1": 100, "Stage 2": 200}
        actuals = {"Stage 1": 50, "Stage 2": 180}
        metrics = compute_stage_metrics(allocations, actuals)

        assert len(metrics) == 2
        assert metrics[0]["burn_percentage"] == 50.0
        assert metrics[0]["risk_status"] == "On Track"
        assert metrics[1]["burn_percentage"] == 90.0
        assert metrics[1]["risk_status"] == "At Risk"

    def test_missing_allocation(self):
        """Time logged against a stage with no allocation."""
        allocations = {}
        actuals = {"Stage 1": 50}
        metrics = compute_stage_metrics(allocations, actuals)
        assert metrics[0]["burn_percentage"] == 0.0


class TestPortfolioRisk:
    def test_portfolio_summary(self):
        projects = [
            {"project_name": "A", "overall_burn_percentage": 50},
            {"project_name": "B", "overall_burn_percentage": 85},
            {"project_name": "C", "overall_burn_percentage": 110},
        ]
        result = compute_portfolio_risk(projects)
        assert result["on_track_count"] == 1
        assert result["at_risk_count"] == 1
        assert result["overrun_count"] == 1
        assert "B" in result["at_risk_projects"]
        assert "C" in result["overrun_projects"]
