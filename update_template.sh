#!/bin/bash

# Create a map_view_fixed.html file with our updated JavaScript
cat > templates/map_view_fixed.html << 'HTMLEND'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Property Map</title>
    <!-- Styles from the original template -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Lexend:wght@400;500;600&display=swap" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.4.1/dist/MarkerCluster.css">
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.4.1/dist/MarkerCluster.Default.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/nouislider@14.7.0/distribute/nouislider.min.css">
    <link rel="stylesheet" href="/static/css/main.css">
    <link rel="stylesheet" href="/static/css/micro-interactions.css">
    <style>
        /* Map-specific styles */
        #map {
            height: calc(100vh - 120px);
            min-height: 500px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
            z-index: 1;
        }
        
        .map-control-panel {
            background: white;
            padding: 18px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
            margin-bottom: 16px;
        }
        
        .loading-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255, 255, 255, 0.7);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
            border-radius: 12px;
        }
        
        .spinner {
            width: 40px;
            height: 40px;
            border: 3px solid rgba(0, 0, 0, 0.1);
            border-radius: 50%;
            border-top-color: #3772FF;
            animation: spin 1s ease-in-out infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .custom-marker {
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background-color: #3772FF;
            border: 3px solid white;
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.2);
        }
        
        .marker-residential { background-color: #4daf7c; }
        .marker-commercial { background-color: #3772ff; }
        .marker-agricultural { background-color: #f9c74f; color: #333; }
        .marker-industrial { background-color: #9d4edd; }
    </style>
</head>
<body>
    <!-- Navigation -->
    <div class="container-fluid p-0">
        <div class="row">
            <div class="col-12 mb-4">
                <div class="top-nav d-flex align-items-center justify-content-between p-3">
                    <a href="/" class="text-decoration-none">
                        <h3 class="m-0 text-primary">
                            <i class="fas fa-home me-2"></i>
                            Benton County Assessor
                        </h3>
                    </a>
                    <div class="d-flex">
                        <a href="/" class="btn btn-sm btn-outline-primary me-2">
                            <i class="fas fa-home me-1"></i> Home
                        </a>
                        <a href="/properties" class="btn btn-sm btn-outline-primary me-2">
                            <i class="fas fa-search me-1"></i> Properties
                        </a>
                        <a href="/statistics" class="btn btn-sm btn-outline-primary me-2">
                            <i class="fas fa-chart-bar me-1"></i> Statistics
                        </a>
                        <a href="/export-data" class="btn btn-sm btn-outline-primary me-2">
                            <i class="fas fa-file-export me-1"></i> Export
                        </a>
                        <a href="/map" class="btn btn-sm btn-primary">
                            <i class="fas fa-map-marked-alt me-1"></i> Map
                        </a>
                    </div>
                </div>
            </div>
        </div>

        <div class="container-fluid px-4">
            <div class="row mb-4">
                <div class="col">
                    <h1 class="fs-2 fw-bold d-flex align-items-center">
                        <i class="fas fa-map-marked-alt me-3 text-primary"></i> 
                        Interactive Property Map
                    </h1>
                    <p class="text-muted">
                        Explore properties across Benton County with our interactive map. Filter by property type, location, and value range.
                    </p>
                </div>
            </div>

            <div class="row">
                <!-- Map Container -->
                <div class="col-lg-9 col-md-12 mb-4">
                    <div class="card border-0 shadow-sm h-100">
                        <div class="card-body p-0 position-relative">
                            <div id="map-container" class="position-relative">
                                <div id="map"></div>
                                <div id="loading-overlay" class="loading-overlay">
                                    <div class="spinner"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Filter Panel -->
                <div class="col-lg-3 col-md-12">
                    <div class="map-filters">
                        <div class="map-control-panel">
                            <h5 class="mb-3">
                                <i class="fas fa-filter me-2 text-primary"></i> 
                                Filter Properties
                            </h5>
                            
                            <div class="mb-3">
                                <label class="form-label">Property Type</label>
                                <select id="property-type-filter" class="form-select form-select-sm">
                                    <option value="all">All Types</option>
                                    <option value="Residential">Residential</option>
                                    <option value="Commercial">Commercial</option>
                                    <option value="Agricultural">Agricultural</option>
                                    <option value="Industrial">Industrial</option>
                                </select>
                            </div>
                            
                            <div class="mb-3">
                                <label class="form-label">City</label>
                                <select id="city-filter" class="form-select form-select-sm">
                                    <option value="all">All Cities</option>
                                    <option value="Richland">Richland</option>
                                    <option value="Kennewick">Kennewick</option>
                                    <option value="Pasco">Pasco</option>
                                    <option value="West Richland">West Richland</option>
                                    <option value="Prosser">Prosser</option>
                                </select>
                            </div>
                            
                            <div class="mb-3">
                                <label class="form-label d-flex justify-content-between">
                                    <span>Property Value Range</span>
                                    <span class="text-muted" id="value-range-display">$0 - $1,000,000</span>
                                </label>
                                <div id="value-range-slider" class="mb-3"></div>
                            </div>
                            
                            <div class="d-grid gap-2">
                                <button id="refresh-btn" class="btn btn-primary">
                                    <i class="fas fa-filter me-1"></i> Apply Filters
                                </button>
                                <button id="reset-btn" class="btn btn-outline-secondary">
                                    <i class="fas fa-undo me-1"></i> Reset Filters
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Toast Container -->
        <div class="toast-container"></div>
    </div>

    <!-- Scripts -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.markercluster@1.4.1/dist/leaflet.markercluster.js"></script>
    <script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/nouislider@14.7.0/distribute/nouislider.min.js"></script>
    <script>
        // Initialize map
        const map = L.map('map').setView([46.2604, -119.2807], 11); // Centered on Benton County
        
        // Add OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }).addTo(map);
        
        // Create a marker cluster group
        const markers = L.markerClusterGroup();
        
        // Reference UI elements
        const propertyTypeSelect = document.getElementById('property-type-filter');
        const citySelect = document.getElementById('city-filter');
        const valueRangeDisplay = document.getElementById('value-range-display');
        const refreshBtn = document.getElementById('refresh-btn');
        const resetBtn = document.getElementById('reset-btn');
        const mapContainer = document.getElementById('map-container');
        const loadingOverlay = document.getElementById('loading-overlay');
        
        // Initialize global variables
        let propertyType = 'all';
        let city = 'all';
        let valueRange = [0, 1000000]; // Default value range
        
        // Initialize range slider
        const valueSlider = document.getElementById('value-range-slider');
        if (valueSlider) {
            noUiSlider.create(valueSlider, {
                start: [0, 1000000],
                connect: true,
                step: 10000,
                range: {
                    'min': 0,
                    'max': 1000000
                },
                format: {
                    to: function (value) {
                        return Math.round(value);
                    },
                    from: function (value) {
                        return Number(value);
                    }
                }
            });
            
            valueSlider.noUiSlider.on('update', function (values, handle) {
                valueRange = values;
                valueRangeDisplay.textContent = `$${numberWithCommas(values[0])} - $${numberWithCommas(values[1])}`;
            });
        }
        
        // Event listeners
        if (propertyTypeSelect) {
            propertyTypeSelect.addEventListener('change', function() {
                propertyType = this.value;
            });
        }
        
        if (citySelect) {
            citySelect.addEventListener('change', function() {
                city = this.value;
            });
        }
        
        if (refreshBtn) {
            refreshBtn.addEventListener('click', function() {
                this.disabled = true;
                this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...';
                loadMapData();
            });
        }
        
        if (resetBtn) {
            resetBtn.addEventListener('click', function() {
                // Reset filters to default values
                propertyType = 'all';
                city = 'all';
                valueRange = [0, 1000000];
                
                // Reset UI elements
                if (propertyTypeSelect) propertyTypeSelect.value = 'all';
                if (citySelect) citySelect.value = 'all';
                if (valueSlider) valueSlider.noUiSlider.set([0, 1000000]);
                
                // Reload map data
                loadMapData();
            });
        }
        
        // Helper function to format numbers with commas
        function numberWithCommas(x) {
            return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
        }
        
        // Helper function to show toast notifications
        function showToast(message, type = 'info') {
            const toastContainer = document.querySelector('.toast-container');
            
            let icon = '<i class="fas fa-info-circle"></i>';
            if (type === 'success') icon = '<i class="fas fa-check-circle"></i>';
            if (type === 'warning') icon = '<i class="fas fa-exclamation-triangle"></i>';
            if (type === 'error') icon = '<i class="fas fa-times-circle"></i>';
            
            const toast = document.createElement('div');
            toast.className = `alert alert-${type} alert-dismissible fade show`;
            toast.innerHTML = `
                ${icon} ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            
            toastContainer.appendChild(toast);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                if (toast.parentNode === toastContainer) {
                    const alert = new bootstrap.Alert(toast);
                    alert.close();
                }
            }, 5000);
        }
        
        // Function to create a custom property marker
        function createPropertyMarker(property, latlng) {
            // Determine marker class based on property type
            let markerClass = 'marker-residential'; // Default
            let typeInitial = 'R';
            
            if (property.property_type) {
                const type = property.property_type.toLowerCase();
                
                if (type.includes('commercial')) {
                    markerClass = 'marker-commercial';
                    typeInitial = 'C';
                } else if (type.includes('agricultural')) {
                    markerClass = 'marker-agricultural';
                    typeInitial = 'A';
                } else if (type.includes('industrial')) {
                    markerClass = 'marker-industrial';
                    typeInitial = 'I';
                }
            }
            
            // Create custom icon
            const customIcon = L.divIcon({
                className: `custom-marker ${markerClass}`,
                html: `<span>${typeInitial}</span>`,
                iconSize: [36, 36],
                iconAnchor: [18, 18]
            });
            
            return L.marker(latlng, { icon: customIcon });
        }
        
        // Main function to load map data
        function loadMapData() {
            // Clear existing markers
            markers.clearLayers();
            
            // Show loading overlay if it was removed
            if (!mapContainer.contains(loadingOverlay)) {
                mapContainer.appendChild(loadingOverlay);
            }
            
            // Fetch and filter properties
            fetch('/api/map/data')
                .then(response => response.json())
                .then(data => {
                    console.log('Map data received:', data); // Debug log
                    
                    // Hide loading overlay
                    if (loadingOverlay.parentNode === mapContainer) {
                        mapContainer.removeChild(loadingOverlay);
                    }
                    
                    // Reset button
                    if (refreshBtn) {
                        refreshBtn.disabled = false;
                        refreshBtn.innerHTML = '<i class="fas fa-filter me-1"></i> Apply Filters';
                    }
                    
                    // Check if data has the correct structure
                    if (!data.geojson || !data.geojson.features || data.geojson.features.length === 0) {
                        console.log('No property data available');
                        showToast('No property data available', 'warning');
                        return;
                    }
                    
                    // Convert GeoJSON features to properties array
                    const properties = data.geojson.features.map(feature => {
                        return {
                            ...feature.properties,
                            latitude: feature.geometry.coordinates[1],
                            longitude: feature.geometry.coordinates[0]
                        };
                    });
                    
                    console.log('Converted properties:', properties.slice(0, 2)); // Debug log
                    
                    // Filter properties based on selection
                    const filteredProperties = properties.filter(property => {
                        const matchesType = propertyType === 'all' || property.property_type === propertyType;
                        const matchesCity = city === 'all' || property.property_city === city;
                        const matchesValue = property.assessed_value >= valueRange[0] && 
                                           property.assessed_value <= valueRange[1];
                        
                        return matchesType && matchesCity && matchesValue;
                    });
                    
                    // Add markers for filtered properties
                    filteredProperties.forEach(property => {
                        // Skip if no location data
                        if (!property.latitude || !property.longitude) return;
                        
                        const latlng = [property.latitude, property.longitude];
                        const marker = createPropertyMarker(property, latlng);
                        
                        // Add popup with property info
                        const popupContent = `
                            <div>
                                <h5>${property.property_type || 'Property'} #${property.account_id}</h5>
                                <p><strong>Location:</strong> ${property.property_city || 'Unknown'}</p>
                                <p><strong>Owner:</strong> ${property.owner_name || 'Unknown'}</p>
                                <p><strong>Assessed Value:</strong> $${numberWithCommas(property.assessed_value || 0)}</p>
                                <p><strong>Tax Amount:</strong> $${numberWithCommas(property.tax_amount || 0)}</p>
                                <a href="/property/${property.account_id}" class="btn btn-sm btn-primary">View Details</a>
                            </div>
                        `;
                        marker.bindPopup(popupContent);
                        
                        // Add marker to cluster group
                        markers.addLayer(marker);
                    });
                    
                    // Add markers to map
                    map.addLayer(markers);
                    
                    // Set map bounds based on filtered properties
                    if (filteredProperties.length > 0) {
                        try {
                            if (data.bounds) {
                                map.fitBounds([
                                    [data.bounds.south, data.bounds.west],
                                    [data.bounds.north, data.bounds.east]
                                ]);
                            }
                        } catch (error) {
                            console.error('Error setting map bounds:', error);
                        }
                    }
                    
                    // Show toast with property count
                    showToast(`Displaying ${filteredProperties.length} properties on the map.`, 'info');
                })
                .catch(error => {
                    console.error('Error loading map data:', error);
                    showToast('Error loading map data. Please try again.', 'error');
                    
                    // Reset button
                    if (refreshBtn) {
                        refreshBtn.disabled = false;
                        refreshBtn.innerHTML = '<i class="fas fa-filter me-1"></i> Apply Filters';
                    }
                    
                    // Hide loading overlay
                    if (loadingOverlay.parentNode === mapContainer) {
                        mapContainer.removeChild(loadingOverlay);
                    }
                });
        }
        
        // Initialize the map with data
        loadMapData();
    </script>
</body>
</html>
HTMLEND

# Create a Python file to update the routes.py file to use our fixed template
cat > update_routes.py << 'PYTHONEND'
import os
import re

# Function to update routes.py to use the new template
def update_routes_file():
    routes_path = 'routes.py'
    
    # Check if the file exists
    if not os.path.exists(routes_path):
        print(f"Error: {routes_path} not found")
        return False
    
    # Read the original file
    with open(routes_path, 'r') as file:
        content = file.read()
    
    # Look for the map route
    map_route_pattern = r'@app\.route\([\'\"]\/map[\'\"](.*?)\)\s*?def\s+map_view\(\):(.*?)return\s+render_template\([\'\"](.*?)[\'\"]'
    
    # Replace the template name in the map_view function
    updated_content = re.sub(
        map_route_pattern,
        lambda m: m.group(0).replace(m.group(3), 'map_view_fixed.html'),
        content,
        flags=re.DOTALL
    )
    
    # Write the updated content back to the file
    with open(routes_path, 'w') as file:
        file.write(updated_content)
    
    return True

# Run the function
if __name__ == "__main__":
    result = update_routes_file()
    if result:
        print("Routes file updated successfully")
    else:
        print("Failed to update routes file")
PYTHONEND

# Make the scripts executable
chmod +x update_template.sh
chmod +x update_routes.py

# Run the scripts
./update_template.sh
python update_routes.py

# Restart the application workflow
echo "Files updated. Restarting application."
restart_workflow "Start application"
