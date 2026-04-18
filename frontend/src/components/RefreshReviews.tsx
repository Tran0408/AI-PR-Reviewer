'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export function RefreshReviews() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function onClick() {
    setLoading(true);
    setMsg(null);
    try {
      const res = await fetch('/api/reviews/refresh', { method: 'POST' });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail ?? 'Refresh failed');
      setMsg(`Removed ${json.removed ?? 0}, queued ${json.enqueued ?? 0}`);
      router.refresh();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Refresh failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={onClick}
        disabled={loading}
        className="rounded border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-slate-800"
      >
        {loading ? 'Refreshing…' : 'Refresh PRs'}
      </button>
      {msg && <span className="text-xs text-slate-500">{msg}</span>}
    </div>
  );
}
