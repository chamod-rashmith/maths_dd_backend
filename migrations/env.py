import os
import sys
import urllib.parse
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Ensure backend root is on Python sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.database import resolve_cloudsql_socket_dir

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def get_database_url() -> str:
    """Builds Cloud SQL Unix socket or TCP postgresql+psycopg2:// URL from settings."""
    user = urllib.parse.quote_plus(settings.DB_USER)
    encoded_pass = urllib.parse.quote_plus(settings.DB_PASSWORD)
    name = settings.DB_NAME

    explicit_host = settings.DB_HOST.strip() if settings.DB_HOST else ""
    if explicit_host and not explicit_host.startswith("/"):
        return f"postgresql+psycopg2://{user}:{encoded_pass}@{explicit_host}:{settings.DB_PORT}/{name}"

    socket_dir = urllib.parse.quote_plus(resolve_cloudsql_socket_dir())
    return f"postgresql+psycopg2://{user}:{encoded_pass}@/{name}?host={socket_dir}"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
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
