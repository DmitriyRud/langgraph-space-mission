from typing import Annotated, Any, TypedDict

from app.state.reducers import append_list, merge_specialist_reports


class ShipState(TypedDict):
    energy: int
    oxygen: int
    hull_integrity: int
    engine_condition: int
    communication: int
    navigation: int
    crew_health: int
    crew_morale: int
    reserve_fuel: int
    mission_status: str


def create_baseline_ship_state() -> ShipState:
    """Initial healthy baseline for spacecraft AURORA-7."""
    return ShipState(
        energy=100,
        oxygen=100,
        hull_integrity=100,
        engine_condition=100,
        communication=100,
        navigation=100,
        crew_health=100,
        crew_morale=100,
        reserve_fuel=100,
        mission_status="Operational",
    )


class MissionState(TypedDict):
    mission_id: str
    scenario_id: str
    mode: str
    language: str
    mission_status: str
    incident: dict[str, Any]
    ship_state: ShipState
    initial_ship_state: ShipState
    selected_specialists: list[str]
    specialist_reports: Annotated[list[dict[str, Any]], merge_specialist_reports]
    current_plan: dict[str, Any] | None
    previous_plans: Annotated[list[dict[str, Any]], append_list]
    executed_actions: Annotated[list[dict[str, Any]], append_list]
    safety_assessment: dict[str, Any] | None
    risk_level: str
    iteration: int
    max_iterations: int
    user_feedback: str | None
    approval_status: str
    mission_result: dict[str, Any] | None
    event_history: Annotated[list[dict[str, Any]], append_list]
    errors: Annotated[list[dict[str, Any]], append_list]
    plan_revision_count: int
