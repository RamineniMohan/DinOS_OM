"""add_missing_tables_and_constraints

Revision ID: 9a8b7c6d5e4f
Revises: e98c54354e81
Create Date: 2026-08-05 20:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

revision: str = '9a8b7c6d5e4f'
down_revision: Union[str, Sequence[str], None] = 'e98c54354e81'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _constraint_exists(conn, table: str, constraint: str) -> bool:
    result = conn.execute(text(
        "SELECT 1 FROM information_schema.table_constraints "
        "WHERE table_name=:t AND constraint_name=:c"
    ), {"t": table, "c": constraint})
    return result.fetchone() is not None


def _index_exists(conn, index: str) -> bool:
    result = conn.execute(text(
        "SELECT 1 FROM pg_indexes WHERE indexname=:i"
    ), {"i": index})
    return result.fetchone() is not None


def _table_exists(conn, table: str) -> bool:
    result = conn.execute(text(
        "SELECT 1 FROM information_schema.tables WHERE table_name=:t AND table_schema='public'"
    ), {"t": table})
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Foreign keys and indexes for existing tables
    # DiningTable model uses __tablename__ = 'tables'
    if not _constraint_exists(conn, 'orders', 'fk_orders_table_id_tables'):
        op.create_foreign_key(
            'fk_orders_table_id_tables', 'orders', 'tables',
            ['table_id'], ['id'], ondelete='SET NULL'
        )
    if not _index_exists(conn, 'ix_orders_table_id'):
        op.create_index('ix_orders_table_id', 'orders', ['table_id'], unique=False)

    if not _constraint_exists(conn, 'invoices', 'fk_invoices_branch_id_branches'):
        op.create_foreign_key(
            'fk_invoices_branch_id_branches', 'invoices', 'branches',
            ['branch_id'], ['id'], ondelete='SET NULL'
        )
    if not _constraint_exists(conn, 'kot_tickets', 'fk_kot_tickets_branch_id_branches'):
        op.create_foreign_key(
            'fk_kot_tickets_branch_id_branches', 'kot_tickets', 'branches',
            ['branch_id'], ['id'], ondelete='SET NULL'
        )

    if not _constraint_exists(conn, 'units', 'uq_unit_restaurant_name'):
        op.create_unique_constraint('uq_unit_restaurant_name', 'units', ['restaurant_id', 'name'])

    if not _index_exists(conn, 'ix_stock_ledger_ingredient_id'):
        op.create_index('ix_stock_ledger_ingredient_id', 'stock_ledger', ['ingredient_id'], unique=False)

    # 2. Update RestaurantSettings float columns to Numeric(5, 2) — safe to run multiple times
    for col in ('default_gst_rate', 'cgst_rate', 'sgst_rate', 'igst_rate'):
        op.alter_column(
            'restaurant_settings', col,
            type_=sa.Numeric(5, 2),
            existing_type=sa.Float(),
            nullable=False
        )

    # 3. Vendors
    if not _table_exists(conn, 'vendors'):
        op.create_table(
            'vendors',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('restaurant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('restaurants.id', ondelete='CASCADE'), nullable=False),
            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('contact_person', sa.String(255), nullable=True),
            sa.Column('phone', sa.String(20), nullable=True),
            sa.Column('email', sa.String(255), nullable=True),
            sa.Column('address', sa.Text(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index('ix_vendors_restaurant_id', 'vendors', ['restaurant_id'], unique=False)

    # 4. Purchase Orders
    if not _table_exists(conn, 'purchase_orders'):
        op.create_table(
            'purchase_orders',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('restaurant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('restaurants.id', ondelete='CASCADE'), nullable=False),
            sa.Column('vendor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vendors.id', ondelete='CASCADE'), nullable=False),
            sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
            sa.Column('total_amount', sa.Numeric(12, 2), nullable=False, server_default='0'),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index('ix_purchase_orders_restaurant_id', 'purchase_orders', ['restaurant_id'], unique=False)

    if not _table_exists(conn, 'purchase_order_items'):
        op.create_table(
            'purchase_order_items',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('purchase_orders.id', ondelete='CASCADE'), nullable=False),
            sa.Column('ingredient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ingredients.id'), nullable=False),
            sa.Column('quantity', sa.Numeric(12, 4), nullable=False),
            sa.Column('unit_price', sa.Numeric(10, 2), nullable=False),
        )

    # 5. Membership Tiers, Offers, Coupons
    if not _table_exists(conn, 'membership_tiers'):
        op.create_table(
            'membership_tiers',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('restaurant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('restaurants.id', ondelete='CASCADE'), nullable=False),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('min_points', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('discount_percentage', sa.Numeric(5, 2), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index('ix_membership_tiers_restaurant_id', 'membership_tiers', ['restaurant_id'], unique=False)

    if not _table_exists(conn, 'offers'):
        op.create_table(
            'offers',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('restaurant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('restaurants.id', ondelete='CASCADE'), nullable=False),
            sa.Column('title', sa.String(255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('discount_type', sa.String(50), nullable=False),
            sa.Column('discount_value', sa.Numeric(10, 2), nullable=False),
            sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index('ix_offers_restaurant_id', 'offers', ['restaurant_id'], unique=False)

    if not _table_exists(conn, 'coupons'):
        op.create_table(
            'coupons',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('restaurant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('restaurants.id', ondelete='CASCADE'), nullable=False),
            sa.Column('offer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('offers.id', ondelete='CASCADE'), nullable=False),
            sa.Column('code', sa.String(50), nullable=False),
            sa.Column('max_uses', sa.Integer(), nullable=True),
            sa.Column('uses_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint('restaurant_id', 'code', name='uq_coupon_restaurant_code'),
        )
        op.create_index('ix_coupons_restaurant_id', 'coupons', ['restaurant_id'], unique=False)

    # 6. GST Transactions
    if not _table_exists(conn, 'gst_transactions'):
        op.create_table(
            'gst_transactions',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('restaurant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('restaurants.id'), nullable=False),
            sa.Column('invoice_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('invoices.id'), nullable=False),
            sa.Column('taxable_amount', sa.Numeric(10, 2), nullable=False),
            sa.Column('cgst_amount', sa.Numeric(10, 2), nullable=False, server_default='0'),
            sa.Column('sgst_amount', sa.Numeric(10, 2), nullable=False, server_default='0'),
            sa.Column('igst_amount', sa.Numeric(10, 2), nullable=False, server_default='0'),
            sa.Column('total_gst', sa.Numeric(10, 2), nullable=False),
            sa.Column('period_month', sa.Integer(), nullable=False),
            sa.Column('period_year', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index('ix_gst_transactions_restaurant_id', 'gst_transactions', ['restaurant_id'], unique=False)


def downgrade() -> None:
    op.drop_table('gst_transactions')
    op.drop_table('coupons')
    op.drop_table('offers')
    op.drop_table('membership_tiers')
    op.drop_table('purchase_order_items')
    op.drop_table('purchase_orders')
    op.drop_table('vendors')

    op.drop_index('ix_stock_ledger_ingredient_id', table_name='stock_ledger')
    op.drop_constraint('uq_unit_restaurant_name', 'units', type_='unique')
    op.drop_constraint('fk_kot_tickets_branch_id_branches', 'kot_tickets', type_='foreignkey')
    op.drop_constraint('fk_invoices_branch_id_branches', 'invoices', type_='foreignkey')
    op.drop_index('ix_orders_table_id', table_name='orders')
    op.drop_constraint('fk_orders_table_id_tables', 'orders', type_='foreignkey')
