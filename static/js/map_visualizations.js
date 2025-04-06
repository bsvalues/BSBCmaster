/**
 * Advanced Map Visualizations for MCP Assessor Agent API
 * 
 * This module provides enhanced visualization modes for the property map,
 * including heat maps, time-series animations, and advanced clustering effects.
 */

class PropertyMapVisualizations {
    /**
     * Initialize the map visualizations
     * 
     * @param {Object} map - Leaflet map instance
     * @param {Object} options - Configuration options
     */
    constructor(map, options = {}) {
        this.map = map;
        this.options = Object.assign({
            heatmapRadius: 25,
            heatmapBlur: 15,
            heatmapMaxZoom: 16,
            heatmapGradient: {
                0.2: '#ffffb2',
                0.4: '#fed976',
                0.6: '#feb24c',
                0.8: '#fd8d3c',
                0.9: '#f03b20',
                1.0: '#bd0026'
            },
            animationDuration: 500,
            clusterAnimationEnabled: true,
            timeSeriesEnabled: false
        }, options);

        // Initialize layer groups
        this.heatmapLayer = null;
        this.clusterLayer = null;
        this.markerLayer = null;
        this.timeSeriesLayer = null;

        // State tracking
        this.activeVisualization = 'markers'; // markers, heatmap, timeseries
        this.propertyData = [];
        this.animationInterval = null;
        
        // Initialize
        this._setupEventListeners();
    }

    /**
     * Set up event listeners for interactions
     * @private
     */
    _setupEventListeners() {
        // Add zoom event listener for responsive visualizations
        this.map.on('zoomend', () => {
            this._updateVisualizationForZoom();
        });
    }

    /**
     * Update visualization based on current zoom level
     * @private
     */
    _updateVisualizationForZoom() {
        const currentZoom = this.map.getZoom();
        
        // Switch to clustered view at lower zoom levels
        if (this.activeVisualization === 'markers') {
            if (currentZoom < 13 && this.propertyData.length > 100) {
                this._updateClusterOpacity(1.0);
            } else {
                this._updateClusterOpacity(0.4);
            }
        }
        
        // Adjust heatmap intensity based on zoom
        if (this.heatmapLayer) {
            const radius = Math.max(5, this.options.heatmapRadius - (currentZoom - 10) * 2);
            this.heatmapLayer.setOptions({ radius });
        }
    }

    /**
     * Update the marker cluster opacity based on zoom level and data density
     * @private
     * @param {number} opacity - Opacity value between 0 and 1
     */
    _updateClusterOpacity(opacity) {
        if (this.clusterLayer) {
            const clusters = document.querySelectorAll('.marker-cluster');
            clusters.forEach(cluster => {
                cluster.style.opacity = opacity;
            });
        }
    }

    /**
     * Clear all map visualization layers
     */
    clearAllLayers() {
        if (this.heatmapLayer) {
            this.map.removeLayer(this.heatmapLayer);
            this.heatmapLayer = null;
        }
        
        if (this.clusterLayer) {
            this.map.removeLayer(this.clusterLayer);
            this.clusterLayer = null;
        }
        
        if (this.markerLayer) {
            this.map.removeLayer(this.markerLayer);
            this.markerLayer = null;
        }
        
        if (this.timeSeriesLayer) {
            this.map.removeLayer(this.timeSeriesLayer);
            this.timeSeriesLayer = null;
        }
        
        // Stop any ongoing animations
        this.stopTimeSeriesAnimation();
    }

    /**
     * Set the property data for visualizations
     * 
     * @param {Array} data - Array of property data objects
     */
    setPropertyData(data) {
        this.propertyData = data;
        return this;
    }

    /**
     * Switch to heat map visualization mode
     * 
     * @param {string} valueField - The property value field to use for heat intensity
     * @returns {PropertyMapVisualizations} - For method chaining
     */
    showHeatmap(valueField = 'assessed_value') {
        // Clear existing layers first
        this.clearAllLayers();
        
        // Initialize Leaflet.heat if not loaded
        if (!L.heatLayer) {
            console.error('Leaflet.heat plugin is required for heatmap visualization');
            return this;
        }
        
        // Prepare heat map points with intensity based on property values
        const heatPoints = this.propertyData
            .filter(prop => prop.latitude && prop.longitude && prop[valueField])
            .map(prop => {
                // Scale value for better visualization
                const intensity = Math.sqrt(prop[valueField]) / 100;
                return [prop.latitude, prop.longitude, intensity];
            });
        
        // Create and add the heat layer
        this.heatmapLayer = L.heatLayer(heatPoints, {
            radius: this.options.heatmapRadius,
            blur: this.options.heatmapBlur,
            maxZoom: this.options.heatmapMaxZoom,
            gradient: this.options.heatmapGradient
        }).addTo(this.map);
        
        this.activeVisualization = 'heatmap';
        return this;
    }

    /**
     * Switch to marker cluster visualization
     * 
     * @param {function} markerFactory - Function to create markers 
     * @param {function} popupFactory - Function to create popups
     * @returns {PropertyMapVisualizations} - For method chaining
     */
    showClusters(markerFactory, popupFactory) {
        // Clear existing layers first
        this.clearAllLayers();
        
        // Create marker cluster group with enhanced options
        this.clusterLayer = L.markerClusterGroup({
            maxClusterRadius: 50,
            spiderfyOnMaxZoom: true,
            showCoverageOnHover: true,
            zoomToBoundsOnClick: true,
            animate: true,
            animateAddingMarkers: this.options.clusterAnimationEnabled,
            disableClusteringAtZoom: 18,
            iconCreateFunction: function(cluster) {
                const childCount = cluster.getChildCount();
                const childMarkers = cluster.getAllChildMarkers();
                
                // Calculate average property value for the cluster
                let totalValue = 0;
                let valueCount = 0;
                childMarkers.forEach(marker => {
                    if (marker.feature && marker.feature.properties && marker.feature.properties.assessed_value) {
                        totalValue += marker.feature.properties.assessed_value;
                        valueCount++;
                    }
                });
                const avgValue = valueCount > 0 ? totalValue / valueCount : 0;
                
                // Determine class based on count and value
                let clusterClass = "marker-cluster-";
                if (childCount < 10) {
                    clusterClass += "small";
                } else if (childCount < 50) {
                    clusterClass += "medium";
                } else {
                    clusterClass += "large";
                }
                
                // Add value class
                if (avgValue > 500000) {
                    clusterClass += " high-value";
                } else if (avgValue > 250000) {
                    clusterClass += " medium-value";
                } else {
                    clusterClass += " standard-value";
                }
                
                // Create enhanced cluster icon
                return new L.DivIcon({
                    html: `<div><span>${childCount}</span></div>`,
                    className: `marker-cluster ${clusterClass}`,
                    iconSize: new L.Point(40, 40),
                    iconAnchor: new L.Point(20, 20)
                });
            }
        });
        
        // Add markers to the cluster
        this.propertyData
            .filter(prop => prop.latitude && prop.longitude)
            .forEach(prop => {
                const marker = markerFactory(prop);
                marker.bindPopup(popupFactory(prop));
                this.clusterLayer.addLayer(marker);
            });
        
        // Add the cluster layer to the map
        this.map.addLayer(this.clusterLayer);
        
        this.activeVisualization = 'markers';
        return this;
    }

    /**
     * Show time series visualization of property values
     * 
     * @param {string} timeField - The field containing time/date information
     * @param {number} frameDuration - Duration of each animation frame in ms
     * @returns {PropertyMapVisualizations} - For method chaining
     */
    showTimeSeries(timeField = 'year', frameDuration = 1000) {
        // Only proceed if time series is enabled in options
        if (!this.options.timeSeriesEnabled) {
            console.warn('Time series visualization is not enabled in options');
            return this;
        }
        
        // Clear existing layers first
        this.clearAllLayers();
        
        // Group properties by time period
        const timeGroups = {};
        this.propertyData
            .filter(prop => prop.latitude && prop.longitude && prop[timeField])
            .forEach(prop => {
                const timePeriod = prop[timeField].toString();
                if (!timeGroups[timePeriod]) {
                    timeGroups[timePeriod] = [];
                }
                timeGroups[timePeriod].push(prop);
            });
        
        // Sort time periods
        const periods = Object.keys(timeGroups).sort();
        
        // Create layer for time series
        this.timeSeriesLayer = L.layerGroup().addTo(this.map);
        
        // Set up animation
        let currentPeriodIndex = 0;
        const animate = () => {
            // Clear previous markers
            this.timeSeriesLayer.clearLayers();
            
            // Get current period and properties
            const currentPeriod = periods[currentPeriodIndex];
            const periodProperties = timeGroups[currentPeriod];
            
            // Add markers for this period
            periodProperties.forEach(prop => {
                const marker = L.circleMarker([prop.latitude, prop.longitude], {
                    radius: Math.sqrt(prop.assessed_value) / 1000 * 10, // Scale by value
                    fillColor: this._getValueColor(prop.assessed_value),
                    color: '#fff',
                    weight: 1,
                    opacity: 1,
                    fillOpacity: 0.7
                }).addTo(this.timeSeriesLayer);
                
                // Add popup
                marker.bindPopup(`
                    <div>
                        <h6>${prop.property_address || 'Property'}</h6>
                        <p><strong>Value (${currentPeriod}):</strong> $${prop.assessed_value.toLocaleString()}</p>
                        <p><strong>Type:</strong> ${prop.property_type || 'Residential'}</p>
                    </div>
                `);
                
                // Add animation effect
                marker.setRadius(0);
                setTimeout(() => {
                    marker.setRadius(Math.sqrt(prop.assessed_value) / 1000 * 10);
                }, 10);
            });
            
            // Update period indicator
            if (document.getElementById('time-period-indicator')) {
                document.getElementById('time-period-indicator').textContent = currentPeriod;
            }
            
            // Move to next period
            currentPeriodIndex = (currentPeriodIndex + 1) % periods.length;
        };
        
        // Start animation
        animate(); // Show first frame immediately
        this.animationInterval = setInterval(animate, frameDuration);
        
        this.activeVisualization = 'timeseries';
        return this;
    }

    /**
     * Stop time series animation if running
     */
    stopTimeSeriesAnimation() {
        if (this.animationInterval) {
            clearInterval(this.animationInterval);
            this.animationInterval = null;
        }
    }

    /**
     * Get a color based on property value
     * 
     * @param {number} value - The property value
     * @returns {string} - Color code
     * @private
     */
    _getValueColor(value) {
        if (value > 1000000) return '#bd0026'; // Very high value (>$1M)
        if (value > 500000) return '#f03b20';  // High value ($500K-$1M)
        if (value > 250000) return '#fd8d3c';  // Medium-high value ($250K-$500K)
        if (value > 100000) return '#feb24c';  // Medium value ($100K-$250K)
        if (value > 50000) return '#fed976';   // Low-medium value ($50K-$100K)
        return '#ffffb2';                      // Low value (<$50K)
    }

    /**
     * Create a value-based legend for the current visualization
     * 
     * @param {string} position - Legend position ('topright', 'bottomleft', etc.)
     * @returns {Object} - Leaflet control
     */
    addValueLegend(position = 'bottomright') {
        const legend = L.control({position});
        
        legend.onAdd = (map) => {
            const div = L.DomUtil.create('div', 'property-legend property-value-legend');
            let legendContent = `
                <h6>Property Values</h6>
                <div class="legend-item">
                    <div class="legend-marker" style="background-color: #bd0026;"></div>
                    <span>Over $1,000,000</span>
                </div>
                <div class="legend-item">
                    <div class="legend-marker" style="background-color: #f03b20;"></div>
                    <span>$500,000 - $1,000,000</span>
                </div>
                <div class="legend-item">
                    <div class="legend-marker" style="background-color: #fd8d3c;"></div>
                    <span>$250,000 - $500,000</span>
                </div>
                <div class="legend-item">
                    <div class="legend-marker" style="background-color: #feb24c;"></div>
                    <span>$100,000 - $250,000</span>
                </div>
                <div class="legend-item">
                    <div class="legend-marker" style="background-color: #fed976;"></div>
                    <span>$50,000 - $100,000</span>
                </div>
                <div class="legend-item">
                    <div class="legend-marker" style="background-color: #ffffb2;"></div>
                    <span>Under $50,000</span>
                </div>
            `;
            
            // Add time indicator for time series
            if (this.activeVisualization === 'timeseries') {
                legendContent += `
                    <div class="time-indicator">
                        <strong>Period: </strong><span id="time-period-indicator">-</span>
                    </div>
                `;
            }
            
            div.innerHTML = legendContent;
            return div;
        };
        
        return legend.addTo(this.map);
    }
}
