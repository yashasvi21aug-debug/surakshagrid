-- Enable PostGIS & pgRouting extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgrouting;

DROP TABLE IF EXISTS incidents CASCADE;
DROP TABLE IF EXISTS flood_zones CASCADE;

-- SAR Extracted Inundation Polygons (FR-2.1)
CREATE TABLE flood_zones (
    id SERIAL PRIMARY KEY,
    zone_name VARCHAR(100) NOT NULL,
    severity VARCHAR(20) DEFAULT 'CRITICAL',
    geom GEOMETRY(Polygon, 4326) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Real-Time Citizen Incidents (FR-1.3, FR-2.2)
CREATE TABLE incidents (
    ticket_id VARCHAR(32) PRIMARY KEY,
    contact VARCHAR(32) NOT NULL,
    triage_type VARCHAR(64) NOT NULL,
    notes TEXT,
    location GEOMETRY(Point, 4326) NOT NULL,
    status VARCHAR(32) DEFAULT 'DISPATCH_PENDING',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_flood_zones_geom ON flood_zones USING GIST (geom);
CREATE INDEX idx_incidents_geom ON incidents USING GIST (location);

-- Real-Time Notification Trigger (FR-1.3 / WebSocket stream)
CREATE OR REPLACE FUNCTION notify_eoc_stream()
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
            'lat', ST_Y(NEW.location),
            'lng', ST_X(NEW.location)
        )::text
    );
    RETURN NEW;
END;
$func$ LANGUAGE plpgsql;

CREATE TRIGGER trg_incident_notify
AFTER INSERT ON incidents
FOR EACH ROW
EXECUTE FUNCTION notify_eoc_stream();

-- Seed Ground-Truth Flood Zone (Ghaziabad / Hindon Sector)
INSERT INTO flood_zones (zone_name, geom)
VALUES (
    'Hindon High-Risk Basin',
    ST_GeomFromText('POLYGON((77.4380 28.6360, 77.4480 28.6375, 77.4520 28.6290, 77.4410 28.6270, 77.4380 28.6360))', 4326)
);