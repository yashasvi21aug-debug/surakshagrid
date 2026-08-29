DROP TABLE IF EXISTS incidents CASCADE;
DROP TABLE IF EXISTS flood_zones CASCADE;

-- 1. Flood Inundation Zones (Stored as GeoJSON / Polygon Coordinates)
CREATE TABLE flood_zones (
    id SERIAL PRIMARY KEY,
    zone_name VARCHAR(100) NOT NULL,
    severity VARCHAR(20) DEFAULT 'CRITICAL',
    min_lat DOUBLE PRECISION NOT NULL,
    max_lat DOUBLE PRECISION NOT NULL,
    min_lng DOUBLE PRECISION NOT NULL,
    max_lng DOUBLE PRECISION NOT NULL,
    polygon_geojson JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Real-Time Incidents Table
CREATE TABLE incidents (
    ticket_id VARCHAR(32) PRIMARY KEY,
    contact VARCHAR(32) NOT NULL,
    triage_type VARCHAR(64) NOT NULL,
    notes TEXT,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    status VARCHAR(32) DEFAULT 'DISPATCHED',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Standard B-Tree Indexes
CREATE INDEX idx_incidents_coords ON incidents (lat, lng);
CREATE INDEX idx_flood_bounds ON flood_zones (min_lat, max_lat, min_lng, max_lng);

-- 4. Native PostgreSQL Real-Time Notification Trigger
CREATE OR REPLACE FUNCTION broadcast_incident_trigger()
RETURNS TRIGGER AS $func$
BEGIN
    PERFORM pg_notify(
        'eoc_incident_stream',
        json_build_object(
            'type', 'NEW_INCIDENT',
            'ticket_id', NEW.ticket_id,
            'contact', NEW.contact,
            'triage_type', NEW.triage_type,
            'notes', NEW.notes,
            'lat', NEW.lat,
            'lng', NEW.lng
        )::text
    );
    RETURN NEW;
END;
$func$ LANGUAGE plpgsql;

CREATE TRIGGER trg_incident_notify
AFTER INSERT ON incidents
FOR EACH ROW
EXECUTE FUNCTION broadcast_incident_trigger();

-- 5. Seed Flood Hazard Polygon
INSERT INTO flood_zones (zone_name, min_lat, max_lat, min_lng, max_lng, polygon_geojson)
VALUES (
    'Hindon High-Risk Inundation Zone',
    28.6270, 28.6375, 77.4380, 77.4520,
    '[[28.6360, 77.4380], [28.6375, 77.4480], [28.6290, 77.4520], [28.6270, 77.4410]]'::jsonb
);