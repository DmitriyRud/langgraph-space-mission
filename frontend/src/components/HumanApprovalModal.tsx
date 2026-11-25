import { useState } from 'react';
import { AlertTriangle, CheckCircle2, MessageSquareWarning, ShieldCheck, XCircle } from 'lucide-react';
import { useI18n } from '../i18n';
import type { MissionPlan, SafetyAssessment } from '../types/mission';

interface HumanApprovalModalProps {
  interruptPayload: Record<string, unknown>;
  busy: boolean;
  onDecision: (decision: 'approve' | 'reject' | 'request_revision', feedback: string) => void;
}

export function HumanApprovalModal({
  interruptPayload,
  busy,
  onDecision,
}: HumanApprovalModalProps) {
  const { t } = useI18n();
  const [feedback, setFeedback] = useState('');
  const plan = (interruptPayload.plan as MissionPlan | undefined) ?? null;
  const safety = (interruptPayload.safety_assessment as SafetyAssessment | undefined) ?? null;
  const iteration = Number(interruptPayload.iteration ?? 1);

  return (
    <div className="fixed inset-x-0 bottom-6 z-40 flex justify-center px-4 pointer-events-none">
      <div className="pointer-events-auto w-full max-w-2xl rounded-lg border border-amber-500/60 bg-[#0c1425]/98 shadow-2xl shadow-black/70 backdrop-blur-md">
        <div className="px-4 py-3 border-b border-amber-500/30 bg-amber-500/10 flex items-center justify-between">
          <div className="flex items-center gap-2 text-amber-300 font-mono text-xs font-semibold">
            <AlertTriangle className="w-4 h-4" />
            <span>{t('hitl.header', { iteration })}</span>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-200 border border-amber-500/40">
            Command(resume=...)
          </span>
        </div>

        <div className="p-4 space-y-3 max-h-[55vh] overflow-y-auto">
          {plan && (
            <div className="space-y-2">
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-slate-100">{plan.title}</h3>
                <span className="text-[11px] font-mono uppercase px-2 py-0.5 rounded border border-cyan-500/40 bg-cyan-500/10 text-cyan-300">
                  {t('hitl.riskLabel', { risk: t(`risk.${plan.risk_level}`) })}
                </span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">{plan.summary}</p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-1">
                <div className="rounded border border-slate-800 bg-[#080e1c] p-2.5">
                  <div className="text-[10px] font-mono uppercase text-slate-400 mb-1.5">
                    {t('hitl.proposedActions', { count: plan.action_ids.length })}
                  </div>
                  <ul className="space-y-1.5">
                    {(plan.actions_detail ?? []).map((act) => (
                      <li key={act.id} className="text-xs text-slate-200">
                        <span className="font-mono text-cyan-300">{act.label}</span>
                        <div className="text-[11px] text-slate-400">{act.description}</div>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="rounded border border-slate-800 bg-[#080e1c] p-2.5 space-y-2">
                  <div>
                    <div className="text-[10px] font-mono uppercase text-slate-400 mb-1">
                      {t('hitl.projectedDeltas')}
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {Object.entries(plan.projected_effects ?? {}).map(([metric, delta]) => (
                        <span
                          key={metric}
                          className={`text-[11px] font-mono px-1.5 py-0.5 rounded border ${
                            delta >= 0
                              ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                              : 'border-amber-500/40 bg-amber-500/10 text-amber-300'
                          }`}
                        >
                          {t(`telemetry.metrics.${metric}`)}: {delta > 0 ? `+${delta}` : delta}%
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="text-[11px] text-slate-400">
                    <span className="text-slate-300 font-mono">{t('hitl.resources')}</span> {plan.resource_summary}
                  </div>
                </div>
              </div>
            </div>
          )}

          {safety && (
            <div className="rounded border border-emerald-500/30 bg-emerald-500/5 p-2.5 flex items-start gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <div className="text-xs">
                <div className="font-mono text-emerald-300 font-semibold">
                  {t('hitl.safetyVerdict', {
                    verdict: safety.approved ? t('hitl.verdictApproved') : t('hitl.verdictEscalated'),
                  })}
                </div>
                <p className="text-slate-300 mt-0.5">{safety.summary}</p>
              </div>
            </div>
          )}

          <div>
            <label className="block text-[11px] font-mono text-slate-400 mb-1">
              {t('hitl.feedbackLabel')}
            </label>
            <input
              type="text"
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder={t('hitl.feedbackPlaceholder')}
              className="w-full h-9 rounded border border-slate-700 bg-[#080d18] px-3 text-xs text-slate-100 placeholder:text-slate-500 focus:border-cyan-500 focus:outline-none"
            />
          </div>
        </div>

        <div className="px-4 py-3 border-t border-slate-800 bg-[#090f1d] flex flex-wrap items-center justify-end gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={() => onDecision('reject', feedback)}
            className="h-8 px-3 rounded border border-red-500/50 bg-red-500/15 hover:bg-red-500/25 disabled:opacity-50 text-red-300 text-xs font-mono flex items-center gap-1.5 transition"
          >
            <XCircle className="w-3.5 h-3.5" />
            <span>{t('hitl.reject')}</span>
          </button>

          <button
            type="button"
            disabled={busy}
            onClick={() => onDecision('request_revision', feedback || t('hitl.defaultRevisionFeedback'))}
            className="h-8 px-3 rounded border border-amber-500/50 bg-amber-500/15 hover:bg-amber-500/25 disabled:opacity-50 text-amber-300 text-xs font-mono flex items-center gap-1.5 transition"
          >
            <MessageSquareWarning className="w-3.5 h-3.5" />
            <span>{t('hitl.requestRevision')}</span>
          </button>

          <button
            type="button"
            disabled={busy}
            onClick={() => onDecision('approve', feedback)}
            className="h-8 px-4 rounded bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-slate-950 font-semibold text-xs font-mono flex items-center gap-1.5 transition"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{t('hitl.approve')}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
