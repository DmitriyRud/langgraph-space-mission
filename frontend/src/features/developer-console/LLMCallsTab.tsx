import { Cpu } from 'lucide-react';
import { useI18n } from '../../i18n';
import type { LLMCallRecord } from '../../types/mission';

interface LLMCallsTabProps {
  calls: LLMCallRecord[];
}

export function LLMCallsTab({ calls }: LLMCallsTabProps) {
  const { t } = useI18n();

  return (
    <div className="h-full overflow-y-auto p-3 space-y-2.5 font-mono text-[11px]">
      {calls.length === 0 ? (
        <div className="text-slate-500">{t('llmTab.empty')}</div>
      ) : (
        calls.map((c) => (
          <div key={c.id} className="rounded border border-slate-800 bg-[#080d18] overflow-hidden">
            <div className="px-3 py-1.5 border-b border-slate-800 bg-[#0d1526] flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Cpu className="w-3.5 h-3.5 text-cyan-400" />
                <span className="text-slate-100 font-semibold">{c.agent}</span>
                <span className="text-slate-500">
                  {t('llmTab.iterShort', { iteration: c.iteration })}
                </span>
                <span className="px-1.5 py-0.2 rounded bg-slate-800 text-cyan-300 text-[10px]">
                  {c.model}
                </span>
              </div>
              <div className="flex items-center gap-3 text-slate-400 text-[10px]">
                {c.durationMs != null && <span>{t('crew.ms', { value: c.durationMs })}</span>}
                {c.tokenUsage && (
                  <span className="text-emerald-300">
                    {t('llmTab.tokensFmt', {
                      input: c.tokenUsage.input_tokens ?? 0,
                      output: c.tokenUsage.output_tokens ?? 0,
                    })}
                  </span>
                )}
              </div>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-slate-800">
              <div className="p-2.5">
                <div className="text-[10px] text-slate-500 uppercase mb-1">
                  {t('llmTab.promptInput')}
                </div>
                <pre className="text-slate-300 whitespace-pre-wrap max-h-36 overflow-y-auto">
                  {c.userPrompt}
                </pre>
              </div>
              <div className="p-2.5">
                <div className="text-[10px] text-slate-500 uppercase mb-1">
                  {t('llmTab.structuredOutput')}
                </div>
                <pre className="text-emerald-300 whitespace-pre-wrap max-h-36 overflow-y-auto">
                  {c.structuredOutput
                    ? JSON.stringify(c.structuredOutput, null, 2)
                    : t('llmTab.awaiting')}
                </pre>
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
