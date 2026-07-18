import hashlib
import hmac

from app.github.security import verify_github_signature


def test_validates_github_hmac_signature() -> None:
    secret, payload = "test-secret", b'{"action":"created"}'
    signature = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    assert verify_github_signature(payload, signature, secret)
    assert not verify_github_signature(payload, "sha256=invalid", secret)
