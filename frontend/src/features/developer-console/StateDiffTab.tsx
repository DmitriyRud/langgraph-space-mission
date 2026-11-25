import { useMemo, useState } from 'react';
import { useI18n } from '../../i18n';
import type { DerivedExecutionView } from '../../stores/missionStore';

interface StateDiffTabProps {
  snapshots: DerivedExecutionView['stateSnapshots'];
}

export function StateDiffTab({ snapshots }: StateDiffTabProps) {
  const { t } = useI18n();
  const [selectedIdx, setSelectedIdx] = useState<number>(-1);
  const effectiveIdx =
    selectedIdx >= 0 && selectedIdx < snapshots.length
      ? selectedIdx
      : Math.max(0, snapshots.length - 1);

  const afterSnap = snapshots[effectiveIdx] ?? null;
  const beforeSnap = effectiveIdx > 0 ? snapshots[effectiveIdx - 1] : null;

  const diffs = useMemo(() => {
    if (!afterSnap) return [];
    const beforeObj = (beforeSnap?.state ?? {}) as Record<string, unknown>;
    const afterObj = afterSnap.state as Record<string, unknown>;
    const keys = Array.from(new Set([...Object.keys(beforeObj), ...Object.keys(afterObj)]));

    return keys
      .map((key) => {
        const beforeStr = JSON.stringify(beforeObj[key], null, 2);
        const afterStr = JSON.stringify(afterObj[key], null, 2);
        if (beforeStr === afterStr) return null;
        return { key, beforeStr: beforeStr ?? 'undefined', afterStr: afterStr ?? 'undefined' };
      })
      .filter(Boolean) as Array<{ key: string; beforeStr: string; afterStr: string }>;
  }, [beforeSnap, afterSnap]);

  return (
    <div className="h-full flex flex-col">
      <div className="px-3 py-1.5 border-b border-slate-800/80 flex items-center gap-2 text-[11px] font-mono bg-[#090f1d]">
        <span className="text-slate-400">{t('diffTab.label')}</span>
        <select
          value={effectiveIdx}
          onChange={(e) => setSelectedIdx(Number(e.target.value))}
          className="bg-[#0f172a] border border-slate-700 rounded px-2 py-0.5 text-slate-200"
        >
          {snapshots.map((s, idx) => (
            <option key={s.eventId} value={idx}>
              {t('diffTab.stepOption', {
                step: idx + 1,
                iteration: s.iteration,
                node: s.nodeId ?? t('diffTab.initNode'),
              })}
            </option>
          ))}
        </select>
        <span className="ml-auto text-cyan-300">
          {t('diffTab.changedCount', { count: diffs.length })}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2.5 font-mono text-[11px]">
        {snapshots.length === 0 ? (
          <div className="text-slate-500">{t('diffTab.empty')}</div>
        ) : diffs.length === 0 ? (
          <div className="text-slate-500">{t('diffTab.noChanges')}</div>
        ) : (
          diffs.map((d) => (
            <div key={d.key} className="rounded border border-slate-800 bg-[#080d18] overflow-hidden">
              <div className="px-2.5 py-1 border-b border-slate-800 bg-slate-900/70 text-cyan-300 font-semibold">
                {d.key}
              </div>
              <div className="grid grid-cols-2 divide-x divide-slate-800">
                <pre className="p-2 text-red-300/80 bg-red-950/10 whitespace-pre-wrap max-h-40 overflow-y-auto">
                  {d.beforeStr}
                </pre>
                <pre className="p-2 text-emerald-300 bg-emerald-950/10 whitespace-pre-wrap max-h-40 overflow-y-auto">
                  {d.afterStr}
                </pre>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
