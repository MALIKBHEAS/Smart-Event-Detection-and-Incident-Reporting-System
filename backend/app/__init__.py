"""Application package marker for backend.app

This file makes the backend/app directory an importable package, which
allows relative imports used throughout the modules (including models)
to resolve correctly during Alembic discovery and other tooling.
"""
__all__ = ["models"]
