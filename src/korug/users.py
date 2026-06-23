"""User management: lookup, creation, authentication, and admin seeding."""
import logging
import secrets
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from subdomain_hunter.auth_utils import hash_password, verify_password
from subdomain_hunter.config import get_settings
from subdomain_hunter.models import User

logger = logging.getLogger(__name__)
settings = get_settings()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Return the user with the given username, or None."""
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Return the user with the given email, or None."""
    return db.query(User).filter(User.email == email).first()


def create_user(
    db: Session,
    username: str,
    email: str,
    password: str,
    role: str = "admin",
) -> User:
    """Create a new user with a bcrypt-hashed password.

    Raises ValueError if the username or email is already taken.
    """
    if get_user_by_username(db, username):
        raise ValueError(f"Username '{username}' already exists")
    if get_user_by_email(db, email):
        raise ValueError(f"Email '{email}' already exists")

    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Return the user if credentials are valid and the account is active.

    Uses a constant-ish work factor even when the user is missing (by verifying
    against a dummy hash) to reduce username-enumeration via timing.
    """
    user = get_user_by_username(db, username)
    if user is None:
        # Perform a dummy verification to keep timing roughly uniform.
        verify_password(password, _DUMMY_HASH)
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def record_login(db: Session, user: User) -> None:
    """Stamp the user's last_login timestamp."""
    user.last_login = datetime.utcnow()
    db.add(user)
    db.commit()


def seed_admin_user(db: Session) -> None:
    """Create the initial admin account on first run if no users exist.

    The password comes from ADMIN_PASSWORD; if unset, a strong random password is
    generated and logged once so there is never a weak default credential.
    """
    if db.query(User).count() > 0:
        return

    password = settings.admin_password
    generated = False
    if not password:
        password = secrets.token_urlsafe(16)
        generated = True

    user = create_user(
        db,
        username=settings.admin_username,
        email=settings.admin_email,
        password=password,
        role="admin",
    )

    if generated:
        logger.warning(
            "=" * 70
            + "\nNo ADMIN_PASSWORD set. Created initial admin account:\n"
            f"    username: {user.username}\n"
            f"    password: {password}\n"
            "Store this now and change it after first login. It will not be "
            "shown again.\n" + "=" * 70
        )
    else:
        logger.info("Seeded initial admin user '%s'", user.username)


# Bcrypt hash of a random string, used only for timing equalisation.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))
