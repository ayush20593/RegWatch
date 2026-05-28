import bcrypt
from itsdangerous import URLSafeTimedSerializer, BadSignature
from ..config import settings

_signer = URLSafeTimedSerializer(settings.secret_key)


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def make_session_token(user_id: int, org_id: int) -> str:
    return _signer.dumps({"user_id": user_id, "org_id": org_id})


def decode_session_token(token: str, max_age: int = 86400 * 30) -> dict | None:
    try:
        return _signer.loads(token, max_age=max_age)
    except BadSignature:
        return None
