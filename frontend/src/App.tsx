import { useCallback, useEffect, useMemo } from 'react';
import { AlertTriangle } from 'lucide-react';
import { api } from './api/client';
import { Header } from './components/Header';
import { HumanApprovalModal } from './components/HumanApprovalModal';
import { MissionControlBar } from './components/MissionControlBar';
import { SettingsModal } from './components/SettingsModal';
import { AICrewPanel } from './features/ai-crew/AICrewPanel';
import { DeveloperConsole } from './features/developer-console/DeveloperConsole';
import { GraphInspector } from './features/graph-inspector/GraphInspector';
import { NodeInspectorDrawer } from './features/graph-inspector/NodeInspectorDrawer';
import { ShipTelemetryPanel } from './features/telemetry/ShipTelemetryPanel';
import { useMissionStream } from './hooks/useMissionStream';
import { useI18n } from './i18n';
import { deriveExecutionView, useMissionStore } from './stores/missionStore';

export function App() {
  const { language, t } = useI18n();
  const scenarios = useMissionStore((s) => s.scenarios);
  const topology = useMissionStore((s) => s.topology);
  const activeMission = useMissionStore((s) => s.activeMission);
  const fallbackSnapshot = useMissionStore((s) => s.fallbackSnapshot);
  const selectedScenarioId = useMissionStore((s) => s.selectedScenarioId);
  const mode = useMissionStore((s) => s.mode);
  const viewMode = useMissionStore((s) => s.viewMode);
  const events = useMissionStore((s) => s.events);
  const replayIndex = useMissionStore((s) => s.replayIndex);
  const busy = useMissionStore((s) => s.busy);
  const toastMessage = useMissionStore((s) => s.toastMessage);

  const setHealth = useMissionStore((s) => s.setHealth);
  const setScenarios = useMissionStore((s) => s.setScenarios);
  const setTopology = useMissionStore((s) => s.setTopology);
  const setMissions = useMissionStore((s) => s.setMissions);
  const setActiveMission = useMissionStore((s) => s.setActiveMission);
  const setSelectedScenarioId = useMissionStore((s) => s.setSelectedScenarioId);
  const setMode = useMissionStore((s) => s.setMode);
  const setBusy = useMissionStore((s) => s.setBusy);
  const setToastMessage = useMissionStore((s) => s.setToastMessage);
  const resetMissionView = useMissionStore((s) => s.resetMissionView);

  const showToast = useCallback(
    (msg: string) => {
      setToastMessage(msg);
      window.setTimeout(() => {
        if (useMissionStore.getState().toastMessage === msg) {
          setToastMessage(null);
        }
      }, 4500);
    },
    [setToastMessage]
  );

  const refreshHealth = useCallback(async () => {
    try {
      const h = await api.getHealth();
      setHealth(h);
    } catch {
      // backend may still be starting
    }
  }, [setHealth]);

  const refreshMissions = useCallback(async () => {
    try {
      const res = await api.listMissions();
      setMissions(res.missions);
    } catch {
      // ignore
    }
  }, [setMissions]);

  // Sync document metadata and reload localized scenarios & graph topology whenever language changes
  useEffect(() => {
    document.documentElement.lang = language;
    document.title = t('app.documentTitle');
    const loadLocalizedCatalogs = async () => {
      try {
        const [scRes, graphRes] = await Promise.all([
          api.getScenarios(language),
          api.getGraph(language),
        ]);
        setScenarios(scRes.scenarios);
        setTopology(graphRes);
      } catch {
        // handled during initial boot
      }
    };
    void loadLocalizedCatalogs();
  }, [language, t, setScenarios, setTopology]);

  // Initial bootstrap: health check and restore paused mission if present
  useEffect(() => {
    const boot = async () => {
      await refreshHealth();
      try {
        const msnRes = await api.listMissions();
        setMissions(msnRes.missions);

        const paused = msnRes.missions.find((m) => m.status === 'awaiting_approval');
        if (paused) {
          const detail = await api.getMission(paused.mission_id);
          setSelectedScenarioId(detail.mission.scenario_id);
          setMode(detail.mission.mode);
          setActiveMission(detail.mission, detail.snapshot);
          showToast(t('app.toast.restoredPaused', { missionId: detail.mission.mission_id }));
        }
      } catch (err) {
        showToast(err instanceof Error ? err.message : t('app.toast.backendError'));
      }
    };
    void boot();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useMissionStream(activeMission?.mission_id ?? null);

  const visibleEvents = useMemo(() => {
    if (viewMode === 'replay') {
      return events.slice(0, replayIndex + 1);
    }
    return events;
  }, [events, viewMode, replayIndex]);

  const derived = useMemo(
    () => deriveExecutionView(visibleEvents, topology, fallbackSnapshot),
    [visibleEvents, topology, fallbackSnapshot]
  );

  const handleStartMission = async () => {
    setBusy(true);
    try {
      const created = await api.createMission(selectedScenarioId, mode, 5, language);
      setActiveMission(created.mission, null);
      await api.startMission(created.mission.mission_id);
      await refreshMissions();
    } catch (err) {
      showToast(err instanceof Error ? err.message : t('app.toast.startError'));
    } finally {
      setBusy(false);
    }
  };

  const handleRandomScenario = () => {
    if (scenarios.length === 0) return;
    const pick = scenarios[Math.floor(Math.random() * scenarios.length)];
    setSelectedScenarioId(pick.id);
    showToast(t('app.toast.randomSelected', { title: pick.title }));
  };

  const handleRestoreMission = async (missionId: string) => {
    setBusy(true);
    try {
      const detail = await api.getMission(missionId);
      setSelectedScenarioId(detail.mission.scenario_id);
      setMode(detail.mission.mode);
      setActiveMission(detail.mission, detail.snapshot);
      showToast(
        t('app.toast.restoredMission', {
          missionId: detail.mission.mission_id,
          status: t(`missionDbStatus.${detail.mission.status}`),
        })
      );
    } catch (err) {
      showToast(err instanceof Error ? err.message : t('app.toast.restoreError'));
    } finally {
      setBusy(false);
    }
  };

  const handleHumanDecision = async (
    decision: 'approve' | 'reject' | 'request_revision',
    feedback: string
  ) => {
    if (!activeMission) return;
    setBusy(true);
    try {
      await api.resumeMission(activeMission.mission_id, decision, feedback);
      await refreshMissions();
    } catch (err) {
      showToast(err instanceof Error ? err.message : t('app.toast.resumeError'));
    } finally {
      setBusy(false);
    }
  };

  const handleSwitchToDemoAndRetry = async () => {
    setMode('demo');
    if (!activeMission) return;
    setBusy(true);
    try {
      await api.resumeMission(activeMission.mission_id, 'approve', '', true);
      showToast(t('app.toast.switchedToDemoResumed'));
    } catch {
      const created = await api.createMission(selectedScenarioId, 'demo', 5, language);
      setActiveMission(created.mission, null);
      await api.startMission(created.mission.mission_id);
      showToast(t('app.toast.startedNewDemo'));
    } finally {
      setBusy(false);
      await refreshMissions();
    }
  };

  const handleForkCheckpoint = async (checkpointId: string) => {
    if (!activeMission) return;
    setBusy(true);
    try {
      const res = await api.forkMission(activeMission.mission_id, checkpointId, mode, true);
      setActiveMission(res.mission, null);
      await refreshMissions();
      showToast(
        t('app.toast.forkCreated', {
          missionId: res.mission.mission_id,
          checkpointId: checkpointId.slice(0, 10),
        })
      );
    } catch (err) {
      showToast(err instanceof Error ? err.message : t('app.toast.forkError'));
    } finally {
      setBusy(false);
    }
  };

  const handleExportJson = async () => {
    if (!activeMission) return;
    try {
      const data = await api.exportMission(activeMission.mission_id);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `aurora7-${activeMission.mission_id}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      showToast(err instanceof Error ? err.message : t('app.toast.exportError'));
    }
  };

  return (
    <div className="h-screen w-screen overflow-hidden flex flex-col bg-[#070b14] text-slate-100">
      <Header derived={derived} />
      <MissionControlBar
        derived={derived}
        onStartMission={() => void handleStartMission()}
        onRandomScenario={handleRandomScenario}
        onResetMission={resetMissionView}
        onRestoreMission={(id) => void handleRestoreMission(id)}
        onExportJson={() => void handleExportJson()}
      />

      {derived.latestError && (
        <div className="shrink-0 px-4 py-2 bg-red-950/70 border-b border-red-500/40 flex flex-wrap items-center justify-between gap-2 text-xs font-mono text-red-200">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
            <span>{derived.latestError.message}</span>
          </div>
          {derived.latestError.canSwitchToDemo && (
            <button
              type="button"
              onClick={() => void handleSwitchToDemoAndRetry()}
              className="px-3 py-1 rounded bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold"
            >
              {t('app.switchToDemo')}
            </button>
          )}
        </div>
      )}

      <div className="flex-1 min-h-0 flex overflow-hidden">
        <ShipTelemetryPanel derived={derived} />

        <main className="relative flex-1 min-w-0 flex flex-col overflow-hidden">
          <GraphInspector derived={derived} />
          <NodeInspectorDrawer derived={derived} />
        </main>

        <AICrewPanel derived={derived} />
      </div>

      <DeveloperConsole
        visibleEvents={visibleEvents}
        derived={derived}
        onForkCheckpoint={(cid) => void handleForkCheckpoint(cid)}
      />

      {viewMode === 'live' && derived.pendingInterrupt && (
        <HumanApprovalModal
          interruptPayload={derived.pendingInterrupt}
          busy={busy}
          onDecision={(dec, fb) => void handleHumanDecision(dec, fb)}
        />
      )}

      <SettingsModal onRefreshHealth={() => void refreshHealth()} />

      {toastMessage && (
        <div className="fixed top-16 right-4 z-50 px-3.5 py-2 rounded border border-cyan-500/50 bg-[#0d182d]/95 text-xs font-mono text-cyan-200 shadow-lg">
          {toastMessage}
        </div>
      )}
    </div>
  );
}

export default App;
