document.addEventListener("DOMContentLoaded", () => {
    const mapContainer = document.getElementById("map") || document.getElementById("live-main-map") || document.getElementById("osm-map-viewport");
    if (!mapContainer) return;

    const map = new maplibregl.Map({
        container: mapContainer,
        style: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
        center: [77.4350, 28.6350],
        zoom: 12
    });

    map.on("load", () => {
        // FR-2.1: Dynamic SAR Inundation Vector Polygon
        map.addSource("flood-zone", {
            type: "geojson",
            data: {
                type: "Feature",
                geometry: {
                    type: "Polygon",
                    coordinates: [[
                        [77.4380, 28.6360],
                        [77.4480, 28.6375],
                        [77.4520, 28.6290],
                        [77.4410, 28.6270],
                        [77.4380, 28.6360]
                    ]]
                }
            }
        });

        map.addLayer({
            id: "flood-hazard-layer",
            type: "fill",
            source: "flood-zone",
            paint: {
                "fill-color": "#ef4444",
                "fill-opacity": 0.4
            }
        });

        // FR-4.2: Dynamic OSRM Green Rescue Corridor
        map.addSource("safe-route", {
            type: "geojson",
            data: {
                type: "Feature",
                geometry: {
                    type: "LineString",
                    coordinates: [
                        [77.4280, 28.6410],
                        [77.4320, 28.6385],
                        [77.4390, 28.6360],
                        [77.4415, 28.6340],
                        [77.4446, 28.6322]
                    ]
                }
            }
        });

        map.addLayer({
            id: "safe-corridor-line",
            type: "line",
            source: "safe-route",
            paint: {
                "line-color": "#10b981",
                "line-width": 5,
                "line-dasharray": [2, 2]
            }
        });

        // FR-2.2: Priority-Coded SOS Distress Marker
        new maplibregl.Marker({ color: "#ef4444" })
            .setLngLat([77.4446, 28.6322])
            .setPopup(new maplibregl.Popup().setHTML("<b>TICK-7325</b><br/>CRITICAL_TRAPPED<br/>+91 9451195342"))
            .addTo(map);
    });

    window.mapInstance = map;
});