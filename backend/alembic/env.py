import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Add app directory to path so we can import app modules
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import settings and metadata
from app.core.config import settings
from app.core.db import Base

# Import all models to ensure metadata has them registered
from app.modules.auth.models import User, Role, Permission
from app.modules.tenancy.models import Restaurant, Branch, RestaurantSettings
from app.modules.menu.models import MenuCategory, MenuItem, ItemVariant, ItemAddon, MenuAvailability, MenuItemBranchPrice
from app.modules.orders.models import Order, OrderItem, OrderAddon, OrderStatusHistory, KotTicket
from app.modules.billing.models import Invoice, InvoiceItem, Payment, Refund, HsnCode, GSTRate, GSTTransaction
from app.modules.inventory.models import Unit, Ingredient, StockLedger, Recipe, RecipeIngredient
from app.modules.operations.models import Floor, TableSection, DiningTable, Tip, TipAllocation
from app.modules.system.models import AuditLog
from app.modules.crm.models import Customer, LoyaltyTransaction, Feedback


# this is the Alembic Config object, which provides access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the SQLAlchemy URL from settings (escape % for ConfigParser interpolation)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.DATABASE_URL
    
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
