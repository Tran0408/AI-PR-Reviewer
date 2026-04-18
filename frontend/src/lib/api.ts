const BACKEND =
  process.env.BACKEND_URL ?? process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000';

type FetchOpts = {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: unknown;
  revalidate?: number | false;
};

export async function backend<T>(path: string, opts: FetchOpts = {}): Promise<T> {
  const res = await fetch(`${BACKEND}${path}`, {
    method: opts.method ?? 'GET',
    headers: { 'Content-Type': 'application/json' },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
    next: opts.revalidate === false ? undefined : { revalidate: opts.revalidate ?? 0 },
    cache: opts.revalidate === false ? 'no-store' : undefined,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Backend ${res.status}: ${text.slice(0, 500)}`);
  }
  return (await res.json()) as T;
}

export type ReviewSummary = {
  id: string;
  repository_id: string;
  repository_full_name: string | null;
  pr_number: number;
  pr_title: string;
  pr_author: string;
  pr_url: string;
  commit_sha: string;
  score: number;
  assessment: 'approve' | 'request_changes' | 'comment';
  summary: string;
  posted_to_github: boolean;
  error: string | null;
  created_at: string;
};

export type InlineComment = {
  file_path: string;
  line_number: number;
  severity: 'info' | 'minor' | 'major' | 'critical';
  comment: string;
  suggestion: string | null;
};

export type Issue = {
  file_path: string | null;
  line_number: number | null;
  severity: 'info' | 'minor' | 'major' | 'critical';
  description: string;
};

export type ReviewDetail = ReviewSummary & {
  payload: {
    summary: string;
    overall_assessment: string;
    score: number;
    inline_comments: InlineComment[];
    security_issues: Issue[];
    performance_issues: Issue[];
    positive_highlights: string[];
  };
};

export type Repo = {
  id: string;
  full_name: string;
  owner: string;
  name: string;
  private: boolean;
  connected: boolean;
  webhook_id: number | null;
};
