from typing import Literal

from pydantic import BaseModel, Field, field_validator

Severity = Literal["info", "minor", "major", "critical"]
Assessment = Literal["approve", "request_changes", "comment"]


class InlineComment(BaseModel):
    file_path: str
    line_number: int = Field(..., ge=1)
    severity: Severity = "minor"
    comment: str
    suggestion: str | None = None


class Issue(BaseModel):
    file_path: str | None = None
    line_number: int | None = None
    severity: Severity = "minor"
    description: str


class ReviewOutput(BaseModel):
    summary: str
    overall_assessment: Assessment
    score: int = Field(..., ge=1, le=10)
    inline_comments: list[InlineComment] = Field(default_factory=list)
    security_issues: list[Issue] = Field(default_factory=list)
    performance_issues: list[Issue] = Field(default_factory=list)
    positive_highlights: list[str] = Field(default_factory=list)

    @field_validator("score")
    @classmethod
    def clamp_score(cls, v: int) -> int:
        return max(1, min(10, v))


class ReviewRequest(BaseModel):
    repo_full_name: str
    pr_number: int
    pr_title: str
    pr_body: str | None = None
    diff: str
    truncated: bool = False
