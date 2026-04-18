'use client';

import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import type { Repo } from '@/lib/api';

export function SettingsClient({ userId, repos }: { userId: string; repos: Repo[] }) {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [, startTransition] = useTransition();

  async function toggle(repo: Repo) {
    setErr(null);
    setBusy(repo.id);
    try {
      const path = repo.connected
        ? `/api/repositories/${repo.id}/disconnect`
        : `/api/repositories/${repo.id}/connect`;
      const res = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId }),
      });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(t.slice(0, 300));
      }
      startTransition(() => router.refresh());
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Repositories</h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Connect a repo to install the webhook. New/updated PRs trigger an AI review.
        </p>
      </div>

      {err && (
        <div className="rounded-lg border border-rose-300 bg-rose-50 p-3 text-sm text-rose-900 dark:border-rose-800 dark:bg-rose-900/30 dark:text-rose-200">
          {err}
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-950 dark:text-slate-400">
            <tr>
              <th className="px-4 py-2">Repository</th>
              <th className="px-4 py-2">Visibility</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
            {repos.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-sm text-slate-500">
                  No repos found. Make sure you granted repo access on GitHub.
                </td>
              </tr>
            )}
            {repos.map((r) => (
              <tr key={r.id}>
                <td className="px-4 py-3 font-mono text-xs">{r.full_name}</td>
                <td className="px-4 py-3 text-xs">{r.private ? 'private' : 'public'}</td>
                <td className="px-4 py-3 text-xs">
                  {r.connected ? (
                    <span className="rounded bg-emerald-100 px-2 py-0.5 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
                      Connected
                    </span>
                  ) : (
                    <span className="rounded bg-slate-200 px-2 py-0.5 text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                      Disconnected
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    disabled={busy === r.id}
                    onClick={() => toggle(r)}
                    className="rounded border border-slate-300 px-3 py-1 text-xs hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-slate-800"
                  >
                    {busy === r.id
                      ? 'Working…'
                      : r.connected
                        ? 'Disconnect'
                        : 'Connect'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
