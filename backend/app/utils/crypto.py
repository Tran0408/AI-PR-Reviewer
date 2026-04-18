import hashlib
import hmac


def verify_github_signature(secret: str, payload: bytes, signature_header: str | None) -> bool:
    """
    Verify GitHub webhook HMAC-SHA256 signature.
    Header format: 'sha256=<hex>'.
    Constant-time compare to avoid timing attacks.
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    sent = signature_header.split("=", 1)[1].strip()
    mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
    expected = mac.hexdigest()
    return hmac.compare_digest(expected, sent)
