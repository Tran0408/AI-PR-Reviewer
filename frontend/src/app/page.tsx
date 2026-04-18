import Link from 'next/link';

export default function Home() {
  return (
    <div className="mx-auto max-w-3xl py-12">
      <h1 className="text-4xl font-bold tracking-tight">AI PR Reviewer</h1>
      <p className="mt-4 text-lg text-slate-600 dark:text-slate-300">
        Connect your GitHub repositories and get automated, structured AI code reviews on every pull
        request — posted inline, stored in a dashboard.
      </p>
      <div className="mt-8 grid gap-4 sm:grid-cols-3">
        <Feature
          title="Inline comments"
          body="Severity-tagged inline reviews posted directly on PR diff."
        />
        <Feature
          title="Score + assessment"
          body="1–10 quality score plus approve / request changes / comment."
        />
        <Feature
          title="Security + perf"
          body="Flags potential security and performance issues."
        />
      </div>
      <div className="mt-10 flex gap-3">
        <Link
          href="/dashboard"
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          Open dashboard
        </Link>
        <Link
          href="/settings"
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
        >
          Connect a repo
        </Link>
      </div>
    </div>
  );
}

function Feature({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <h3 className="font-semibold">{title}</h3>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{body}</p>
    </div>
  );
}
