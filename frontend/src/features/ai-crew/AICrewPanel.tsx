import {
  ChevronLeft,
  ChevronRight,
  Compass,
  FlaskConical,
  HeartPulse,
  ShieldCheck,
  Users,
  Wrench,
} from 'lucide-react';
import { useI18n } from '../../i18n';
import { useMissionStore } from '../../stores/missionStore';
import type { DerivedExecutionView } from '../../stores/missionStore';
import type { NodeVisualStatus } from '../../types/mission';

interface AICrewPanelProps {
  derived: DerivedExecutionView;
}

const CREW_AGENTS = [
  { id: 'commander', icon: Compass },
  { id: 'engineer', icon: Wrench },
  { id: 'scientist', icon: FlaskConical },
  { id: 'medical_officer', icon: HeartPulse },
  { id: 'safety_officer', icon: ShieldCheck },
] as const;

function statusBadge(status: NodeVisualStatus) {
  switch (status) {
    case 'running':
      return 'border-cyan-500/50 bg-cyan-500/15 text-cyan-300';
    case 'retrying':
      return 'border-purple-500/50 bg-purple-500/15 text-purple-300';
    case 'completed':
      return 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300';
    case 'error':
      return 'border-red-500/50 bg-red-500/15 text-red-300';
    case 'skipped':
      return 'border-slate-700 bg-slate-800/40 text-slate-500';
    default:
      return 'border-slate-700 bg-slate-900 text-slate-400';
  }
}

export function AICrewPanel({ derived }: AICrewPanelProps) {
  const { t } = useI18n();
  const collapsed = useMissionStore((s) => s.rightCollapsed);
  const toggleCollapsed = useMissionStore((s) => s.toggleRightCollapsed);
  const selectedNodeId = useMissionStore((s) => s.selectedNodeId);
  const setSelectedNodeId = useMissionStore((s) => s.setSelectedNodeId);

  if (collapsed) {
    return (
      <aside className="w-10 shrink-0 border-l border-slate-800 bg-[#0a101d] flex flex-col items-center py-3 gap-3">
        <button
          type="button"
          onClick={toggleCollapsed}
          className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-cyan-300"
          title={t('crew.expand')}
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
        <Users className="w-4 h-4 text-cyan-400" />
      </aside>
    );
  }

  const outcomeKey = String(derived.currentState?.mission_result?.outcome ?? '');

  return (
    <aside className="w-80 shrink-0 border-l border-slate-800 bg-[#0a101d] flex flex-col overflow-hidden">
      <div className="px-3 py-2.5 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-mono font-semibold text-slate-200">
          <Users className="w-3.5 h-3.5 text-cyan-400" />
          <span>{t('crew.title')}</span>
        </div>
        <button
          type="button"
          onClick={toggleCollapsed}
          className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-cyan-300"
          title={t('crew.collapse')}
        >
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
        {CREW_AGENTS.map((agent) => {
          const Icon = agent.icon;
          const info = derived.nodeStates[agent.id];
          const status: NodeVisualStatus = info?.status ?? 'idle';
          const isSelected = selectedNodeId === agent.id;
          const summaryText =
            info?.lastSummary === '__PLAN_REJECTED__'
              ? t('nodeDrawer.planRejectedSummary')
              : info?.lastSummary;

          return (
            <button
              key={agent.id}
              type="button"
              onClick={() => setSelectedNodeId(agent.id)}
              className={`w-full text-left rounded border p-2.5 transition ${
                isSelected
                  ? 'border-cyan-500/70 bg-cyan-500/10'
                  : 'border-slate-800 bg-[#080e1c] hover:border-slate-700'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded bg-slate-900 border border-slate-700 flex items-center justify-center text-cyan-400">
                    <Icon className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-slate-100">
                      {t(`crew.agents.${agent.id}.name`)}
                    </div>
                    <div className="text-[10px] font-mono text-slate-400">
                      {t(`crew.agents.${agent.id}.role`)}
                    </div>
                  </div>
                </div>
                <span
                  className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded border ${statusBadge(status)}`}
                >
                  {t(`nodeStatus.${status}`)}
                </span>
              </div>

              <div className="mt-2 flex items-center justify-between text-[10px] font-mono text-slate-500">
                <span>{t('crew.runs', { count: info?.runCount ?? 0 })}</span>
                <span>{info?.durationMs != null ? t('crew.ms', { value: info.durationMs }) : '—'}</span>
              </div>

              {summaryText ? (
                <p className="mt-1.5 text-[11px] text-slate-300 line-clamp-3 leading-relaxed">
                  {summaryText}
                </p>
              ) : (
                <p className="mt-1.5 text-[11px] text-slate-500 italic">
                  {t('crew.standby')}
                </p>
              )}

              {info?.error && (
                <div className="mt-1.5 text-[11px] text-red-400 font-mono truncate">
                  {info.error}
                </div>
              )}
            </button>
          );
        })}

        {derived.currentState?.mission_result && (
          <div className="rounded border border-cyan-500/40 bg-cyan-500/10 p-3 space-y-1">
            <div className="text-[11px] font-mono font-semibold text-cyan-300 uppercase">
              {t('crew.missionOutcome', { outcome: t(`outcomes.${outcomeKey}`) })}
            </div>
            <p className="text-xs text-slate-200 leading-relaxed">
              {String(derived.currentState.mission_result.reason ?? '')}
            </p>
          </div>
        )}
      </div>
    </aside>
  );
}
