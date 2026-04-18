import { cn } from '@/lib/cn';

export function ScoreBadge({ score, className }: { score: number; className?: string }) {
  const color =
    score >= 8
      ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
      : score >= 5
        ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
        : 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300';
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold tabular-nums',
        color,
        className,
      )}
      aria-label={`Score ${score} out of 10`}
    >
      {score}/10
    </span>
  );
}
