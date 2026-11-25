export type Language = 'en' | 'ru';
export type MissionMode = 'demo' | 'live';
export type ViewMode = 'live' | 'replay';
export type ConsoleTab = 'logs' | 'state' | 'diff' | 'checkpoints' | 'llm' | 'learning';

export type NodeVisualStatus =
  | 'idle'
  | 'running'
  | 'completed'
  | 'waiting_human'
  | 'error'
  | 'retrying'
  | 'skipped';

export interface ShipState {
  energy: number;
  oxygen: number;
  hull_integrity: number;
  engine_condition: number;
  communication: number;
  navigation: number;
  crew_health: number;
  crew_morale: number;
  reserve_fuel: number;
  mission_status: string;
}

export interface ActionSpec {
  id: string;
  label: string;
  description: string;
  category: string;
  specialist_owner: string;
  risk_level: string;
  resource_requirements: Record<string, number>;
  telemetry_effects: Record<string, number>;
  resolves_flags: string[];
}

export interface ScenarioDefinition {
  id: string;
  title: string;
  subtitle: string;
  severity: string;
  description: string;
  objectives: string[];
  initial_ship_state: ShipState;
  allowed_actions: ActionSpec[];
  success_thresholds: Record<string, number>;
  failure_thresholds: Record<string, number>;
  recommended_specialists: string[];
}

export interface MissionPlan {
  plan_id: string;
  iteration: number;
  revision: number;
  title: string;
  summary: string;
  action_ids: string[];
  actions_detail: ActionSpec[];
  expected_outcomes: string;
  resource_summary: string;
  projected_effects: Record<string, number>;
  risk_level: string;
}

export interface SafetyAssessment {
  approved: boolean;
  risk_level: string;
  resource_check_passed: boolean;
  findings: string[];
  required_revisions: string;
  summary: string;
}

export interface SpecialistReport {
  agent: string;
  iteration: number;
  diagnosis: string;
  recommended_actions: string[];
  resource_estimate: string;
  projected_consequences: string;
  risk_level: string;
}

export interface MissionState {
  mission_id: string;
  scenario_id: string;
  mode: string;
  mission_status: string;
  incident: Record<string, unknown>;
  ship_state: ShipState;
  initial_ship_state: ShipState;
  selected_specialists: string[];
  specialist_reports: SpecialistReport[];
  current_plan: MissionPlan | null;
  previous_plans: MissionPlan[];
  executed_actions: Array<Record<string, unknown>>;
  safety_assessment: SafetyAssessment | null;
  risk_level: string;
  iteration: number;
  max_iterations: number;
  user_feedback: string | null;
  approval_status: string;
  mission_result: Record<string, unknown> | null;
  event_history: Array<Record<string, unknown>>;
  errors: Array<Record<string, unknown>>;
  plan_revision_count: number;
}

export interface GraphNodeMeta {
  id: string;
  label: string;
  role: string;
  category: 'boundary' | 'system' | 'agent' | 'specialist' | 'hitl';
  description: string;
  langgraph_mechanism: string;
  system_prompt: string | null;
  position: { x: number; y: number };
}

export interface GraphEdgeMeta {
  id: string;
  source: string;
  target: string;
  conditional: boolean;
  dynamic: boolean;
  cyclic: boolean;
  label: string;
}

export interface LearningItem {
  id: string;
  name: string;
  summary: string;
  where_used: string;
  nodes: string[];
  snippet: string;
  doc_url: string;
}

export interface GraphTopology {
  nodes: GraphNodeMeta[];
  edges: GraphEdgeMeta[];
  learning_catalog: LearningItem[];
}

export interface MissionRecord {
  mission_id: string;
  thread_id: string;
  scenario_id: string;
  mode: MissionMode;
  status: string;
  max_iterations: number;
  parent_mission_id: string | null;
  parent_checkpoint_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExecutionEvent {
  seq?: number;
  event_id: string;
  event_type: string;
  timestamp: string;
  mission_id: string;
  thread_id: string;
  node_id: string | null;
  task_id: string | null;
  iteration: number | null;
  checkpoint_id: string | null;
  payload: Record<string, unknown>;
}

export interface CheckpointSnapshot {
  checkpoint_id: string | null;
  thread_id: string | null;
  parent_checkpoint_id: string | null;
  created_at: string | null;
  next: string[];
  step: number | null;
  source: string | null;
  writes: Record<string, unknown> | null;
  values: Partial<MissionState>;
  interrupts: Array<{ id?: string; value: Record<string, unknown> }>;
}

export interface LLMHealth {
  provider: string;
  connected: boolean;
  base_url: string;
  active_model: string;
  model_available?: boolean;
  available_models: string[];
  error: string | null;
}

export interface SystemInfo {
  cpu: string;
  ram_gb: number | null;
  os: string;
  recommended_models: string[];
}

export interface HealthResponse {
  status: string;
  spacecraft: string;
  llm: LLMHealth;
  system?: SystemInfo;
  default_max_iterations: number;
}

export interface NodeRuntimeInfo {
  nodeId: string;
  status: NodeVisualStatus;
  runCount: number;
  iteration: number;
  startedAt: string | null;
  completedAt: string | null;
  durationMs: number | null;
  attempts: number;
  inputState: Record<string, unknown> | null;
  partialUpdate: Record<string, unknown> | null;
  systemPrompt: string | null;
  llmInput: string | null;
  llmOutput: Record<string, unknown> | null;
  tokenUsage: Record<string, number> | null;
  modelUsed: string | null;
  error: string | null;
  lastSummary: string | null;
}

export interface LLMCallRecord {
  id: string;
  timestamp: string;
  nodeId: string;
  agent: string;
  iteration: number;
  mode: string;
  provider: string;
  model: string;
  systemPrompt: string;
  userPrompt: string;
  structuredOutput: Record<string, unknown> | null;
  durationMs: number | null;
  tokenUsage: Record<string, number> | null;
}
