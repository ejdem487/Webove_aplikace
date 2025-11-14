
from fastapi import HTTPException, Request, status, Depends
from sqlalchemy.orm import Session
from .db import get_db
from .models import User

# Mapping of roles to their privilege levels. Higher number means more privileges.
ROLE_HIERARCHY = {
    "USER": 1,
    "MANAGER": 2,
    "ADMIN": 3,
}

def _highest_role(user: User) -> str:
    if not user.role_names:
        return "USER"
    return max(user.role_names, key=lambda r: ROLE_HIERARCHY.get(r, 0))

def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    request.session["role"] = _highest_role(user)
    return user

def role_required(*required_roles: str):
    """
    Dependency that checks if the current user satisfies at least one of the required roles.
    A user with a higher role automatically satisfies lower-level roles.
    """
    if not required_roles:
        raise ValueError("role_required needs at least one role.")

    def dep(user: User = Depends(current_user)):
        user_role = _highest_role(user)
        user_level = ROLE_HIERARCHY.get(user_role, 0)

        allowed = any(user_level >= ROLE_HIERARCHY.get(role, 0) for role in required_roles)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Allowed roles: {', '.join(required_roles)}."
            )
        return user

    return dep

def highest_role(user: User) -> str:
    """
    Helper exposed for other modules that need to render the current user's dominant role.
    """
    return _highest_role(user)
