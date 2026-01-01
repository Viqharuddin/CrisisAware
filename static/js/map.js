// static/js/map.js
let map;
let userMarker;
let alertMarkers = [];
let placeMarkers = [];
let routingControl = null;

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
        "Landmarks": landmarkLayer
    };
    
    L.control.layers(baseMaps, overlayMaps).addTo(map);
    
    // Try to get user's location
    if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(
            function(position) {
                const userLat = position.coords.latitude;
                const userLng = position.coords.longitude;
                
                // Center map on user's location
                map.setView([userLat, userLng], 12);
                
                // Add user marker
                userMarker = L.marker([userLat, userLng], {
                    icon: L.icon({
                        iconUrl: '/static/images/user-marker.png',
                        iconSize: [30, 30],
                        iconAnchor: [15, 30],
                        popupAnchor: [0, -30]
                    })
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
            function(error) {
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
                
                let iconColor;
                let iconUrl;
                
                switch(type) {
                    case 'hospital':
                        iconColor = '#e74c3c';
                        iconUrl = '/static/images/hospital-marker.png';
                        break;
                    case 'pharmacy':
                        iconColor = '#3498db';
                        iconUrl = '/static/images/pharmacy-marker.png';
                        break;
                    case 'school':
                        iconColor = '#f39c12';
                        iconUrl = '/static/images/school-marker.png';
                        break;
                    default:
                        iconColor = '#2c3e50';
                        iconUrl = '/static/images/marker.png';
                }
                
                const marker = L.marker([markerLat, markerLng], {
                    icon: L.icon({
                        iconUrl: iconUrl,
                        iconSize: [25, 41],
                        iconAnchor: [12, 41],
                        popupAnchor: [1, -34],
                        shadowUrl: '/static/images/marker-shadow.png',
                        shadowSize: [41, 41]
                    })
                });
                
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
        
        let iconUrl;
        let placeName;
        
        switch(type) {
            case 'hospital':
                iconUrl = '/static/images/hospital-marker.png';
                placeName = `Hospital ${i+1}`;
                break;
            case 'pharmacy':
                iconUrl = '/static/images/pharmacy-marker.png';
                placeName = `Pharmacy ${i+1}`;
                break;
            case 'school':
                iconUrl = '/static/images/school-marker.png';
                placeName = `School ${i+1}`;
                break;
        }
        
        const marker = L.marker([lat + offsetLat, lng + offsetLng], {
            icon: L.icon({
                iconUrl: iconUrl,
                iconSize: [25, 41],
                iconAnchor: [12, 41],
                popupAnchor: [1, -34]
            })
        }).addTo(layer);
        
        marker.bindPopup(`<b>${placeName}</b><br>${type.charAt(0).toUpperCase() + type.slice(1)}<br><button onclick="showRoute(${lat + offsetLat}, ${lng + offsetLng})" class="route-btn">Get Directions</button>`);
        placeMarkers.push(marker);
    }
}

// Add demo landmarks
function addDemoLandmarks(lat, lng, layer) {
    const landmarks = [
        {name: 'City Center', lat: lat + 0.01, lng: lng + 0.01, type: 'landmark'},
        {name: 'Main Bridge', lat: lat + 0.02, lng: lng - 0.01, type: 'landmark'},
        {name: 'Central Park', lat: lat - 0.01, lng: lng + 0.02, type: 'landmark'},
        {name: 'River Front', lat: lat - 0.02, lng: lng - 0.02, type: 'landmark'}
    ];
    
    landmarks.forEach(landmark => {
        const marker = L.marker([landmark.lat, landmark.lng], {
            icon: L.icon({
                iconUrl: '/static/images/landmark-marker.png',
                iconSize: [25, 41],
                iconAnchor: [12, 41],
                popupAnchor: [1, -34]
            })
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
    
    if (userMarker) {
        const userLatLng = userMarker.getLatLng();
        
        routingControl = L.Routing.control({
            waypoints: [
                L.latLng(userLatLng.lat, userLatLng.lng),
                L.latLng(lat, lng)
            ],
            routeWhileDragging: true,
            lineOptions: {
                styles: [{color: '#3498db', weight: 5}]
            }
        }).addTo(map);
    } else {
        alert('Please allow location access to use routing');
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
    let alertIcon;
    if (alert.severity === 'critical') {
        alertIcon = L.icon({
            iconUrl: '/static/images/alert-critical.png',
            iconSize: [30, 30],
            iconAnchor: [15, 30],
            popupAnchor: [0, -30]
        });
    } else if (alert.severity === 'warning') {
        alertIcon = L.icon({
            iconUrl: '/static/images/alert-warning.png',
            iconSize: [30, 30],
            iconAnchor: [15, 30],
            popupAnchor: [0, -30]
        });
    } else {
        alertIcon = L.icon({
            iconUrl: '/static/images/alert-info.png',
            iconSize: [30, 30],
            iconAnchor: [15, 30],
            popupAnchor: [0, -30]
        });
    }
    
    const marker = L.marker([alert.latitude, alert.longitude], {icon: alertIcon}).addTo(layer);
    
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
document.addEventListener('DOMContentLoaded', function() {
    initMap();
    
    // Add routing plugin
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.css';
    document.head.appendChild(link);
    
    const script = document.createElement('script');
    script.src = 'https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.js';
    script.onload = function() {
        console.log('Routing plugin loaded');
    };
    document.head.appendChild(script);
}); 