import re
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User

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


PASSWORD_MIN_LENGTH = 8


async def change_password(
    db: AsyncSession,
    user: User,
    current_password: str,
    new_password: str,
    confirm_password: str,
) -> tuple[bool, dict[str, str], int | None]:
    """
    Change a user's own password.

    Returns `(ok, field_errors, new_session_version)`. `field_errors` is empty
    on success. Bumping the session version ends the user's other sessions;
    the caller must copy the returned version into the current cookie so the
    session making the change survives.
    """
    errors: dict[str, str] = {}

    if not current_password:
        errors["current_password"] = "Enter your current password."
    elif not verify_password(current_password, user.password_hash):
        errors["current_password"] = "That is not your current password."

    if not new_password:
        errors["new_password"] = "Enter a new password."
    elif len(new_password) < PASSWORD_MIN_LENGTH:
        errors["new_password"] = f"Use at least {PASSWORD_MIN_LENGTH} characters."

    if not confirm_password:
        errors["confirm_password"] = "Re-enter your new password."
    elif new_password and new_password != confirm_password:
        errors["confirm_password"] = "The two passwords do not match."

    if errors:
        return False, errors, None

    if verify_password(new_password, user.password_hash):
        return False, {"new_password": "Choose a password you have not used before."}, None

    new_version = user.session_version + 1
    user.password_hash = hash_password(new_password)
    user.session_version = new_version
    await db.commit()
    return True, {}, new_version


def generate_csrf_token(session_id: str) -> str:
    return _csrf_serializer.dumps(session_id, salt=_CSRF_SALT)


def verify_csrf_token(token: str, session_id: str, max_age: int = 3600) -> bool:
    try:
        value = _csrf_serializer.loads(token, salt=_CSRF_SALT, max_age=max_age)
        return value == session_id
    except (BadSignature, SignatureExpired):
        return False
