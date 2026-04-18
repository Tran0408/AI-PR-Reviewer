TRUNCATION_NOTICE = "\n\n... [DIFF TRUNCATED — too large for model context] ..."


def truncate_diff(diff: str, max_chars: int) -> tuple[str, bool]:
    """
    Character-based diff truncation (~4 chars per token heuristic).
    Returns (possibly-truncated-diff, was_truncated).
    """
    if len(diff) <= max_chars:
        return diff, False
    keep = max_chars - len(TRUNCATION_NOTICE)
    if keep <= 0:
        return diff[:max_chars], True
    return diff[:keep] + TRUNCATION_NOTICE, True
