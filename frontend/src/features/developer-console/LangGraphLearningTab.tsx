import { BookOpen, ExternalLink } from 'lucide-react';
import { useI18n } from '../../i18n';
import type { LearningItem } from '../../types/mission';

interface LangGraphLearningTabProps {
  items: LearningItem[];
  onSelectNode: (nodeId: string) => void;
}

export function LangGraphLearningTab({ items, onSelectNode }: LangGraphLearningTabProps) {
  const { t } = useI18n();

  return (
    <div className="h-full overflow-y-auto p-3 grid grid-cols-1 lg:grid-cols-2 gap-3">
      {items.map((item) => (
        <div
          key={item.id}
          className="rounded border border-slate-800 bg-[#080d18] p-3 flex flex-col gap-2"
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-cyan-300">
              <BookOpen className="w-3.5 h-3.5 shrink-0" />
              <span>{item.name}</span>
            </div>
            <a
              href={item.doc_url}
              target="_blank"
              rel="noreferrer"
              className="text-[10px] font-mono text-slate-400 hover:text-cyan-300 flex items-center gap-1 shrink-0"
            >
              <span>{t('learningTab.docs')}</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed">{item.summary}</p>

          <div className="text-[10px] font-mono text-slate-400">
            {t('learningTab.implementedIn')}{' '}
            <span className="text-slate-200">{item.where_used}</span>
          </div>

          <pre className="p-2 rounded border border-slate-800 bg-[#050911] text-[11px] font-mono text-emerald-300 overflow-x-auto">
            {item.snippet}
          </pre>

          <div className="flex flex-wrap items-center gap-1.5 pt-1">
            <span className="text-[10px] font-mono text-slate-500">
              {t('learningTab.inspectNodes')}
            </span>
            {item.nodes.map((nid) => (
              <button
                key={nid}
                type="button"
                onClick={() => onSelectNode(nid)}
                className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 hover:bg-cyan-500/20 text-cyan-300 border border-slate-700"
              >
                {nid}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
