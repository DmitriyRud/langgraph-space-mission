import { useState } from 'react';
import { AlertTriangle, GitFork, History } from 'lucide-react';
import { useI18n } from '../../i18n';
import type { CheckpointSnapshot, MissionMode } from '../../types/mission';

interface CheckpointExplorerTabProps {
  checkpoints: CheckpointSnapshot[];
  mode: MissionMode;
  busy: boolean;
  onForkCheckpoint: (checkpointId: string) => void;
}

export function CheckpointExplorerTab({
  checkpoints,
  mode,
  busy,
  onForkCheckpoint,
}: CheckpointExplorerTabProps) {
  const { t } = useI18n();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [compareId, setCompareId] = useState<string | null>(null);

  const selected =
    checkpoints.find((c) => c.checkpoint_id === selectedId) ?? checkpoints[0] ?? null;
  const compared = checkpoints.find((c) => c.checkpoint_id === compareId) ?? null;

  return (
    <div className="h-full flex divide-x divide-slate-800 overflow-hidden font-mono text-[11px]">
      <div className="w-80 shrink-0 flex flex-col overflow-hidden bg-[#080e1c]">
        <div className="px-3 py-1.5 border-b border-slate-800 flex items-center justify-between text-slate-400">
          <span className="flex items-center gap-1.5">
            <History className="w-3.5 h-3.5 text-cyan-400" />
            {t('checkpointsTab.listTitle', { count: checkpoints.length })}
          </span>
        </div>
        <div className="flex-1 overflow-y-auto divide-y divide-slate-800/70">
          {checkpoints.length === 0 ? (
            <div className="p-3 text-slate-500">{t('checkpointsTab.emptyList')}</div>
          ) : (
            checkpoints.map((c, idx) => {
              const cid = c.checkpoint_id ?? `ckpt-${idx}`;
              const isSelected = selected?.checkpoint_id === c.checkpoint_id;
              const writerNode = c.writes ? Object.keys(c.writes)[0] : c.source;
              return (
                <button
                  key={cid}
                  type="button"
                  onClick={() => setSelectedId(c.checkpoint_id)}
                  className={`w-full text-left px-3 py-2 transition ${
                    isSelected ? 'bg-cyan-500/15 border-l-2 border-cyan-400' : 'hover:bg-slate-900/70'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-slate-200 font-semibold">
                      {t('checkpointsTab.stepRow', {
                        step: c.step ?? '?',
                        writer: writerNode ?? 'checkpoint',
                      })}
                    </span>
                    <span className="text-[10px] text-slate-500">
                      {t('checkpointsTab.iterShort', { iteration: c.values.iteration ?? 1 })}
                    </span>
                  </div>
                  <div className="text-[10px] text-slate-500 truncate mt-0.5">
                    id: {cid}
                  </div>
                  {c.next.length > 0 && (
                    <div className="text-[10px] text-amber-300 mt-0.5">
                      {t('checkpointsTab.next', { nodes: c.next.join(', ') })}
                    </div>
                  )}
                </button>
              );
            })
          )}
        </div>
      </div>

      <div className="flex-1 flex flex-col overflow-hidden bg-[#070b14]">
        {!selected ? (
          <div className="p-4 text-slate-500">{t('checkpointsTab.selectPrompt')}</div>
        ) : (
          <>
            <div className="px-3 py-2 border-b border-slate-800 bg-[#0a101d] flex flex-wrap items-center justify-between gap-2">
              <div className="text-slate-300">
                {t('checkpointsTab.inspecting')}{' '}
                <span className="text-cyan-300">{selected.checkpoint_id}</span>
                {selected.parent_checkpoint_id && (
                  <span className="text-slate-500 ml-2">
                    {t('checkpointsTab.parent', { id: selected.parent_checkpoint_id.slice(0, 10) })}
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2">
                <select
                  value={compareId ?? ''}
                  onChange={(e) => setCompareId(e.target.value || null)}
                  className="bg-[#0f172a] border border-slate-700 rounded px-2 py-1 text-slate-300"
                >
                  <option value="">{t('checkpointsTab.comparePlaceholder')}</option>
                  {checkpoints
                    .filter((c) => c.checkpoint_id !== selected.checkpoint_id)
                    .map((c) => (
                      <option key={c.checkpoint_id} value={c.checkpoint_id ?? ''}>
                        {t('checkpointsTab.compareOption', {
                          step: c.step ?? '?',
                          id: c.checkpoint_id?.slice(0, 8) ?? '',
                        })}
                      </option>
                    ))}
                </select>

                <button
                  type="button"
                  disabled={busy || !selected.checkpoint_id}
                  onClick={() => selected.checkpoint_id && onForkCheckpoint(selected.checkpoint_id)}
                  className="px-2.5 py-1 rounded bg-purple-500/25 hover:bg-purple-500/35 border border-purple-400/50 text-purple-200 flex items-center gap-1.5 transition disabled:opacity-50"
                >
                  <GitFork className="w-3.5 h-3.5" />
                  <span>{t('checkpointsTab.forkButton')}</span>
                </button>
              </div>
            </div>

            {mode === 'live' && (
              <div className="px-3 py-1.5 bg-amber-500/10 border-b border-amber-500/30 text-amber-300 flex items-center gap-2 text-[10px]">
                <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                <span>{t('checkpointsTab.liveWarning')}</span>
              </div>
            )}

            <div className="flex-1 overflow-y-auto p-3 grid grid-cols-1 lg:grid-cols-2 gap-3">
              <div>
                <div className="text-[10px] uppercase text-cyan-400 mb-1">
                  {t('checkpointsTab.selectedStateTitle', { step: selected.step ?? '?' })}
                </div>
                <pre className="p-2 rounded border border-slate-800 bg-[#090f1d] text-slate-300 whitespace-pre-wrap">
                  {JSON.stringify(selected.values, null, 2)}
                </pre>
              </div>

              {compared && (
                <div>
                  <div className="text-[10px] uppercase text-purple-300 mb-1">
                    {t('checkpointsTab.comparedStateTitle', { step: compared.step ?? '?' })}
                  </div>
                  <pre className="p-2 rounded border border-slate-800 bg-[#090f1d] text-slate-300 whitespace-pre-wrap">
                    {JSON.stringify(compared.values, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
