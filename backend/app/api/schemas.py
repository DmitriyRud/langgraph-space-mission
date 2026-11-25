from typing import Any, Literal

from pydantic import BaseModel, Field


class CreateMissionRequest(BaseModel):
    scenario_id: str = Field(
        default="engine_failure",
        description="Scenario identifier or 'random' for random selection.",
    )
    mode: Literal["demo", "live"] = Field(default="demo")
    language: Literal["en", "ru"] = Field(default="en")
    max_iterations: int = Field(default=5, ge=1, le=10)


class ResumeMissionRequest(BaseModel):
    decision: Literal["approve", "reject", "request_revision"] = Field(default="approve")
    feedback: str = Field(default="", max_length=1000)
    switch_to_demo: bool = Field(default=False)


class ForkMissionRequest(BaseModel):
    checkpoint_id: str = Field(min_length=1)
    mode: Literal["demo", "live"] | None = None
    state_overrides: dict[str, Any] | None = None
    auto_start: bool = Field(default=True)
