import { useState } from 'react';
import { ChevronLeft, ChevronRight, Gauge, X } from 'lucide-react';
import { useI18n } from '../../i18n';
import { BASELINE_SHIP_STATE, useMissionStore } from '../../stores/missionStore';
import type { DerivedExecutionView } from '../../stores/missionStore';
import type { ShipState } from '../../types/mission';
import { Aurora3DViewer } from './Aurora3DViewer';

interface ShipTelemetryPanelProps {
  derived: DerivedExecutionView;
}

const TELEMETRY_KEYS: Array<keyof ShipState> = [
  'energy',
  'oxygen',
  'hull_integrity',
  'engine_condition',
  'communication',
  'navigation',
  'crew_health',
  'crew_morale',
  'reserve_fuel',
];

function barColor(val: number): string {
  if (val >= 70) return 'bg-emerald-400';
  if (val >= 45) return 'bg-amber-400';
  return 'bg-red-500';
}

export function ShipTelemetryPanel({ derived }: ShipTelemetryPanelProps) {
  const { t } = useI18n();
  const [expanded3D, setExpanded3D] = useState(false);
  const collapsed = useMissionStore((s) => s.leftCollapsed);
  const toggleCollapsed = useMissionStore((s) => s.toggleLeftCollapsed);
  const scenarios = useMissionStore((s) => s.scenarios);
  const selectedScenarioId = useMissionStore((s) => s.selectedScenarioId);

  const selectedScenario = scenarios.find((s) => s.id === selectedScenarioId);
  const ship: ShipState =
    derived.currentState?.ship_state ??
    selectedScenario?.initial_ship_state ??
    BASELINE_SHIP_STATE;
  const initialShip: ShipState =
    derived.currentState?.initial_ship_state ??
    selectedScenario?.initial_ship_state ??
    BASELINE_SHIP_STATE;

  if (collapsed) {
    return (
      <aside className="w-10 shrink-0 border-r border-slate-800 bg-[#0a101d] flex flex-col items-center py-3 gap-3">
        <button
          type="button"
          onClick={toggleCollapsed}
          className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-cyan-300"
          title={t('telemetry.expand')}
        >
          <ChevronRight className="w-4 h-4" />
        </button>
        <Gauge className="w-4 h-4 text-cyan-400" />
      </aside>
    );
  }

  return (
    <>
      <aside className="w-76 shrink-0 border-r border-slate-800 bg-[#0a101d] flex flex-col overflow-hidden">
        <div className="px-3 py-2.5 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-mono font-semibold text-slate-200">
            <Gauge className="w-3.5 h-3.5 text-cyan-400" />
            <span>{t('telemetry.title')}</span>
          </div>
          <button
            type="button"
            onClick={toggleCollapsed}
            className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-cyan-300"
            title={t('telemetry.collapse')}
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          {/* Interactive 3D Holographic Spacecraft Viewer */}
          {!expanded3D && (
            <Aurora3DViewer
              ship={ship}
              scenarioId={selectedScenarioId}
              activeNodes={derived.activeParallelNodes}
              onToggleExpand={() => setExpanded3D(true)}
            />
          )}

          {/* 9 Telemetry Bars */}
          <div className="space-y-2">
            {TELEMETRY_KEYS.map((key) => {
              const val = Number(ship[key] ?? 100);
              const initVal = Number(initialShip[key] ?? val);
              const delta = val - initVal;
              return (
                <div key={key} className="space-y-1">
                  <div className="flex items-center justify-between text-[11px] font-mono">
                    <span className="text-slate-300">{t(`telemetry.metrics.${key}`)}</span>
                    <div className="flex items-center gap-1.5">
                      {delta !== 0 && (
                        <span className={delta > 0 ? 'text-emerald-400' : 'text-red-400'}>
                          {delta > 0 ? `+${delta}` : delta}
                        </span>
                      )}
                      <span className="text-slate-100 font-semibold w-9 text-right">{val}%</span>
                    </div>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-slate-800/90 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-300 ${barColor(val)}`}
                      style={{ width: `${Math.max(0, Math.min(100, val))}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          {selectedScenario && (
            <div className="rounded border border-slate-800 bg-[#080e1c] p-2.5 space-y-1.5">
              <div className="text-[10px] font-mono uppercase text-cyan-400">
                {t('telemetry.activeScenario', { title: selectedScenario.title })}
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                {selectedScenario.description}
              </p>
              <div className="pt-1 border-t border-slate-800/80 space-y-1">
                <div className="text-[10px] font-mono text-slate-500 uppercase">
                  {t('telemetry.objectives')}
                </div>
                {selectedScenario.objectives.map((obj) => (
                  <div key={obj} className="text-[11px] text-slate-300 flex items-start gap-1.5">
                    <span className="text-cyan-400">•</span>
                    <span>{obj}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* Expanded 3D Holographic Inspection Modal */}
      {expanded3D && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-6">
          <div className="w-full max-w-4xl h-[75vh] rounded-lg border border-cyan-500/40 bg-[#070b14] shadow-2xl flex flex-col overflow-hidden">
            <div className="px-4 py-2.5 border-b border-slate-800 bg-[#0a101d] flex items-center justify-between">
              <span className="text-xs font-mono font-semibold text-cyan-300">
                {t('telemetry.viewer3d.modalTitle')}
              </span>
              <button
                type="button"
                onClick={() => setExpanded3D(false)}
                className="p-1 rounded text-slate-400 hover:text-slate-100 hover:bg-slate-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="flex-1 min-h-0 p-3">
              <Aurora3DViewer
                ship={ship}
                scenarioId={selectedScenarioId}
                activeNodes={derived.activeParallelNodes}
                expanded
                onToggleExpand={() => setExpanded3D(false)}
              />
            </div>
          </div>
        </div>
      )}
    </>
  );
}
