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
        sa.Column('phone', sa.String(length=32), nullable=False),
        sa.Column('severity', sa.Enum('CRITICAL_TRAPPED', 'MEDICAL_EVAC', 'FOOD_WATER', 'INFRASTRUCTURE_DAMAGE', name='incidentseverity'), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'DISPATCHED', 'RESOLVED', name='incidentstatus'), nullable=False),
        sa.Column('geom', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True),
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('lng', sa.Float(), nullable=True),
        sa.Column('rain_rate', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. Create Flood Polygons table
    op.create_table(
        'flood_polygons',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('zone_name', sa.String(length=128), nullable=False),
        sa.Column('geom', geoalchemy2.types.Geometry(geometry_type='POLYGON', srid=4326, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True),
        sa.Column('depth_m', sa.Float(), nullable=False),
        sa.Column('severity', sa.String(length=32), nullable=False),
        sa.Column('risk_score', sa.Float(), nullable=False),
        sa.Column('predicted_horizon_hours', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. Create Sensor Gauges table
    op.create_table(
        'sensor_gauges',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('sensor_name', sa.String(length=128), nullable=False),
        sa.Column('geom', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True),
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('lng', sa.Float(), nullable=True),
        sa.Column('water_level_m', sa.Float(), nullable=False),
        sa.Column('warning_threshold_m', sa.Float(), nullable=False),
        sa.Column('threshold_status', sa.Enum('NORMAL', 'WARNING', 'CRITICAL', name='gaugestatus'), nullable=False),
        sa.Column('last_ping', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('sensor_gauges')
    op.drop_table('flood_polygons')
    op.drop_table('incidents')
