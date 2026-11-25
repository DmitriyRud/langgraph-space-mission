import { Activity, Cpu, Radio, Settings, ShieldAlert, Wifi, WifiOff } from 'lucide-react';
import { useI18n } from '../i18n';
import { useMissionStore } from '../stores/missionStore';
import type { DerivedExecutionView } from '../stores/missionStore';

interface HeaderProps {
  derived: DerivedExecutionView;
}

export function Header({ derived }: HeaderProps) {
  const { t } = useI18n();
  const health = useMissionStore((s) => s.health);
  const mode = useMissionStore((s) => s.mode);
  const setMode = useMissionStore((s) => s.setMode);
  const sseConnected = useMissionStore((s) => s.sseConnected);
  const setSettingsOpen = useMissionStore((s) => s.setSettingsOpen);
  const activeMission = useMissionStore((s) => s.activeMission);

  const missionStatus =
    derived.currentState?.mission_status ??
    derived.currentState?.ship_state?.mission_status ??
    'Operational';

  const statusLabel = t(`missionStatus.${missionStatus}`);

  const statusColor =
    missionStatus === 'Stabilized' || missionStatus === 'Operational'
      ? 'text-emerald-400 border-emerald-500/40 bg-emerald-500/10'
      : missionStatus === 'Failed' || missionStatus === 'Critical'
        ? 'text-red-400 border-red-500/40 bg-red-500/10'
        : 'text-amber-400 border-amber-500/40 bg-amber-500/10';

  const llmConnected = health?.llm.connected ?? false;
  const modelName =
    mode === 'demo'
      ? 'demo-deterministic'
      : (health?.llm.active_model ?? 'qwen3:4b');

  return (
    <header className="h-13 shrink-0 border-b border-slate-800 bg-[#0a101d] px-4 flex items-center justify-between gap-4">
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded bg-cyan-500/15 border border-cyan-500/40 flex items-center justify-center text-cyan-400">
            <Radio className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm tracking-wide text-slate-100">
                AI SPACE MISSION
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-cyan-300 border border-slate-700">
                AURORA-7
              </span>
            </div>
            <div className="text-[11px] text-slate-400 font-mono truncate">
              {t('header.subtitle')}
              {activeMission ? ` • ${activeMission.mission_id}` : ''}
            </div>
          </div>
        </div>

        <div className={`ml-2 px-2.5 py-0.5 rounded border text-xs font-mono flex items-center gap-1.5 ${statusColor}`}>
          <Activity className="w-3.5 h-3.5" />
          <span>{statusLabel.toUpperCase()}</span>
        </div>

        {derived.pendingInterrupt && (
          <div className="px-2.5 py-0.5 rounded border border-amber-500/50 bg-amber-500/15 text-amber-300 text-xs font-mono flex items-center gap-1.5 animate-pulse">
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>{t('header.awaitingApproval')}</span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center rounded border border-slate-800 bg-[#070b14] p-0.5 text-xs font-mono">
          <button
            type="button"
            onClick={() => setMode('demo')}
            className={`px-2.5 py-1 rounded transition ${
              mode === 'demo'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {t('header.demoMode')}
          </button>
          <button
            type="button"
            onClick={() => setMode('live')}
            className={`px-2.5 py-1 rounded transition ${
              mode === 'live'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {t('header.liveLlm')}
          </button>
        </div>

        <div
          className="hidden md:flex items-center gap-2 px-2.5 py-1 rounded border border-slate-800 bg-[#0d1526] text-xs font-mono"
          title={health?.llm.error ?? t('header.connectedTo', { provider: health?.llm.provider ?? 'ollama' })}
        >
          <Cpu className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-300">{modelName}</span>
          <span
            className={`w-2 h-2 rounded-full ${
              mode === 'demo'
                ? 'bg-cyan-400'
                : llmConnected
                  ? 'bg-emerald-400'
                  : 'bg-red-400'
            }`}
          />
        </div>

        <div
          className={`hidden lg:flex items-center gap-1.5 px-2 py-1 rounded border text-[11px] font-mono ${
            sseConnected
              ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
              : 'border-slate-800 bg-slate-900/60 text-slate-500'
          }`}
          title={t('header.sseTitle')}
        >
          {sseConnected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
          <span>{sseConnected ? t('header.sseLive') : t('header.sseIdle')}</span>
        </div>

        <button
          type="button"
          onClick={() => setSettingsOpen(true)}
          className="p-2 rounded border border-slate-800 bg-[#0d1526] hover:border-slate-700 text-slate-300 hover:text-cyan-300 transition"
          title={t('header.settingsTitle')}
        >
          <Settings className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}
