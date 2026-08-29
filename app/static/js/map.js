/**
 * SurakshaGrid Leaflet GIS & Map Engine Module
 */

export class SurakshaMap {
  constructor(elementId, center = [28.6350, 77.4350], zoom = 13) {
    this.elementId = elementId;
    this.map = L.map(elementId).setView(center, zoom);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
      attribution: '&copy; CartoDB & OpenStreetMap'
    }).addTo(this.map);

    this.markers = new Map();
    this.floodLayer = null;
    this.currentRoute = null;

    this.initDefaultFloodPolygon();
    this.initVehicleMarker(center);
  }

  initVehicleMarker(center) {
    this.vehicleMarker = L.marker([center[0] + 0.006, center[1] - 0.007])
      .addTo(this.map)
      .bindPopup('<b class="text-slate-900">NDRF Base Station Unit #4</b>');
  }

  initDefaultFloodPolygon() {
    this.floodLayer = L.polygon([
      [28.6360, 77.4380],
      [28.6375, 77.4480],
      [28.6290, 77.4520],
      [28.6270, 77.4410]
    ], {
      color: '#ef4444',
      fillColor: '#dc2626',
      fillOpacity: 0.35,
      weight: 2,
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
      color: '#ef4444',
      fillColor: '#dc2626',
      fillOpacity: 0.9,
      radius: 8
    }).addTo(this.map);

    if (popupContent) {
      marker.bindPopup(popupContent).openPopup();
    }

    this.markers.set(id, marker);
    this.map.flyTo([lat, lng], 14);
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
      color: '#10b981',
      weight: 6,
      opacity: 0.95,
      lineCap: 'round',
      dashArray: '8, 12'
    }).addTo(this.map);

    this.map.fitBounds(this.currentRoute.getBounds(), { padding: [50, 50] });
    return this.currentRoute;
  }
}
