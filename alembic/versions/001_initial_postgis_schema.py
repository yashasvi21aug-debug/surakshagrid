"""Initial PostGIS spatial tables migration

Revision ID: 001_initial_postgis_schema
Revises: 
Create Date: 2026-08-29 17:23:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2

revision: str = '001_initial_postgis_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure PostGIS extension exists
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # 1. Create Incidents table
    op.create_table(
        'incidents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('category', sa.Enum('CRITICAL_TRAPPED', 'MEDICAL_EVAC', 'FOOD_WATER', 'INFRASTRUCTURE_DAMAGE', name='incidentcategory'), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'DISPATCHED', 'RESOLVED', 'RESCUED', 'CANCELLED', name='incidentstatus'), nullable=False),
        sa.Column('location', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True),
        sa.Column('accuracy', sa.Float(), nullable=True),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.Column('phone_number', sa.String(length=32), nullable=True),
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('lng', sa.Float(), nullable=True),
        sa.Column('rain_rate', sa.Float(), nullable=True),
        sa.Column('risk_status', sa.String(length=20), nullable=False, server_default='LOW'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_incidents_location', 'incidents', ['location'], postgresql_using='gist')

    # 2. Create Flood Zones table
    op.create_table(
        'flood_zones',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('source', sa.String(length=64), nullable=False, server_default='SAR'),
        sa.Column('risk_level', sa.String(length=32), nullable=False, server_default='HIGH'),
        sa.Column('depth_m', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('polygon', geoalchemy2.types.Geometry(geometry_type='POLYGON', srid=4326, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True),
        sa.Column('valid_until', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('zone_name', sa.String(length=128), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=False, server_default='0.85'),
        sa.Column('estimated_water_rise', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('predicted_horizon_hours', sa.Integer(), nullable=False, server_default='6'),
        sa.Column('polygon_geojson', sa.String(length=4000), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_flood_zones_polygon', 'flood_zones', ['polygon'], postgresql_using='gist')

    # 3. Create Sensor Telemetry table
    op.create_table(
        'sensor_telemetry',
        sa.Column('sensor_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('water_level_m', sa.Float(), nullable=False, server_default='1.5'),
        sa.Column('threshold_m', sa.Float(), nullable=False, server_default='2.5'),
        sa.Column('location', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('lng', sa.Float(), nullable=True),
        sa.Column('status', sa.Enum('NORMAL', 'WARNING', 'CRITICAL', name='gaugestatus'), nullable=False, server_default='NORMAL'),
        sa.PrimaryKeyConstraint('sensor_id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('idx_sensor_telemetry_location', 'sensor_telemetry', ['location'], postgresql_using='gist')

    # 4. Create Route Logs table
    op.create_table(
        'route_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('origin', sa.String(length=255), nullable=False),
        sa.Column('destination', sa.String(length=255), nullable=False),
        sa.Column('waypoints', sa.String(length=4000), nullable=True),
        sa.Column('distance_km', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('duration_min', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('avoided_flood_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='safe'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('origin_lat', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('origin_lng', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('dest_lat', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('dest_lng', sa.Float(), nullable=False, server_default='0.0'),
        sa.PrimaryKeyConstraint('id')
    )

    # 5. Create Officers table
    op.create_table(
        'officers',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('badge_id', sa.String(length=50), nullable=False),
        sa.Column('role', sa.Enum('COMMANDER', 'FIELD_OPERATOR', 'DISPATCHER', 'RESPONDER', 'CITIZEN', 'ADMIN', name='officerrole'), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=True),
        sa.Column('phone_number', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('lng', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('badge_id')
    )


def downgrade() -> None:
    op.drop_table('officers')
    op.drop_table('route_logs')
    op.drop_table('sensor_telemetry')
    op.drop_table('flood_zones')
    op.drop_table('incidents')
