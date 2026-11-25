import { useMemo, useState } from 'react';
import { Check, ChevronDown, ChevronRight, Code2, Copy, Search } from 'lucide-react';
import { useI18n } from '../../i18n';
import type { MissionState } from '../../types/mission';

interface StateInspectorTabProps {
  currentState: Partial<MissionState> | null;
  previousState: Partial<MissionState> | null;
}

interface TreeNodeProps {
  name: string;
  value: unknown;
  changedKeys: Set<string>;
  search: string;
  updatedBadge: string;
  depth?: number;
}

function JsonTreeNode({ name, value, changedKeys, search, updatedBadge, depth = 0 }: TreeNodeProps) {
  const [expanded, setExpanded] = useState(depth < 1 || name === 'ship_state' || name === 'current_plan');
  const isObject = value !== null && typeof value === 'object';
  const isChanged = depth === 0 && changedKeys.has(name);
  const matchesSearch =
    search.trim() !== '' && name.toLowerCase().includes(search.trim().toLowerCase());

  if (!isObject) {
    return (
      <div
        className={`flex items-baseline gap-2 py-0.5 px-1 rounded ${
          isChanged ? 'bg-cyan-500/15' : matchesSearch ? 'bg-amber-500/15' : ''
        }`}
        style={{ paddingLeft: `${depth * 14 + 6}px` }}
      >
        <span className="text-cyan-300">{name}:</span>
        <span className="text-emerald-300 break-all">{JSON.stringify(value)}</span>
        {isChanged && (
          <span className="text-[9px] px-1 rounded bg-cyan-500/25 text-cyan-200">{updatedBadge}</span>
        )}
      </div>
    );
  }

  const entries = Array.isArray(value)
    ? value.map((v, idx) => [String(idx), v] as const)
    : Object.entries(value as Record<string, unknown>);

  return (
    <div>
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className={`w-full text-left flex items-center gap-1.5 py-0.5 px-1 rounded hover:bg-slate-800/60 ${
          isChanged ? 'bg-cyan-500/15' : matchesSearch ? 'bg-amber-500/15' : ''
        }`}
        style={{ paddingLeft: `${depth * 14 + 4}px` }}
      >
        {expanded ? (
          <ChevronDown className="w-3 h-3 text-slate-500 shrink-0" />
        ) : (
          <ChevronRight className="w-3 h-3 text-slate-500 shrink-0" />
        )}
        <span className="text-cyan-300">{name}</span>
        <span className="text-slate-500 text-[10px]">
          {Array.isArray(value) ? `[${entries.length}]` : `{${entries.length}}`}
        </span>
        {isChanged && (
          <span className="text-[9px] px-1 rounded bg-cyan-500/25 text-cyan-200">{updatedBadge}</span>
        )}
      </button>
      {expanded &&
        entries.map(([k, v]) => (
          <JsonTreeNode
            key={k}
            name={k}
            value={v}
            changedKeys={changedKeys}
            search={search}
            updatedBadge={updatedBadge}
            depth={depth + 1}
          />
        ))}
    </div>
  );
}

export function StateInspectorTab({ currentState, previousState }: StateInspectorTabProps) {
  const { t } = useI18n();
  const [search, setSearch] = useState('');
  const [rawMode, setRawMode] = useState(false);
  const [copied, setCopied] = useState(false);

  const changedKeys = useMemo(() => {
    const changed = new Set<string>();
    if (!currentState || !previousState) return changed;
    for (const key of Object.keys(currentState)) {
      const a = JSON.stringify((currentState as Record<string, unknown>)[key]);
      const b = JSON.stringify((previousState as Record<string, unknown>)[key]);
      if (a !== b) changed.add(key);
    }
    return changed;
  }, [currentState, previousState]);

  const filteredEntries = useMemo(() => {
    if (!currentState) return [];
    const entries = Object.entries(currentState);
    if (!search.trim()) return entries;
    const q = search.trim().toLowerCase();
    return entries.filter(
      ([k, v]) =>
        k.toLowerCase().includes(q) || JSON.stringify(v).toLowerCase().includes(q)
    );
  }, [currentState, search]);

  const handleCopy = async () => {
    if (!currentState) return;
    await navigator.clipboard.writeText(JSON.stringify(currentState, null, 2));
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="h-full flex flex-col">
      <div className="px-3 py-1.5 border-b border-slate-800/80 flex items-center gap-2 text-[11px] font-mono bg-[#090f1d]">
        <div className="relative flex-1 max-w-xs">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2 top-1.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('stateTab.searchPlaceholder')}
            className="w-full pl-7 pr-2 py-0.5 rounded bg-[#0f172a] border border-slate-700 text-slate-200 focus:border-cyan-500 focus:outline-none"
          />
        </div>
        <button
          type="button"
          onClick={() => setRawMode(!rawMode)}
          className={`px-2 py-0.5 rounded border flex items-center gap-1 ${
            rawMode
              ? 'border-cyan-500/50 bg-cyan-500/15 text-cyan-300'
              : 'border-slate-700 text-slate-400 hover:text-slate-200'
          }`}
        >
          <Code2 className="w-3 h-3" />
          <span>{rawMode ? t('stateTab.rawJson') : t('stateTab.treeView')}</span>
        </button>
        <button
          type="button"
          onClick={() => void handleCopy()}
          className="px-2 py-0.5 rounded border border-slate-700 text-slate-300 hover:border-cyan-500/50 flex items-center gap-1"
        >
          {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
          <span>{copied ? t('stateTab.copied') : t('stateTab.copyJson')}</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 font-mono text-[11px]">
        {!currentState ? (
          <div className="text-slate-500">{t('stateTab.empty')}</div>
        ) : rawMode ? (
          <pre className="text-slate-300 whitespace-pre-wrap">
            {JSON.stringify(currentState, null, 2)}
          </pre>
        ) : (
          <div className="space-y-0.5">
            {filteredEntries.map(([key, val]) => (
              <JsonTreeNode
                key={key}
                name={key}
                value={val}
                changedKeys={changedKeys}
                search={search}
                updatedBadge={t('stateTab.updatedBadge')}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
