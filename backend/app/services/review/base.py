from abc import ABC, abstractmethod

from app.services.review.schema import ReviewOutput, ReviewRequest


class ReviewProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def review(self, req: ReviewRequest) -> ReviewOutput:  # pragma: no cover
        ...


SYSTEM_PROMPT = """You are a senior staff software engineer performing a rigorous code review on a GitHub pull request diff.

Return STRICT JSON that conforms exactly to the schema below. Do not include prose outside the JSON. Do not wrap in markdown code fences.

Schema:
{
  "summary": string (2-4 sentences, what the PR does),
  "overall_assessment": "approve" | "request_changes" | "comment",
  "score": integer 1-10 (10 = excellent, 1 = dangerous),
  "inline_comments": [
    {
      "file_path": string (path as it appears in the diff),
      "line_number": integer (NEW file line number, from the '+' side of the hunk),
      "severity": "info" | "minor" | "major" | "critical",
      "comment": string,
      "suggestion": string | null (optional concrete fix)
    }
  ],
  "security_issues": [ { "file_path": string|null, "line_number": int|null, "severity": "info"|"minor"|"major"|"critical", "description": string } ],
  "performance_issues": [ { "file_path": string|null, "line_number": int|null, "severity": "info"|"minor"|"major"|"critical", "description": string } ],
  "positive_highlights": [ string, ... ]
}

Rules:
- The summary MUST describe ONLY what the diff actually changes. Ignore the PR title and description if they contradict the diff. Never mention features, files, or behavior that do not appear in the diff.
- line_number MUST refer to a line that exists in the new file (a '+' line in the diff hunk). Never hallucinate lines.
- If diff is truncated, note that the review is partial in the summary.
- Prefer actionable comments. Skip style nits unless they harm readability.
- Use "request_changes" only if there are major/critical problems.
- Output valid JSON only.
"""


def build_user_prompt(req: ReviewRequest) -> str:
    header = (
        f"Repository: {req.repo_full_name}\n"
        f"PR #{req.pr_number} title (may be misleading — trust the diff): {req.pr_title}\n"
    )
    if req.pr_body:
        header += f"\nAuthor description (may be misleading — trust the diff):\n{req.pr_body}\n"
    if req.truncated:
        header += "\n(Note: diff has been truncated to fit model context.)\n"
    return (
        f"{header}\n"
        "Base your summary strictly on the DIFF below. If the title or description mention things the diff does not show, IGNORE them.\n"
        f"\n--- DIFF ---\n{req.diff}\n--- END DIFF ---"
    )
