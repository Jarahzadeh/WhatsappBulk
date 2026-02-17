import hashlib
import hmac


def verify_webhook_signature(payload: bytes, signature: str, app_secret: str) -> bool:
    if not signature or not app_secret:
        return False
    expected = "sha256=" + hmac.new(app_secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
