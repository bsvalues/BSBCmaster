/**
 * Property Value Trends Visualization
 * 
 * This module provides functionality for visualizing property value trends over time.
 */

class PropertyValueTrends {
    /**
     * Initialize the property value trends visualization
     * @param {Object} mapInstance - The Leaflet map instance
     * @param {Object} config - Configuration options
     */
    constructor(mapInstance, config = {}) {
        this.map = mapInstance;
        this.trendLayer = L.layerGroup();
        this.chartContainer = null;
        this.propertyData = [];
        this.timelineControl = null;
        this.currentTimeIndex = 0;
        this.isPlaying = false;
        this.playInterval = null;
        
        // Configure options with defaults
        this.config = {
            animationDuration: config.animationDuration || 500,
            timeSteps: config.timeSteps || 10,
            playbackSpeed: config.playbackSpeed || 1000,
            showChart: config.showChart !== undefined ? config.showChart : true,
            valueTrendEstimator: config.valueTrendEstimator || this._estimateValueTrend
        };
        
        // Initialize timeline control
        this._initializeTimelineControl();
    }
    
    /**
     * Set property data for trend visualization
     * @param {Array} data - Array of property data objects
     */
    setPropertyData(data) {
        this.propertyData = data;
        
        // Generate time-based value estimates for each property
        this._generateTimeSeriesData();
        
        // Update the timeline control
        this._updateTimelineControl();
    }
    
    /**
     * Show the trend visualization on the map
     */
    showTrends() {
        // Clear existing layers
        this.trendLayer.clearLayers();
        
        // Add the trend layer to the map
        this.map.addLayer(this.trendLayer);
        
        // Show the timeline control
        if (this.timelineControl) {
            this.timelineControl.addTo(this.map);
        }
        
        // Display the initial time step
        this._displayTimeStep(this.currentTimeIndex);
        
        // Show the chart if enabled
        if (this.config.showChart) {
            this._createOrUpdateChart();
        }
    }
    
    /**
     * Hide the trend visualization
     */
    hideTrends() {
        // Remove the trend layer from the map
        this.map.removeLayer(this.trendLayer);
        
        // Remove the timeline control
        if (this.timelineControl) {
            this.timelineControl.remove();
        }
        
        // Remove the chart if it exists
        if (this.chartContainer) {
            this.chartContainer.remove();
        }
        
        // Stop any ongoing playback
        this._stopPlayback();
    }
    
    /**
     * Play the time-based animation
     */
    playAnimation() {
        if (this.isPlaying) return;
        
        this.isPlaying = true;
        this._updatePlayButton();
        
        this.playInterval = setInterval(() => {
            this.currentTimeIndex = (this.currentTimeIndex + 1) % this.config.timeSteps;
            this._displayTimeStep(this.currentTimeIndex);
            this._updateTimelineSlider();
            
            // Stop when we complete a full cycle
            if (this.currentTimeIndex === 0) {
                this._stopPlayback();
            }
        }, this.config.playbackSpeed);
    }
    
    /**
     * Stop the animation playback
     * @private
     */
    _stopPlayback() {
        if (!this.isPlaying) return;
        
        clearInterval(this.playInterval);
        this.isPlaying = false;
        this._updatePlayButton();
    }
    
    /**
     * Update the play/pause button state
     * @private
     */
    _updatePlayButton() {
        const playButton = document.querySelector('.timeline-play-button');
        if (playButton) {
            playButton.innerHTML = this.isPlaying ? 
                '<i class="fas fa-pause"></i>' : 
                '<i class="fas fa-play"></i>';
        }
    }
    
    /**
     * Initialize the timeline control
     * @private
     */
    _initializeTimelineControl() {
        // Create a custom Leaflet control for the timeline
        this.timelineControl = L.control({ position: 'bottomleft' });
        
        this.timelineControl.onAdd = (map) => {
            const container = L.DomUtil.create('div', 'timeline-control');
            container.innerHTML = `
                <div class="timeline-header">
                    <h6>Property Value Trends</h6>
                    <span class="timeline-date">Time Period: <span class="current-date">Now</span></span>
                </div>
                <div class="timeline-slider-container">
                    <input type="range" min="0" max="${this.config.timeSteps - 1}" value="0" class="timeline-slider" />
                </div>
                <div class="timeline-controls">
                    <button class="timeline-play-button"><i class="fas fa-play"></i></button>
                    <span class="timeline-info">
                        <span class="timeline-info-text">Showing current property values</span>
                    </span>
                </div>
            `;
            
            // Prevent map interactions when using the control
            L.DomEvent.disableClickPropagation(container);
            L.DomEvent.disableScrollPropagation(container);
            
            // Add event listeners
            setTimeout(() => {
                const slider = container.querySelector('.timeline-slider');
                const playButton = container.querySelector('.timeline-play-button');
                
                if (slider) {
                    slider.addEventListener('input', (e) => {
                        this.currentTimeIndex = parseInt(e.target.value);
                        this._displayTimeStep(this.currentTimeIndex);
                        this._stopPlayback();
                    });
                }
                
                if (playButton) {
                    playButton.addEventListener('click', () => {
                        if (this.isPlaying) {
                            this._stopPlayback();
                        } else {
                            this.playAnimation();
                        }
                    });
                }
            }, 100);
            
            return container;
        };
    }
    
    /**
     * Update the timeline control display
     * @private
     */
    _updateTimelineControl() {
        if (!this.timelineControl) return;
        
        // This will be called when the timeline control is already added to the map
        const container = this.timelineControl.getContainer();
        if (!container) return;
        
        const slider = container.querySelector('.timeline-slider');
        if (slider) {
            slider.max = this.config.timeSteps - 1;
            slider.value = this.currentTimeIndex;
        }
    }
    
    /**
     * Update the timeline slider position
     * @private
     */
    _updateTimelineSlider() {
        const slider = document.querySelector('.timeline-slider');
        if (slider) {
            slider.value = this.currentTimeIndex;
        }
        
        // Update the displayed date
        this._updateTimeDisplay();
    }
    
    /**
     * Update the time display text
     * @private
     */
    _updateTimeDisplay() {
        const dateDisplay = document.querySelector('.current-date');
        if (!dateDisplay) return;
        
        // Calculate the date based on the current time index
        const now = new Date();
        const monthsAgo = (this.config.timeSteps - 1 - this.currentTimeIndex) * 3;
        const date = new Date(now.getFullYear(), now.getMonth() - monthsAgo, 1);
        
        // Format the date
        dateDisplay.textContent = date.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'short'
        });
        
        // Update the info text
        const infoText = document.querySelector('.timeline-info-text');
        if (infoText) {
            if (this.currentTimeIndex === this.config.timeSteps - 1) {
                infoText.textContent = 'Showing current property values';
            } else {
                const changePercent = Math.round((1 - this.currentTimeIndex / (this.config.timeSteps - 1)) * 20);
                infoText.textContent = `Estimated values (${changePercent}% change from current)`;
            }
        }
    }
    
    /**
     * Generate time series data for each property
     * @private
     */
    _generateTimeSeriesData() {
        // For each property, generate estimated values for each time step
        this.propertyData.forEach(property => {
            if (!property.timeSeries) {
                property.timeSeries = [];
                
                for (let i = 0; i < this.config.timeSteps; i++) {
                    const timeRatio = i / (this.config.timeSteps - 1);
                    property.timeSeries.push(
                        this.config.valueTrendEstimator(property, timeRatio)
                    );
                }
            }
        });
    }
    
    /**
     * Estimate property value trend
     * @param {Object} property - Property data object
     * @param {number} timeRatio - Time ratio (0 to 1, where 1 is most recent)
     * @returns {number} Estimated property value
     * @private
     */
    _estimateValueTrend(property, timeRatio) {
        // Default implementation - linear increase based on property type
        const currentValue = property.assessed_value || 100000;
        let changeRate;
        
        // Adjust growth rate based on property type
        switch (property.property_type) {
            case 'Commercial':
                changeRate = 0.25; // 25% growth over the full time period
                break;
            case 'Residential':
                changeRate = 0.20; // 20% growth
                break;
            case 'Agricultural':
                changeRate = 0.15; // 15% growth
                break;
            case 'Industrial':
                changeRate = 0.28; // 28% growth
                break;
            default:
                changeRate = 0.18; // 18% growth
        }
        
        // Calculate the estimated value - lower values for earlier times
        return currentValue * (1 - (1 - timeRatio) * changeRate);
    }
    
    /**
     * Display the visualization for a specific time step
     * @param {number} timeIndex - The time index to display
     * @private
     */
    _displayTimeStep(timeIndex) {
        // Clear existing layers
        this.trendLayer.clearLayers();
        
        // Update the time display
        this._updateTimeDisplay();
        
        // Create markers for each property at this time step
        this.propertyData.forEach(property => {
            // Skip properties without coordinates
            if (!property.latitude || !property.longitude) return;
            
            // Get the value for this time step
            const value = property.timeSeries[timeIndex];
            
            // Calculate marker size based on value
            const radius = Math.max(5, Math.min(15, Math.sqrt(value) / 1000 * 5));
            
            // Create marker
            const marker = L.circleMarker([property.latitude, property.longitude], {
                radius: radius,
                fillColor: this._getValueColor(value),
                color: '#fff',
                weight: 1,
                opacity: 0.8,
                fillOpacity: 0.7
            });
            
            // Add popup
            marker.bindPopup(this._createPopupContent(property, value, timeIndex));
            
            // Add to layer
            this.trendLayer.addLayer(marker);
        });
    }
    
    /**
     * Create popup content for a property
     * @param {Object} property - Property data object
     * @param {number} value - Current value for the time step
     * @param {number} timeIndex - Current time index
     * @returns {string} HTML content for popup
     * @private
     */
    _createPopupContent(property, value, timeIndex) {
        // Calculate value change since earliest time
        const earliestValue = property.timeSeries[0];
        const changePercent = Math.round((value / earliestValue - 1) * 100);
        const changeClass = changePercent >= 0 ? 'positive-change' : 'negative-change';
        const changeSign = changePercent >= 0 ? '+' : '';
        
        // Format values for display
        const formattedValue = new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            maximumFractionDigits: 0
        }).format(value);
        
        // Create the popup content
        return `
            <div class="property-popup">
                <h6>${property.property_address || 'Property'}</h6>
                <div class="property-details">
                    <div class="property-value">
                        <span class="label">Estimated Value:</span>
                        <span class="value">${formattedValue}</span>
                    </div>
                    <div class="property-change">
                        <span class="label">Change:</span>
                        <span class="value ${changeClass}">${changeSign}${changePercent}%</span>
                    </div>
                    <div class="property-type">
                        <span class="label">Type:</span>
                        <span class="value">${property.property_type || 'N/A'}</span>
                    </div>
                    <div class="property-city">
                        <span class="label">City:</span>
                        <span class="value">${property.property_city || 'N/A'}</span>
                    </div>
                    ${property.owner_name ? `
                    <div class="property-owner">
                        <span class="label">Owner:</span>
                        <span class="value">${property.owner_name}</span>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;
    }
    
    /**
     * Get color for a property value
     * @param {number} value - Property value
     * @returns {string} Color code
     * @private
     */
    _getValueColor(value) {
        // Color based on value ranges
        if (value >= 1000000) return '#bd0026'; // > $1M
        if (value >= 500000) return '#f03b20';  // $500K-$1M
        if (value >= 250000) return '#fd8d3c';  // $250K-$500K
        if (value >= 100000) return '#feb24c';  // $100K-$250K
        if (value >= 50000) return '#fed976';   // $50K-$100K
        return '#ffffb2';                      // < $50K
    }
    
    /**
     * Create or update the trend chart
     * @private
     */
    _createOrUpdateChart() {
        // Remove existing chart if any
        if (this.chartContainer) {
            this.chartContainer.remove();
        }
        
        // Create chart container
        this.chartContainer = L.DomUtil.create('div', 'trend-chart-container');
        document.body.appendChild(this.chartContainer);
        
        // Position the chart
        Object.assign(this.chartContainer.style, {
            position: 'absolute',
            bottom: '10px',
            right: '10px',
            width: '300px',
            height: '200px',
            backgroundColor: 'rgba(255, 255, 255, 0.9)',
            border: '1px solid #ccc',
            borderRadius: '4px',
            padding: '10px',
            zIndex: 1000,
            boxShadow: '0 1px 5px rgba(0,0,0,0.4)'
        });
        
        // Add a chart title
        const chartTitle = L.DomUtil.create('h6', 'chart-title', this.chartContainer);
        chartTitle.textContent = 'Average Property Value Trend';
        
        // Create chart element
        const chartElement = L.DomUtil.create('canvas', 'trend-chart', this.chartContainer);
        chartElement.width = 280;
        chartElement.height = 150;
        
        // Calculate average values for each time step
        const timeLabels = [];
        const averageValues = [];
        
        for (let i = 0; i < this.config.timeSteps; i++) {
            // Create time labels (months before present)
            const now = new Date();
            const monthsAgo = (this.config.timeSteps - 1 - i) * 3;
            const date = new Date(now.getFullYear(), now.getMonth() - monthsAgo, 1);
            timeLabels.push(date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' }));
            
            // Calculate average value for this time step
            let sum = 0;
            let count = 0;
            
            this.propertyData.forEach(property => {
                if (property.timeSeries && property.timeSeries[i]) {
                    sum += property.timeSeries[i];
                    count++;
                }
            });
            
            averageValues.push(count > 0 ? sum / count : 0);
        }
        
        // Create chart using Chart.js
        new Chart(chartElement, {
            type: 'line',
            data: {
                labels: timeLabels,
                datasets: [{
                    label: 'Avg. Property Value',
                    data: averageValues,
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 2,
                    tension: 0.3,
                    pointBackgroundColor: 'rgba(54, 162, 235, 1)',
                    pointRadius: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.raw;
                                return new Intl.NumberFormat('en-US', {
                                    style: 'currency',
                                    currency: 'USD',
                                    maximumFractionDigits: 0
                                }).format(value);
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        ticks: {
                            callback: function(value) {
                                if (value >= 1000000) {
                                    return '$' + (value / 1000000) + 'M';
                                } else if (value >= 1000) {
                                    return '$' + (value / 1000) + 'K';
                                }
                                return '$' + value;
                            }
                        }
                    }
                }
            }
        });
        
        // Add close button
        const closeButton = L.DomUtil.create('button', 'chart-close-button', this.chartContainer);
        closeButton.innerHTML = '&times;';
        closeButton.title = 'Close chart';
        
        Object.assign(closeButton.style, {
            position: 'absolute',
            top: '5px',
            right: '5px',
            background: 'none',
            border: 'none',
            fontSize: '16px',
            cursor: 'pointer'
        });
        
        closeButton.addEventListener('click', () => {
            this.chartContainer.remove();
            this.chartContainer = null;
        });
        
        // Prevent map interactions on the chart container
        L.DomEvent.disableClickPropagation(this.chartContainer);
        L.DomEvent.disableScrollPropagation(this.chartContainer);
    }
}
