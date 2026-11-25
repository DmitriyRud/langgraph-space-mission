from typing import Literal

from pydantic import BaseModel, Field

SpecialistName = Literal["engineer", "scientist", "medical_officer"]
RiskLevel = Literal["low", "medium", "high", "critical"]


class CommanderOutput(BaseModel):
    situation_summary: str = Field(
        description="Concise assessment of the current spacecraft emergency and priorities."
    )
    priority_focus: str = Field(
        description="Primary stabilization objective for this iteration."
    )
    selected_specialists: list[SpecialistName] = Field(
        min_length=1,
        max_length=3,
        description="Which specialist agents to dispatch in parallel for analysis.",
    )
    directives: dict[str, str] = Field(
        default_factory=dict,
        description="Short task directive for each selected specialist.",
    )
    rationale: str = Field(
        description="Why these specialists were chosen given current telemetry and feedback."
    )


class SpecialistReportOutput(BaseModel):
    agent: SpecialistName = Field(description="Specialist identifier.")
    diagnosis: str = Field(description="Domain-specific assessment of the incident.")
    recommended_actions: list[str] = Field(
        min_length=1,
        max_length=3,
        description="Ordered list of allowed action_ids recommended by this specialist.",
    )
    resource_estimate: str = Field(
        description="Expected energy, fuel, or operational resource impact."
    )
    projected_consequences: str = Field(
        description="Expected effect on spacecraft systems and crew."
    )
    risk_level: RiskLevel = Field(description="Estimated operational risk of these actions.")


class PlanAggregationOutput(BaseModel):
    plan_title: str = Field(description="Short operational title for the action plan.")
    summary: str = Field(description="Clear explanation of how the plan resolves the emergency.")
    action_ids: list[str] = Field(
        min_length=1,
        max_length=3,
        description="Exact allowed action_ids to execute in this iteration.",
    )
    expected_outcomes: str = Field(
        description="Predicted ship telemetry and mission state improvements."
    )
    resource_summary: str = Field(
        description="Summary of resources required to execute the plan."
    )
    risk_level: RiskLevel = Field(description="Overall risk rating of the proposed plan.")


class SafetyAssessmentOutput(BaseModel):
    approved: bool = Field(
        description="True if the plan is safe, feasible with available resources, and free of critical hazards."
    )
    risk_level: RiskLevel = Field(description="Independent safety risk rating.")
    resource_check_passed: bool = Field(
        description="Whether the ship has sufficient resources for all proposed actions."
    )
    findings: list[str] = Field(
        default_factory=list,
        description="Key safety observations, contradictions, or hazard flags.",
    )
    required_revisions: str = Field(
        default="",
        description="Actionable instructions for Commander if the plan is rejected.",
    )
    summary: str = Field(description="Short executive verdict from the Safety Officer.")
