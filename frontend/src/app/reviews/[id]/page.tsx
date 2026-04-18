import Link from 'next/link';
import { notFound } from 'next/navigation';
import { backend, type ReviewDetail } from '@/lib/api';
import { ScoreBadge } from '@/components/ScoreBadge';
import { AssessmentBadge } from '@/components/AssessmentBadge';
import { SeverityBadge } from '@/components/SeverityBadge';
import { PRActions } from '@/components/PRActions';

export const dynamic = 'force-dynamic';

export default async function ReviewPage({ params }: { params: { id: string } }) {
  let review: ReviewDetail;
  try {
    review = await backend<ReviewDetail>(`/reviews/${params.id}`, { revalidate: false });
  } catch {
    notFound();
  }

  const p = review.payload;

  return (
    <div className="space-y-6">
      <div>
        <Link href="/dashboard" className="text-sm text-slate-500 hover:underline">
          ← Back to dashboard
        </Link>
      </div>

      <header className="flex flex-wrap items-start justify-between gap-4 rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
        <div>
          <div className="text-xs text-slate-500">{review.repository_full_name}</div>
          <h1 className="mt-1 text-2xl font-bold">
            #{review.pr_number} — {review.pr_title}
          </h1>
          <div className="mt-1 text-sm text-slate-500">by {review.pr_author}</div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <ScoreBadge score={review.score} />
            <AssessmentBadge assessment={review.assessment} />
            <a
              href={review.pr_url}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-brand-600 hover:underline"
            >
              View on GitHub ↗
            </a>
            {!review.posted_to_github && (
              <span className="rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-900 dark:bg-amber-900/40 dark:text-amber-300">
                Not posted to GitHub
              </span>
            )}
          </div>
        </div>
        <div className="text-right text-xs text-slate-500">
          {new Date(review.created_at).toLocaleString()}
        </div>
      </header>

      <PRActions reviewId={review.id} />

      <Section title="Summary">
        <p className="text-sm leading-relaxed text-slate-700 dark:text-slate-300">{p.summary}</p>
      </Section>

      {(p.positive_highlights?.length ?? 0) > 0 && (
        <Section title="Highlights">
          <ul className="space-y-1 text-sm">
            {p.positive_highlights!.map((h, i) => (
              <li key={i} className="flex gap-2">
                <span>✅</span>
                <span>{h}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {(p.security_issues?.length ?? 0) > 0 && (
        <Section title="Security">
          <IssueList items={p.security_issues!} />
        </Section>
      )}

      {(p.performance_issues?.length ?? 0) > 0 && (
        <Section title="Performance">
          <IssueList items={p.performance_issues!} />
        </Section>
      )}

      {(p.inline_comments?.length ?? 0) > 0 && (
        <Section title={`Inline comments (${p.inline_comments!.length})`}>
          <ul className="space-y-3">
            {p.inline_comments!.map((c, i) => (
              <li
                key={i}
                className="rounded-lg border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900"
              >
                <div className="flex items-center gap-2 text-xs">
                  <SeverityBadge severity={c.severity} />
                  <code className="font-mono text-slate-600 dark:text-slate-300">
                    {c.file_path}:{c.line_number}
                  </code>
                </div>
                <p className="mt-2 text-sm">{c.comment}</p>
                {c.suggestion && (
                  <pre className="mt-2 overflow-x-auto rounded bg-slate-50 p-2 text-xs dark:bg-slate-950">
                    <code>{c.suggestion}</code>
                  </pre>
                )}
              </li>
            ))}
          </ul>
        </Section>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">{title}</h2>
      {children}
    </section>
  );
}

function IssueList({
  items,
}: {
  items: { file_path: string | null; line_number: number | null; severity: string; description: string }[];
}) {
  return (
    <ul className="space-y-2 text-sm">
      {items.map((it, i) => (
        <li key={i} className="flex gap-3">
          <SeverityBadge severity={it.severity} />
          <div>
            {it.file_path && (
              <code className="mr-2 font-mono text-xs text-slate-500">
                {it.file_path}
                {it.line_number ? `:${it.line_number}` : ''}
              </code>
            )}
            <span>{it.description}</span>
          </div>
        </li>
      ))}
    </ul>
  );
}
