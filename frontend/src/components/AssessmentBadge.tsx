import { cn } from '@/lib/cn';

const LABELS: Record<string, { label: string; classes: string }> = {
  approve: {
    label: 'Approve',
    classes: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
  },
  request_changes: {
    label: 'Request changes',
    classes: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300',
  },
  comment: {
    label: 'Comment',
    classes: 'bg-slate-200 text-slate-800 dark:bg-slate-800 dark:text-slate-200',
  },
};

export function AssessmentBadge({ assessment }: { assessment: string }) {
  const entry = LABELS[assessment] ?? LABELS.comment;
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        entry.classes,
      )}
    >
      {entry.label}
    </span>
  );
}
