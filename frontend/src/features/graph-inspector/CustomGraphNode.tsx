import { Handle, Position, type NodeProps } from '@xyflow/react';
import {
  AlertOctagon,
  CheckCircle2,
  Compass,
  Cpu,
  Flag,
  FlaskConical,
  Hand,
  HeartPulse,
  Layers,
  PlayCircle,
  RefreshCw,
  ShieldCheck,
  Wrench,
} from 'lucide-react';
import { useI18n } from '../../i18n';
import type { NodeVisualStatus } from '../../types/mission';

export interface CustomNodeData extends Record<string, unknown> {
  nodeId: string;
  label: string;
  role: string;
  category: string;
  status: NodeVisualStatus;
  runCount: number;
  durationMs: number | null;
  isParallelActive: boolean;
  selected: boolean;
}

const STATUS_STYLES: Record<
  NodeVisualStatus,
  { border: string; bg: string; dot: string; text: string }
> = {
  idle: {
    border: 'border-slate-700',
    bg: 'bg-[#0e1628]',
    dot: 'bg-slate-500',
    text: 'text-slate-300',
  },
  skipped: {
    border: 'border-slate-800 border-dashed opacity-55',
    bg: 'bg-[#0a101d]',
    dot: 'bg-slate-600',
    text: 'text-slate-500',
  },
  running: {
    border: 'border-cyan-400 shadow-[0_0_16px_rgba(34,211,238,0.35)]',
    bg: 'bg-[#0c2136]',
    dot: 'bg-cyan-400 animate-ping',
    text: 'text-cyan-200',
  },
  completed: {
    border: 'border-emerald-500/70',
    bg: 'bg-[#0a1f1e]',
    dot: 'bg-emerald-400',
    text: 'text-emerald-200',
  },
  waiting_human: {
    border: 'border-amber-400 shadow-[0_0_16px_rgba(251,191,36,0.35)]',
    bg: 'bg-[#241b0b]',
    dot: 'bg-amber-400 animate-pulse',
    text: 'text-amber-200',
  },
  error: {
    border: 'border-red-500 shadow-[0_0_14px_rgba(239,68,68,0.35)]',
    bg: 'bg-[#260e14]',
    dot: 'bg-red-400',
    text: 'text-red-200',
  },
  retrying: {
    border: 'border-purple-400 shadow-[0_0_16px_rgba(192,132,252,0.35)]',
    bg: 'bg-[#1c102e]',
    dot: 'bg-purple-400 animate-pulse',
    text: 'text-purple-200',
  },
};

function NodeIcon({ nodeId }: { nodeId: string }) {
  const cls = 'w-3.5 h-3.5 shrink-0';
  switch (nodeId) {
    case '__start__':
      return <PlayCircle className={cls} />;
    case '__end__':
      return <Flag className={cls} />;
    case 'commander':
      return <Compass className={cls} />;
    case 'engineer':
      return <Wrench className={cls} />;
    case 'scientist':
      return <FlaskConical className={cls} />;
    case 'medical_officer':
      return <HeartPulse className={cls} />;
    case 'plan_aggregator':
      return <Layers className={cls} />;
    case 'safety_officer':
      return <ShieldCheck className={cls} />;
    case 'human_approval':
      return <Hand className={cls} />;
    case 'executor':
      return <Cpu className={cls} />;
    case 'mission_evaluator':
      return <CheckCircle2 className={cls} />;
    default:
      return <AlertOctagon className={cls} />;
  }
}

export function CustomGraphNode({ data }: NodeProps) {
  const { t } = useI18n();
  const d = data as CustomNodeData;
  const style = STATUS_STYLES[d.status] ?? STATUS_STYLES.idle;

  if (d.category === 'boundary') {
    return (
      <div
        className={`px-3 py-2 rounded-full border font-mono text-xs flex items-center gap-1.5 transition-all ${style.border} ${style.bg} ${style.text}`}
      >
        <Handle type="target" position={Position.Left} className="!bg-slate-600 !w-2 !h-2" />
        <NodeIcon nodeId={d.nodeId} />
        <span className="font-semibold">{d.label}</span>
        <Handle type="source" position={Position.Right} className="!bg-slate-600 !w-2 !h-2" />
      </div>
    );
  }

  return (
    <div
      className={`w-44 rounded-lg border px-3 py-2 transition-all cursor-pointer ${style.border} ${style.bg} ${
        d.selected ? 'ring-2 ring-cyan-400/80 ring-offset-1 ring-offset-[#080d18]' : ''
      }`}
    >
      <Handle type="target" position={Position.Left} className="!bg-cyan-500/70 !w-2 !h-2" />
      <div className="flex items-center justify-between gap-1.5">
        <div className={`flex items-center gap-1.5 font-semibold text-xs truncate ${style.text}`}>
          <NodeIcon nodeId={d.nodeId} />
          <span className="truncate">{d.label}</span>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {d.runCount > 1 && (
            <span
              className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-purple-500/25 border border-purple-400/50 text-purple-200 flex items-center gap-0.5"
              title={t('graph.executedTimes', { count: d.runCount })}
            >
              <RefreshCw className="w-2.5 h-2.5" />
              {d.runCount}x
            </span>
          )}
          <span className={`w-2 h-2 rounded-full ${style.dot}`} />
        </div>
      </div>

      <div className="mt-1 flex items-center justify-between text-[10px] font-mono text-slate-400">
        <span className="truncate">{d.role}</span>
        {d.durationMs != null && d.durationMs > 0 && (
          <span className="text-slate-500">{t('crew.ms', { value: d.durationMs })}</span>
        )}
      </div>

      {d.isParallelActive && (
        <div className="mt-1 text-[9px] font-mono uppercase tracking-wider text-cyan-300 bg-cyan-500/15 border border-cyan-500/30 rounded px-1.5 py-0.5 text-center">
          {t('graph.parallelBranch')}
        </div>
      )}

      <Handle type="source" position={Position.Right} className="!bg-cyan-500/70 !w-2 !h-2" />
    </div>
  );
}
