import uuid
from datetime import datetime, timezone
from hashlib import sha256


def encode_password(password: str) -> str:
    return sha256(str(password).encode()).hexdigest()


def now() -> datetime:
    return datetime.now(tz=timezone.utc)


def generate_uuid() -> str:
    return str(uuid.uuid4())
