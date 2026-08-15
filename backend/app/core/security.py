"""
Authentication/authorization abstraction.

Phase 1: stubbed out so routes can depend on `get_current_user` without
the whole app being blocked on Firebase Auth wiring. Once Firebase Auth
is connected (later phase), swap the body of `get_current_user` to verify
the ID token from the Authorization header — the function signature and
call sites elsewhere in the app should not need to change.
"""
from typing import Optional

from fastapi import Header


class CurrentUser:
    def __init__(self, uid: str, email: Optional[str] = None):
        self.uid = uid
        self.email = email


async def get_current_user(authorization: Optional[str] = Header(default=None)) -> CurrentUser:
    """
    Placeholder dependency. Returns a fixed demo user for now so protected
    routes can be wired up ahead of real auth. Replace with Firebase ID
    token verification when auth is implemented.
    """
    return CurrentUser(uid="demo-user", email="demo@example.com")
