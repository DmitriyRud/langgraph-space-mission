import { create } from 'zustand';
import type {
  CheckpointSnapshot,
  ConsoleTab,
  ExecutionEvent,
  GraphTopology,
  HealthResponse,
  Language,
  LLMCallRecord,
  MissionMode,
  MissionRecord,
  MissionState,
  NodeRuntimeInfo,
  ScenarioDefinition,
  ShipState,
  ViewMode,
} from '../types/mission';

const LANG_STORAGE_KEY = 'aurora7_lang';

function getInitialLanguage(): Language {
  try {
    const saved = window.localStorage.getItem(LANG_STORAGE_KEY);
    if (saved === 'en' || saved === 'ru') return saved;
  } catch {
    // ignore storage errors
  }
  return 'en';
}

export const BASELINE_SHIP_STATE: ShipState = {
  energy: 100,
  oxygen: 100,
  hull_integrity: 100,
  engine_condition: 100,
  communication: 100,
  navigation: 100,
  crew_health: 100,
  crew_morale: 100,
  reserve_fuel: 100,
  mission_status: 'Operational',
};

export interface DerivedExecutionView {
  nodeStates: Record<string, NodeRuntimeInfo>;
  activeEdges: Set<string>;
  activeParallelNodes: string[];
  currentState: Partial<MissionState> | null;
  previousState: Partial<MissionState> | null;
  stateSnapshots: Array<{ eventId: string; timestamp: string; nodeId: string | null; iteration: number; state: Partial<MissionState> }>;
  llmCalls: LLMCallRecord[];
  currentIteration: number;
  pendingInterrupt: Record<string, unknown> | null;
  latestError: { message: string; canSwitchToDemo: boolean } | null;
  isCompleted: boolean;
}

export function deriveExecutionView(
  events: ExecutionEvent[],
  topology: GraphTopology | null,
  fallbackSnapshot: CheckpointSnapshot | null
): DerivedExecutionView {
  const nodeStates: Record<string, NodeRuntimeInfo> = {};
  if (topology) {
    for (const n of topology.nodes) {
      nodeStates[n.id] = {
        nodeId: n.id,
        status: 'idle',
        runCount: 0,
        iteration: 0,
        startedAt: null,
        completedAt: null,
        durationMs: null,
        attempts: 0,
        inputState: null,
        partialUpdate: null,
        systemPrompt: n.system_prompt,
        llmInput: null,
        llmOutput: null,
        tokenUsage: null,
        modelUsed: null,
        error: null,
        lastSummary: null,
      };
    }
  }

  const ensureNode = (id: string): NodeRuntimeInfo => {
    if (!nodeStates[id]) {
      nodeStates[id] = {
        nodeId: id,
        status: 'idle',
        runCount: 0,
        iteration: 0,
        startedAt: null,
        completedAt: null,
        durationMs: null,
        attempts: 0,
        inputState: null,
        partialUpdate: null,
        systemPrompt: null,
        llmInput: null,
        llmOutput: null,
        tokenUsage: null,
        modelUsed: null,
        error: null,
        lastSummary: null,
      };
    }
    return nodeStates[id];
  };

  const activeEdges = new Set<string>();
  const stateSnapshots: DerivedExecutionView['stateSnapshots'] = [];
  const llmCalls: LLMCallRecord[] = [];
  const llmByNode = new Map<string, LLMCallRecord>();

  let currentState: Partial<MissionState> | null = fallbackSnapshot?.values ?? null;
  let previousState: Partial<MissionState> | null = null;
  let currentIteration = Number(currentState?.iteration ?? 1);
  let pendingInterrupt: Record<string, unknown> | null =
    fallbackSnapshot?.interrupts?.[0]?.value ?? null;
  let latestError: { message: string; canSwitchToDemo: boolean } | null = null;
  let isCompleted = false;
  let lastCompletedNode: string | null = '__start__';

  for (const evt of events) {
    if (evt.iteration) currentIteration = evt.iteration;
    const nodeId = evt.node_id;

    switch (evt.event_type) {
      case 'mission_started': {
        ensureNode('__start__').status = 'completed';
        ensureNode('__start__').runCount = 1;
        activeEdges.add('__start__->incident_init');
        latestError = null;
        break;
      }
      case 'node_started': {
        if (!nodeId) break;
        const info = ensureNode(nodeId);
        info.status = info.runCount > 0 ? 'retrying' : 'running';
        info.runCount += 1;
        info.iteration = evt.iteration ?? currentIteration;
        info.startedAt = evt.timestamp;
        info.attempts = Number(evt.payload.attempt ?? 1);
        info.error = null;
        if (evt.payload.input_state && typeof evt.payload.input_state === 'object') {
          info.inputState = evt.payload.input_state as Record<string, unknown>;
        }
        if (lastCompletedNode && lastCompletedNode !== nodeId) {
          activeEdges.add(`${lastCompletedNode}->${nodeId}`);
        }
        break;
      }
      case 'retry': {
        if (!nodeId) break;
        const info = ensureNode(nodeId);
        info.status = 'retrying';
        info.attempts = Number(evt.payload.attempt ?? info.attempts + 1);
        break;
      }
      case 'node_completed': {
        if (!nodeId) break;
        const info = ensureNode(nodeId);
        info.status = 'completed';
        info.completedAt = evt.timestamp;
        info.durationMs = Number(evt.payload.duration_ms ?? 0);
        lastCompletedNode = nodeId;
        break;
      }
      case 'parallel_branch_started': {
        const targets = (evt.payload.targets as string[]) ?? [];
        const allSpecialists = ['engineer', 'scientist', 'medical_officer'];
        for (const s of allSpecialists) {
          if (targets.includes(s)) {
            activeEdges.add(`commander->${s}`);
            activeEdges.add(`${s}->plan_aggregator`);
          } else if (ensureNode(s).status === 'idle') {
            ensureNode(s).status = 'skipped';
          }
        }
        break;
      }
      case 'conditional_edge_selected': {
        const from = String(evt.payload.from ?? '');
        const to = String(evt.payload.to ?? '');
        if (from && to) {
          activeEdges.add(`${from}->${to}`);
        }
        break;
      }
      case 'plan_rejected': {
        if (nodeId) {
          const info = ensureNode(nodeId);
          info.status = 'error';
          info.lastSummary = '__PLAN_REJECTED__';
        }
        break;
      }
      case 'llm_request_started': {
        if (!nodeId) break;
        const info = ensureNode(nodeId);
        info.systemPrompt = String(evt.payload.system_prompt ?? info.systemPrompt ?? '');
        info.llmInput = String(evt.payload.user_prompt ?? '');
        info.modelUsed = String(evt.payload.model ?? '');
        const rec: LLMCallRecord = {
          id: evt.event_id,
          timestamp: evt.timestamp,
          nodeId,
          agent: String(evt.payload.agent ?? nodeId),
          iteration: evt.iteration ?? currentIteration,
          mode: String(evt.payload.mode ?? 'demo'),
          provider: String(evt.payload.provider ?? ''),
          model: String(evt.payload.model ?? ''),
          systemPrompt: String(evt.payload.system_prompt ?? ''),
          userPrompt: String(evt.payload.user_prompt ?? ''),
          structuredOutput: null,
          durationMs: null,
          tokenUsage: null,
        };
        llmCalls.push(rec);
        llmByNode.set(nodeId, rec);
        break;
      }
      case 'llm_response_received': {
        if (!nodeId) break;
        const info = ensureNode(nodeId);
        const structured = (evt.payload.structured_output as Record<string, unknown>) ?? null;
        info.llmOutput = structured;
        info.durationMs = Number(evt.payload.duration_ms ?? info.durationMs ?? 0);
        info.tokenUsage = (evt.payload.token_usage as Record<string, number>) ?? null;
        if (structured) {
          info.lastSummary = String(
            structured.summary ?? structured.diagnosis ?? structured.situation_summary ?? ''
          );
        }
        const rec = llmByNode.get(nodeId);
        if (rec) {
          rec.structuredOutput = structured;
          rec.durationMs = Number(evt.payload.duration_ms ?? 0);
          rec.tokenUsage = (evt.payload.token_usage as Record<string, number>) ?? null;
        }
        break;
      }
      case 'state_updated': {
        if (nodeId && evt.payload.partial_update) {
          ensureNode(nodeId).partialUpdate = evt.payload.partial_update as Record<string, unknown>;
        }
        break;
      }
      case 'state_snapshot': {
        if (evt.payload.state && typeof evt.payload.state === 'object') {
          previousState = currentState;
          currentState = evt.payload.state as Partial<MissionState>;
          stateSnapshots.push({
            eventId: evt.event_id,
            timestamp: evt.timestamp,
            nodeId: lastCompletedNode,
            iteration: Number(currentState.iteration ?? currentIteration),
            state: currentState,
          });
        }
        break;
      }
      case 'human_approval_requested': {
        if (nodeId) {
          ensureNode(nodeId).status = 'waiting_human';
        }
        pendingInterrupt = (evt.payload.interrupt as Record<string, unknown>) ?? null;
        break;
      }
      case 'execution_resumed': {
        pendingInterrupt = null;
        latestError = null;
        if (evt.payload.decision === 'approve') {
          activeEdges.add('human_approval->executor');
        } else {
          activeEdges.add('human_approval->commander');
        }
        break;
      }
      case 'error': {
        const message = String(evt.payload.message ?? evt.payload.error ?? 'Execution error');
        const canSwitchToDemo = Boolean(evt.payload.can_switch_to_demo);
        latestError = { message, canSwitchToDemo };
        if (nodeId) {
          const info = ensureNode(nodeId);
          info.status = 'error';
          info.error = message;
        }
        break;
      }
      case 'mission_completed': {
        isCompleted = true;
        pendingInterrupt = null;
        ensureNode('__end__').status = 'completed';
        ensureNode('__end__').runCount = 1;
        activeEdges.add('mission_evaluator->__end__');
        break;
      }
      default:
        break;
    }
  }

  const activeParallelNodes = Object.values(nodeStates)
    .filter((n) => n.status === 'running' || n.status === 'retrying')
    .map((n) => n.nodeId);

  return {
    nodeStates,
    activeEdges,
    activeParallelNodes,
    currentState,
    previousState,
    stateSnapshots,
    llmCalls,
    currentIteration,
    pendingInterrupt,
    latestError,
    isCompleted,
  };
}

interface MissionStore {
  language: Language;
  health: HealthResponse | null;
  scenarios: ScenarioDefinition[];
  topology: GraphTopology | null;
  missions: MissionRecord[];
  activeMission: MissionRecord | null;
  fallbackSnapshot: CheckpointSnapshot | null;
  selectedScenarioId: string;
  mode: MissionMode;
  viewMode: ViewMode;
  events: ExecutionEvent[];
  replayIndex: number;
  checkpoints: CheckpointSnapshot[];
  selectedNodeId: string | null;
  activeConsoleTab: ConsoleTab;
  consoleCollapsed: boolean;
  consoleHeight: number;
  leftCollapsed: boolean;
  rightCollapsed: boolean;
  settingsOpen: boolean;
  sseConnected: boolean;
  busy: boolean;
  toastMessage: string | null;

  setLanguage: (language: Language) => void;
  setHealth: (health: HealthResponse) => void;
  setScenarios: (scenarios: ScenarioDefinition[]) => void;
  setTopology: (topology: GraphTopology) => void;
  setMissions: (missions: MissionRecord[]) => void;
  setActiveMission: (mission: MissionRecord | null, snapshot?: CheckpointSnapshot | null) => void;
  setSelectedScenarioId: (id: string) => void;
  setMode: (mode: MissionMode) => void;
  setViewMode: (mode: ViewMode) => void;
  setReplayIndex: (index: number) => void;
  appendEvent: (event: ExecutionEvent) => void;
  setEvents: (events: ExecutionEvent[]) => void;
  setCheckpoints: (checkpoints: CheckpointSnapshot[]) => void;
  setSelectedNodeId: (nodeId: string | null) => void;
  setActiveConsoleTab: (tab: ConsoleTab) => void;
  toggleConsoleCollapsed: () => void;
  setConsoleHeight: (height: number) => void;
  toggleLeftCollapsed: () => void;
  toggleRightCollapsed: () => void;
  setSettingsOpen: (open: boolean) => void;
  setSseConnected: (connected: boolean) => void;
  setBusy: (busy: boolean) => void;
  setToastMessage: (msg: string | null) => void;
  resetMissionView: () => void;
}

export const useMissionStore = create<MissionStore>((set) => ({
  language: getInitialLanguage(),
  health: null,
  scenarios: [],
  topology: null,
  missions: [],
  activeMission: null,
  fallbackSnapshot: null,
  selectedScenarioId: 'engine_failure',
  mode: 'demo',
  viewMode: 'live',
  events: [],
  replayIndex: 0,
  checkpoints: [],
  selectedNodeId: null,
  activeConsoleTab: 'logs',
  consoleCollapsed: false,
  consoleHeight: 260,
  leftCollapsed: false,
  rightCollapsed: false,
  settingsOpen: false,
  sseConnected: false,
  busy: false,
  toastMessage: null,

  setLanguage: (language) => {
    try {
      window.localStorage.setItem(LANG_STORAGE_KEY, language);
    } catch {
      // ignore storage errors
    }
    set({ language });
  },
  setHealth: (health) => set({ health }),
  setScenarios: (scenarios) => set({ scenarios }),
  setTopology: (topology) => set({ topology }),
  setMissions: (missions) => set({ missions }),
  setActiveMission: (mission, snapshot = null) =>
    set({
      activeMission: mission,
      fallbackSnapshot: snapshot,
      events: [],
      replayIndex: 0,
      checkpoints: [],
      viewMode: 'live',
    }),
  setSelectedScenarioId: (selectedScenarioId) => set({ selectedScenarioId }),
  setMode: (mode) => set({ mode }),
  setViewMode: (viewMode) =>
    set((s) => ({
      viewMode,
      replayIndex: viewMode === 'replay' ? Math.max(0, s.events.length - 1) : s.events.length,
    })),
  setReplayIndex: (replayIndex) => set({ replayIndex }),
  appendEvent: (event) =>
    set((s) => {
      if (s.events.some((e) => e.event_id === event.event_id)) return s;
      const next = [...s.events, event];
      return {
        events: next,
        replayIndex: s.viewMode === 'live' ? next.length - 1 : s.replayIndex,
      };
    }),
  setEvents: (events) => set({ events, replayIndex: Math.max(0, events.length - 1) }),
  setCheckpoints: (checkpoints) => set({ checkpoints }),
  setSelectedNodeId: (selectedNodeId) => set({ selectedNodeId }),
  setActiveConsoleTab: (activeConsoleTab) => set({ activeConsoleTab, consoleCollapsed: false }),
  toggleConsoleCollapsed: () => set((s) => ({ consoleCollapsed: !s.consoleCollapsed })),
  setConsoleHeight: (consoleHeight) => set({ consoleHeight: Math.max(160, Math.min(520, consoleHeight)) }),
  toggleLeftCollapsed: () => set((s) => ({ leftCollapsed: !s.leftCollapsed })),
  toggleRightCollapsed: () => set((s) => ({ rightCollapsed: !s.rightCollapsed })),
  setSettingsOpen: (settingsOpen) => set({ settingsOpen }),
  setSseConnected: (sseConnected) => set({ sseConnected }),
  setBusy: (busy) => set({ busy }),
  setToastMessage: (toastMessage) => set({ toastMessage }),
  resetMissionView: () =>
    set({
      activeMission: null,
      fallbackSnapshot: null,
      events: [],
      replayIndex: 0,
      checkpoints: [],
      selectedNodeId: null,
      viewMode: 'live',
    }),
}));
