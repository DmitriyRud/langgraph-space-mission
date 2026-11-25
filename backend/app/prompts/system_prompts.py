from app.i18n import DEFAULT_LANGUAGE, t


def get_system_prompt(agent_name: str, lang: str = DEFAULT_LANGUAGE) -> str:
    return t(f"prompts.{agent_name}", lang)


AGENT_SYSTEM_PROMPTS: dict[str, str] = {
    name: get_system_prompt(name, DEFAULT_LANGUAGE)
    for name in (
        "commander",
        "engineer",
        "scientist",
        "medical_officer",
        "plan_aggregator",
        "safety_officer",
    )
}
