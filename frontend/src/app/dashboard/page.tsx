import Link from 'next/link';
import { getServerSession } from 'next-auth';
import { redirect } from 'next/navigation';
import { authOptions } from '@/lib/auth';
import { backend, type ReviewSummary, type Repo } from '@/lib/api';
import { ScoreBadge } from '@/components/ScoreBadge';
import { AssessmentBadge } from '@/components/AssessmentBadge';
import { RefreshReviews } from '@/components/RefreshReviews';

export const dynamic = 'force-dynamic';

type SearchParams = {
  repo?: string;
  assessment?: string;
};

export default async function Dashboard({ searchParams }: { searchParams: SearchParams }) {
  const session = await getServerSession(authOptions);
  if (!session) redirect('/api/auth/signin');

  const userId = (session.user as { backendUserId?: string }).backendUserId;
  if (!userId) {
    return (
      <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm dark:border-amber-800 dark:bg-amber-900/30">
        Backend is not reachable. Ensure the FastAPI server is running on{' '}
        <code>BACKEND_URL</code>.
      </div>
    );
  }

  const qs = new URLSearchParams({ user_id: userId, limit: '50' });
  if (searchParams.repo) qs.set('repository_id', searchParams.repo);
  if (searchParams.assessment) qs.set('assessment', searchParams.assessment);

  const [{ items }, { items: repos }] = await Promise.all([
    backend<{ items: ReviewSummary[] }>(`/reviews?${qs.toString()}`, { revalidate: false }),
    backend<{ items: Repo[] }>(`/repositories?user_id=${userId}`, { revalidate: false }),
  ]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Reviews</h1>
        <div className="flex items-center gap-2">
          <RefreshReviews />
          <Link
            href="/settings"
            className="rounded border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
          >
            Manage repos
          </Link>
        </div>
      </div>

      <Filters repos={repos.filter((r) => r.connected)} current={searchParams} />

      {items.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-950 dark:text-slate-400">
              <tr>
                <th className="px-4 py-2">PR</th>
                <th className="px-4 py-2">Repo</th>
                <th className="px-4 py-2">Score</th>
                <th className="px-4 py-2">Assessment</th>
                <th className="px-4 py-2">When</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
              {items.map((r) => (
                <tr key={r.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                  <td className="px-4 py-3">
                    <Link href={`/reviews/${r.id}`} className="font-medium text-brand-600 hover:underline">
                      #{r.pr_number} {r.pr_title}
                    </Link>
                    <div className="text-xs text-slate-500">by {r.pr_author}</div>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-600 dark:text-slate-400">
                    {r.repository_full_name}
                  </td>
                  <td className="px-4 py-3">
                    <ScoreBadge score={r.score} />
                  </td>
                  <td className="px-4 py-3">
                    <AssessmentBadge assessment={r.assessment} />
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500">
                    {new Date(r.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Filters({ repos, current }: { repos: Repo[]; current: SearchParams }) {
  return (
    <form className="flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900">
      <label className="flex flex-col gap-1 text-xs">
        <span className="font-medium text-slate-600 dark:text-slate-300">Repository</span>
        <select
          name="repo"
          defaultValue={current.repo ?? ''}
          className="rounded border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-950"
        >
          <option value="">All</option>
          {repos.map((r) => (
            <option key={r.id} value={r.id}>
              {r.full_name}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-xs">
        <span className="font-medium text-slate-600 dark:text-slate-300">Assessment</span>
        <select
          name="assessment"
          defaultValue={current.assessment ?? ''}
          className="rounded border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-950"
        >
          <option value="">All</option>
          <option value="approve">Approve</option>
          <option value="request_changes">Request changes</option>
          <option value="comment">Comment</option>
        </select>
      </label>
      <button
        type="submit"
        className="rounded bg-slate-900 px-3 py-1.5 text-xs font-medium text-white dark:bg-white dark:text-slate-900"
      >
        Apply
      </button>
    </form>
  );
}

function EmptyState() {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center dark:border-slate-700 dark:bg-slate-900">
      <h3 className="font-semibold">No reviews yet</h3>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
        Connect a repository in <Link href="/settings" className="text-brand-600 hover:underline">Settings</Link> and
        open a pull request to trigger your first review.
      </p>
    </div>
  );
}
