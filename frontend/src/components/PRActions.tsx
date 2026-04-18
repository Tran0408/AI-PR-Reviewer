'use client';

import { useEffect, useState } from 'react';

type PRFile = {
  filename: string;
  status: string;
  additions: number;
  deletions: number;
  blob_url: string;
};

type PRDetails = {
  pr_author: string | null;
  pr_author_avatar: string | null;
  state: string | null;
  merged: boolean;
  mergeable: boolean | null;
  mergeable_state: string | null;
  base_ref: string | null;
  head_ref: string | null;
  additions: number;
  deletions: number;
  changed_files: number;
  files: PRFile[];
};

type MergeMethod = 'merge' | 'squash' | 'rebase';

export function PRActions({ reviewId }: { reviewId: string }) {
  const [data, setData] = useState<PRDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [method, setMethod] = useState<MergeMethod>('merge');
  const [merging, setMerging] = useState(false);
  const [mergeMsg, setMergeMsg] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setErr(null);
    try {
      const res = await fetch(`/api/reviews/${reviewId}/pr-details`, { cache: 'no-store' });
      if (!res.ok) throw new Error(await res.text());
      setData(await res.json());
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Failed to load PR details');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [reviewId]);

  async function onMerge() {
    if (!confirm(`Merge this PR using "${method}"?`)) return;
    setMerging(true);
    setMergeMsg(null);
    try {
      const res = await fetch(`/api/reviews/${reviewId}/merge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ method }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail ?? 'Merge failed');
      setMergeMsg(json.merged ? `Merged: ${json.sha?.slice(0, 7)}` : 'Merge reported failure');
      await load();
    } catch (e) {
      setMergeMsg(e instanceof Error ? e.message : 'Merge failed');
    } finally {
      setMerging(false);
    }
  }

  if (loading) {
    return <Section title="PR Status"><p className="text-sm text-slate-500">Loading…</p></Section>;
  }
  if (err || !data) {
    return (
      <Section title="PR Status">
        <p className="text-sm text-red-600">Could not load PR details: {err}</p>
      </Section>
    );
  }

  const isOpen = data.state === 'open' && !data.merged;
  const canMerge = isOpen && data.mergeable === true;
  const hasConflict = isOpen && data.mergeable === false;
  const mergeableUnknown = isOpen && data.mergeable === null;

  return (
    <>
      <Section title="PR Status">
        <div className="flex flex-wrap items-center gap-3 text-sm">
          {data.pr_author_avatar && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={data.pr_author_avatar}
              alt={data.pr_author ?? ''}
              className="h-7 w-7 rounded-full"
            />
          )}
          <span>
            <span className="text-slate-500">Author:</span>{' '}
            <strong>{data.pr_author ?? 'unknown'}</strong>
          </span>
          <Pill>
            {data.head_ref} → {data.base_ref}
          </Pill>
          <Pill>{data.merged ? 'merged' : data.state ?? 'unknown'}</Pill>
          <Pill className="text-green-700 dark:text-green-400">+{data.additions}</Pill>
          <Pill className="text-red-700 dark:text-red-400">-{data.deletions}</Pill>
          <Pill>{data.changed_files} files</Pill>
        </div>

        {isOpen && (
          <div className="mt-4">
            {canMerge && (
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm text-green-700 dark:text-green-400">
                  ✓ No conflicts — ready to merge
                </span>
                <select
                  className="rounded border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900"
                  value={method}
                  onChange={(e) => setMethod(e.target.value as MergeMethod)}
                  disabled={merging}
                >
                  <option value="merge">Merge commit</option>
                  <option value="squash">Squash and merge</option>
                  <option value="rebase">Rebase and merge</option>
                </select>
                <button
                  onClick={onMerge}
                  disabled={merging}
                  className="rounded bg-green-600 px-3 py-1 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
                >
                  {merging ? 'Merging…' : 'Merge PR'}
                </button>
                {mergeMsg && <span className="text-xs text-slate-500">{mergeMsg}</span>}
              </div>
            )}
            {hasConflict && <ConflictHelp files={data.files} />}
            {mergeableUnknown && (
              <p className="text-sm text-slate-500">
                GitHub is still computing mergeability. Refresh in a moment.
              </p>
            )}
          </div>
        )}
        {data.merged && (
          <p className="mt-3 text-sm text-purple-700 dark:text-purple-400">
            This PR has already been merged.
          </p>
        )}
      </Section>

      <Section title={`Files changed (${data.files.length})`}>
        {data.files.length === 0 ? (
          <p className="text-sm text-slate-500">No files reported.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {data.files.map((f) => (
              <li key={f.filename} className="flex items-center gap-3">
                <StatusDot status={f.status} />
                <a
                  href={f.blob_url}
                  target="_blank"
                  rel="noreferrer"
                  className="font-mono text-xs text-brand-600 hover:underline"
                >
                  {f.filename}
                </a>
                <span className="text-xs text-green-600">+{f.additions}</span>
                <span className="text-xs text-red-600">-{f.deletions}</span>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </>
  );
}

function ConflictHelp({ files }: { files: PRFile[] }) {
  return (
    <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-800/50 dark:bg-amber-900/20">
      <p className="font-semibold text-amber-900 dark:text-amber-300">
        ⚠️ Merge conflicts detected
      </p>
      <p className="mt-1 text-amber-800 dark:text-amber-200">
        This branch has conflicts with the base branch. GitHub needs them resolved before merging.
      </p>
      <p className="mt-2 text-amber-800 dark:text-amber-200">How to resolve:</p>
      <ol className="ml-5 mt-1 list-decimal space-y-0.5 text-amber-800 dark:text-amber-200">
        <li>
          <code>git fetch origin &amp;&amp; git checkout &lt;branch&gt;</code>
        </li>
        <li>
          <code>git merge origin/&lt;base&gt;</code> (or <code>git rebase origin/&lt;base&gt;</code>)
        </li>
        <li>
          Fix conflicts in the files below, then <code>git add</code> &amp;{' '}
          <code>git commit</code> (or <code>--continue</code>).
        </li>
        <li>
          <code>git push</code>. Conflicts will clear and the merge button will enable.
        </li>
      </ol>
      {files.length > 0 && (
        <div className="mt-2">
          <p className="text-xs text-amber-800 dark:text-amber-300">
            Files most likely to conflict (review carefully):
          </p>
          <ul className="ml-5 list-disc text-xs text-amber-900 dark:text-amber-200">
            {files.slice(0, 10).map((f) => (
              <li key={f.filename}>
                <code>{f.filename}</code>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function Pill({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <span
      className={`rounded bg-slate-100 px-2 py-0.5 text-xs dark:bg-slate-800 ${className}`}
    >
      {children}
    </span>
  );
}

function StatusDot({ status }: { status: string }) {
  const color =
    status === 'added'
      ? 'bg-green-500'
      : status === 'removed'
        ? 'bg-red-500'
        : status === 'renamed'
          ? 'bg-blue-500'
          : 'bg-amber-500';
  return <span className={`inline-block h-2 w-2 rounded-full ${color}`} title={status} />;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
        {title}
      </h2>
      {children}
    </section>
  );
}
