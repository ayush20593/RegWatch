from app.auth.utils import hash_password, verify_password, make_session_token, decode_session_token


def test_password_round_trip():
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_session_token_round_trip():
    token = make_session_token(user_id=42, org_id=7)
    payload = decode_session_token(token)
    assert payload["user_id"] == 42
    assert payload["org_id"] == 7


def test_invalid_token_returns_none():
    assert decode_session_token("garbage") is None
