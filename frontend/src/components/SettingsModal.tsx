import { Cpu, Globe, RefreshCw, X } from 'lucide-react';
import { useI18n } from '../i18n';
import { useMissionStore } from '../stores/missionStore';

interface SettingsModalProps {
  onRefreshHealth: () => void;
}

export function SettingsModal({ onRefreshHealth }: SettingsModalProps) {
  const { language, setLanguage, t } = useI18n();
  const open = useMissionStore((s) => s.settingsOpen);
  const setOpen = useMissionStore((s) => s.setSettingsOpen);
  const health = useMissionStore((s) => s.health);
  const mode = useMissionStore((s) => s.mode);
  const setMode = useMissionStore((s) => s.setMode);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-lg rounded-lg border border-slate-700 bg-[#0b1222] shadow-2xl">
        <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2 font-mono text-sm text-slate-100">
            <Cpu className="w-4 h-4 text-cyan-400" />
            <span>{t('settings.title')}</span>
          </div>
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="p-1 text-slate-400 hover:text-slate-100"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-4 space-y-4 text-xs">
          {/* Language Switcher */}
          <div className="rounded border border-slate-800 bg-[#080d18] p-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-mono text-slate-400 flex items-center gap-1.5">
                <Globe className="w-3.5 h-3.5 text-cyan-400" />
                {t('settings.languageSection')}
              </span>
              <div className="flex gap-1.5 font-mono">
                <button
                  type="button"
                  onClick={() => setLanguage('en')}
                  className={`px-2.5 py-1 rounded border transition ${
                    language === 'en'
                      ? 'border-cyan-500/50 bg-cyan-500/20 text-cyan-300'
                      : 'border-slate-700 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  English
                </button>
                <button
                  type="button"
                  onClick={() => setLanguage('ru')}
                  className={`px-2.5 py-1 rounded border transition ${
                    language === 'ru'
                      ? 'border-cyan-500/50 bg-cyan-500/20 text-cyan-300'
                      : 'border-slate-700 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Русский
                </button>
              </div>
            </div>
            <p className="text-slate-400 leading-relaxed">{t('settings.languageHint')}</p>
          </div>

          {/* Execution Mode */}
          <div className="rounded border border-slate-800 bg-[#080d18] p-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-mono text-slate-400">{t('settings.executionMode')}</span>
              <div className="flex gap-1.5 font-mono">
                <button
                  type="button"
                  onClick={() => setMode('demo')}
                  className={`px-2.5 py-1 rounded border ${
                    mode === 'demo'
                      ? 'border-cyan-500/50 bg-cyan-500/20 text-cyan-300'
                      : 'border-slate-700 text-slate-400'
                  }`}
                >
                  {t('settings.demoMode')}
                </button>
                <button
                  type="button"
                  onClick={() => setMode('live')}
                  className={`px-2.5 py-1 rounded border ${
                    mode === 'live'
                      ? 'border-emerald-500/50 bg-emerald-500/20 text-emerald-300'
                      : 'border-slate-700 text-slate-400'
                  }`}
                >
                  {t('settings.liveMode')}
                </button>
              </div>
            </div>
            <p className="text-slate-400 leading-relaxed">{t('settings.modeDescription')}</p>
          </div>

          {/* Local LLM Status */}
          <div className="rounded border border-slate-800 bg-[#080d18] p-3 space-y-2 font-mono">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">{t('settings.localLlmStatus')}</span>
              <button
                type="button"
                onClick={onRefreshHealth}
                className="flex items-center gap-1 text-cyan-400 hover:text-cyan-300"
              >
                <RefreshCw className="w-3 h-3" />
                <span>{t('settings.refresh')}</span>
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div className="text-slate-400">{t('settings.provider')}</div>
              <div className="text-slate-200">{health?.llm.provider ?? 'ollama'}</div>
              <div className="text-slate-400">{t('settings.endpoint')}</div>
              <div className="text-slate-200 truncate">{health?.llm.base_url ?? 'http://localhost:11434'}</div>
              <div className="text-slate-400">{t('settings.activeModel')}</div>
              <div className="text-cyan-300">{health?.llm.active_model ?? 'qwen3:4b'}</div>
              <div className="text-slate-400">{t('settings.connected')}</div>
              <div className={health?.llm.connected ? 'text-emerald-400' : 'text-red-400'}>
                {health?.llm.connected ? t('settings.online') : t('settings.offline')}
              </div>
            </div>
            {health?.llm.error && (
              <div className="mt-2 p-2 rounded border border-amber-500/40 bg-amber-500/10 text-amber-300 text-[11px]">
                {health.llm.error}
              </div>
            )}
            <div className="pt-2 text-[11px] text-slate-400 border-t border-slate-800">
              {(() => {
                const sys = health?.system;
                const hardware = sys
                  ? sys.ram_gb
                    ? `${sys.cpu} (${sys.ram_gb} GB RAM)`
                    : sys.cpu
                  : t('settings.hardwareFallback');
                const models = sys?.recommended_models?.length
                  ? sys.recommended_models
                  : ['qwen3:4b', 'qwen3:8b'];
                const commands = models.map((m) => `ollama pull ${m}`).join(' / ');
                return t('settings.recommendedHint', { hardware, commands });
              })()}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
