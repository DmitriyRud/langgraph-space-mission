import { useRef } from 'react';
import {
  BookOpen,
  ChevronDown,
  ChevronUp,
  Cpu,
  Database,
  GitCompare,
  History,
  Terminal,
} from 'lucide-react';
import { useI18n } from '../../i18n';
import { useMissionStore } from '../../stores/missionStore';
import type { DerivedExecutionView } from '../../stores/missionStore';
import type { ConsoleTab, ExecutionEvent } from '../../types/mission';
import { CheckpointExplorerTab } from './CheckpointExplorerTab';
import { ExecutionTimelineTab } from './ExecutionTimelineTab';
import { LangGraphLearningTab } from './LangGraphLearningTab';
import { LLMCallsTab } from './LLMCallsTab';
import { StateDiffTab } from './StateDiffTab';
import { StateInspectorTab } from './StateInspectorTab';

interface DeveloperConsoleProps {
  visibleEvents: ExecutionEvent[];
  derived: DerivedExecutionView;
  onForkCheckpoint: (checkpointId: string) => void;
}

const TABS: Array<{ id: ConsoleTab; icon: typeof Terminal }> = [
  { id: 'logs', icon: Terminal },
  { id: 'state', icon: Database },
  { id: 'diff', icon: GitCompare },
  { id: 'checkpoints', icon: History },
  { id: 'llm', icon: Cpu },
  { id: 'learning', icon: BookOpen },
];

export function DeveloperConsole({
  visibleEvents,
  derived,
  onForkCheckpoint,
}: DeveloperConsoleProps) {
  const { t } = useI18n();
  const activeTab = useMissionStore((s) => s.activeConsoleTab);
  const setActiveTab = useMissionStore((s) => s.setActiveConsoleTab);
  const collapsed = useMissionStore((s) => s.consoleCollapsed);
  const toggleCollapsed = useMissionStore((s) => s.toggleConsoleCollapsed);
  const height = useMissionStore((s) => s.consoleHeight);
  const setHeight = useMissionStore((s) => s.setConsoleHeight);
  const checkpoints = useMissionStore((s) => s.checkpoints);
  const topology = useMissionStore((s) => s.topology);
  const mode = useMissionStore((s) => s.mode);
  const busy = useMissionStore((s) => s.busy);
  const setSelectedNodeId = useMissionStore((s) => s.setSelectedNodeId);

  const dragStartRef = useRef<{ y: number; h: number } | null>(null);

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    dragStartRef.current = { y: e.clientY, h: height };
    const onMove = (ev: MouseEvent) => {
      if (!dragStartRef.current) return;
      const delta = dragStartRef.current.y - ev.clientY;
      setHeight(dragStartRef.current.h + delta);
    };
    const onUp = () => {
      dragStartRef.current = null;
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  };

  return (
    <section
      className="shrink-0 border-t border-slate-800 bg-[#0a101d] flex flex-col"
      style={{ height: collapsed ? '36px' : `${height}px` }}
    >
      {!collapsed && (
        <div
          onMouseDown={handleMouseDown}
          className="h-1 cursor-row-resize bg-transparent hover:bg-cyan-500/40 transition"
          title={t('console.resizeTitle')}
        />
      )}

      <div className="h-9 shrink-0 px-3 border-b border-slate-800 flex items-center justify-between bg-[#0b1222]">
        <div className="flex items-center gap-1 overflow-x-auto">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id && !collapsed;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`px-2.5 py-1 rounded text-[11px] font-mono flex items-center gap-1.5 whitespace-nowrap transition ${
                  active
                    ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/40'
                    : 'text-slate-400 hover:text-slate-200 border border-transparent'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{t(`console.tabs.${tab.id}`)}</span>
                {tab.id === 'logs' && (
                  <span className="text-[10px] text-slate-500">({visibleEvents.length})</span>
                )}
                {tab.id === 'checkpoints' && (
                  <span className="text-[10px] text-slate-500">({checkpoints.length})</span>
                )}
                {tab.id === 'llm' && (
                  <span className="text-[10px] text-slate-500">({derived.llmCalls.length})</span>
                )}
              </button>
            );
          })}
        </div>

        <button
          type="button"
          onClick={toggleCollapsed}
          className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-cyan-300"
          title={collapsed ? t('console.expand') : t('console.collapse')}
        >
          {collapsed ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {!collapsed && (
        <div className="flex-1 min-h-0 overflow-hidden">
          {activeTab === 'logs' && (
            <ExecutionTimelineTab
              events={visibleEvents}
              onSelectNode={(nid) => setSelectedNodeId(nid)}
            />
          )}
          {activeTab === 'state' && (
            <StateInspectorTab
              currentState={derived.currentState}
              previousState={derived.previousState}
            />
          )}
          {activeTab === 'diff' && <StateDiffTab snapshots={derived.stateSnapshots} />}
          {activeTab === 'checkpoints' && (
            <CheckpointExplorerTab
              checkpoints={checkpoints}
              mode={mode}
              busy={busy}
              onForkCheckpoint={onForkCheckpoint}
            />
          )}
          {activeTab === 'llm' && <LLMCallsTab calls={derived.llmCalls} />}
          {activeTab === 'learning' && (
            <LangGraphLearningTab
              items={topology?.learning_catalog ?? []}
              onSelectNode={(nid) => setSelectedNodeId(nid)}
            />
          )}
        </div>
      )}
    </section>
  );
}
