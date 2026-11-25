import { BookOpen, Clock, Cpu, X } from 'lucide-react';
import { useI18n } from '../../i18n';
import { useMissionStore } from '../../stores/missionStore';
import type { DerivedExecutionView } from '../../stores/missionStore';
import type { NodeVisualStatus } from '../../types/mission';

interface NodeInspectorDrawerProps {
  derived: DerivedExecutionView;
}

export function NodeInspectorDrawer({ derived }: NodeInspectorDrawerProps) {
  const { t } = useI18n();
  const selectedNodeId = useMissionStore((s) => s.selectedNodeId);
  const setSelectedNodeId = useMissionStore((s) => s.setSelectedNodeId);
  const topology = useMissionStore((s) => s.topology);

  if (!selectedNodeId || !topology) return null;

  const meta = topology.nodes.find((n) => n.id === selectedNodeId);
  const runtime = derived.nodeStates[selectedNodeId];
  if (!meta) return null;

  const st: NodeVisualStatus = runtime?.status ?? 'idle';

  return (
    <div className="absolute top-10 right-3 bottom-3 w-96 max-w-[90%] z-30 rounded-lg border border-slate-700 bg-[#0b1222]/96 backdrop-blur-md shadow-2xl flex flex-col overflow-hidden">
      <div className="px-3.5 py-2.5 border-b border-slate-800 flex items-center justify-between bg-[#0f172a]">
        <div>
          <div className="text-xs font-semibold text-slate-100 flex items-center gap-2">
            <span>{meta.label}</span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-cyan-300">
              {meta.id}
            </span>
          </div>
          <div className="text-[11px] text-slate-400">{meta.role}</div>
        </div>
        <button
          type="button"
          onClick={() => setSelectedNodeId(null)}
          className="p-1 text-slate-400 hover:text-slate-100"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3.5 space-y-3 text-xs">
        <p className="text-slate-300 leading-relaxed">{meta.description}</p>

        <div className="rounded border border-cyan-500/30 bg-cyan-500/10 p-2.5 space-y-1">
          <div className="flex items-center gap-1.5 text-[10px] font-mono uppercase text-cyan-300 font-semibold">
            <BookOpen className="w-3 h-3" />
            <span>{t('nodeDrawer.mechanism')}</span>
          </div>
          <div className="text-[11px] text-cyan-100 font-mono">{meta.langgraph_mechanism}</div>
        </div>

        <div className="grid grid-cols-2 gap-2 font-mono text-[11px] rounded border border-slate-800 bg-[#080d18] p-2.5">
          <div>
            <span className="text-slate-500 block">{t('nodeDrawer.status')}</span>
            <span className="text-slate-200 uppercase">{t(`nodeStatus.${st}`)}</span>
          </div>
          <div>
            <span className="text-slate-500 block">{t('nodeDrawer.iterationRuns')}</span>
            <span className="text-slate-200">
              {t('nodeDrawer.iterValue', {
                iteration: runtime?.iteration ?? 0,
                runs: runtime?.runCount ?? 0,
              })}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block flex items-center gap-1">
              <Clock className="w-3 h-3" /> {t('nodeDrawer.duration')}
            </span>
            <span className="text-slate-200">
              {runtime?.durationMs != null ? t('crew.ms', { value: runtime.durationMs }) : '—'}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block">{t('nodeDrawer.attempts')}</span>
            <span className="text-slate-200">{runtime?.attempts ?? 0}</span>
          </div>
          {runtime?.modelUsed && (
            <div className="col-span-2 pt-1 border-t border-slate-800 flex items-center justify-between">
              <span className="text-slate-500 flex items-center gap-1">
                <Cpu className="w-3 h-3" /> {t('nodeDrawer.model')}
              </span>
              <span className="text-cyan-300">{runtime.modelUsed}</span>
            </div>
          )}
          {runtime?.tokenUsage && (
            <div className="col-span-2 flex items-center justify-between text-emerald-300">
              <span className="text-slate-500">{t('nodeDrawer.tokenUsage')}</span>
              <span>
                {t('nodeDrawer.tokensFmt', {
                  input: runtime.tokenUsage.input_tokens ?? 0,
                  output: runtime.tokenUsage.output_tokens ?? 0,
                })}
              </span>
            </div>
          )}
        </div>

        {runtime?.error && (
          <div className="rounded border border-red-500/40 bg-red-500/10 p-2.5 text-red-300 font-mono text-[11px]">
            {t('nodeDrawer.errorPrefix', { error: runtime.error })}
          </div>
        )}

        {meta.system_prompt && (
          <div>
            <div className="text-[10px] font-mono uppercase text-slate-400 mb-1">
              {t('nodeDrawer.systemPrompt')}
            </div>
            <pre className="p-2 rounded border border-slate-800 bg-[#070b14] text-[11px] text-slate-300 whitespace-pre-wrap font-mono max-h-32 overflow-y-auto">
              {meta.system_prompt}
            </pre>
          </div>
        )}

        {runtime?.llmInput && (
          <div>
            <div className="text-[10px] font-mono uppercase text-slate-400 mb-1">
              {t('nodeDrawer.llmInput')}
            </div>
            <pre className="p-2 rounded border border-slate-800 bg-[#070b14] text-[11px] text-slate-300 whitespace-pre-wrap font-mono max-h-36 overflow-y-auto">
              {runtime.llmInput}
            </pre>
          </div>
        )}

        {runtime?.llmOutput && (
          <div>
            <div className="text-[10px] font-mono uppercase text-slate-400 mb-1">
              {t('nodeDrawer.structuredOutput')}
            </div>
            <pre className="p-2 rounded border border-slate-800 bg-[#070b14] text-[11px] text-emerald-300 whitespace-pre-wrap font-mono max-h-44 overflow-y-auto">
              {JSON.stringify(runtime.llmOutput, null, 2)}
            </pre>
          </div>
        )}

        {runtime?.partialUpdate && (
          <div>
            <div className="text-[10px] font-mono uppercase text-slate-400 mb-1">
              {t('nodeDrawer.partialUpdate')}
            </div>
            <pre className="p-2 rounded border border-slate-800 bg-[#070b14] text-[11px] text-cyan-200 whitespace-pre-wrap font-mono max-h-44 overflow-y-auto">
              {JSON.stringify(runtime.partialUpdate, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
