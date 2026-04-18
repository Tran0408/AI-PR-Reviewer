import hashlib
import re

from app.services.review.base import ReviewProvider
from app.services.review.schema import (
    InlineComment,
    Issue,
    ReviewOutput,
    ReviewRequest,
)


class MockProvider(ReviewProvider):
    """
    Deterministic review generator for offline dev. No network.
    Picks first few '+' lines of diff and produces plausible comments.
    """

    name = "mock"

    async def review(self, req: ReviewRequest) -> ReviewOutput:
        added = _extract_added_lines(req.diff)[:3]
        digest = int(hashlib.sha256(req.diff.encode()).hexdigest(), 16)
        score = 5 + (digest % 5)  # 5..9

        comments: list[InlineComment] = []
        for file_path, lineno, text in added:
            sev = "minor" if "TODO" not in text else "major"
            comments.append(
                InlineComment(
                    file_path=file_path,
                    line_number=lineno,
                    severity=sev,
                    comment=f"[mock] Consider reviewing this change: `{text.strip()[:80]}`",
                    suggestion=None,
                )
            )

        assessment = "approve" if score >= 8 else "comment"
        if any(c.severity in ("major", "critical") for c in comments):
            assessment = "request_changes"

        return ReviewOutput(
            summary=(
                f"[mock review] PR #{req.pr_number} in {req.repo_full_name}. "
                f"Diff spans {len(req.diff)} chars. "
                + ("Diff was truncated. " if req.truncated else "")
                + "This is a deterministic placeholder review — set REVIEW_PROVIDER=openrouter for real analysis."
            ),
            overall_assessment=assessment,
            score=score,
            inline_comments=comments,
            security_issues=[
                Issue(
                    file_path=None,
                    line_number=None,
                    severity="info",
                    description="No security issues detected by mock provider.",
                )
            ],
            performance_issues=[],
            positive_highlights=[
                "Code compiles (assumed by mock).",
                "Diff is well-scoped.",
            ],
        )


_HUNK_HEADER_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
_DIFF_FILE_RE = re.compile(r"^\+\+\+ b/(.+)$")


def _extract_added_lines(diff: str) -> list[tuple[str, int, str]]:
    result: list[tuple[str, int, str]] = []
    current_file: str | None = None
    new_lineno = 0
    for line in diff.splitlines():
        m_file = _DIFF_FILE_RE.match(line)
        if m_file:
            current_file = m_file.group(1)
            new_lineno = 0
            continue
        m_hunk = _HUNK_HEADER_RE.match(line)
        if m_hunk:
            new_lineno = int(m_hunk.group(1)) - 1
            continue
        if not current_file:
            continue
        if line.startswith("+") and not line.startswith("+++"):
            new_lineno += 1
            result.append((current_file, new_lineno, line[1:]))
        elif line.startswith("-") and not line.startswith("---"):
            continue
        else:
            new_lineno += 1
    return result
