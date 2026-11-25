import {
  Download,
  History,
  Play,
  RotateCcw,
  Shuffle,
  SkipBack,
  SkipForward,
  SlidersHorizontal,
} from 'lucide-react';
import { useI18n } from '../i18n';
import { useMissionStore } from '../stores/missionStore';
import type { DerivedExecutionView } from '../stores/missionStore';

interface MissionControlBarProps {
  derived: DerivedExecutionView;
  onStartMission: () => void;
  onRandomScenario: () => void;
  onResetMission: () => void;
  onRestoreMission: (missionId: string) => void;
  onExportJson: () => void;
}

export function MissionControlBar({
  derived,
  onStartMission,
  onRandomScenario,
  onResetMission,
  onRestoreMission,
  onExportJson,
}: MissionControlBarProps) {
  const { t } = useI18n();
  const scenarios = useMissionStore((s) => s.scenarios);
  const selectedScenarioId = useMissionStore((s) => s.selectedScenarioId);
  const setSelectedScenarioId = useMissionStore((s) => s.setSelectedScenarioId);
  const missions = useMissionStore((s) => s.missions);
  const activeMission = useMissionStore((s) => s.activeMission);
  const viewMode = useMissionStore((s) => s.viewMode);
  const setViewMode = useMissionStore((s) => s.setViewMode);
  const events = useMissionStore((s) => s.events);
  const replayIndex = useMissionStore((s) => s.replayIndex);
  const setReplayIndex = useMissionStore((s) => s.setReplayIndex);
  const busy = useMissionStore((s) => s.busy);
  const setActiveConsoleTab = useMissionStore((s) => s.setActiveConsoleTab);

  return (
    <div className="shrink-0 border-b border-slate-800 bg-[#0b1222] px-4 py-2 flex flex-wrap items-center justify-between gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={selectedScenarioId}
          onChange={(e) => setSelectedScenarioId(e.target.value)}
          className="h-8 rounded border border-slate-700 bg-[#0f172a] px-2.5 text-xs font-mono text-slate-200 focus:border-cyan-500 focus:outline-none"
        >
          {scenarios.map((s) => (
            <option key={s.id} value={s.id}>
              {s.title} ({t(`severity.${s.severity}`)})
            </option>
          ))}
        </select>

        <button
          type="button"
          onClick={onRandomScenario}
          className="h-8 px-2.5 rounded border border-slate-700 bg-[#0f172a] hover:border-cyan-500/50 text-xs font-mono text-slate-300 hover:text-cyan-300 flex items-center gap-1.5 transition"
          title={t('controlBar.randomTitle')}
        >
          <Shuffle className="w-3.5 h-3.5" />
          <span>{t('controlBar.random')}</span>
        </button>

        <button
          type="button"
          disabled={busy}
          onClick={onStartMission}
          className="h-8 px-3.5 rounded bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-slate-950 font-semibold text-xs font-mono flex items-center gap-1.5 transition"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          <span>{t('controlBar.startMission')}</span>
        </button>

        <button
          type="button"
          onClick={onResetMission}
          className="h-8 px-2.5 rounded border border-slate-700 bg-[#0f172a] hover:border-slate-600 text-xs font-mono text-slate-300 flex items-center gap-1.5 transition"
          title={t('controlBar.resetTitle')}
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>{t('controlBar.reset')}</span>
        </button>

        {missions.length > 0 && (
          <select
            value={activeMission?.mission_id ?? ''}
            onChange={(e) => {
              if (e.target.value) onRestoreMission(e.target.value);
            }}
            className="h-8 max-w-[240px] rounded border border-slate-700 bg-[#0f172a] px-2 text-xs font-mono text-slate-300 focus:border-cyan-500 focus:outline-none"
            title={t('controlBar.restoreTitle')}
          >
            <option value="">{t('controlBar.restoreMission', { count: missions.length })}</option>
            {missions.map((m) => (
              <option key={m.mission_id} value={m.mission_id}>
                {m.mission_id} • {m.scenario_id} [{t(`missionDbStatus.${m.status}`)}]
                {m.parent_checkpoint_id ? ' (fork)' : ''}
              </option>
            ))}
          </select>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center rounded border border-slate-700 bg-[#070b14] p-0.5 text-[11px] font-mono">
          <button
            type="button"
            onClick={() => setViewMode('live')}
            className={`px-2 py-1 rounded transition ${
              viewMode === 'live'
                ? 'bg-cyan-500/20 text-cyan-300'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {t('controlBar.live')}
          </button>
          <button
            type="button"
            disabled={events.length === 0}
            onClick={() => setViewMode('replay')}
            className={`px-2 py-1 rounded transition disabled:opacity-40 ${
              viewMode === 'replay'
                ? 'bg-purple-500/25 text-purple-300'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {t('controlBar.replay', { count: events.length })}
          </button>
        </div>

        {viewMode === 'replay' && events.length > 0 && (
          <div className="flex items-center gap-1.5 px-2 py-1 rounded border border-purple-500/40 bg-purple-500/10 text-xs font-mono text-purple-200">
            <button
              type="button"
              onClick={() => setReplayIndex(Math.max(0, replayIndex - 1))}
              className="p-0.5 hover:text-white"
              title={t('controlBar.prevEvent')}
            >
              <SkipBack className="w-3.5 h-3.5" />
            </button>
            <input
              type="range"
              min={0}
              max={Math.max(0, events.length - 1)}
              value={replayIndex}
              onChange={(e) => setReplayIndex(Number(e.target.value))}
              className="w-24 accent-purple-400"
            />
            <button
              type="button"
              onClick={() => setReplayIndex(Math.min(events.length - 1, replayIndex + 1))}
              className="p-0.5 hover:text-white"
              title={t('controlBar.nextEvent')}
            >
              <SkipForward className="w-3.5 h-3.5" />
            </button>
            <span className="text-[11px] min-w-[46px] text-right">
              {replayIndex + 1}/{events.length}
            </span>
          </div>
        )}

        <button
          type="button"
          onClick={() => setActiveConsoleTab('checkpoints')}
          className="h-8 px-2.5 rounded border border-slate-700 bg-[#0f172a] hover:border-cyan-500/50 text-xs font-mono text-slate-300 hover:text-cyan-300 flex items-center gap-1.5 transition"
        >
          <History className="w-3.5 h-3.5" />
          <span>{t('controlBar.checkpoints')}</span>
        </button>

        <button
          type="button"
          disabled={!activeMission}
          onClick={onExportJson}
          className="h-8 px-2.5 rounded border border-slate-700 bg-[#0f172a] hover:border-cyan-500/50 disabled:opacity-40 text-xs font-mono text-slate-300 hover:text-cyan-300 flex items-center gap-1.5 transition"
        >
          <Download className="w-3.5 h-3.5" />
          <span>{t('controlBar.exportJson')}</span>
        </button>

        <div className="hidden xl:flex items-center gap-1.5 px-2 py-1 rounded bg-slate-900 border border-slate-800 text-[11px] font-mono text-slate-400">
          <SlidersHorizontal className="w-3 h-3 text-cyan-400" />
          <span>
            {t('controlBar.iter', {
              current: derived.currentIteration,
              max: derived.currentState?.max_iterations ?? 5,
            })}
          </span>
        </div>
      </div>
    </div>
  );
}
