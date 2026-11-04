import base64, hashlib, hmac, json, time
from pwdlib import PasswordHash
from app.config import settings
_passwords = PasswordHash.recommended()
def hash_password(password: str) -> str:
    if len(password) < 12: raise ValueError("Password must contain at least 12 characters")
    return _passwords.hash(password)
def verify_password(password: str, password_hash: str) -> bool: return _passwords.verify(password, password_hash)
def _b64(data: bytes) -> str: return base64.urlsafe_b64encode(data).rstrip(b"=").decode()
def create_access_token(subject: str) -> str:
    header = _b64(json.dumps({"alg":"HS256","typ":"JWT"}, separators=(",",":")).encode())
    payload = _b64(json.dumps({"sub":subject,"iss":settings.jwt_issuer,"exp":int(time.time()) + settings.access_token_minutes*60}, separators=(",",":")).encode())
    signing = f"{header}.{payload}".encode()
    return f"{header}.{payload}.{_b64(hmac.new(settings.jwt_secret.encode(), signing, hashlib.sha256).digest())}"
def decode_access_token(token: str) -> str:
    try:
        header, payload, signature = token.split(".")
        signing = f"{header}.{payload}".encode()
        expected = _b64(hmac.new(settings.jwt_secret.encode(), signing, hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected): raise ValueError()
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if claims.get("iss") != settings.jwt_issuer or claims.get("exp", 0) < time.time(): raise ValueError()
        return claims["sub"]
    except Exception as exc: raise ValueError("Invalid access token") from exc
