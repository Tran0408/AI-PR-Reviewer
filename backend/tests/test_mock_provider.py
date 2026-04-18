import pytest

from app.services.review.mock import MockProvider
from app.services.review.schema import ReviewRequest


SAMPLE_DIFF = """diff --git a/app.py b/app.py
index 0000000..1111111 100644
--- a/app.py
+++ b/app.py
@@ -1,3 +1,6 @@
 import os
+
+def add(a, b):
+    return a + b
 """


@pytest.mark.asyncio
async def test_mock_review_schema_valid():
    p = MockProvider()
    req = ReviewRequest(
        repo_full_name="acme/app",
        pr_number=7,
        pr_title="Add add()",
        pr_body="",
        diff=SAMPLE_DIFF,
        truncated=False,
    )
    result = await p.review(req)
    assert 1 <= result.score <= 10
    assert result.overall_assessment in ("approve", "request_changes", "comment")
    assert isinstance(result.inline_comments, list)
