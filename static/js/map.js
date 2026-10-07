// static/js/map.js
let map;
let userMarker;
let alertMarkers = [];
let placeMarkers = [];
let routingControl = null;
let markedLocationsLayer;
let markedMarkerObjects = {};
let isRoutingReady = false;

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
    const sev = (severity || 'info').toLowerCase();
    if (sev === 'critical' || sev === 'extreme' || sev === 'severe') {
        bgColor = '#e74c3c';
        iconClass = 'fa-exclamation-triangle';
    } else if (sev === 'warning' || sev === 'high' || sev === 'moderate') {
        bgColor = '#f39c12';
        iconClass = 'fa-exclamation-circle';
    }

    return L.divIcon({
        className: `custom-alert-pin alert-${sev}`,
        html: `<div style="background-color: ${bgColor}; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid white; box-shadow: 0 3px 8px rgba(0,0,0,0.4);"><i class="fas ${iconClass}" style="color: white; font-size: 15px;"></i></div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
        popupAnchor: [0, -16]
    });
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

// Great-circle distance in kilometers between two lat/lon points
function haversineKm(lat1, lon1, lat2, lon2) {
    const R = 6371;
    const toRad = (d) => d * Math.PI / 180;
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a = Math.sin(dLat / 2) ** 2 +
        Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// Show a clear, non-fabricated status/error banner above the map (uses textContent — no HTML injection)
function showMapNotice(message, isError) {
    let el = document.getElementById('map-notice');
    if (!el) {
        el = document.createElement('div');
        el.id = 'map-notice';
        const mapEl = document.getElementById('map');
        if (mapEl && mapEl.parentNode) {
            mapEl.parentNode.insertBefore(el, mapEl);
        } else {
            document.body.appendChild(el);
        }
    }
    el.textContent = message;
    el.style.cssText = 'margin: 0.5rem 2rem; padding: 0.75rem 1rem; border-radius: 6px; font-size: 0.9rem; border-left: 4px solid ' +
        (isError ? '#e74c3c' : '#f39c12') + '; background: ' + (isError ? '#fdecea' : '#fef5e7') +
        '; color: ' + (isError ? '#922b21' : '#9c640c') + ';';
    el.style.display = 'block';
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
    const input = document.getElementById(`input-${id}`);
    const name = input ? input.value.trim() : '';
    if (markedMarkerObjects[id]) {
        markedMarkerObjects[id].name = name;

        // Persist to localStorage
        saveMarkedLocationsToStorage();

        // Update popup title
        const updatePopupFn = (currentName) => {
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
                    <input type="text" id="input-${id}" value="${escapeHtml(currentName)}" placeholder="e.g. Flood Zone, Safe Shelter" style="width: 100%; box-sizing: border-box; padding: 5px; margin: 2px 0 8px 0; border: 1px solid #ccc; border-radius: 4px; font-size: 0.85rem;">
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
            markedMarkerObjects[id].marker.bindPopup(popupContent);
        };
        updatePopupFn(name);
        markedMarkerObjects[id].marker.closePopup();
        updateSavedLandmarksUI();
    }
}

function deleteMark(id) {
    if (markedMarkerObjects[id]) {
        if (markedLocationsLayer) {
            markedLocationsLayer.removeLayer(markedMarkerObjects[id].marker);
        }
        delete markedMarkerObjects[id];
        saveMarkedLocationsToStorage();
        updateSavedLandmarksUI();
    }
}

function saveMarkedLocationsToStorage() {
    const list = Object.values(markedMarkerObjects).map(item => ({
        id: item.id,
        lat: item.lat,
        lng: item.lng,
        name: item.name
    }));
    localStorage.setItem('floodguard_marked_locations', JSON.stringify(list));
}

function focusMarkOnMap(id) {
    if (markedMarkerObjects[id]) {
        const item = markedMarkerObjects[id];
        map.setView([item.lat, item.lng], 14);
        item.marker.openPopup();
        const mapEl = document.getElementById('map');
        if (mapEl) {
            mapEl.scrollIntoView({ behavior: 'smooth' });
        }
    }
}

function updateSavedLandmarksUI() {
    const container = document.getElementById('saved-landmarks-list');
    if (!container) return;

    const items = Object.values(markedMarkerObjects);
    if (items.length === 0) {
        container.innerHTML = `
            <div style="grid-column: 1 / -1; background: #f8f9fa; border: 1px dashed #d6dbdf; border-radius: 8px; padding: 1.25rem; text-align: center; color: #7f8c8d; font-size: 0.9rem;">
                <i class="fas fa-map-pin" style="color: #bdc3c7; font-size: 1.5rem; margin-bottom: 0.35rem; display: block;"></i>
                No custom landmarks marked yet. Click anywhere on the map above to mark a location!
            </div>
        `;
        return;
    }

    let html = '';
    items.forEach((item, index) => {
        const label = item.name ? item.name : `Marked Location #${index + 1}`;
        html += `
            <div style="background: white; border-radius: 8px; padding: 1rem; box-shadow: 0 2px 6px rgba(0,0,0,0.06); border-left: 4px solid #9b59b6; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.35rem;">
                        <h4 style="margin: 0; color: #2c3e50; font-size: 1rem; font-weight: 600;">
                            <i class="fas fa-bookmark" style="color: #9b59b6; margin-right: 4px;"></i> ${escapeHtml(label)}
                        </h4>
                    </div>
                    <div style="font-size: 0.8rem; color: #7f8c8d; margin-bottom: 0.75rem;">
                        <i class="fas fa-compass"></i> ${item.lat.toFixed(4)}, ${item.lng.toFixed(4)}
                    </div>
                </div>
                <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem;">
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
    if (window.confirm('Are you sure you want to remove all your location marks?')) {
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

    // Layer groups for markers
    const hospitalLayer = L.layerGroup().addTo(map);
    const pharmacyLayer = L.layerGroup().addTo(map);
    const schoolLayer = L.layerGroup().addTo(map);
    const alertLayer = L.layerGroup().addTo(map);
    const landmarkLayer = L.layerGroup().addTo(map);
    markedLocationsLayer = L.layerGroup().addTo(map);

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

                map.setView([userLat, userLng], 12);

                userMarker = L.marker([userLat, userLng], {
                    icon: createUserIcon()
                }).addTo(map).bindPopup('Your Location').openPopup();

                loadNearbyPlaces(userLat, userLng, 'hospital', hospitalLayer);
                loadNearbyPlaces(userLat, userLng, 'pharmacy', pharmacyLayer);
                loadNearbyPlaces(userLat, userLng, 'school', schoolLayer);
                addDemoLandmarks(userLat, userLng, landmarkLayer);
                checkForAlerts(userLat, userLng, alertLayer);
            },
            function (error) {
                console.warn("Geolocation permission error: ", error);
                loadAlerts(alertLayer);
                addDemoLandmarks(20.5937, 78.9629, landmarkLayer);
            },
            { timeout: 8000 }
        );
    } else {
        loadAlerts(alertLayer);
        addDemoLandmarks(20.5937, 78.9629, landmarkLayer);
    }
}

// Load nearby places from Overpass API
function loadNearbyPlaces(lat, lng, type, layer) {
    fetch(`/api/nearby-places?lat=${lat}&lon=${lng}&type=${type}&radius=5000`)
        .then(response => response.json())
        .then(data => {
            if (data.elements && data.elements.length > 0) {
                data.elements.forEach(element => {
                    let markerLat, markerLng;

                    if (element.type === 'node') {
                        markerLat = element.lat;
                        markerLng = element.lon;
                    } else if (element.type === 'way' || element.type === 'relation') {
                        markerLat = element.center.lat;
                        markerLng = element.center.lon;
                    }

                    if (!markerLat || !markerLng) return;

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
                    let popupContent = `<b>${escapeHtml(type.charAt(0).toUpperCase() + type.slice(1))}</b>`;
                    if (element.tags && element.tags.name) {
                        popupContent = `<b>${escapeHtml(element.tags.name)}</b><br>${popupContent}`;
                    }
                    popupContent += `<br><button onclick="showRoute(${markerLat}, ${markerLng})" class="route-btn">Get Directions</button>`;

                    marker.bindPopup(popupContent);
                    marker.addTo(layer);
                    placeMarkers.push(marker);
                });
            } else {
                // No fabricated fallback data — just report that nothing was found nearby.
                console.info(`No ${type} results returned near this location.`);
            }
        })
        .catch(error => {
            console.error('Error fetching nearby places:', error);
            showMapNotice('Could not load nearby emergency places (external map service unavailable). Only alerts and your own marks are shown.', true);
        });
}

// Add demo landmarks
function addDemoLandmarks(lat, lng, layer) {
    const landmarks = [
        { name: 'City Center Hub', lat: lat + 0.012, lng: lng + 0.012, type: 'landmark' },
        { name: 'Main River Bridge', lat: lat + 0.022, lng: lng - 0.014, type: 'landmark' },
        { name: 'Central Relief Grounds', lat: lat - 0.015, lng: lng + 0.018, type: 'landmark' },
        { name: 'Coastal Watch Point', lat: lat - 0.024, lng: lng - 0.022, type: 'landmark' }
    ];

    landmarks.forEach(landmark => {
        const marker = L.marker([landmark.lat, landmark.lng], {
            icon: createLandmarkIcon()
        }).addTo(layer);

        marker.bindPopup(`<b>${escapeHtml(landmark.name)}</b><br><span style="color:#7f8c8d; font-size:0.8rem;">[Landmark]</span><br><button onclick="showRoute(${landmark.lat}, ${landmark.lng})" class="route-btn">Get Directions</button>`);
        placeMarkers.push(marker);
    });
}

// Show route to a location
function showRoute(lat, lng) {
    if (typeof L.Routing === 'undefined' || !L.Routing.control) {
        window.alert('The routing system is currently loading. Please try clicking Get Directions again in a few seconds.');
        return;
    }

    if (routingControl) {
        try {
            map.removeControl(routingControl);
        } catch (e) {
            console.warn('Error clearing previous route control:', e);
        }
    }

    const drawRouteFromUser = (userLat, userLng) => {
        try {
            routingControl = L.Routing.control({
                waypoints: [
                    L.latLng(userLat, userLng),
                    L.latLng(lat, lng)
                ],
                routeWhileDragging: false,
                lineOptions: {
                    styles: [{ color: '#3498db', weight: 5 }]
                }
            }).addTo(map);

            const mapEl = document.getElementById('map');
            if (mapEl) {
                mapEl.scrollIntoView({ behavior: 'smooth' });
            }
        } catch (err) {
            console.error('Error drawing route:', err);
            window.alert('Unable to generate map route at this moment.');
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
                window.alert('Please allow browser location access so we can draw driving directions from your location.');
            }
        );
    } else {
        window.alert('Geolocation is not supported by your browser.');
    }
}

// Load alerts from server
function loadAlerts(layer) {
    fetch('/api/alerts')
        .then(response => response.json())
        .then(alerts => {
            if (alerts && alerts.length > 0) {
                alerts.forEach(alertItem => {
                    addAlertMarker(alertItem, layer);
                });
            }
            // No alerts is a valid state — do not fabricate demo alerts.
        })
        .catch(error => {
            console.error('Error fetching alerts:', error);
            showMapNotice('Could not load emergency alerts right now. Please try again shortly.', true);
        });
}

// Add an alert marker to the map
function addAlertMarker(alertItem, layer) {
    const alertIcon = createAlertIcon(alertItem.severity);
    const marker = L.marker([alertItem.latitude, alertItem.longitude], { icon: alertIcon }).addTo(layer);

    const popupContent = `
        <b>${escapeHtml((alertItem.type || 'EMERGENCY').toUpperCase())} ALERT: ${escapeHtml((alertItem.severity || 'INFO').toUpperCase())}</b><br>
        <b>Location:</b> ${escapeHtml(alertItem.location || 'Your Region')}<br>
        <b>Description:</b> ${escapeHtml(alertItem.description || '')}<br>
        <b>Time:</b> ${alertItem.created_at ? new Date(alertItem.created_at).toLocaleString() : 'Active'}
    `;

    marker.bindPopup(popupContent);
    alertMarkers.push(marker);
}

// Check for alerts near user
function checkForAlerts(lat, lng, layer) {
    fetch('/api/alerts')
        .then(response => response.json())
        .then(alerts => {
            if (alerts && Array.isArray(alerts)) {
                alerts.forEach(alertItem => {
                    if (typeof alertItem.latitude !== 'number' || typeof alertItem.longitude !== 'number') {
                        return;
                    }
                    const distance = haversineKm(lat, lng, alertItem.latitude, alertItem.longitude);

                    if (distance < 50) {
                        addAlertMarker(alertItem, layer);
                        showAlertNotification(alertItem);
                    }
                });
            }
        })
        .catch(error => {
            console.error('Error checking for alerts:', error);
        });
}

// Show alert notification safely (renamed parameter from alert to alertData to avoid shadowing window.alert)
function showAlertNotification(alertData) {
    if ("Notification" in window && Notification.permission === "granted") {
        try {
            new Notification(`CrisisAware Alert: ${String(alertData.type || 'Warning').toUpperCase()} in ${alertData.location || 'Your Area'}`, {
                body: alertData.description || 'Emergency weather alert active.'
            });
        } catch (e) {
            console.warn('Could not trigger HTML5 notification:', e);
        }
    }
}

// Request notification permission
if ("Notification" in window && Notification.permission === "default") {
    Notification.requestPermission();
}

// Initialize map on DOM load
document.addEventListener('DOMContentLoaded', function () {
    initMap();

    // Dynamically load leaflet-routing-machine
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.css';
    document.head.appendChild(link);

    const script = document.createElement('script');
    script.src = 'https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.js';
    script.onload = function () {
        isRoutingReady = true;
        console.log('Leaflet Routing Machine ready.');
    };
    script.onerror = function () {
        console.warn('Failed to load Leaflet Routing Machine plugin.');
    };
    document.head.appendChild(script);
});