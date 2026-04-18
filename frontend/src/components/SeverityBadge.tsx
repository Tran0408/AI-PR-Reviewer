import { cn } from '@/lib/cn';

const MAP: Record<string, string> = {
  info: 'bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300',
  minor: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  major: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300',
  critical: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300',
};

export function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide',
        MAP[severity] ?? MAP.minor,
      )}
    >
      {severity}
    </span>
  );
}
