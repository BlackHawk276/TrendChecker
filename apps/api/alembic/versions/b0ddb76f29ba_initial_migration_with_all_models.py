"""Initial migration with all models

Revision ID: b0ddb76f29ba
Revises:
Create Date: 2025-11-06 11:58:17.447313

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b0ddb76f29ba'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    store_category_enum = postgresql.ENUM(
        'fashion', 'beauty', 'electronics', 'home', 'health', 'sports', 'other',
        name='storecategory'
    )
    store_category_enum.create(op.get_bind())

    subscription_tier_enum = postgresql.ENUM(
        'free', 'starter', 'pro', 'agency',
        name='subscriptiontier'
    )
    subscription_tier_enum.create(op.get_bind())

    subscription_status_enum = postgresql.ENUM(
        'active', 'canceled', 'past_due', 'trialing',
        name='subscriptionstatus'
    )
    subscription_status_enum.create(op.get_bind())

    alert_type_enum = postgresql.ENUM(
        'new_store', 'price_drop', 'product_added',
        name='alerttype'
    )
    alert_type_enum.create(op.get_bind())

    # Create stores table
    op.create_table(
        'stores',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('domain', sa.String(255), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', store_category_enum, nullable=False),
        sa.Column('country_code', sa.String(2), nullable=True),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_scraped_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('product_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('avg_product_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('estimated_monthly_revenue', sa.Integer(), nullable=True),
        sa.Column('estimated_monthly_visitors', sa.Integer(), nullable=True),
        sa.Column('trending_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('growth_rate', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('theme_name', sa.String(255), nullable=True),
        sa.Column('tech_stack', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('social_links', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index('ix_stores_id', 'stores', ['id'])
    op.create_index('ix_stores_domain', 'stores', ['domain'])
    op.create_index('ix_stores_category', 'stores', ['category'])
    op.create_index('ix_stores_country_code', 'stores', ['country_code'])
    op.create_index('ix_stores_trending_score', 'stores', ['trending_score'])
    op.create_index('ix_stores_is_active', 'stores', ['is_active'])

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('subscription_tier', subscription_tier_enum, nullable=False),
        sa.Column('subscription_status', subscription_status_enum, nullable=False),
        sa.Column('stripe_customer_id', sa.String(255), nullable=True, unique=True),
        sa.Column('stripe_subscription_id', sa.String(255), nullable=True, unique=True),
        sa.Column('trial_ends_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('subscription_ends_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('searches_used_this_month', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('searches_limit', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('api_key', sa.String(64), nullable=False, unique=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_subscription_tier', 'users', ['subscription_tier'])
    op.create_index('ix_users_subscription_status', 'users', ['subscription_status'])
    op.create_index('ix_users_stripe_customer_id', 'users', ['stripe_customer_id'])
    op.create_index('ix_users_api_key', 'users', ['api_key'])
    op.create_index('ix_users_is_active', 'users', ['is_active'])

    # Create products table
    op.create_table(
        'products',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('store_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
        sa.Column('compare_at_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('image_url', sa.String(500), nullable=True),
        sa.Column('images', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('vendor', sa.String(255), nullable=True),
        sa.Column('product_type', sa.String(255), nullable=True),
        sa.Column('handle', sa.String(255), nullable=True),
        sa.Column('first_seen', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_available', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('variant_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_products_id', 'products', ['id'])
    op.create_index('ix_products_store_id', 'products', ['store_id'])
    op.create_index('ix_products_price', 'products', ['price'])
    op.create_index('ix_products_vendor', 'products', ['vendor'])
    op.create_index('ix_products_product_type', 'products', ['product_type'])
    op.create_index('ix_products_handle', 'products', ['handle'])
    op.create_index('ix_products_first_seen', 'products', ['first_seen'])
    op.create_index('ix_products_is_available', 'products', ['is_available'])
    # Create GIN index for tags array
    op.create_index('ix_products_tags', 'products', ['tags'], postgresql_using='gin')

    # Create saved_stores table
    op.create_table(
        'saved_stores',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('store_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('saved_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_saved_stores_saved_at', 'saved_stores', ['saved_at'])

    # Create alerts table
    op.create_table(
        'alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('store_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('alert_type', alert_type_enum, nullable=False),
        sa.Column('criteria', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_alerts_id', 'alerts', ['id'])
    op.create_index('ix_alerts_user_id', 'alerts', ['user_id'])
    op.create_index('ix_alerts_store_id', 'alerts', ['store_id'])
    op.create_index('ix_alerts_alert_type', 'alerts', ['alert_type'])
    op.create_index('ix_alerts_is_active', 'alerts', ['is_active'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('alerts')
    op.drop_table('saved_stores')
    op.drop_table('products')
    op.drop_table('users')
    op.drop_table('stores')

    # Drop enum types
    sa.Enum(name='alerttype').drop(op.get_bind())
    sa.Enum(name='subscriptionstatus').drop(op.get_bind())
    sa.Enum(name='subscriptiontier').drop(op.get_bind())
    sa.Enum(name='storecategory').drop(op.get_bind())
