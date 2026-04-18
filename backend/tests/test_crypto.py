import hashlib
import hmac

from app.utils.crypto import verify_github_signature


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_signature_valid():
    body = b'{"hello":"world"}'
    assert verify_github_signature("s3cret", body, _sign("s3cret", body)) is True


def test_signature_invalid():
    body = b'{"hello":"world"}'
    assert verify_github_signature("s3cret", body, _sign("wrong", body)) is False


def test_signature_missing_header():
    assert verify_github_signature("s3cret", b"x", None) is False


def test_signature_malformed_header():
    assert verify_github_signature("s3cret", b"x", "md5=abc") is False
