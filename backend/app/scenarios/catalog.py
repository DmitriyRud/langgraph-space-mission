import random
from dataclasses import dataclass, field
from typing import Any

from app.i18n import DEFAULT_LANGUAGE, get_localized, t
from app.state.mission_state import ShipState, create_baseline_ship_state


@dataclass(frozen=True)
class ActionSpec:
    id: str
    label: str
    description: str
    category: str
    specialist_owner: str
    risk_level: str
    resource_requirements: dict[str, int]
    telemetry_effects: dict[str, int]
    resolves_flags: tuple[str, ...] = ()

    def localized_label(self, scenario_id: str, lang: str = DEFAULT_LANGUAGE) -> str:
        val = t(f"scenarios.{scenario_id}.actions.{self.id}.label", lang)
        return self.label if val.startswith("scenarios.") else val

    def localized_description(self, scenario_id: str, lang: str = DEFAULT_LANGUAGE) -> str:
        val = t(f"scenarios.{scenario_id}.actions.{self.id}.description", lang)
        return self.description if val.startswith("scenarios.") else val

    def to_dict(self, scenario_id: str | None = None, lang: str = DEFAULT_LANGUAGE) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.localized_label(scenario_id, lang) if scenario_id else self.label,
            "description": self.localized_description(scenario_id, lang) if scenario_id else self.description,
            "category": self.category,
            "specialist_owner": self.specialist_owner,
            "risk_level": self.risk_level,
            "resource_requirements": dict(self.resource_requirements),
            "telemetry_effects": dict(self.telemetry_effects),
            "resolves_flags": list(self.resolves_flags),
        }


@dataclass(frozen=True)
class ScenarioDefinition:
    id: str
    title: str
    subtitle: str
    severity: str
    description: str
    objectives: tuple[str, ...]
    initial_ship_state: ShipState
    allowed_actions: dict[str, ActionSpec]
    success_thresholds: dict[str, int]
    required_flags: tuple[str, ...]
    failure_thresholds: dict[str, int]
    passive_decay: dict[str, int] = field(default_factory=dict)
    recommended_specialists: tuple[str, ...] = ("engineer", "scientist", "medical_officer")

    def localized_title(self, lang: str = DEFAULT_LANGUAGE) -> str:
        return t(f"scenarios.{self.id}.title", lang)

    def localized_subtitle(self, lang: str = DEFAULT_LANGUAGE) -> str:
        return t(f"scenarios.{self.id}.subtitle", lang)

    def localized_description(self, lang: str = DEFAULT_LANGUAGE) -> str:
        return t(f"scenarios.{self.id}.description", lang)

    def localized_objectives(self, lang: str = DEFAULT_LANGUAGE) -> list[str]:
        val = get_localized(f"scenarios.{self.id}.objectives", lang)
        return list(val) if isinstance(val, list) else list(self.objectives)

    def to_summary_dict(self, lang: str = DEFAULT_LANGUAGE) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.localized_title(lang),
            "subtitle": self.localized_subtitle(lang),
            "severity": self.severity,
            "description": self.localized_description(lang),
            "objectives": self.localized_objectives(lang),
            "initial_ship_state": dict(self.initial_ship_state),
            "allowed_actions": [action.to_dict(self.id, lang) for action in self.allowed_actions.values()],
            "success_thresholds": dict(self.success_thresholds),
            "failure_thresholds": dict(self.failure_thresholds),
            "recommended_specialists": list(self.recommended_specialists),
        }


def _ship_with(**overrides: Any) -> ShipState:
    base = create_baseline_ship_state()
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


SCENARIOS: dict[str, ScenarioDefinition] = {
    "engine_failure": ScenarioDefinition(
        id="engine_failure",
        title="Отказ двигателя",
        subtitle="Столкновение с космическим мусором в кормовом отсеке",
        severity="high",
        description=(
            "Высокоскоростной космический мусор повредил кормовой двигательный отсек AURORA-7. "
            "Работоспособность основного двигателя упала до 35%, шина питания реактора нестабильна, "
            "а микротрещины корпуса нагружают кормовые переборки."
        ),
        objectives=(
            "Восстановить состояние двигателя минимум до 70%",
            "Стабилизировать уровень энергии не ниже 60%",
            "Удержать здоровье экипажа >= 75% и целостность корпуса >= 65%",
        ),
        initial_ship_state=_ship_with(
            energy=58,
            oxygen=92,
            hull_integrity=74,
            engine_condition=35,
            communication=88,
            navigation=72,
            crew_health=90,
            crew_morale=78,
            reserve_fuel=82,
            mission_status="Alert",
        ),
        allowed_actions={
            "eva_thruster_repair": ActionSpec(
                id="eva_thruster_repair",
                label="Ремонт основного двигателя в открытом космосе (ВКД)",
                description="Отправить ремонтную группу с роботами для замены повреждённых магнитных катушек сопла.",
                category="engineering",
                specialist_owner="engineer",
                risk_level="medium",
                resource_requirements={"energy": 12, "reserve_fuel": 5},
                telemetry_effects={
                    "engine_condition": 40,
                    "energy": -8,
                    "reserve_fuel": -5,
                    "hull_integrity": 6,
                    "crew_health": -4,
                    "crew_morale": 8,
                },
                resolves_flags=("propulsion_restored",),
            ),
            "engage_reserve_thruster": ActionSpec(
                id="engage_reserve_thruster",
                label="Запуск резервного ионного двигателя",
                description="Перевести тягу на вспомогательный ионный двигатель за счёт резервного топлива.",
                category="engineering",
                specialist_owner="engineer",
                risk_level="low",
                resource_requirements={"reserve_fuel": 18, "energy": 8},
                telemetry_effects={
                    "engine_condition": 36,
                    "reserve_fuel": -18,
                    "navigation": 12,
                    "energy": -5,
                    "crew_morale": 5,
                },
                resolves_flags=("propulsion_restored",),
            ),
            "rebalance_reactor_bus": ActionSpec(
                id="rebalance_reactor_bus",
                label="Балансировка силовой шины реактора",
                description="Изолировать короткое замыкание в кормовых магистралях и переподключить конденсаторы.",
                category="engineering",
                specialist_owner="engineer",
                risk_level="low",
                resource_requirements={"energy": 5},
                telemetry_effects={
                    "energy": 22,
                    "communication": 6,
                    "navigation": 8,
                },
                resolves_flags=("power_stabilized",),
            ),
            "medical_eva_prep": ActionSpec(
                id="medical_eva_prep",
                label="Биозащита и медобеспечение экипажа для ВКД",
                description="Провести радиационную профилактику и усилить мониторинг жизненных показателей экипажа.",
                category="medical",
                specialist_owner="medical_officer",
                risk_level="low",
                resource_requirements={"energy": 4},
                telemetry_effects={
                    "crew_health": 8,
                    "crew_morale": 10,
                    "energy": -3,
                },
            ),
            "overdrive_damaged_core": ActionSpec(
                id="overdrive_damaged_core",
                label="Аварийный форсаж повреждённого ядра (Опасно)",
                description="Вывести повреждённый двигатель на 120% мощности без замены катушек.",
                category="engineering",
                specialist_owner="engineer",
                risk_level="critical",
                resource_requirements={"reserve_fuel": 25},
                telemetry_effects={
                    "engine_condition": 25,
                    "hull_integrity": -28,
                    "energy": -22,
                    "crew_health": -15,
                    "reserve_fuel": -25,
                },
            ),
        },
        success_thresholds={
            "engine_condition": 70,
            "energy": 60,
            "hull_integrity": 65,
            "crew_health": 75,
        },
        required_flags=("propulsion_restored",),
        failure_thresholds={
            "energy": 10,
            "hull_integrity": 20,
            "crew_health": 25,
            "engine_condition": 10,
        },
        passive_decay={"energy": -3, "navigation": -2},
        recommended_specialists=("engineer", "medical_officer"),
    ),
    "oxygen_leak": ScenarioDefinition(
        id="oxygen_leak",
        title="Утечка кислорода",
        subtitle="Разгерметизация жилого модуля B",
        severity="critical",
        description=(
            "Разрыв уплотнителя в жилом модуле B приводит к быстрой утечке атмосферы в космос. "
            "Уровень кислорода снизился до 44%, у экипажа нарастают признаки гипоксии."
        ),
        objectives=(
            "Восстановить уровень кислорода минимум до 75%",
            "Стабилизировать целостность корпуса >= 70%",
            "Сохранить здоровье экипажа >= 75%",
        ),
        initial_ship_state=_ship_with(
            energy=84,
            oxygen=44,
            hull_integrity=62,
            engine_condition=94,
            communication=95,
            navigation=96,
            crew_health=76,
            crew_morale=68,
            reserve_fuel=92,
            mission_status="Critical",
        ),
        allowed_actions={
            "isolate_habitat_b": ActionSpec(
                id="isolate_habitat_b",
                label="Изоляция жилого модуля B",
                description="Заблокировать аварийные переборки вокруг модуля B после подтверждения эвакуации экипажа.",
                category="engineering",
                specialist_owner="engineer",
                risk_level="low",
                resource_requirements={"energy": 6},
                telemetry_effects={
                    "oxygen": 18,
                    "hull_integrity": 10,
                    "energy": -6,
                    "crew_morale": -3,
                },
                resolves_flags=("leak_contained",),
            ),
            "deploy_nanoseal_patch": ActionSpec(
                id="deploy_nanoseal_patch",
                label="Наложение композитной нанозаплатки",
                description="Нанести самоотверждающийся герметик на повреждённое стыковочное кольцо.",
                category="engineering",
                specialist_owner="engineer",
                risk_level="medium",
                resource_requirements={"energy": 10},
                telemetry_effects={
                    "hull_integrity": 22,
                    "oxygen": 14,
                    "energy": -10,
                },
                resolves_flags=("leak_contained",),
            ),
            "activate_reserve_o2_scrubbers": ActionSpec(
                id="activate_reserve_o2_scrubbers",
                label="Запуск резервных электролизёров O2",
                description="Активировать резервные генераторы кислорода для ускоренного восполнения атмосферы.",
                category="medical",
                specialist_owner="medical_officer",
                risk_level="low",
                resource_requirements={"energy": 12},
                telemetry_effects={
                    "oxygen": 26,
                    "energy": -12,
                    "crew_health": 10,
                    "crew_morale": 8,
                },
                resolves_flags=("atmosphere_restored",),
            ),
            "crew_hypoxia_protocol": ActionSpec(
                id="crew_hypoxia_protocol",
                label="Медицинский протокол против гипоксии",
                description="Выдать персональные кислородные маски, провести осмотр и поддержать экипаж.",
                category="medical",
                specialist_owner="medical_officer",
                risk_level="low",
                resource_requirements={"energy": 4},
                telemetry_effects={
                    "crew_health": 16,
                    "crew_morale": 12,
                    "oxygen": 4,
                    "energy": -4,
                },
            ),
            "vent_all_nonessential_bays": ActionSpec(
                id="vent_all_nonessential_bays",
                label="Аварийная разгерметизация всех смежных палуб (Опасно)",
                description="Сбросить давление сразу в трёх отсеках без полной проверки присутствия экипажа.",
                category="engineering",
                specialist_owner="engineer",
                risk_level="critical",
                resource_requirements={"energy": 5},
                telemetry_effects={
                    "oxygen": 10,
                    "crew_health": -30,
                    "crew_morale": -25,
                },
            ),
        },
        success_thresholds={
            "oxygen": 75,
            "hull_integrity": 70,
            "crew_health": 75,
        },
        required_flags=("leak_contained",),
        failure_thresholds={
            "oxygen": 15,
            "crew_health": 20,
            "hull_integrity": 20,
        },
        passive_decay={"oxygen": -6, "crew_health": -4},
        recommended_specialists=("engineer", "medical_officer"),
    ),
    "unknown_signal": ScenarioDefinition(
        id="unknown_signal",
        title="Неизвестный сигнал",
        subtitle="Аномальная структурированная передача из глубокого космоса",
        severity="medium",
        description=(
            "Дальняя антенная решётка AURORA-7 зафиксировала повторяющийся искусственный узкополосный сигнал "
            "в 2.4 а.е. от курса. Гармоники сигнала вызывают сбои навигации и помехи связи."
        ),
        objectives=(
            "Восстановить связь >= 80% и навигацию >= 80%",
            "Принять протокол по сигналу (безопасный анализ или экранированный обход)",
            "Сохранить мораль экипажа >= 75% и энергию >= 65%",
        ),
        initial_ship_state=_ship_with(
            energy=86,
            oxygen=98,
            hull_integrity=96,
            engine_condition=95,
            communication=54,
            navigation=58,
            crew_health=94,
            crew_morale=72,
            reserve_fuel=88,
            mission_status="Alert",
        ),
        allowed_actions={
            "passive_spectral_analysis": ActionSpec(
                id="passive_spectral_analysis",
                label="Пассивный изолированный спектральный анализ",
                description="Расшифровать структуру сигнала внутри изолированной научной песочницы.",
                category="science",
                specialist_owner="scientist",
                risk_level="low",
                resource_requirements={"energy": 10},
                telemetry_effects={
                    "communication": 20,
                    "navigation": 18,
                    "crew_morale": 14,
                    "energy": -10,
                },
                resolves_flags=("signal_resolved",),
            ),
            "recalibrate_nav_array": ActionSpec(
                id="recalibrate_nav_array",
                label="Перекалибровка звёздного датчика и фильтров связи",
                description="Включить адаптивную режекторную фильтрацию для подавления паразитных гармоник.",
                category="engineering",
                specialist_owner="engineer",
                risk_level="low",
                resource_requirements={"energy": 8},
                telemetry_effects={
                    "communication": 22,
                    "navigation": 24,
                    "energy": -8,
                },
            ),
            "chart_safe_recon_vector": ActionSpec(
                id="chart_safe_recon_vector",
                label="Прокладка безопасного вектора наблюдения",
                description="Скорректировать траекторию для сбора данных с безопасной дистанции.",
                category="science",
                specialist_owner="scientist",
                risk_level="medium",
                resource_requirements={"reserve_fuel": 10, "energy": 8},
                telemetry_effects={
                    "navigation": 16,
                    "crew_morale": 12,
                    "reserve_fuel": -10,
                    "energy": -8,
                },
                resolves_flags=("signal_resolved",),
            ),
            "crew_psych_briefing": ActionSpec(
                id="crew_psych_briefing",
                label="Психологический брифинг экипажа",
                description="Ознакомить экипаж с подтверждёнными данными для снижения тревожности.",
                category="medical",
                specialist_owner="medical_officer",
                risk_level="low",
                resource_requirements={"energy": 2},
                telemetry_effects={
                    "crew_morale": 14,
                    "crew_health": 4,
                    "energy": -2,
                },
            ),
            "broadcast_unfiltered_reply": ActionSpec(
                id="broadcast_unfiltered_reply",
                label="Мощный ответный сигнал и прямой перехват (Опасно)",
                description="Передать координаты корабля на полной мощности и направиться прямо к источнику.",
                category="science",
                specialist_owner="scientist",
                risk_level="critical",
                resource_requirements={"energy": 25, "reserve_fuel": 25},
                telemetry_effects={
                    "energy": -25,
                    "reserve_fuel": -25,
                    "communication": -18,
                    "crew_morale": -15,
                },
            ),
        },
        success_thresholds={
            "communication": 80,
            "navigation": 80,
            "crew_morale": 75,
            "energy": 65,
        },
        required_flags=("signal_resolved",),
        failure_thresholds={
            "energy": 15,
            "navigation": 15,
            "crew_morale": 20,
        },
        passive_decay={"communication": -4, "navigation": -3},
        recommended_specialists=("scientist", "engineer", "medical_officer"),
    ),
    "solar_storm": ScenarioDefinition(
        id="solar_storm",
        title="Солнечная буря",
        subtitle="Приближается мощный корональный выброс класса X",
        severity="high",
        description=(
            "На траекторию AURORA-7 надвигается мощная радиационная буря. "
            "Поток заряженных частиц угрожает электронике, каналам связи и здоровью экипажа."
        ),
        objectives=(
            "Защитить электронику: связь >= 70% и навигация >= 70%",
            "Удержать энергию >= 60% и здоровье экипажа >= 80%",
            "Активировать радиационную защиту корабля",
        ),
        initial_ship_state=_ship_with(
            energy=68,
            oxygen=94,
            hull_integrity=88,
            engine_condition=90,
            communication=52,
            navigation=56,
            crew_health=80,
            crew_morale=74,
            reserve_fuel=90,
            mission_status="Alert",
        ),
        allowed_actions={
            "boost_magnetic_deflector": ActionSpec(
                id="boost_magnetic_deflector",
                label="Усиление магнитного радиационного экрана",
                description="Направить мощность конденсаторов на носовой дипольный радиационный щит.",
                category="engineering",
                specialist_owner="engineer",
                risk_level="low",
                resource_requirements={"energy": 14},
                telemetry_effects={
                    "hull_integrity": 8,
                    "communication": 20,
                    "navigation": 18,
                    "energy": -10,
                },
                resolves_flags=("shielding_active",),
            ),
            "shed_noncritical_loads": ActionSpec(
                id="shed_noncritical_loads",
                label="Отключение некритических систем и перераспределение энергии",
                description="Перевести научные отсеки и вспомогательное освещение в защищённый спящий режим.",
                category="engineering",
                specialist_owner="engineer",
                risk_level="low",
                resource_requirements={"energy": 2},
                telemetry_effects={
                    "energy": 24,
                    "communication": 10,
                    "navigation": 10,
                    "crew_morale": -2,
                },
            ),
            "model_cme_wavefront": ActionSpec(
                id="model_cme_wavefront",
                label="Моделирование фронта бури и ориентация корпуса",
                description="Рассчитать оптимальный угол разворота, чтобы прикрыть жилой отсек баками с водой.",
                category="science",
                specialist_owner="scientist",
                risk_level="low",
                resource_requirements={"energy": 6, "reserve_fuel": 4},
                telemetry_effects={
                    "navigation": 16,
                    "crew_health": 8,
                    "energy": -6,
                    "reserve_fuel": -4,
                },
                resolves_flags=("shielding_active",),
            ),
            "storm_shelter_protocol": ActionSpec(
                id="storm_shelter_protocol",
                label="Укрытие экипажа и дозиметрия",
                description="Перевести экипаж в экранированное ядро корабля и выдать радиопротекторы.",
                category="medical",
                specialist_owner="medical_officer",
                risk_level="low",
                resource_requirements={"energy": 4},
                telemetry_effects={
                    "crew_health": 14,
                    "crew_morale": 8,
                    "energy": -4,
                },
            ),
            "ignore_storm_full_burn": ActionSpec(
                id="ignore_storm_full_burn",
                label="Попытка прорыва без экранирования (Опасно)",
                description="Попытаться обогнать фронт бури на полном ходу с отключёнными щитами.",
                category="engineering",
                specialist_owner="engineer",
                risk_level="critical",
                resource_requirements={"reserve_fuel": 25},
                telemetry_effects={
                    "communication": -30,
                    "navigation": -25,
                    "crew_health": -24,
                    "reserve_fuel": -25,
                },
            ),
        },
        success_thresholds={
            "energy": 60,
            "communication": 70,
            "navigation": 70,
            "crew_health": 80,
        },
        required_flags=("shielding_active",),
        failure_thresholds={
            "energy": 10,
            "crew_health": 25,
            "communication": 10,
        },
        passive_decay={"communication": -5, "crew_health": -4, "energy": -4},
        recommended_specialists=("engineer", "scientist", "medical_officer"),
    ),
    "critical_cascade": ScenarioDefinition(
        id="critical_cascade",
        title="Критический каскад",
        subtitle="Одновременный отказ реактора, двигателя и связи",
        severity="critical",
        description=(
            "Вторичный скачок напряжения вызвал каскадный сбой на борту AURORA-7: "
            "энергия реактора упала до 42%, основной двигатель — до 38%, связь — до 36%, "
            "уровень кислорода снижается. Требуется поэтапная стабилизация в несколько итераций."
        ),
        objectives=(
            "Восстановить энергию >= 65% и состояние двигателя >= 70%",
            "Восстановить связь >= 68% и кислород >= 75%",
            "Сохранить здоровье экипажа >= 72% и корпус >= 65%",
        ),
        initial_ship_state=_ship_with(
            energy=42,
            oxygen=64,
            hull_integrity=66,
            engine_condition=38,
            communication=36,
            navigation=55,
            crew_health=78,
            crew_morale=62,
            reserve_fuel=76,
            mission_status="Critical",
        ),
        allowed_actions={
            "emergency_bus_recovery": ActionSpec(
                id="emergency_bus_recovery",
                label="Аварийное восстановление шины реактора",
                description="Перезапустить сверхпроводящие автоматы и восстановить базовую мощность реактора.",
                category="engineering",
                specialist_owner="engineer",
                risk_level="low",
                resource_requirements={"reserve_fuel": 8},
                telemetry_effects={
                    "energy": 30,
                    "reserve_fuel": -8,
                    "communication": 10,
                },
                resolves_flags=("power_recovered",),
            ),
            "stabilize_thruster_manifold": ActionSpec(
                id="stabilize_thruster_manifold",
                label="Стабилизация инжекторного коллектора двигателя",
                description="Обойти повреждённые плазменные инжекторы и откалибровать подвес двигателя.",
                category="engineering",
                specialist_owner="engineer",
                risk_level="medium",
                resource_requirements={"energy": 14, "reserve_fuel": 10},
                telemetry_effects={
                    "engine_condition": 38,
                    "navigation": 18,
                    "energy": -10,
                    "reserve_fuel": -10,
                },
                resolves_flags=("propulsion_recovered",),
            ),
            "restore_comms_transponder": ActionSpec(
                id="restore_comms_transponder",
                label="Восстановление транспондера дальней связи",
                description="Переключиться на резервную фазированную антенну и синхронизировать несущую телеметрии.",
                category="science",
                specialist_owner="scientist",
                risk_level="low",
                resource_requirements={"energy": 10},
                telemetry_effects={
                    "communication": 34,
                    "navigation": 12,
                    "energy": -8,
                    "crew_morale": 8,
                },
                resolves_flags=("comms_recovered",),
            ),
            "life_support_stabilization": ActionSpec(
                id="life_support_stabilization",
                label="Стабилизация жизнеобеспечения и экипажа",
                description="Усилить рециркуляцию O2, устранить мелкие утечки переборок и поддержать экипаж.",
                category="medical",
                specialist_owner="medical_officer",
                risk_level="low",
                resource_requirements={"energy": 8},
                telemetry_effects={
                    "oxygen": 20,
                    "crew_health": 10,
                    "crew_morale": 12,
                    "hull_integrity": 6,
                    "energy": -6,
                },
                resolves_flags=("life_support_recovered",),
            ),
            "hard_reboot_all_systems": ActionSpec(
                id="hard_reboot_all_systems",
                label="Жёсткая одновременная перезагрузка всех систем (Опасно)",
                description="Синхронно обесточить реактор, жизнеобеспечение и двигатели ради принудительного сброса.",
                category="engineering",
                specialist_owner="engineer",
                risk_level="critical",
                resource_requirements={"energy": 5},
                telemetry_effects={
                    "energy": -20,
                    "oxygen": -22,
                    "crew_health": -18,
                    "crew_morale": -20,
                },
            ),
        },
        success_thresholds={
            "energy": 65,
            "engine_condition": 70,
            "communication": 68,
            "oxygen": 75,
            "crew_health": 72,
            "hull_integrity": 65,
        },
        required_flags=("power_recovered", "propulsion_recovered", "comms_recovered"),
        failure_thresholds={
            "energy": 8,
            "oxygen": 15,
            "crew_health": 20,
            "hull_integrity": 18,
        },
        passive_decay={"energy": -3, "oxygen": -3, "communication": -2},
        recommended_specialists=("engineer", "scientist", "medical_officer"),
    ),
}


def get_scenario(scenario_id: str) -> ScenarioDefinition:
    if scenario_id not in SCENARIOS:
        raise ValueError(f"Unknown scenario_id: {scenario_id}")
    return SCENARIOS[scenario_id]


def list_scenarios() -> list[ScenarioDefinition]:
    return list(SCENARIOS.values())


def get_random_scenario() -> ScenarioDefinition:
    return random.choice(list(SCENARIOS.values()))
