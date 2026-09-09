from .cameras import router as cameras_router
from .events import router as events_router
from .reports import router as reports_router
from .users import router as users_router

__all__ = ["cameras_router", "reports_router", "events_router", "users_router"]
