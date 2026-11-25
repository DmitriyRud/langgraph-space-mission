import { useMemo } from 'react';
import {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from '@xyflow/react';
import { GitBranch, Layers } from 'lucide-react';
import { useI18n } from '../../i18n';
import { useMissionStore } from '../../stores/missionStore';
import type { DerivedExecutionView } from '../../stores/missionStore';
import { CustomGraphNode, type CustomNodeData } from './CustomGraphNode';

interface GraphInspectorProps {
  derived: DerivedExecutionView;
}

const nodeTypes = {
  missionNode: CustomGraphNode,
};

export function GraphInspector({ derived }: GraphInspectorProps) {
  const { t } = useI18n();
  const topology = useMissionStore((s) => s.topology);
  const selectedNodeId = useMissionStore((s) => s.selectedNodeId);
  const setSelectedNodeId = useMissionStore((s) => s.setSelectedNodeId);
  const viewMode = useMissionStore((s) => s.viewMode);

  const nodes: Node<CustomNodeData>[] = useMemo(() => {
    if (!topology) return [];
    const parallelActive = derived.activeParallelNodes.length > 1;
    return topology.nodes.map((n) => {
      const runtime = derived.nodeStates[n.id];
      const status = runtime?.status ?? 'idle';
      return {
        id: n.id,
        type: 'missionNode',
        position: n.position,
        data: {
          nodeId: n.id,
          label: n.label,
          role: n.role,
          category: n.category,
          status,
          runCount: runtime?.runCount ?? 0,
          durationMs: runtime?.durationMs ?? null,
          isParallelActive:
            parallelActive && derived.activeParallelNodes.includes(n.id),
          selected: selectedNodeId === n.id,
        },
      };
    });
  }, [topology, derived.nodeStates, derived.activeParallelNodes, selectedNodeId]);

  const edges: Edge[] = useMemo(() => {
    if (!topology) return [];
    return topology.edges.map((e) => {
      const isActive = derived.activeEdges.has(e.id);
      const stroke = e.cyclic
        ? isActive
          ? '#c084fc'
          : '#581c87'
        : isActive
          ? '#38bdf8'
          : '#334155';

      return {
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label || undefined,
        animated: isActive,
        type: e.cyclic ? 'smoothstep' : 'default',
        style: {
          stroke,
          strokeWidth: isActive ? 2.2 : 1.3,
          strokeDasharray: e.conditional ? '5 4' : undefined,
        },
        labelStyle: {
          fill: isActive ? '#e2e8f0' : '#64748b',
          fontSize: 10,
          fontFamily: 'monospace',
        },
        labelBgStyle: {
          fill: '#080d18',
          fillOpacity: 0.85,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: stroke,
          width: 15,
          height: 15,
        },
      };
    });
  }, [topology, derived.activeEdges]);

  return (
    <div className="relative flex-1 min-h-0 flex flex-col bg-[#080d18]">
      {/* Graph Inspector Overlay Header */}
      <div className="px-3 py-2 border-b border-slate-800/80 bg-[#0a101d]/90 flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-cyan-300 font-semibold">
            <GitBranch className="w-3.5 h-3.5" />
            <span>{t('graph.title')}</span>
          </div>
          <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300">
            {t('graph.iteration', {
              current: derived.currentIteration,
              max: derived.currentState?.max_iterations ?? 5,
            })}
          </span>
          {derived.activeParallelNodes.length > 0 && (
            <span className="px-2 py-0.5 rounded bg-cyan-500/15 border border-cyan-500/40 text-cyan-300 flex items-center gap-1">
              <Layers className="w-3 h-3" />
              {t('graph.active', { nodes: derived.activeParallelNodes.join(', ') })}
            </span>
          )}
          {viewMode === 'replay' && (
            <span className="px-2 py-0.5 rounded bg-purple-500/20 border border-purple-500/50 text-purple-200">
              {t('graph.replayBadge')}
            </span>
          )}
        </div>

        <div className="hidden lg:flex items-center gap-3 text-[10px] text-slate-400">
          <span className="flex items-center gap-1"><i className="w-2 h-2 rounded-full bg-slate-500 inline-block" />{t('graph.legend.idle')}</span>
          <span className="flex items-center gap-1"><i className="w-2 h-2 rounded-full bg-cyan-400 inline-block" />{t('graph.legend.running')}</span>
          <span className="flex items-center gap-1"><i className="w-2 h-2 rounded-full bg-emerald-400 inline-block" />{t('graph.legend.completed')}</span>
          <span className="flex items-center gap-1"><i className="w-2 h-2 rounded-full bg-amber-400 inline-block" />{t('graph.legend.hitl')}</span>
          <span className="flex items-center gap-1"><i className="w-2 h-2 rounded-full bg-red-400 inline-block" />{t('graph.legend.error')}</span>
          <span className="flex items-center gap-1"><i className="w-2 h-2 rounded-full bg-purple-400 inline-block" />{t('graph.legend.rerun')}</span>
        </div>
      </div>

      {/* React Flow Canvas */}
      <div className="flex-1 min-h-0">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodeClick={(_evt, node) => setSelectedNodeId(node.id)}
          onPaneClick={() => setSelectedNodeId(null)}
          fitView
          fitViewOptions={{ padding: 0.22 }}
          minZoom={0.3}
          maxZoom={1.6}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#1e293b" gap={22} size={1} />
          <Controls showInteractive={false} />
          <MiniMap
            nodeColor={(n) => {
              const st = (n.data as CustomNodeData | undefined)?.status;
              if (st === 'running') return '#22d3ee';
              if (st === 'completed') return '#10b981';
              if (st === 'waiting_human') return '#fbbf24';
              if (st === 'error') return '#ef4444';
              if (st === 'retrying') return '#a855f7';
              return '#334155';
            }}
            maskColor="rgba(7, 11, 20, 0.75)"
          />
        </ReactFlow>
      </div>
    </div>
  );
}
