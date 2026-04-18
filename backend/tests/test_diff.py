from app.utils.diff import TRUNCATION_NOTICE, truncate_diff


def test_no_truncation_under_limit():
    out, t = truncate_diff("abc", 100)
    assert out == "abc"
    assert t is False


def test_truncates_when_over():
    big = "x" * 200
    out, t = truncate_diff(big, 100)
    assert t is True
    assert len(out) <= 100
    assert TRUNCATION_NOTICE in out or len(out) == 100


def test_truncation_notice_preserved_when_possible():
    big = "y" * 1000
    out, t = truncate_diff(big, 500)
    assert t is True
    assert out.endswith(TRUNCATION_NOTICE)
