import { useMemo, useState } from 'react';
import { Filter } from 'lucide-react';
import { useI18n } from '../../i18n';
import type { ExecutionEvent } from '../../types/mission';

interface ExecutionTimelineTabProps {
  events: ExecutionEvent[];
  onSelectNode: (nodeId: string) => void;
}

function eventSeverity(evt: ExecutionEvent): 'info' | 'warn' | 'error' | 'success' {
  if (evt.event_type === 'error' || evt.event_type === 'plan_rejected') return 'error';
  if (evt.event_type === 'human_approval_requested' || evt.event_type === 'retry') return 'warn';
  if (evt.event_type === 'mission_completed' || evt.event_type === 'node_completed') return 'success';
  return 'info';
}

export function ExecutionTimelineTab({ events, onSelectNode }: ExecutionTimelineTabProps) {
  const { t } = useI18n();
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [nodeFilter, setNodeFilter] = useState<string>('all');
  const [severityFilter, setSeverityFilter] = useState<string>('all');

  const summarizeEvent = (evt: ExecutionEvent): string => {
    const p = evt.payload;
    switch (evt.event_type) {
      case 'mission_started':
        return t('timeline.events.mission_started', {
          scenario: String(p.scenario_id ?? ''),
          mode: String(p.mode ?? ''),
          forkTag: p.time_travel ? ' [TIME TRAVEL FORK]' : '',
        });
      case 'node_started':
        return t('timeline.events.node_started', {
          node: String(evt.node_id ?? ''),
          attempt: String(p.attempt ?? 1),
        });
      case 'node_completed':
        return t('timeline.events.node_completed', {
          node: String(evt.node_id ?? ''),
          ms: String(p.duration_ms ?? 0),
        });
      case 'llm_request_started':
        return t('timeline.events.llm_request_started', {
          agent: String(p.agent ?? evt.node_id ?? ''),
          model: String(p.model ?? ''),
        });
      case 'llm_response_received':
        return t('timeline.events.llm_response_received', {
          agent: String(p.agent ?? evt.node_id ?? ''),
          ms: String(p.duration_ms ?? 0),
        });
      case 'parallel_branch_started':
        return t('timeline.events.parallel_branch_started', {
          targets: ((p.targets as string[]) ?? []).join(', '),
        });
      case 'conditional_edge_selected':
        return t('timeline.events.conditional_edge_selected', {
          from: String(p.from ?? ''),
          to: String(p.to ?? ''),
        });
      case 'state_updated':
        return t('timeline.events.state_updated', {
          node: String(evt.node_id ?? ''),
          keys: Object.keys((p.partial_update as Record<string, unknown>) ?? {}).join(', '),
        });
      case 'state_snapshot':
        return t('timeline.events.state_snapshot', {
          iteration: String(evt.iteration ?? ''),
        });
      case 'plan_rejected':
        return t('timeline.events.plan_rejected', {
          by: String(p.rejected_by ?? evt.node_id ?? ''),
        });
      case 'checkpoint_created':
        return t('timeline.events.checkpoint_created', {
          id: String(evt.checkpoint_id ?? '').slice(0, 12),
        });
      case 'human_approval_requested':
        return t('timeline.events.human_approval_requested');
      case 'execution_resumed':
        return t('timeline.events.execution_resumed', {
          decision: String(p.decision ?? ''),
        });
      case 'retry':
        return t('timeline.events.retry', {
          node: String(evt.node_id ?? ''),
          attempt: String(p.attempt ?? ''),
        });
      case 'error':
        return String(p.message ?? p.error ?? t('timeline.events.error_fallback'));
      case 'mission_completed':
        return t('timeline.events.mission_completed', {
          outcome: String(p.outcome ?? ''),
        });
      default:
        return evt.event_type;
    }
  };

  const uniqueTypes = useMemo(
    () => Array.from(new Set(events.map((e) => e.event_type))).sort(),
    [events]
  );
  const uniqueNodes = useMemo(
    () => Array.from(new Set(events.map((e) => e.node_id).filter(Boolean) as string[])).sort(),
    [events]
  );

  const filtered = useMemo(() => {
    return events.filter((e) => {
      if (typeFilter !== 'all' && e.event_type !== typeFilter) return false;
      if (nodeFilter !== 'all' && e.node_id !== nodeFilter) return false;
      if (severityFilter !== 'all' && eventSeverity(e) !== severityFilter) return false;
      return true;
    });
  }, [events, typeFilter, nodeFilter, severityFilter]);

  return (
    <div className="h-full flex flex-col">
      <div className="px-3 py-1.5 border-b border-slate-800/80 flex flex-wrap items-center gap-2 text-[11px] font-mono bg-[#090f1d]">
        <Filter className="w-3.5 h-3.5 text-slate-400" />
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="bg-[#0f172a] border border-slate-700 rounded px-2 py-0.5 text-slate-300"
        >
          <option value="all">{t('timeline.allTypes', { count: events.length })}</option>
          {uniqueTypes.map((type) => (
            <option key={type} value={type}>{type}</option>
          ))}
        </select>

        <select
          value={nodeFilter}
          onChange={(e) => setNodeFilter(e.target.value)}
          className="bg-[#0f172a] border border-slate-700 rounded px-2 py-0.5 text-slate-300"
        >
          <option value="all">{t('timeline.allNodes')}</option>
          {uniqueNodes.map((n) => (
            <option key={n} value={n}>{n}</option>
          ))}
        </select>

        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className="bg-[#0f172a] border border-slate-700 rounded px-2 py-0.5 text-slate-300"
        >
          <option value="all">{t('timeline.allSeverities')}</option>
          <option value="info">{t('timeline.info')}</option>
          <option value="success">{t('timeline.success')}</option>
          <option value="warn">{t('timeline.warn')}</option>
          <option value="error">{t('timeline.error')}</option>
        </select>

        <span className="ml-auto text-slate-500">{t('timeline.showing', { count: filtered.length })}</span>
      </div>

      <div className="flex-1 overflow-y-auto font-mono text-[11px] divide-y divide-slate-800/60">
        {filtered.length === 0 ? (
          <div className="p-4 text-slate-500">{t('timeline.empty')}</div>
        ) : (
          filtered.map((evt) => {
            const sev = eventSeverity(evt);
            const badgeColor =
              sev === 'error'
                ? 'text-red-300 bg-red-500/15 border-red-500/40'
                : sev === 'warn'
                  ? 'text-amber-300 bg-amber-500/15 border-amber-500/40'
                  : sev === 'success'
                    ? 'text-emerald-300 bg-emerald-500/10 border-emerald-500/30'
                    : 'text-cyan-300 bg-cyan-500/10 border-cyan-500/30';

            const timeStr = evt.timestamp ? evt.timestamp.slice(11, 23) : '';
            return (
              <div
                key={evt.event_id}
                className="px-3 py-1.5 hover:bg-slate-900/70 flex items-center gap-2.5"
              >
                <span className="text-slate-500 shrink-0 w-20">{timeStr}</span>
                <span className={`px-1.5 py-0.2 rounded border text-[10px] shrink-0 ${badgeColor}`}>
                  {evt.event_type}
                </span>
                {evt.node_id && (
                  <button
                    type="button"
                    onClick={() => onSelectNode(evt.node_id!)}
                    className="px-1.5 py-0.2 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 shrink-0"
                  >
                    {evt.node_id}
                  </button>
                )}
                {evt.iteration != null && (
                  <span className="text-slate-500 shrink-0">
                    {t('timeline.iterPrefix', { iteration: evt.iteration })}
                  </span>
                )}
                <span className="text-slate-300 truncate">{summarizeEvent(evt)}</span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
