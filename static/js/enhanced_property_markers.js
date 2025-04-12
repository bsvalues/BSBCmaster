/**
 * Enhanced Property Markers
 * 
 * This module creates advanced 3D property markers with enhanced 
 * visual representation and interactive elements.
 * 
 * Features:
 * - Property type-specific 3D marker styles
 * - Value-based sizing and coloring
 * - Interactive animations and effects
 * - Detailed popup information
 * - Support for clustering and heatmap integration
 */
class EnhancedPropertyMarkers {
    /**
     * Initialize enhanced property markers
     * @param {Object} map - Leaflet map instance
     * @param {Object} options - Configuration options
     */
    constructor(map, options = {}) {
        this.map = map;
        this.markers = [];
        this.markerLayer = L.layerGroup().addTo(map);
        this.clusterGroup = null;
        this.heatLayer = null;
        this.propertyData = [];
        
        // Marker appearance configuration - merge defaults with provided options
        this.config = {
            // Size settings
            baseSize: options.baseSize || 30,
            minSize: options.minSize || 20,
            maxSize: options.maxSize || 50,
            
            // Animation settings
            pulseEnabled: options.pulseEnabled !== undefined ? options.pulseEnabled : true,
            pulseColor: options.pulseColor || '#4a89dc',
            pulseOpacity: options.pulseOpacity || 0.4,
            pulseDuration: options.pulseDuration || 2000,
            
            // Value ranges for color scale - can be updated with actual data ranges
            valueMin: options.valueMin || 100000,  // $100K
            valueMax: options.valueMax || 1000000, // $1M
            
            // Color settings
            colorScheme: options.colorScheme || [
                { value: 0, color: '#43a047' },       // Low value (green)
                { value: 0.5, color: '#fdd835' },     // Mid value (yellow) 
                { value: 1, color: '#e53935' }        // High value (red)
            ],
            
            // Additional options for enhanced visualization
            showLabels: options.showLabels !== undefined ? options.showLabels : false,
            animateMarkers: options.animateMarkers !== undefined ? options.animateMarkers : true,
            useTimeBasedVisualization: options.useTimeBasedVisualization || false,
            
            // Visualization modes
            defaultVisualizationMode: options.defaultVisualizationMode || 'markers' // markers, heatmap, clusters
        };
        
        // Initialize components
        this.initMarkerPrototype();
        this.initClusterGroup();
        this.setupEventListeners();
    }
    
    /**
     * Initialize the marker cluster group
     */
    initClusterGroup() {
        // Create marker cluster group if available
        if (typeof L.MarkerClusterGroup !== 'undefined') {
            this.clusterGroup = L.markerClusterGroup({
                showCoverageOnHover: false,
                maxClusterRadius: 50,
                iconCreateFunction: (cluster) => {
                    // Calculate average property value for all markers in the cluster
                    let totalValue = 0;
                    let count = 0;
                    
                    cluster.getAllChildMarkers().forEach(marker => {
                        if (marker.propertyValue) {
                            totalValue += marker.propertyValue;
                            count++;
                        }
                    });
                    
                    const avgValue = count > 0 ? totalValue / count : 0;
                    const normalizedValue = this.normalizeValue(avgValue);
                    const color = this.getColorForValue(normalizedValue);
                    
                    // Create a custom HTML-based icon for the cluster
                    return new L.DivIcon({
                        html: `<div class="cluster-icon" style="background-color: ${color};">
                                <div class="cluster-center"></div>
                                <span>${cluster.getChildCount()}</span>
                               </div>`,
                        className: 'custom-cluster-icon',
                        iconSize: new L.Point(40, 40)
                    });
                }
            });
        }
    }
    
    /**
     * Setup event listeners for map and markers
     */
    setupEventListeners() {
        // Event handler for property comparison mode
        document.addEventListener('enhanced-markers:comparison-mode', (e) => {
            const enabled = e.detail.enabled;
            this.setComparisonMode(enabled);
        });
        
        // Event handler for visualization mode change
        document.addEventListener('enhanced-markers:visualization-mode', (e) => {
            const mode = e.detail.mode;
            this.setVisualizationMode(mode);
        });
        
        // Event handler for filter changes
        document.addEventListener('enhanced-markers:filter-changed', (e) => {
            const filters = e.detail.filters;
            this.applyFilters(filters);
        });
    }
    
    /**
     * Create marker prototype for enhanced markers
     */
    initMarkerPrototype() {
        // Create marker icon canvas prototype
        this.markerCanvas = document.createElement('canvas');
        this.markerCanvas.width = 100;
        this.markerCanvas.height = 100;
        this.ctx = this.markerCanvas.getContext('2d');
    }
    
    /**
     * Create an enhanced marker for a property
     * @param {Object} property - Property data
     * @returns {Object} Leaflet marker
     */
    createMarker(property) {
        // Calculate marker size based on property value
        const size = this.calculateMarkerSize(property.total_value);
        
        // Generate marker icon
        const icon = this.createMarkerIcon(property, size);
        
        // Create marker with custom options
        const marker = L.marker([property.latitude, property.longitude], {
            icon: icon,
            riseOnHover: true,
            title: `${property.property_type || 'Property'}: $${this.formatNumber(property.total_value)}`
        });
        
        // Add pulse effect if enabled
        if (this.config.pulseEnabled) {
            this.addPulseEffect(marker, property);
        }
        
        // Add popup
        marker.bindPopup(this.createPopupContent(property));
        
        // Add to markers collection
        this.markers.push({
            marker: marker,
            property: property
        });
        
        // Add click handler
        this.addMarkerClickHandler(marker, property);
        
        return marker;
    }
    
    /**
     * Calculate marker size based on property value
     * @param {Number} value - Property value
     * @returns {Number} Marker size in pixels
     */
    calculateMarkerSize(value) {
        // Normalize value between 0 and 1
        const normalizedValue = this.normalizeValue(value);
        
        // Calculate size between min and max size based on value
        return this.config.minSize + (normalizedValue * (this.config.maxSize - this.config.minSize));
    }
    
    /**
     * Normalize a property value between 0 and 1
     * @param {Number} value - Property value
     * @returns {Number} Normalized value between 0 and 1
     */
    normalizeValue(value) {
        // Ensure value is between min and max
        const clampedValue = Math.max(this.config.valueMin, Math.min(this.config.valueMax, value));
        
        // Normalize to range 0-1
        return (clampedValue - this.config.valueMin) / (this.config.valueMax - this.config.valueMin);
    }
    
    /**
     * Create enhanced marker icon
     * @param {Object} property - Property data
     * @param {Number} size - Marker size in pixels
     * @returns {Object} Leaflet icon
     */
    createMarkerIcon(property, size) {
        // Clear canvas
        this.ctx.clearRect(0, 0, this.markerCanvas.width, this.markerCanvas.height);
        
        // Get property value and normalize it
        const normalizedValue = this.normalizeValue(property.total_value);
        
        // Get color for marker based on normalized value
        const color = this.getColorForValue(normalizedValue);
        
        // Center position
        const centerX = this.markerCanvas.width / 2;
        const centerY = this.markerCanvas.height / 2;
        
        // Base size
        const baseSize = size;
        
        // Draw 3D marker with shadow
        this.drawPropertyMarker(centerX, centerY, baseSize, color, property);
        
        // Create Leaflet icon from canvas
        return L.icon({
            iconUrl: this.markerCanvas.toDataURL(),
            iconSize: [size * 2, size * 2],
            iconAnchor: [size, size * 1.6], // Adjust anchor to bottom center of the icon
            popupAnchor: [0, -size * 1.6]  // Position popup above marker
        });
    }
    
    /**
     * Draw a 3D-style property marker on canvas
     * @param {Number} x - Center X position
     * @param {Number} y - Center Y position
     * @param {Number} size - Base size of marker
     * @param {String} color - Main color of marker
     * @param {Object} property - Property data
     */
    drawPropertyMarker(x, y, size, color, property) {
        const ctx = this.ctx;
        
        // Draw shadow
        ctx.beginPath();
        ctx.ellipse(x, y + size * 1.6, size * 0.8, size * 0.3, 0, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
        ctx.fill();
        
        // Property type determines the shape
        const propertyType = property.property_type || 'Residential';
        
        switch (propertyType) {
            case 'Commercial':
                this.drawCommercialBuilding(x, y, size, color);
                break;
            case 'Industrial':
                this.drawIndustrialBuilding(x, y, size, color);
                break;
            case 'Agricultural':
                this.drawAgriculturalProperty(x, y, size, color);
                break;
            case 'Residential':
            default:
                this.drawResidentialHouse(x, y, size, color);
                break;
        }
        
        // Add value indicator
        this.drawValueIndicator(x, y, size, property.total_value);
    }
    
    /**
     * Draw residential house marker
     * @param {Number} x - Center X position
     * @param {Number} y - Center Y position
     * @param {Number} size - Base size of marker
     * @param {String} color - Main color of marker
     */
    drawResidentialHouse(x, y, size, color) {
        const ctx = this.ctx;
        
        // House base
        ctx.beginPath();
        ctx.rect(x - size * 0.8, y - size * 0.4, size * 1.6, size * 1.2);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.strokeStyle = this.darkenColor(color, 30);
        ctx.lineWidth = 2;
        ctx.stroke();
        
        // Roof
        ctx.beginPath();
        ctx.moveTo(x - size * 0.9, y - size * 0.4);
        ctx.lineTo(x, y - size * 1.2);
        ctx.lineTo(x + size * 0.9, y - size * 0.4);
        ctx.closePath();
        ctx.fillStyle = this.darkenColor(color, 40);
        ctx.fill();
        ctx.strokeStyle = this.darkenColor(color, 60);
        ctx.lineWidth = 2;
        ctx.stroke();
        
        // Door
        ctx.beginPath();
        ctx.rect(x - size * 0.2, y + size * 0.4, size * 0.4, size * 0.4);
        ctx.fillStyle = this.darkenColor(color, 50);
        ctx.fill();
        
        // Window
        ctx.beginPath();
        ctx.rect(x - size * 0.5, y, size * 0.3, size * 0.3);
        ctx.rect(x + size * 0.2, y, size * 0.3, size * 0.3);
        ctx.fillStyle = '#a7c5eb';
        ctx.fill();
        ctx.strokeStyle = this.darkenColor(color, 40);
        ctx.lineWidth = 1;
        ctx.stroke();
    }
    
    /**
     * Draw commercial building marker
     * @param {Number} x - Center X position
     * @param {Number} y - Center Y position
     * @param {Number} size - Base size of marker
     * @param {String} color - Main color of marker
     */
    drawCommercialBuilding(x, y, size, color) {
        const ctx = this.ctx;
        
        // Building base
        ctx.beginPath();
        ctx.rect(x - size * 0.9, y - size * 0.5, size * 1.8, size * 1.4);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.strokeStyle = this.darkenColor(color, 30);
        ctx.lineWidth = 2;
        ctx.stroke();
        
        // Building top
        ctx.beginPath();
        ctx.rect(x - size * 0.7, y - size * 0.8, size * 1.4, size * 0.3);
        ctx.fillStyle = this.darkenColor(color, 20);
        ctx.fill();
        ctx.strokeStyle = this.darkenColor(color, 40);
        ctx.lineWidth = 1;
        ctx.stroke();
        
        // Windows
        for (let i = 0; i < 3; i++) {
            for (let j = 0; j < 3; j++) {
                ctx.beginPath();
                ctx.rect(
                    x - size * 0.7 + i * size * 0.5, 
                    y - size * 0.3 + j * size * 0.4, 
                    size * 0.4, 
                    size * 0.3
                );
                ctx.fillStyle = '#a7c5eb';
                ctx.fill();
                ctx.strokeStyle = this.darkenColor(color, 40);
                ctx.lineWidth = 1;
                ctx.stroke();
            }
        }
        
        // Door
        ctx.beginPath();
        ctx.rect(x - size * 0.2, y + size * 0.5, size * 0.4, size * 0.4);
        ctx.fillStyle = this.darkenColor(color, 50);
        ctx.fill();
    }
    
    /**
     * Draw industrial building marker
     * @param {Number} x - Center X position
     * @param {Number} y - Center Y position
     * @param {Number} size - Base size of marker
     * @param {String} color - Main color of marker
     */
    drawIndustrialBuilding(x, y, size, color) {
        const ctx = this.ctx;
        
        // Warehouse
        ctx.beginPath();
        ctx.rect(x - size * 0.9, y - size * 0.2, size * 1.8, size * 1.1);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.strokeStyle = this.darkenColor(color, 30);
        ctx.lineWidth = 2;
        ctx.stroke();
        
        // Roof
        ctx.beginPath();
        ctx.moveTo(x - size * 0.9, y - size * 0.2);
        ctx.lineTo(x, y - size * 0.7);
        ctx.lineTo(x + size * 0.9, y - size * 0.2);
        ctx.closePath();
        ctx.fillStyle = this.darkenColor(color, 30);
        ctx.fill();
        ctx.strokeStyle = this.darkenColor(color, 50);
        ctx.lineWidth = 1.5;
        ctx.stroke();
        
        // Chimney
        ctx.beginPath();
        ctx.rect(x + size * 0.4, y - size * 0.9, size * 0.2, size * 0.7);
        ctx.fillStyle = this.darkenColor(color, 40);
        ctx.fill();
        ctx.strokeStyle = this.darkenColor(color, 60);
        ctx.lineWidth = 1;
        ctx.stroke();
        
        // Door
        ctx.beginPath();
        ctx.rect(x - size * 0.3, y + size * 0.3, size * 0.6, size * 0.6);
        ctx.fillStyle = this.darkenColor(color, 50);
        ctx.fill();
        
        // Windows
        ctx.beginPath();
        ctx.rect(x - size * 0.7, y + size * 0.1, size * 0.3, size * 0.3);
        ctx.rect(x + size * 0.4, y + size * 0.1, size * 0.3, size * 0.3);
        ctx.fillStyle = '#a7c5eb';
        ctx.fill();
        ctx.strokeStyle = this.darkenColor(color, 40);
        ctx.lineWidth = 1;
        ctx.stroke();
    }
    
    /**
     * Draw agricultural property marker
     * @param {Number} x - Center X position
     * @param {Number} y - Center Y position
     * @param {Number} size - Base size of marker
     * @param {String} color - Main color of marker
     */
    drawAgriculturalProperty(x, y, size, color) {
        const ctx = this.ctx;
        
        // Barn base
        ctx.beginPath();
        ctx.rect(x - size * 0.7, y - size * 0.2, size * 1.4, size * 1.1);
        ctx.fillStyle = '#c62828'; // Red barn color
        ctx.fill();
        ctx.strokeStyle = '#7f1d1d';
        ctx.lineWidth = 2;
        ctx.stroke();
        
        // Barn roof
        ctx.beginPath();
        ctx.moveTo(x - size * 0.8, y - size * 0.2);
        ctx.lineTo(x, y - size * 0.9);
        ctx.lineTo(x + size * 0.8, y - size * 0.2);
        ctx.closePath();
        ctx.fillStyle = '#5d4037'; // Brown roof
        ctx.fill();
        ctx.strokeStyle = '#3e2723';
        ctx.lineWidth = 1.5;
        ctx.stroke();
        
        // Door
        ctx.beginPath();
        ctx.rect(x - size * 0.3, y + size * 0.3, size * 0.6, size * 0.6);
        ctx.fillStyle = '#5d4037'; // Brown door
        ctx.fill();
        ctx.strokeStyle = '#3e2723';
        ctx.lineWidth = 1;
        ctx.stroke();
        
        // Windows
        ctx.beginPath();
        ctx.rect(x - size * 0.5, y, size * 0.2, size * 0.2);
        ctx.rect(x + size * 0.3, y, size * 0.2, size * 0.2);
        ctx.fillStyle = '#a7c5eb';
        ctx.fill();
        ctx.strokeStyle = '#3e2723';
        ctx.lineWidth = 1;
        ctx.stroke();
        
        // Field (grass around the barn)
        ctx.beginPath();
        ctx.ellipse(x, y + size * 1.2, size * 1.2, size * 0.4, 0, 0, Math.PI * 2);
        ctx.fillStyle = color; // Use property value color for field
        ctx.fill();
    }
    
    /**
     * Draw value indicator
     * @param {Number} x - Center X position
     * @param {Number} y - Center Y position
     * @param {Number} size - Base size of marker
     * @param {Number} value - Property value
     */
    drawValueIndicator(x, y, size, value) {
        const ctx = this.ctx;
        
        // Draw value badge
        ctx.beginPath();
        ctx.arc(x + size * 0.8, y - size * 0.8, size * 0.4, 0, Math.PI * 2);
        ctx.fillStyle = '#1565c0';
        ctx.fill();
        ctx.strokeStyle = '#0d47a1';
        ctx.lineWidth = 2;
        ctx.stroke();
        
        // Add value text
        ctx.font = `bold ${size * 0.35}px Arial`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#ffffff';
        
        // Format value to K/M format
        let displayValue;
        if (value >= 1000000) {
            displayValue = `${(value / 1000000).toFixed(1)}M`;
        } else {
            displayValue = `${(value / 1000).toFixed(0)}K`;
        }
        
        ctx.fillText(displayValue, x + size * 0.8, y - size * 0.8);
    }
    
    /**
     * Set visualization mode (markers, heatmap, clusters)
     * @param {String} mode - Visualization mode
     */
    setVisualizationMode(mode) {
        // Clear existing visualizations
        this.map.removeLayer(this.markerLayer);
        
        if (this.clusterGroup && this.map.hasLayer(this.clusterGroup)) {
            this.map.removeLayer(this.clusterGroup);
        }
        
        if (this.heatLayer && this.map.hasLayer(this.heatLayer)) {
            this.map.removeLayer(this.heatLayer);
        }
        
        // Apply the selected visualization mode
        if (mode === 'clusters' && this.clusterGroup) {
            // Add markers to the cluster group
            this.clusterGroup.clearLayers();
            
            for (const item of this.markers) {
                this.clusterGroup.addLayer(item.marker);
                
                // Store property value on marker for clustering
                item.marker.propertyValue = item.property.total_value;
            }
            
            // Add cluster group to map
            this.map.addLayer(this.clusterGroup);
        } 
        else if (mode === 'heatmap') {
            // Create heatmap data if needed
            if (!this.heatLayer) {
                // Check if L.heatLayer is available (requires Leaflet.heat plugin)
                if (typeof L.heatLayer !== 'undefined') {
                    // Create heatmap data
                    const heatData = [];
                    
                    for (const item of this.markers) {
                        const prop = item.property;
                        const intensity = this.normalizeValue(prop.total_value);
                        
                        // Add heat point [lat, lng, intensity]
                        heatData.push([
                            prop.latitude, 
                            prop.longitude, 
                            intensity * 1.0 // Scale intensity
                        ]);
                    }
                    
                    // Create heat layer
                    this.heatLayer = L.heatLayer(heatData, {
                        radius: 25,
                        blur: 15,
                        maxZoom: 17,
                        max: 1.0,
                        gradient: {
                            0.0: '#43a047',
                            0.5: '#fdd835',
                            1.0: '#e53935'
                        }
                    });
                } else {
                    console.warn('Leaflet.heat plugin is not available. Fallback to markers mode.');
                    mode = 'markers';
                }
            }
            
            if (mode === 'heatmap') {
                // Add heat layer to map
                this.map.addLayer(this.heatLayer);
            }
        }
        
        // Default to markers mode
        if (mode === 'markers') {
            // Add marker layer back to map
            this.map.addLayer(this.markerLayer);
        }
    }
    
    /**
     * Enable or disable property comparison mode
     * @param {Boolean} enabled - Whether to enable comparison mode
     */
    setComparisonMode(enabled) {
        this.comparisonMode = enabled;
        
        if (enabled) {
            // Create comparison panel if it doesn't exist
            if (!this.comparisonPanel) {
                this.createComparisonPanel();
            }
            
            // Show comparison panel
            this.comparisonPanel.style.display = 'block';
        } else if (this.comparisonPanel) {
            // Hide comparison panel
            this.comparisonPanel.style.display = 'none';
            
            // Clear compared properties
            this.comparedProperties = [];
            this.updateComparisonPanel();
        }
    }
    
    /**
     * Apply filters to property markers
     * @param {Object} filters - Filter criteria
     */
    applyFilters(filters) {
        // Clear existing layers
        this.markerLayer.clearLayers();
        
        if (this.clusterGroup) {
            this.clusterGroup.clearLayers();
        }
        
        if (this.heatLayer) {
            // Recreate heatmap with filtered data
            this.heatLayer = null;
        }
        
        // Apply filters to markers
        const filteredMarkers = [];
        
        for (const item of this.markers) {
            const prop = item.property;
            
            // Apply property type filter
            if (filters.propertyType && filters.propertyType !== 'all' && 
                prop.property_type !== filters.propertyType) {
                continue;
            }
            
            // Apply city filter
            if (filters.city && filters.city !== 'all' && 
                prop.property_city !== filters.city) {
                continue;
            }
            
            // Apply value range filter
            if (filters.minValue && prop.total_value < filters.minValue) {
                continue;
            }
            
            if (filters.maxValue && prop.total_value > filters.maxValue) {
                continue;
            }
            
            // Add marker to filtered markers
            filteredMarkers.push(item);
            this.markerLayer.addLayer(item.marker);
        }
        
        // Update visualization mode with filtered markers
        this.setVisualizationMode(filters.visualizationMode || this.config.defaultVisualizationMode);
    }
    
    /**
     * Add pulse animation effect to a marker
     * @param {Object} marker - Leaflet marker
     * @param {Object} property - Property data
     */
    addPulseEffect(marker, property) {
        // Create pulse element
        const pulseElement = document.createElement('div');
        pulseElement.className = 'enhanced-marker-pulse';
        pulseElement.style.backgroundColor = this.config.pulseColor;
        pulseElement.style.opacity = this.config.pulseOpacity;
        pulseElement.style.animationDuration = `${this.config.pulseDuration}ms`;
        
        // Add pulse to marker
        marker.on('add', function(e) {
            setTimeout(() => {
                const markerElement = e.target._icon;
                if (markerElement) {
                    markerElement.appendChild(pulseElement);
                }
            }, 100);
        });
    }
    
    /**
     * Add click handler to marker
     * @param {Object} marker - Leaflet marker
     * @param {Object} property - Property data
     */
    addMarkerClickHandler(marker, property) {
        marker.on('click', () => {
            // If property comparison is active, toggle selection
            if (window.propertyComparison && window.propertyComparison.comparisonActive) {
                const isSelected = window.propertyComparison.togglePropertySelection(property);
                
                // Update marker appearance based on selection state
                if (isSelected) {
                    marker._icon.classList.add('selected-property');
                } else {
                    marker._icon.classList.remove('selected-property');
                }
                
                // Update comparison panel
                window.propertyComparison.updateComparisonPanel();
                return;
            }
            
            // Otherwise just open popup
            marker.openPopup();
        });
    }
    
    /**
     * Create popup content for a property
     * @param {Object} property - Property data
     * @returns {String} HTML content for popup
     */
    createPopupContent(property) {
        // Customize popup based on property type
        const propertyType = property.property_type || 'Property';
        const title = property.title || `${propertyType} #${property.parcel_id}`;
        
        let html = `
            <div class="enhanced-property-popup">
                <h5>${title}</h5>
                <div class="property-value">
                    <strong>Value: </strong>
                    <span class="value-amount">$${this.formatNumber(property.total_value)}</span>
                </div>
                <div class="property-details">
                    <p><strong>Type:</strong> ${propertyType}</p>
                    ${property.city ? `<p><strong>City:</strong> ${property.city}</p>` : ''}
                    ${property.year_built ? `<p><strong>Year Built:</strong> ${property.year_built}</p>` : ''}
                </div>
                <div class="popup-actions">
                    <button class="btn btn-sm btn-primary view-details-btn" 
                            onclick="window.location.href='/parcels/${property.parcel_id}'">
                        View Details
                    </button>
                    ${window.propertyComparison ? `
                    <button class="btn btn-sm btn-outline-secondary add-to-compare-btn"
                            onclick="toggleCompareProperty(${JSON.stringify(property).replace(/"/g, '&quot;')})">
                        Compare
                    </button>
                    ` : ''}
                </div>
            </div>
        `;
        
        return html;
    }
    
    /**
     * Clear all markers
     */
    clearMarkers() {
        this.markerLayer.clearLayers();
        this.markers = [];
    }
    
    /**
     * Add multiple property markers to the map
     * @param {Array} properties - Array of property data objects
     */
    addMarkers(properties) {
        // Clear existing markers
        this.clearMarkers();
        
        // Add new markers
        properties.forEach(property => {
            // Skip properties without coordinates
            if (!property.latitude || !property.longitude) return;
            
            const marker = this.createMarker(property);
            this.markerLayer.addLayer(marker);
        });
    }
    
    /**
     * Get color for property value
     * @param {Number} normalizedValue - Normalized property value (0-1)
     * @returns {String} Color in hex format
     */
    getColorForValue(normalizedValue) {
        // Use colorScheme to determine color
        const scheme = this.config.colorScheme;
        
        // Find the two color points to interpolate between
        let startColor, endColor, startValue, endValue;
        
        for (let i = 0; i < scheme.length - 1; i++) {
            if (normalizedValue >= scheme[i].value && normalizedValue <= scheme[i + 1].value) {
                startColor = scheme[i].color;
                endColor = scheme[i + 1].color;
                startValue = scheme[i].value;
                endValue = scheme[i + 1].value;
                break;
            }
        }
        
        // If value is outside the range, use the extremes
        if (!startColor) {
            if (normalizedValue <= scheme[0].value) {
                return scheme[0].color;
            } else {
                return scheme[scheme.length - 1].color;
            }
        }
        
        // Interpolate between the two colors
        const ratio = (normalizedValue - startValue) / (endValue - startValue);
        return this.interpolateColors(startColor, endColor, ratio);
    }
    
    /**
     * Interpolate between two colors
     * @param {String} color1 - Starting color in hex format
     * @param {String} color2 - Ending color in hex format
     * @param {Number} ratio - Interpolation ratio (0-1)
     * @returns {String} Interpolated color in hex format
     */
    interpolateColors(color1, color2, ratio) {
        // Convert hex to RGB
        const r1 = parseInt(color1.substring(1, 3), 16);
        const g1 = parseInt(color1.substring(3, 5), 16);
        const b1 = parseInt(color1.substring(5, 7), 16);
        
        const r2 = parseInt(color2.substring(1, 3), 16);
        const g2 = parseInt(color2.substring(3, 5), 16);
        const b2 = parseInt(color2.substring(5, 7), 16);
        
        // Interpolate
        const r = Math.round(r1 + (r2 - r1) * ratio);
        const g = Math.round(g1 + (g2 - g1) * ratio);
        const b = Math.round(b1 + (b2 - b1) * ratio);
        
        // Convert back to hex
        return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
    }
    
    /**
     * Darken a color by a certain percentage
     * @param {String} color - Color in hex format
     * @param {Number} percent - Percentage to darken (0-100)
     * @returns {String} Darkened color in hex format
     */
    darkenColor(color, percent) {
        // Convert hex to RGB
        const r = parseInt(color.substring(1, 3), 16);
        const g = parseInt(color.substring(3, 5), 16);
        const b = parseInt(color.substring(5, 7), 16);
        
        // Darken
        const factor = 1 - (percent / 100);
        const newR = Math.floor(r * factor);
        const newG = Math.floor(g * factor);
        const newB = Math.floor(b * factor);
        
        // Convert back to hex
        return `#${((1 << 24) + (newR << 16) + (newG << 8) + newB).toString(16).slice(1)}`;
    }
    
    /**
     * Format number with commas
     * @param {Number} num - Number to format
     * @returns {String} Formatted number string
     */
    formatNumber(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    }
}

// Helper function to toggle property in comparison
function toggleCompareProperty(property) {
    if (window.propertyComparison) {
        const isSelected = window.propertyComparison.togglePropertySelection(property);
        window.propertyComparison.updateComparisonPanel();
        
        // If comparison mode isn't active, activate it
        if (isSelected && !window.propertyComparison.comparisonActive) {
            window.propertyComparison.toggleComparisonMode();
        }
    }
}

// Add CSS for enhanced markers
document.addEventListener('DOMContentLoaded', function() {
    if (!document.getElementById('enhanced-markers-style')) {
        const style = document.createElement('style');
        style.id = 'enhanced-markers-style';
        style.textContent = `
            .enhanced-marker-pulse {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 50px;
                height: 50px;
                border-radius: 50%;
                animation: pulse 2s infinite;
                pointer-events: none;
            }
            
            @keyframes pulse {
                0% {
                    transform: translate(-50%, -50%) scale(0.5);
                    opacity: 0.7;
                }
                70% {
                    transform: translate(-50%, -50%) scale(2);
                    opacity: 0;
                }
                100% {
                    transform: translate(-50%, -50%) scale(2.5);
                    opacity: 0;
                }
            }
            
            .enhanced-property-popup {
                min-width: 200px;
            }
            
            .enhanced-property-popup .property-value {
                margin: 10px 0;
                font-size: 1.1em;
            }
            
            .enhanced-property-popup .value-amount {
                color: #1565c0;
                font-weight: bold;
            }
            
            .enhanced-property-popup .property-details {
                margin-bottom: 15px;
            }
            
            .enhanced-property-popup .popup-actions {
                display: flex;
                justify-content: space-between;
                gap: 10px;
            }
            
            .selected-property {
                border: 3px solid #1e88e5 !important;
                box-shadow: 0 0 10px rgba(30, 136, 229, 0.7) !important;
                z-index: 1000 !important;
            }
            
            .value-bar-container {
                width: 100%;
                height: 4px;
                background-color: #e0e0e0;
                border-radius: 2px;
                overflow: hidden;
            }
            
            .value-bar {
                height: 100%;
                background-color: #1e88e5;
                border-radius: 2px;
            }
            
            .property-comparison-panel {
                position: absolute;
                bottom: 20px;
                right: 20px;
                width: 400px;
                max-width: calc(100% - 40px);
                z-index: 1000;
                background: white;
                border-radius: 8px;
                max-height: 500px;
                overflow-y: auto;
            }
            
            .comparison-table th,
            .comparison-table td {
                padding: 6px 10px;
            }
            
            @media (max-width: 768px) {
                .property-comparison-panel {
                    width: calc(100% - 40px);
                    max-height: 300px;
                }
            }
        `;
        document.head.appendChild(style);
    }
});
