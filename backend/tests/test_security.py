import pytest
from app.security import create_access_token, decode_access_token, hash_password, verify_password

def test_password_hash_and_verify():
    hashed = hash_password("a-long-test-password-123")
    assert hashed != "a-long-test-password-123"
    assert verify_password("a-long-test-password-123", hashed)
    assert not verify_password("wrong-password-123", hashed)

def test_password_policy():
    with pytest.raises(ValueError):
        hash_password("short")

def test_access_token_round_trip():
    token = create_access_token("user-123")
    assert decode_access_token(token) == "user-123"

def test_access_token_rejects_tampering():
    token = create_access_token("user-123")
    with pytest.raises(ValueError):
        decode_access_token(token + "x")
