import type {
  CheckpointSnapshot,
  ExecutionEvent,
  GraphTopology,
  HealthResponse,
  Language,
  MissionMode,
  MissionRecord,
  ScenarioDefinition,
} from '../types/mission';

const API_BASE = '/api';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  });
  if (!resp.ok) {
    const text = await resp.text();
    let detail = text;
    try {
      const parsed = JSON.parse(text) as { detail?: string };
      if (parsed.detail) detail = parsed.detail;
    } catch {
      // keep raw text
    }
    throw new Error(detail || `Request failed (${resp.status})`);
  }
  return (await resp.json()) as T;
}

export const api = {
  getHealth: () => request<HealthResponse>('/health'),
  getScenarios: (lang: Language = 'en') =>
    request<{ scenarios: ScenarioDefinition[] }>(`/scenarios?lang=${lang}`),
  getGraph: (lang: Language = 'en') => request<GraphTopology>(`/graph?lang=${lang}`),
  listMissions: () => request<{ missions: MissionRecord[] }>('/missions'),

  createMission: (
    scenario_id: string,
    mode: MissionMode,
    max_iterations = 5,
    language: Language = 'en'
  ) =>
    request<{ mission: MissionRecord }>('/missions', {
      method: 'POST',
      body: JSON.stringify({ scenario_id, mode, max_iterations, language }),
    }),

  getMission: (missionId: string) =>
    request<{
      mission: MissionRecord;
      running: boolean;
      snapshot: CheckpointSnapshot | null;
      event_count: number;
    }>(`/missions/${missionId}`),

  startMission: (missionId: string) =>
    request<{ mission: MissionRecord; started: boolean }>(`/missions/${missionId}/start`, {
      method: 'POST',
    }),

  resumeMission: (
    missionId: string,
    decision: 'approve' | 'reject' | 'request_revision',
    feedback = '',
    switch_to_demo = false
  ) =>
    request<{ mission: MissionRecord; resumed: boolean }>(`/missions/${missionId}/resume`, {
      method: 'POST',
      body: JSON.stringify({ decision, feedback, switch_to_demo }),
    }),

  getCheckpoints: (missionId: string) =>
    request<{ mission_id: string; thread_id: string; checkpoints: CheckpointSnapshot[] }>(
      `/missions/${missionId}/checkpoints`
    ),

  forkMission: (
    missionId: string,
    checkpoint_id: string,
    mode?: MissionMode,
    auto_start = true
  ) =>
    request<{ mission: MissionRecord; warning: string }>(`/missions/${missionId}/fork`, {
      method: 'POST',
      body: JSON.stringify({ checkpoint_id, mode, auto_start }),
    }),

  exportMission: (missionId: string) =>
    request<{
      mission: MissionRecord;
      current_state: CheckpointSnapshot | null;
      checkpoints: CheckpointSnapshot[];
      events: ExecutionEvent[];
    }>(`/missions/${missionId}/export`),

  getStreamUrl: (missionId: string, lastEventId?: string | null) => {
    const query = lastEventId ? `?last_event_id=${encodeURIComponent(lastEventId)}` : '';
    return `${API_BASE}/missions/${missionId}/events${query}`;
  },
};
