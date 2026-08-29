/**
 * SurakshaGrid Leaflet GIS & Tactical Map Engine Module
 */

export class SurakshaMap {
  constructor(elementId, center = [28.6350, 77.4350], zoom = 13) {
    this.elementId = elementId;
    this.map = L.map(elementId, {
      zoomControl: false
    }).setView(center, zoom);

    // Add compact Leaflet zoom control in top-right
    L.control.zoom({ position: 'topright' }).addTo(this.map);

    // Carto Dark Matter Basemap Tiles
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
      subdomains: 'abcd',
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
    }).addTo(this.map);

    // Invalidate map size on load to ensure smooth rendering without tile seams
    setTimeout(() => {
      if (this.map) {
        this.map.invalidateSize();
      }
    }, 200);

    this.markers = new Map();
    this.floodLayer = null;
    this.currentRoute = null;

    this.initDefaultFloodPolygon();
    this.initVehicleMarker(center);
  }

  initVehicleMarker(center) {
    this.vehicleMarker = L.circleMarker([center[0] + 0.006, center[1] - 0.007], {
      color: '#388bfd',
      fillColor: '#388bfd',
      fillOpacity: 0.9,
      radius: 7,
      weight: 2
    })
      .addTo(this.map)
      .bindPopup('<b style="color: #58a6ff;">NDRF BASE UNIT #4</b><br/><span style="color: #8b949e; font-size: 11px;">Staging Post: Hindon Sector</span>');
  }

  initDefaultFloodPolygon() {
    this.floodLayer = L.polygon([
      [28.6360, 77.4380],
      [28.6375, 77.4480],
      [28.6290, 77.4520],
      [28.6270, 77.4410]
    ], {
      color: '#f85149',
      fillColor: '#f85149',
      fillOpacity: 0.25,
      weight: 1.5,
      dashArray: '4, 4'
    }).addTo(this.map);
  }

  toggleInundationLayer() {
    if (this.map.hasLayer(this.floodLayer)) {
      this.map.removeLayer(this.floodLayer);
      return false;
    } else {
      this.floodLayer.addTo(this.map);
      return true;
    }
  }

  addIncidentMarker(id, lat, lng, popupContent) {
    const marker = L.circleMarker([lat, lng], {
      color: '#f85149',
      fillColor: '#da3633',
      fillOpacity: 0.9,
      radius: 8,
      weight: 2
    }).addTo(this.map);

    if (popupContent) {
      marker.bindPopup(popupContent).openPopup();
    }

    this.markers.set(id, marker);
    this.map.flyTo([lat, lng], 14, { animate: true, duration: 0.8 });
    return marker;
  }

  renderSafeCorridor(start, end, customWaypoints = null) {
    if (this.currentRoute) {
      this.map.removeLayer(this.currentRoute);
    }

    const points = customWaypoints || [
      start,
      [28.6385, 77.4320],
      [28.6360, 77.4390],
      [28.6340, 77.4415],
      end
    ];

    this.currentRoute = L.polyline(points, {
      color: '#3fb950',
      weight: 4,
      opacity: 0.95,
      lineCap: 'round',
      dashArray: '6, 8'
    }).addTo(this.map);

    this.map.fitBounds(this.currentRoute.getBounds(), { padding: [40, 40] });
    return this.currentRoute;
  }
}
