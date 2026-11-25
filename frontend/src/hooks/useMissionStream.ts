import { useEffect, useRef } from 'react';
import { api } from '../api/client';
import { useMissionStore } from '../stores/missionStore';
import type { ExecutionEvent } from '../types/mission';

const EVENT_TYPES = [
  'mission_started',
  'node_started',
  'node_completed',
  'llm_request_started',
  'llm_response_received',
  'conditional_edge_selected',
  'parallel_branch_started',
  'state_updated',
  'state_snapshot',
  'plan_rejected',
  'checkpoint_created',
  'human_approval_requested',
  'execution_resumed',
  'retry',
  'error',
  'mission_completed',
];

export function useMissionStream(missionId: string | null) {
  const appendEvent = useMissionStore((s) => s.appendEvent);
  const setSseConnected = useMissionStore((s) => s.setSseConnected);
  const setCheckpoints = useMissionStore((s) => s.setCheckpoints);
  const lastEventIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (!missionId) {
      setSseConnected(false);
      lastEventIdRef.current = null;
      return;
    }

    lastEventIdRef.current = null;
    let closed = false;
    let source: EventSource | null = null;
    let reconnectTimer: number | null = null;

    const refreshCheckpoints = async () => {
      try {
        const res = await api.getCheckpoints(missionId);
        if (!closed) setCheckpoints(res.checkpoints);
      } catch {
        // ignore transient checkpoint fetch error
      }
    };

    const connect = () => {
      if (closed) return;
      const url = api.getStreamUrl(missionId, lastEventIdRef.current);
      source = new EventSource(url);

      source.onopen = () => {
        if (!closed) setSseConnected(true);
      };

      source.onerror = () => {
        if (closed) return;
        setSseConnected(false);
        source?.close();
        reconnectTimer = window.setTimeout(connect, 2000);
      };

      const handleEvent = (raw: MessageEvent) => {
        try {
          const parsed = JSON.parse(raw.data) as ExecutionEvent;
          if (parsed.event_id && parsed.event_id !== 'keepalive') {
            lastEventIdRef.current = parsed.event_id;
          }
          appendEvent(parsed);
          if (
            parsed.event_type === 'checkpoint_created' ||
            parsed.event_type === 'human_approval_requested' ||
            parsed.event_type === 'mission_completed'
          ) {
            void refreshCheckpoints();
          }
        } catch {
          // ignore malformed event
        }
      };

      for (const evtType of EVENT_TYPES) {
        source.addEventListener(evtType, handleEvent as EventListener);
      }
    };

    connect();
    void refreshCheckpoints();

    return () => {
      closed = true;
      setSseConnected(false);
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      source?.close();
    };
  }, [missionId, appendEvent, setSseConnected, setCheckpoints]);
}
