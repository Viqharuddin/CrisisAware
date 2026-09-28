// static/js/map.js
let map;
let userMarker;
let alertMarkers = [];
let placeMarkers = [];
let routingControl = null;
let markedLocationsLayer;
let markedMarkerObjects = {};

function createMarkIcon() {
    return L.divIcon({
        className: 'custom-location-pin',
        html: `<div style="background-color: #e74c3c; width: 30px; height: 30px; border-radius: 50% 50% 50% 0; transform: rotate(-45deg); display: flex; align-items: center; justify-content: center; border: 2px solid white; box-shadow: 0 3px 8px rgba(0,0,0,0.35);"><i class="fas fa-map-marker-alt" style="transform: rotate(45deg); color: white; font-size: 14px;"></i></div>`,
        iconSize: [30, 30],
        iconAnchor: [15, 30],
        popupAnchor: [0, -30]
    });
}

function createHospitalIcon() {
    return L.divIcon({
        className: 'custom-hospital-pin',
        html: `<div style="background-color: #e74c3c; width: 32px; height: 32px; border-radius: 50% 50% 50% 0; transform: rotate(-45deg); display: flex; align-items: center; justify-content: center; border: 2px solid white; box-shadow: 0 3px 8px rgba(0,0,0,0.35);"><i class="fas fa-hospital" style="transform: rotate(45deg); color: white; font-size: 14px;"></i></div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 32],
        popupAnchor: [0, -32]
    });
}

function createPharmacyIcon() {
    return L.divIcon({
        className: 'custom-pharmacy-pin',
        html: `<div style="background-color: #3498db; width: 32px; height: 32px; border-radius: 50% 50% 50% 0; transform: rotate(-45deg); display: flex; align-items: center; justify-content: center; border: 2px solid white; box-shadow: 0 3px 8px rgba(0,0,0,0.35);"><i class="fas fa-clinic-medical" style="transform: rotate(45deg); color: white; font-size: 14px;"></i></div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 32],
        popupAnchor: [0, -32]
    });
}

function createSchoolIcon() {
    return L.divIcon({
        className: 'custom-school-pin',
        html: `<div style="background-color: #f39c12; width: 32px; height: 32px; border-radius: 50% 50% 50% 0; transform: rotate(-45deg); display: flex; align-items: center; justify-content: center; border: 2px solid white; box-shadow: 0 3px 8px rgba(0,0,0,0.35);"><i class="fas fa-school" style="transform: rotate(45deg); color: white; font-size: 14px;"></i></div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 32],
        popupAnchor: [0, -32]
    });
}

function createLandmarkIcon() {
    return L.divIcon({
        className: 'custom-landmark-pin',
        html: `<div style="background-color: #9b59b6; width: 32px; height: 32px; border-radius: 50% 50% 50% 0; transform: rotate(-45deg); display: flex; align-items: center; justify-content: center; border: 2px solid white; box-shadow: 0 3px 8px rgba(0,0,0,0.35);"><i class="fas fa-landmark" style="transform: rotate(45deg); color: white; font-size: 14px;"></i></div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 32],
        popupAnchor: [0, -32]
    });
}

function createUserIcon() {
    return L.divIcon({
        className: 'custom-user-pin',
        html: `<div style="background-color: #2980b9; width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 3px solid white; box-shadow: 0 0 0 4px rgba(41,128,185,0.4), 0 4px 10px rgba(0,0,0,0.3); animation: userPulse 2s infinite;"><i class="fas fa-crosshairs" style="color: white; font-size: 16px;"></i></div>`,
        iconSize: [34, 34],
        iconAnchor: [17, 17],
        popupAnchor: [0, -17]
    });
}

function createAlertIcon(severity) {
    let bgColor = '#3498db';
    let iconClass = 'fa-info-circle';
    if (severity === 'critical') {
        bgColor = '#e74c3c';
        iconClass = 'fa-exclamation-triangle';
    } else if (severity === 'warning') {
        bgColor = '#f39c12';
        iconClass = 'fa-exclamation-circle';
    }

    return L.divIcon({
        className: `custom-alert-pin alert-${severity}`,
        html: `<div style="background-color: ${bgColor}; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid white; box-shadow: 0 3px 8px rgba(0,0,0,0.4);"><i class="fas ${iconClass}" style="color: white; font-size: 15px;"></i></div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
        popupAnchor: [0, -16]
    });
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

function addLocationMark(lat, lng, name = '', openPopup = false, id = null) {
    const markId = id || 'mark_' + Date.now() + '_' + Math.random().toString(36).substr(2, 4);

    const marker = L.marker([lat, lng], { icon: createMarkIcon() });

    const updatePopup = (currentName) => {
        const titleText = currentName ? currentName : 'Marked Location';
        const popupContent = `
            <div style="padding: 6px; min-width: 210px;">
                <h4 style="margin: 0 0 6px 0; color: #e74c3c; font-size: 0.95rem; display: flex; align-items: center;">
                    <i class="fas fa-map-marker-alt" style="margin-right: 6px;"></i> ${escapeHtml(titleText)}
                </h4>
                <p style="margin: 0 0 6px 0; font-size: 0.8rem; color: #666;">
                    Lat: ${lat.toFixed(4)}, Lng: ${lng.toFixed(4)}
                </p>
                <label style="font-size: 0.8rem; font-weight: bold; display: block; margin-bottom: 2px;">Label / Note:</label>
                <input type="text" id="input-${markId}" value="${escapeHtml(currentName)}" placeholder="e.g. Flood Zone, Safe Shelter" style="width: 100%; box-sizing: border-box; padding: 5px; margin: 2px 0 8px 0; border: 1px solid #ccc; border-radius: 4px; font-size: 0.85rem;">
                <div style="display: flex; gap: 4px; margin-bottom: 6px;">
                    <button onclick="saveMark('${markId}', ${lat}, ${lng})" style="background: #2ecc71; color: white; border: none; padding: 6px 10px; border-radius: 4px; cursor: pointer; font-size: 0.8rem; flex: 1; display: flex; align-items: center; justify-content: center; gap: 4px;">
                        <i class="fas fa-save"></i> Save
                    </button>
                    <button onclick="deleteMark('${markId}')" style="background: #e74c3c; color: white; border: none; padding: 6px 10px; border-radius: 4px; cursor: pointer; font-size: 0.8rem; display: flex; align-items: center; justify-content: center; gap: 4px;">
                        <i class="fas fa-trash-alt"></i> Delete
                    </button>
                </div>
                <button onclick="showRoute(${lat}, ${lng})" class="route-btn" style="background: #3498db; color: white; border: none; padding: 7px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85rem; width: 100%; display: flex; align-items: center; justify-content: center; gap: 5px; font-weight: bold;">
                    <i class="fas fa-directions"></i> Get Directions
                </button>
            </div>
        `;
        marker.bindPopup(popupContent);
    };

    updatePopup(name);

    if (markedLocationsLayer) {
        marker.addTo(markedLocationsLayer);
    }

    markedMarkerObjects[markId] = {
        marker: marker,
        lat: lat,
        lng: lng,
        name: name,
        id: markId
    };

    if (openPopup) {
        marker.openPopup();
    }

    updateSavedLandmarksUI();
    return markId;
}

function saveMark(id, lat, lng) {
    const inputEl = document.getElementById(`input-${id}`);
    const name = inputEl ? inputEl.value.trim() : '';

    if (markedMarkerObjects[id]) {
        markedMarkerObjects[id].name = name;
    }

    const saved = JSON.parse(localStorage.getItem('floodguard_marked_locations') || '[]');
    const existingIndex = saved.findIndex(m => m.id === id);
    if (existingIndex >= 0) {
        saved[existingIndex].name = name;
    } else {
        saved.push({ id, lat, lng, name });
    }
    localStorage.setItem('floodguard_marked_locations', JSON.stringify(saved));

    if (markedMarkerObjects[id] && markedMarkerObjects[id].marker) {
        const titleText = name ? name : 'Marked Location';
        const popupContent = `
            <div style="padding: 6px; min-width: 210px;">
                <h4 style="margin: 0 0 6px 0; color: #e74c3c; font-size: 0.95rem; display: flex; align-items: center;">
                    <i class="fas fa-map-marker-alt" style="margin-right: 6px;"></i> ${escapeHtml(titleText)}
                </h4>
                <p style="margin: 0 0 6px 0; font-size: 0.8rem; color: #666;">
                    Lat: ${lat.toFixed(4)}, Lng: ${lng.toFixed(4)}
                </p>
                <p style="margin: 0 0 6px 0; font-size: 0.85rem; color: #2ecc71; font-weight: bold;">
                    ✓ Saved location landmark!
                </p>
                <label style="font-size: 0.8rem; font-weight: bold; display: block; margin-bottom: 2px;">Label / Note:</label>
                <input type="text" id="input-${id}" value="${escapeHtml(name)}" placeholder="e.g. Flood Zone, Safe Shelter" style="width: 100%; box-sizing: border-box; padding: 5px; margin: 2px 0 8px 0; border: 1px solid #ccc; border-radius: 4px; font-size: 0.85rem;">
                <div style="display: flex; gap: 4px; margin-bottom: 6px;">
                    <button onclick="saveMark('${id}', ${lat}, ${lng})" style="background: #2ecc71; color: white; border: none; padding: 6px 10px; border-radius: 4px; cursor: pointer; font-size: 0.8rem; flex: 1; display: flex; align-items: center; justify-content: center; gap: 4px;">
                        <i class="fas fa-save"></i> Save
                    </button>
                    <button onclick="deleteMark('${id}')" style="background: #e74c3c; color: white; border: none; padding: 6px 10px; border-radius: 4px; cursor: pointer; font-size: 0.8rem; display: flex; align-items: center; justify-content: center; gap: 4px;">
                        <i class="fas fa-trash-alt"></i> Delete
                    </button>
                </div>
                <button onclick="showRoute(${lat}, ${lng})" class="route-btn" style="background: #3498db; color: white; border: none; padding: 7px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85rem; width: 100%; display: flex; align-items: center; justify-content: center; gap: 5px; font-weight: bold;">
                    <i class="fas fa-directions"></i> Get Directions
                </button>
            </div>
        `;
        markedMarkerObjects[id].marker.setPopupContent(popupContent);
    }
    updateSavedLandmarksUI();
}

function deleteMark(id) {
    if (markedMarkerObjects[id]) {
        if (markedLocationsLayer) {
            markedLocationsLayer.removeLayer(markedMarkerObjects[id].marker);
        }
        delete markedMarkerObjects[id];
    }
    const saved = JSON.parse(localStorage.getItem('floodguard_marked_locations') || '[]');
    const updated = saved.filter(m => m.id !== id);
    localStorage.setItem('floodguard_marked_locations', JSON.stringify(updated));
    updateSavedLandmarksUI();
}

function focusMarkOnMap(id) {
    if (markedMarkerObjects[id] && markedMarkerObjects[id].marker) {
        const item = markedMarkerObjects[id];
        map.setView([item.lat, item.lng], 15);
        item.marker.openPopup();
    }
}

function updateSavedLandmarksUI() {
    const container = document.getElementById('saved-landmarks-list');
    if (!container) return;

    const saved = JSON.parse(localStorage.getItem('floodguard_marked_locations') || '[]');
    if (saved.length === 0) {
        container.innerHTML = `
            <div style="background: #f8f9fa; padding: 1.5rem; text-align: center; border-radius: 8px; border: 1px dashed #ccc; color: #7f8c8d; grid-column: 1 / -1;">
                <i class="fas fa-map-pin" style="font-size: 2rem; margin-bottom: 0.5rem; color: #bdc3c7;"></i>
                <p style="margin: 0; font-size: 0.95rem;">No saved landmarks yet. Click anywhere on the map to pin and save a location landmark.</p>
            </div>
        `;
        return;
    }

    let html = '';
    saved.forEach(item => {
        const titleText = item.name ? item.name : 'Saved Location Mark';
        html += `
            <div style="background: white; border-radius: 8px; padding: 1rem; border-left: 5px solid #e74c3c; box-shadow: 0 2px 8px rgba(0,0,0,0.06); display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <h4 style="margin: 0 0 0.3rem 0; color: #2c3e50; font-size: 1.05rem; display: flex; align-items: center; justify-content: space-between;">
                        <span><i class="fas fa-map-marker-alt" style="color: #e74c3c; margin-right: 6px;"></i> ${escapeHtml(titleText)}</span>
                    </h4>
                    <p style="margin: 0 0 0.75rem 0; font-size: 0.85rem; color: #7f8c8d;">
                        <i class="fas fa-globe"></i> ${item.lat.toFixed(4)}, ${item.lng.toFixed(4)}
                    </p>
                </div>
                <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.5rem;">
                    <button onclick="showRoute(${item.lat}, ${item.lng})" style="background: #3498db; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 0.85rem; font-weight: bold; flex: 1; display: flex; align-items: center; justify-content: center; gap: 5px;">
                        <i class="fas fa-directions"></i> Get Directions
                    </button>
                    <button onclick="focusMarkOnMap('${item.id}')" style="background: #2ecc71; color: white; border: none; padding: 6px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85rem; display: flex; align-items: center; gap: 4px;">
                        <i class="fas fa-search-location"></i> View
                    </button>
                    <button onclick="deleteMark('${item.id}')" style="background: #e74c3c; color: white; border: none; padding: 6px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85rem; display: flex; align-items: center; gap: 4px;">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function loadSavedMarkedLocations() {
    try {
        const saved = JSON.parse(localStorage.getItem('floodguard_marked_locations') || '[]');
        saved.forEach(item => {
            addLocationMark(item.lat, item.lng, item.name, false, item.id);
        });
        updateSavedLandmarksUI();
    } catch (e) {
        console.error('Error loading saved marked locations:', e);
    }
}

function clearAllMarkedLocations() {
    if (confirm('Are you sure you want to remove all your location marks?')) {
        for (let id in markedMarkerObjects) {
            if (markedLocationsLayer) {
                markedLocationsLayer.removeLayer(markedMarkerObjects[id].marker);
            }
        }
        markedMarkerObjects = {};
        localStorage.removeItem('floodguard_marked_locations');
        updateSavedLandmarksUI();
    }
}

// Initialize map
function initMap() {
    map = L.map('map').setView([20.5937, 78.9629], 5); // Center on India

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // Create layer groups for different types of markers
    const hospitalLayer = L.layerGroup().addTo(map);
    const pharmacyLayer = L.layerGroup().addTo(map);
    const schoolLayer = L.layerGroup().addTo(map);
    const alertLayer = L.layerGroup().addTo(map);
    const landmarkLayer = L.layerGroup().addTo(map);
    markedLocationsLayer = L.layerGroup().addTo(map);

    // Add layer control
    const baseMaps = {
        "OpenStreetMap": L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        })
    };

    const overlayMaps = {
        "Hospitals": hospitalLayer,
        "Pharmacies": pharmacyLayer,
        "Schools": schoolLayer,
        "Alerts": alertLayer,
        "Landmarks": landmarkLayer,
        "Marked Locations": markedLocationsLayer
    };

    L.control.layers(baseMaps, overlayMaps).addTo(map);

    // Load saved marked locations
    loadSavedMarkedLocations();

    // Map click handler to add location marks
    map.on('click', function (e) {
        addLocationMark(e.latlng.lat, e.latlng.lng, '', true);
    });

    // Try to get user's location
    if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(
            function (position) {
                const userLat = position.coords.latitude;
                const userLng = position.coords.longitude;

                // Center map on user's location
                map.setView([userLat, userLng], 12);

                // Add user marker
                userMarker = L.marker([userLat, userLng], {
                    icon: createUserIcon()
                }).addTo(map).bindPopup('Your Location').openPopup();

                // Load nearby places
                loadNearbyPlaces(userLat, userLng, 'hospital', hospitalLayer);
                loadNearbyPlaces(userLat, userLng, 'pharmacy', pharmacyLayer);
                loadNearbyPlaces(userLat, userLng, 'school', schoolLayer);

                // Add some demo landmarks
                addDemoLandmarks(userLat, userLng, landmarkLayer);

                // Check for alerts in the area
                checkForAlerts(userLat, userLng, alertLayer);
            },
            function (error) {
                console.error("Error getting location: ", error);
                // Load some default data
                loadAlerts(alertLayer);
                addDemoLandmarks(20.5937, 78.9629, landmarkLayer);
            }
        );
    } else {
        console.log("Geolocation is not supported by this browser.");
        // Load some default data
        loadAlerts(alertLayer);
        addDemoLandmarks(20.5937, 78.9629, landmarkLayer);
    }
}

// Load nearby places from Overpass API
function loadNearbyPlaces(lat, lng, type, layer) {
    fetch(`/api/nearby-places?lat=${lat}&lon=${lng}&type=${type}&radius=5000`)
        .then(response => response.json())
        .then(data => {
            data.elements.forEach(element => {
                let markerLat, markerLng;

                if (element.type === 'node') {
                    markerLat = element.lat;
                    markerLng = element.lon;
                } else if (element.type === 'way' || element.type === 'relation') {
                    markerLat = element.center.lat;
                    markerLng = element.center.lon;
                }

                let iconObj;
                switch (type) {
                    case 'hospital':
                        iconObj = createHospitalIcon();
                        break;
                    case 'pharmacy':
                        iconObj = createPharmacyIcon();
                        break;
                    case 'school':
                        iconObj = createSchoolIcon();
                        break;
                    default:
                        iconObj = createLandmarkIcon();
                }

                const marker = L.marker([markerLat, markerLng], { icon: iconObj });

                let popupContent = `<b>${type.charAt(0).toUpperCase() + type.slice(1)}</b>`;
                if (element.tags && element.tags.name) {
                    popupContent = `<b>${element.tags.name}</b><br>${popupContent}`;
                }

                // Add route button to popup
                popupContent += `<br><button onclick="showRoute(${markerLat}, ${markerLng})" class="route-btn">Get Directions</button>`;

                marker.bindPopup(popupContent);
                marker.addTo(layer);
                placeMarkers.push(marker);
            });
        })
        .catch(error => {
            console.error('Error fetching nearby places:', error);
            // Add some demo markers for demonstration
            addDemoPlaces(lat, lng, type, layer);
        });
}

// Add demo places for demonstration
function addDemoPlaces(lat, lng, type, layer) {
    for (let i = 0; i < 5; i++) {
        const offsetLat = (Math.random() - 0.5) * 0.1;
        const offsetLng = (Math.random() - 0.5) * 0.1;

        let iconObj;
        let placeName;

        switch (type) {
            case 'hospital':
                iconObj = createHospitalIcon();
                placeName = `Hospital ${i + 1}`;
                break;
            case 'pharmacy':
                iconObj = createPharmacyIcon();
                placeName = `Pharmacy ${i + 1}`;
                break;
            case 'school':
                iconObj = createSchoolIcon();
                placeName = `School / Shelter ${i + 1}`;
                break;
        }

        const marker = L.marker([lat + offsetLat, lng + offsetLng], { icon: iconObj }).addTo(layer);

        marker.bindPopup(`<b>${placeName}</b><br>${type.charAt(0).toUpperCase() + type.slice(1)}<br><button onclick="showRoute(${lat + offsetLat}, ${lng + offsetLng})" class="route-btn">Get Directions</button>`);
        placeMarkers.push(marker);
    }
}

// Add demo landmarks
function addDemoLandmarks(lat, lng, layer) {
    const landmarks = [
        { name: 'City Center', lat: lat + 0.01, lng: lng + 0.01, type: 'landmark' },
        { name: 'Main Bridge', lat: lat + 0.02, lng: lng - 0.01, type: 'landmark' },
        { name: 'Central Park', lat: lat - 0.01, lng: lng + 0.02, type: 'landmark' },
        { name: 'River Front', lat: lat - 0.02, lng: lng - 0.02, type: 'landmark' }
    ];

    landmarks.forEach(landmark => {
        const marker = L.marker([landmark.lat, landmark.lng], {
            icon: createLandmarkIcon()
        }).addTo(layer);

        marker.bindPopup(`<b>${landmark.name}</b><br>Landmark<br><button onclick="showRoute(${landmark.lat}, ${landmark.lng})" class="route-btn">Get Directions</button>`);
        placeMarkers.push(marker);
    });
}

// Show route to a location
function showRoute(lat, lng) {
    if (routingControl) {
        map.removeControl(routingControl);
    }

    const drawRouteFromUser = (userLat, userLng) => {
        routingControl = L.Routing.control({
            waypoints: [
                L.latLng(userLat, userLng),
                L.latLng(lat, lng)
            ],
            routeWhileDragging: true,
            lineOptions: {
                styles: [{ color: '#3498db', weight: 5 }]
            }
        }).addTo(map);

        // Scroll smooth to map container if needed
        const mapEl = document.getElementById('map');
        if (mapEl) {
            mapEl.scrollIntoView({ behavior: 'smooth' });
        }
    };

    if (userMarker) {
        const userLatLng = userMarker.getLatLng();
        drawRouteFromUser(userLatLng.lat, userLatLng.lng);
    } else if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(
            function (position) {
                const userLat = position.coords.latitude;
                const userLng = position.coords.longitude;
                userMarker = L.marker([userLat, userLng], {
                    icon: createUserIcon()
                }).addTo(map).bindPopup('Your Location');
                drawRouteFromUser(userLat, userLng);
            },
            function (error) {
                alert('Please allow location access in your browser to calculate directions.');
            }
        );
    } else {
        alert('Geolocation is not supported by your browser.');
    }
}

// Load alerts from the server
function loadAlerts(layer) {
    fetch('/api/alerts')
        .then(response => response.json())
        .then(alerts => {
            alerts.forEach(alert => {
                addAlertMarker(alert, layer);
            });
        })
        .catch(error => {
            console.error('Error fetching alerts:', error);
            // Add some demo alerts for demonstration
            addDemoAlerts(layer);
        });
}

// Add an alert marker to the map
function addAlertMarker(alert, layer) {
    const alertIcon = createAlertIcon(alert.severity);

    const marker = L.marker([alert.latitude, alert.longitude], { icon: alertIcon }).addTo(layer);

    const popupContent = `
        <b>${alert.type.toUpperCase()} ALERT: ${alert.severity.toUpperCase()}</b><br>
        <b>Location:</b> ${alert.location}<br>
        <b>Description:</b> ${alert.description}<br>
        <b>Time:</b> ${new Date(alert.created_at).toLocaleString()}
    `;

    marker.bindPopup(popupContent);
    alertMarkers.push(marker);
}

// Add demo alerts for demonstration
function addDemoAlerts(layer) {
    const demoAlerts = [
        {
            type: 'flood',
            location: 'Kerala, Kochi',
            severity: 'warning',
            description: 'Heavy rainfall expected in the next 24 hours',
            latitude: 9.9312,
            longitude: 76.2673,
            created_at: new Date()
        },
        {
            type: 'flood',
            location: 'Assam, Guwahati',
            severity: 'critical',
            description: 'River water levels rising rapidly',
            latitude: 26.1445,
            longitude: 91.7362,
            created_at: new Date()
        },
        {
            type: 'cyclone',
            location: 'Odisha, Bhubaneswar',
            severity: 'info',
            description: 'Cyclone watch issued for coastal areas',
            latitude: 20.2961,
            longitude: 85.8245,
            created_at: new Date()
        }
    ];

    demoAlerts.forEach(alert => {
        addAlertMarker(alert, layer);
    });
}

// Check for alerts near the user's location
function checkForAlerts(lat, lng, layer) {
    fetch('/api/alerts')
        .then(response => response.json())
        .then(alerts => {
            alerts.forEach(alert => {
                // Simple distance calculation (for demo purposes)
                const distance = Math.sqrt(
                    Math.pow(alert.latitude - lat, 2) +
                    Math.pow(alert.longitude - lng, 2)
                ) * 100; // Rough approximation in km

                if (distance < 50) { // Within 50 km
                    addAlertMarker(alert, layer);
                    showAlertNotification(alert);
                }
            });
        })
        .catch(error => {
            console.error('Error checking for alerts:', error);
        });
}

// Show alert notification
function showAlertNotification(alert) {
    if ("Notification" in window && Notification.permission === "granted") {
        new Notification(`FloodGuard Alert: ${alert.type.toUpperCase()} in ${alert.location}`, {
            body: alert.description,
            icon: '/static/images/logo.png'
        });
    } else {
        // Fallback to browser alert
        alert(`FLOODGUARD ALERT: ${alert.type.toUpperCase()} in ${alert.location}\nSeverity: ${alert.severity.toUpperCase()}\n\n${alert.description}`);
    }
}

// Request notification permission
if ("Notification" in window) {
    Notification.requestPermission();
}

// Initialize map when page loads
document.addEventListener('DOMContentLoaded', function () {
    initMap();

    // Add routing plugin
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.css';
    document.head.appendChild(link);

    const script = document.createElement('script');
    script.src = 'https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.js';
    script.onload = function () {
        console.log('Routing plugin loaded');
    };
    document.head.appendChild(script);
}); 