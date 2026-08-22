from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

from app.core.settings import settings
from app.models.base import Base

# Import all model modules so their tables register with Base.metadata
import app.models.models  # noqa: F401
import app.models.entities  # noqa: F401
import app.models.reports  # noqa: F401
import app.models.evidence  # noqa: F401
import app.models.monitor  # noqa: F401
import app.models.sources  # noqa: F401
import app.models.skills  # noqa: F401
import app.models.compliance  # noqa: F401
import app.models.review  # noqa: F401
import app.models.registry  # noqa: F401
import app.models.market_13f_cache  # noqa: F401

config = context.config

# Override sqlalchemy.url from app settings so the single source of truth is .env
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
