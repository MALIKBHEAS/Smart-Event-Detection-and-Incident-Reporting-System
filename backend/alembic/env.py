"""Alembic environment for migrations.

This env.py dynamically discovers SQLAlchemy MetaData objects defined in the project
and consolidates them for Alembic autogeneration. It is compatible with the
Clean Architecture layout where models live under backend/app/.

The discovery algorithm:
- Adds the backend directory to sys.path so the 'app' package is importable.
- Walks packages under the 'app' folder and imports modules safely.
- Collects any 'Base' objects (Declarative Base) or module-level 'metadata' objects.
- If multiple MetaData objects are found, they are consolidated into a single
  MetaData by copying Table objects into a combined MetaData using Table.tometadata().

This avoids hardcoding temporary paths and supports projects that declare multiple
Declarative bases (though a single Base is recommended). Consolidation ensures
Alembic autogenerate sees all tables.
"""
from __future__ import with_statement

import os
import sys
import pkgutil
import importlib
import inspect
import logging
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, MetaData
import sqlalchemy as sa

from alembic import context

# Alembic Config object
config = context.config

# Set up logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")

# Provide SQLAlchemy URL from environment variable if present
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    config.set_main_option("sqlalchemy.url", DATABASE_URL)


def _discover_metadatas(app_folder_name: str = "app") -> list:
    """Discover SQLAlchemy MetaData objects under the given app folder.

    Returns a list of MetaData instances found in modules under the app package.
    """
    metas = []

    # Determine backend directory (parent of this env.py's parent)
    here = os.path.abspath(os.path.dirname(__file__))
    backend_dir = os.path.abspath(os.path.join(here, os.pardir))  # backend/
    app_path = os.path.join(backend_dir, app_folder_name)

    if not os.path.isdir(app_path):
        logger.warning("App folder '%s' not found under %s; skipping metadata discovery.", app_folder_name, backend_dir)
        return metas

    # Ensure backend_dir is importable so 'app' package can be imported
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    # Walk packages under app and import modules safely
    for finder, name, ispkg in pkgutil.walk_packages([app_path], prefix=f"{app_folder_name}."):
        try:
            module = importlib.import_module(name)
        except Exception as exc:
            logger.debug("Failed to import module %s during metadata discovery: %s", name, exc)
            continue

        # Look for Declarative Base named 'Base'
        base_obj = getattr(module, "Base", None)
        if base_obj is not None:
            # Declarative base exposes .metadata
            meta = getattr(base_obj, "metadata", None)
            if isinstance(meta, sa.MetaData):
                metas.append(meta)
                logger.debug("Found MetaData via Base in module %s", name)
                continue

        # Look for module-level 'metadata'
        meta_obj = getattr(module, "metadata", None)
        if isinstance(meta_obj, sa.MetaData):
            metas.append(meta_obj)
            logger.debug("Found module-level MetaData in module %s", name)
            continue

    # Deduplicate by id
    unique = []
    seen = set()
    for m in metas:
        if id(m) not in seen:
            unique.append(m)
            seen.add(id(m))
    return unique


# Discover metadata instances
_discovered = _discover_metadatas(app_folder_name="app")

if not _discovered:
    # As a fallback, attempt to import common path 'app.db.base.Base'
    try:
        from app.db.base import Base as _Base  # type: ignore
        _discovered = [getattr(_Base, "metadata")] if getattr(_Base, "metadata", None) is not None else []
        logger.debug("Discovered Base via fallback import: app.db.base.Base")
    except Exception:
        _discovered = []

# Consolidate metadata objects
if len(_discovered) == 0:
    target_metadata = None
    logger.warning("No SQLAlchemy MetaData discovered; autogenerate will be disabled.")
elif len(_discovered) == 1:
    target_metadata = _discovered[0]
    logger.info("Using discovered MetaData from project for Alembic autogenerate.")
else:
    # Multiple metadata objects found - consolidate into a single MetaData
    combined = MetaData()
    logger.info("Multiple MetaData objects found (%d); consolidating into one for Alembic autogenerate.", len(_discovered))
    for meta in _discovered:
        # Copy all tables into combined metadata
        for table in list(meta.tables.values()):
            # Table.tometadata copies a Table into another MetaData instance
            try:
                table.tometadata(combined)
            except Exception as exc:
                logger.exception("Failed to copy table %s into combined MetaData: %s", table.name, exc)
    target_metadata = combined


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
