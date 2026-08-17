"""
auth.py
Minimal username/password auth. Passwords are hashed with bcrypt before
they ever touch the database.
"""

import bcrypt
import database as db


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def signup(username: str, password: str):
    """Returns (success, message)."""
    username = username.strip()
    if not username or not password:
        return False, "Username and password are required."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    if db.get_user_by_username(username):
        return False, "That username is already taken."
    db.create_user(username, hash_password(password))
    return True, "Account created. You can log in now."


def login(username: str, password: str):
    """Returns (user_dict_or_None, message)."""
    user = db.get_user_by_username(username.strip())
    if not user or not verify_password(password, user["password_hash"]):
        return None, "Invalid username or password."
    return user, "Logged in."
