import re
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from app.config import settings

ADMIN_EMAIL = "dantubhavyasree@gmail.com"
_STUDENT_EMAIL_PATTERN = re.compile(r"^[a-z0-9]+@bvrithyderabad\.edu\.in$", re.IGNORECASE)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_csrf_serializer = URLSafeTimedSerializer(settings.SESSION_SECRET_KEY)
_CSRF_SALT = "csrf-token"


def is_valid_student_email(email: str) -> bool:
    return bool(_STUDENT_EMAIL_PATTERN.match(email.strip().lower()))


def student_id_from_email(email: str) -> str:
    """Extract student ID from email. 26wh1a05k2@bvrithyderabad.edu.in → 26WH1A05K2"""
    return email.strip().split("@")[0].upper()


def is_valid_email_for_login(email: str) -> tuple[bool, str | None]:
    email = email.strip().lower()
    if email == ADMIN_EMAIL:
        return True, None
    if is_valid_student_email(email):
        return True, None
    return False, "Enter your college email (e.g. 25wh1a05a2@bvrithyderabad.edu.in)"


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def generate_csrf_token(session_id: str) -> str:
    return _csrf_serializer.dumps(session_id, salt=_CSRF_SALT)


def verify_csrf_token(token: str, session_id: str, max_age: int = 3600) -> bool:
    try:
        value = _csrf_serializer.loads(token, salt=_CSRF_SALT, max_age=max_age)
        return value == session_id
    except (BadSignature, SignatureExpired):
        return False
