/**
 * Dashboard Map Module
 * 
 * This module handles the interactive property map on the statistics dashboard.
 * It initializes a Leaflet map with marker clusters and handles data loading,
 * filtering, and interaction.
 */

let propertyMap;
let markerClusterGroup;
let propertyMarkers = [];
let mapInitialized = false;

/**
 * Initialize the property map
 */
function initializeMap() {
    if (mapInitialized) return;
    
    // Create a map in the #property-map div
    propertyMap = L.map('property-map').setView([46.2804, -119.2752], 10);
    
    // Add the base map layer (OpenStreetMap)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
    }).addTo(propertyMap);
    
    // Add satellite map layer
    const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
        maxZoom: 19
    });
    
    // Create a marker cluster group
    markerClusterGroup = L.markerClusterGroup({
        disableClusteringAtZoom: 16,
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true,
        maxClusterRadius: 50
    });
    
    propertyMap.addLayer(markerClusterGroup);
    
    // Add map controls
    const baseMaps = {
        "Map": L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }),
        "Satellite": satelliteLayer
    };
    
    // Map view type selector listener
    document.getElementById('map-view-type').addEventListener('change', function() {
        const viewType = this.value;
        
        // Remove current layer
        propertyMap.eachLayer(function(layer) {
            if (layer instanceof L.TileLayer) {
                propertyMap.removeLayer(layer);
            }
        });
        
        // Add selected layer
        if (viewType === 'satellite') {
            satelliteLayer.addTo(propertyMap);
        } else {
            baseMaps["Map"].addTo(propertyMap);
        }
    });
    
    // Property filter listener
    document.getElementById('map-property-filter').addEventListener('change', function() {
        filterMapMarkers(this.value);
    });
    
    // Load sample property data
    loadMapData();
    
    mapInitialized = true;
}

/**
 * Load property data for the map
 */
function loadMapData() {
    // In a production app, this would fetch data from an API endpoint
    const sampleData = [
        {id: 1, lat: 46.3071, lng: -119.2941, type: 'residential', value: 325000, address: '123 Main St, Richland'},
        {id: 2, lat: 46.3103, lng: -119.2962, type: 'commercial', value: 1250000, address: '456 Market St, Richland'},
        {id: 3, lat: 46.2122, lng: -119.1361, type: 'residential', value: 280000, address: '789 Oak Ave, Kennewick'},
        {id: 4, lat: 46.2185, lng: -119.1378, type: 'residential', value: 315000, address: '321 Pine St, Kennewick'},
        {id: 5, lat: 46.2165, lng: -119.1665, type: 'commercial', value: 875000, address: '555 Business Pkwy, Kennewick'},
        {id: 6, lat: 46.2289, lng: -119.7782, type: 'agricultural', value: 120000, address: '777 Farm Rd, Prosser'},
        {id: 7, lat: 46.2814, lng: -119.7755, type: 'agricultural', value: 145000, address: '888 Vineyard Ln, Prosser'},
        {id: 8, lat: 46.2916, lng: -119.3608, type: 'residential', value: 495000, address: '432 River Dr, West Richland'},
        {id: 9, lat: 46.2865, lng: -119.3689, type: 'residential', value: 425000, address: '654 Mountain View, West Richland'},
        {id: 10, lat: 46.2636, lng: -119.4822, type: 'agricultural', value: 95000, address: '999 Orchard Rd, Benton City'}
    ];
    
    // Clear existing markers
    if (markerClusterGroup) {
        markerClusterGroup.clearLayers();
        propertyMarkers = [];
    }
    
    // Add markers for each property
    sampleData.forEach(property => {
        const marker = createPropertyMarker(property);
        propertyMarkers.push({marker, property});
        markerClusterGroup.addLayer(marker);
    });
    
    // Update the visible properties count
    document.getElementById('visible-properties').textContent = sampleData.length;
    
    // Update average value
    const totalValue = sampleData.reduce((sum, prop) => sum + prop.value, 0);
    const avgValue = totalValue / sampleData.length;
    document.getElementById('avg-value-in-view').textContent = formatCurrency(avgValue);
    
    // Update property density - assuming a 10 sq mile area for this sample
    document.getElementById('property-density').textContent = (sampleData.length / 10).toFixed(1);
}

/**
 * Create a marker for a property
 */
function createPropertyMarker(property) {
    // Choose icon color based on property type
    let markerColor;
    switch (property.type) {
        case 'residential':
            markerColor = '#4B91F1'; // Blue
            break;
        case 'commercial':
            markerColor = '#F15F4B'; // Red
            break;
        case 'agricultural':
            markerColor = '#42BE65'; // Green
            break;
        case 'industrial':
            markerColor = '#8A3FFC'; // Purple
            break;
        case 'multifamily':
            markerColor = '#F1C21B'; // Yellow
            break;
        default:
            markerColor = '#121619'; // Dark gray
    }
    
    // Create custom marker
    const icon = L.divIcon({
        className: 'custom-marker',
        html: `<div style="background-color: ${markerColor}; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white;"></div>`,
        iconSize: [16, 16],
        iconAnchor: [8, 8]
    });
    
    // Create marker and popup content
    const marker = L.marker([property.lat, property.lng], { icon: icon });
    const popupContent = `
        <div class="property-popup">
            <h6 class="mb-1">${property.address}</h6>
            <p class="mb-1">Type: ${property.type.charAt(0).toUpperCase() + property.type.slice(1)}</p>
            <p class="mb-1">Value: ${formatCurrency(property.value)}</p>
            <a href="/property/${property.id}" class="btn btn-sm btn-primary mt-2">View Details</a>
        </div>
    `;
    marker.bindPopup(popupContent);
    
    // Add property data to marker
    marker.propertyType = property.type;
    
    return marker;
}

/**
 * Filter map markers by property type
 */
function filterMapMarkers(propertyType) {
    // Clear existing markers
    markerClusterGroup.clearLayers();
    
    // Filter markers by property type
    const filteredMarkers = propertyType === 'all' 
        ? propertyMarkers 
        : propertyMarkers.filter(item => item.property.type === propertyType);
    
    // Add filtered markers back to the cluster group
    filteredMarkers.forEach(item => {
        markerClusterGroup.addLayer(item.marker);
    });
    
    // Update stats
    document.getElementById('visible-properties').textContent = filteredMarkers.length;
    
    if (filteredMarkers.length > 0) {
        const totalValue = filteredMarkers.reduce((sum, item) => sum + item.property.value, 0);
        const avgValue = totalValue / filteredMarkers.length;
        document.getElementById('avg-value-in-view').textContent = formatCurrency(avgValue);
    } else {
        document.getElementById('avg-value-in-view').textContent = '$0';
    }
    
    // Update property density
    document.getElementById('property-density').textContent = (filteredMarkers.length / 10).toFixed(1);
}

// Format currency helper function
function formatCurrency(value) {
    if (value === null || value === undefined) return '--';
    
    value = parseFloat(value);
    if (isNaN(value)) return '--';
    
    if (value >= 1000000) {
        return '$' + (value / 1000000).toFixed(1) + 'M';
    } else if (value >= 1000) {
        return '$' + (value / 1000).toFixed(0) + 'K';
    } else {
        return '$' + value.toFixed(0);
    }
}