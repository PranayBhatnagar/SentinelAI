import pytest

from app.agents.specialists import SustainabilityAgent
from app.core.types import InvestigationContext, InvestigationIntent
from app.integrations.base import UnavailableConnector


def test_energy_formula_is_transparent() -> None:
    agent = SustainabilityAgent(UnavailableConnector("cloud"))
    result = agent.normalize({"findings": [{"power_watts": 100, "duration_seconds": 3600, "carbon_intensity_gco2_per_kwh": 400, "retry_count": 2}]}, InvestigationContext(organization_id="a", query="impact", intent=InvestigationIntent.IMPACT))
    assert result.findings[0]["energy_kwh"] == pytest.approx(0.1)
    assert result.findings[0]["retry_waste_gco2"] == pytest.approx(80)
