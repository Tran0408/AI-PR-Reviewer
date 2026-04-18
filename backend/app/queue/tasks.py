from __future__ import annotations

import logging
from typing import Any

import httpx
from prisma import Json

from app.config import get_settings
from app.db import connect
from app.services.github import GitHubClient, map_assessment_to_event
from app.services.review import get_provider
from app.services.review.schema import ReviewRequest
from app.utils.diff import truncate_diff

log = logging.getLogger(__name__)


async def process_pr_event(ctx: dict, event: dict[str, Any]) -> dict[str, Any]:
    """
    ARQ task. Enqueued from webhook handler.
    event keys: repo_full_name, pr_number, commit_sha, pr_title, pr_author, pr_url,
                pr_body, repository_id, installation_token
    """
    settings = get_settings()
    db = await connect()

    owner, repo = event["repo_full_name"].split("/", 1)
    number = int(event["pr_number"])
    token = event["installation_token"]

    gh = GitHubClient(token=token)

    try:
        diff = await gh.get_pr_diff(owner, repo, number)
    except Exception as e:
        log.exception("Failed to fetch diff for %s#%s", event["repo_full_name"], number)
        await _persist_error(db, event, f"fetch_diff_failed: {e}")
        raise

    truncated_diff, was_truncated = truncate_diff(diff, settings.diff_max_chars)

    provider = get_provider()
    req = ReviewRequest(
        repo_full_name=event["repo_full_name"],
        pr_number=number,
        pr_title=event["pr_title"],
        pr_body=event.get("pr_body"),
        diff=truncated_diff,
        truncated=was_truncated,
    )

    try:
        result = await provider.review(req)
    except Exception as e:
        log.exception("LLM review failed for %s#%s", event["repo_full_name"], number)
        await _persist_error(db, event, f"llm_failed: {e}")
        raise

    comments = [
        {
            "path": c.file_path,
            "line": c.line_number,
            "side": "RIGHT",
            "body": _format_comment(c.comment, c.severity, c.suggestion),
        }
        for c in result.inline_comments
    ]

    review_body = _format_review_body(result)
    event_str = map_assessment_to_event(result.overall_assessment)

    github_review_id: int | None = None
    post_error: str | None = None
    try:
        gh_resp = await gh.post_review(
            owner,
            repo,
            number,
            commit_id=event["commit_sha"],
            body=review_body,
            event=event_str,
            comments=comments,
        )
        github_review_id = gh_resp.get("id")
    except httpx.HTTPStatusError as e:
        body_text = e.response.text if e.response is not None else ""
        is_self_pr = e.response is not None and e.response.status_code == 422 and "own pull request" in body_text
        if is_self_pr and event_str != "COMMENT":
            log.warning("Self-PR detected for %s#%s, retrying as COMMENT", event["repo_full_name"], number)
            try:
                gh_resp = await gh.post_review(
                    owner,
                    repo,
                    number,
                    commit_id=event["commit_sha"],
                    body=review_body,
                    event="COMMENT",
                    comments=comments,
                )
                github_review_id = gh_resp.get("id")
            except Exception as e2:
                log.exception("Retry as COMMENT failed for %s#%s", event["repo_full_name"], number)
                post_error = f"post_review_failed: {e2}"
        else:
            log.exception("Failed to post review to GitHub for %s#%s", event["repo_full_name"], number)
            post_error = f"post_review_failed: {e}"
    except Exception as e:
        log.exception("Failed to post review to GitHub for %s#%s", event["repo_full_name"], number)
        post_error = f"post_review_failed: {e}"

    await db.review.create(
        data={
            "repository": {"connect": {"id": event["repository_id"]}},
            "prNumber": number,
            "prTitle": event["pr_title"],
            "prAuthor": event["pr_author"],
            "prUrl": event["pr_url"],
            "commitSha": event["commit_sha"],
            "score": result.score,
            "assessment": result.overall_assessment,
            "summary": result.summary,
            "payload": Json(result.model_dump(mode="json")),
            "postedToGithub": github_review_id is not None,
            "githubReviewId": github_review_id,
            "error": post_error,
        }
    )
    return {"ok": True, "score": result.score, "posted": github_review_id is not None}


async def _persist_error(db, event: dict[str, Any], message: str) -> None:
    try:
        await db.review.create(
            data={
                "repository": {"connect": {"id": event["repository_id"]}},
                "prNumber": int(event["pr_number"]),
                "prTitle": event.get("pr_title", ""),
                "prAuthor": event.get("pr_author", ""),
                "prUrl": event.get("pr_url", ""),
                "commitSha": event.get("commit_sha", ""),
                "score": 1,
                "assessment": "comment",
                "summary": f"Review failed: {message}",
                "payload": Json({"error": message}),
                "postedToGithub": False,
                "error": message,
            }
        )
    except Exception:
        log.exception("Failed to persist error record")


def _format_comment(comment: str, severity: str, suggestion: str | None) -> str:
    icon = {"info": "💡", "minor": "🟡", "major": "🟠", "critical": "🔴"}.get(severity, "💬")
    body = f"{icon} **{severity.upper()}** — {comment}"
    if suggestion:
        body += f"\n\n```suggestion\n{suggestion}\n```"
    return body


def _format_review_body(result) -> str:
    lines = [
        "## AI Code Review",
        "",
        f"**Score:** {result.score}/10  |  **Assessment:** `{result.overall_assessment}`",
        "",
    ]
    if getattr(result, "title_matches_diff", True) is False:
        note = getattr(result, "title_mismatch_note", None) or "Title does not match the diff."
        lines += [f"> ⚠️ **Title mismatch:** {note}", ""]
    lines += ["### Summary", result.summary]
    improvements = getattr(result, "improvement_suggestions", None) or []
    if improvements:
        lines += ["", "### How to improve this PR", *[f"- {s}" for s in improvements]]
    if result.security_issues:
        lines += ["", "### Security", *[f"- [{i.severity}] {i.description}" for i in result.security_issues]]
    if result.performance_issues:
        lines += ["", "### Performance", *[f"- [{i.severity}] {i.description}" for i in result.performance_issues]]
    if result.positive_highlights:
        lines += ["", "### Highlights", *[f"- {h}" for h in result.positive_highlights]]
    lines += ["", "_Automated by AI PR Reviewer._"]
    return "\n".join(lines)
