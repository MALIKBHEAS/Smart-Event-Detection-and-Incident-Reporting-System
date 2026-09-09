"""Centralized model registry for the application.

Import every SQLAlchemy model here so that importing app.models will
register all ORM classes and their Table objects on the Declarative Base
metadata. This ensures Alembic autogenerate sees all tables by importing
app.models (the alembic env discovery walks the app package and imports
modules under it).

Keep this module free from heavy side-effects (no DB connections, no
service imports) to avoid circular imports and to keep model import safe
in migration environments.
"""

# Import model modules to ensure classes register with Base.metadata.
# Keep imports local to model modules only (no cross-module logic) to avoid
# circular imports. If new model files are added, import them here.
from .camera import Camera  # noqa: F401
from .event import Event  # noqa: F401
from .notification import Notification  # noqa: F401
from .refresh_token import RefreshToken  # noqa: F401
from .report import Report  # noqa: F401
from .settings import AppSettingsRow  # noqa: F401
from .user import Role, User, user_roles  # noqa: F401

__all__ = [
    "User",
    "Role",
    "user_roles",
    "RefreshToken",
    "Camera",
    "Event",
    "Report",
    "Notification",
    "AppSettingsRow",
]
