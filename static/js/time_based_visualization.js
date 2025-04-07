/**
 * Time-Based Property Value Visualization
 * 
 * This module provides interactive timeline controls for visualizing
 * property value changes over time with animations and trends.
 */
class TimeBasedVisualization {
    /**
     * Initialize time-based visualization
     * @param {Object} map - Leaflet map instance
     */
    constructor(map) {
        this.map = map;
        this.timelineActive = false;
        
        // Value change simulation parameters
        this.baseYear = 2018;
        this.currentYear = new Date().getFullYear();
        this.selectedYear = this.currentYear;
        this.yearRange = [this.baseYear, this.currentYear];
        
        // Annual appreciation rates by property type (for simulation)
        this.appreciationRates = {
            'Residential': 0.048, // 4.8% average annual increase
            'Commercial': 0.037,  // 3.7% average annual increase
            'Agricultural': 0.029, // 2.9% average annual increase
            'Industrial': 0.033,  // 3.3% average annual increase
            'default': 0.04       // 4% default if type unknown
        };
        
        // Initialize UI components
        this.createTimelineControls();
    }
    
    /**
     * Create timeline control UI
     */
    createTimelineControls() {
        // Create container if it doesn't exist
        let container = document.getElementById('timeline-controls');
        if (!container) {
            container = document.createElement('div');
            container.id = 'timeline-controls';
            container.className = 'timeline-controls';
            
            // Add to map container
            const mapContainer = document.getElementById('map-container');
            if (mapContainer) {
                mapContainer.appendChild(container);
            }
        }
        
        // Create control content
        container.innerHTML = `
            <div class="timeline-container card shadow-sm">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h6 class="mb-0">Property Value Timeline</h6>
                    <div class="timeline-toggle">
                        <div class="form-check form-switch">
                            <input class="form-check-input" type="checkbox" id="timeline-toggle">
                            <label class="form-check-label" for="timeline-toggle">Show Timeline</label>
                        </div>
                    </div>
                </div>
                <div class="card-body timeline-body" style="display: none;">
                    <div class="year-display mb-2">
                        <span class="selected-year">${this.currentYear}</span>
                        <span class="year-label">Selected Year</span>
                    </div>
                    <div class="timeline-slider">
                        <input type="range" class="form-range" id="year-slider"
                               min="${this.baseYear}" max="${this.currentYear}" value="${this.currentYear}"
                               step="1">
                    </div>
                    <div class="timeline-labels d-flex justify-content-between">
                        <span>${this.baseYear}</span>
                        <span>${this.currentYear}</span>
                    </div>
                    <div class="timeline-actions mt-3 d-flex justify-content-between">
                        <button class="btn btn-sm btn-outline-primary" id="play-timeline">
                            <i class="fas fa-play me-1"></i> Play Animation
                        </button>
                        <button class="btn btn-sm btn-outline-secondary" id="reset-timeline">
                            <i class="fas fa-undo me-1"></i> Reset to Current
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Initialize event listeners
        this.initEventListeners();
    }
    
    /**
     * Initialize event listeners for timeline controls
     */
    initEventListeners() {
        const toggleBtn = document.getElementById('timeline-toggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('change', e => {
                this.toggleTimeline(e.target.checked);
            });
        }
        
        const yearSlider = document.getElementById('year-slider');
        if (yearSlider) {
            yearSlider.addEventListener('input', e => {
                this.updateSelectedYear(parseInt(e.target.value, 10));
            });
            
            yearSlider.addEventListener('change', e => {
                this.updateSelectedYear(parseInt(e.target.value, 10), true);
            });
        }
        
        const playBtn = document.getElementById('play-timeline');
        if (playBtn) {
            playBtn.addEventListener('click', () => {
                this.playTimelineAnimation();
            });
        }
        
        const resetBtn = document.getElementById('reset-timeline');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.resetTimeline();
            });
        }
    }
    
    /**
     * Toggle timeline visibility
     * @param {Boolean} active - Whether to show or hide timeline
     */
    toggleTimeline(active) {
        this.timelineActive = active;
        
        // Show/hide timeline body
        const timelineBody = document.querySelector('.timeline-body');
        if (timelineBody) {
            timelineBody.style.display = active ? 'block' : 'none';
        }
        
        // Reset to current year if hiding
        if (!active) {
            this.resetTimeline();
        } else {
            // Update map when showing
            this.updatePropertyValues();
        }
    }
    
    /**
     * Update the selected year and refresh map
     * @param {Number} year - Selected year
     * @param {Boolean} updateMap - Whether to update the map data
     */
    updateSelectedYear(year, updateMap = false) {
        this.selectedYear = year;
        
        // Update year display
        const yearDisplay = document.querySelector('.selected-year');
        if (yearDisplay) {
            yearDisplay.textContent = year;
        }
        
        // Update map data if requested
        if (updateMap) {
            this.updatePropertyValues();
        }
    }
    
    /**
     * Reset timeline to current year
     */
    resetTimeline() {
        this.selectedYear = this.currentYear;
        
        // Update slider value
        const yearSlider = document.getElementById('year-slider');
        if (yearSlider) {
            yearSlider.value = this.currentYear;
        }
        
        // Update year display
        const yearDisplay = document.querySelector('.selected-year');
        if (yearDisplay) {
            yearDisplay.textContent = this.currentYear;
        }
        
        // Update map data
        this.updatePropertyValues();
    }
    
    /**
     * Play timeline animation from base year to current
     */
    playTimelineAnimation() {
        // Get elements
        const yearSlider = document.getElementById('year-slider');
        const playBtn = document.getElementById('play-timeline');
        
        if (!yearSlider || !playBtn) return;
        
        // Disable play button during animation
        playBtn.disabled = true;
        playBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Playing...';
        
        // Start from base year
        yearSlider.value = this.baseYear;
        this.updateSelectedYear(this.baseYear);
        
        // Animation parameters
        const startYear = this.baseYear;
        const endYear = this.currentYear;
        const duration = 3000; // milliseconds
        const fps = 30;
        const totalFrames = duration / (1000 / fps);
        const yearIncrement = (endYear - startYear) / totalFrames;
        
        // Animation variables
        let frame = 0;
        let currentAnimYear = startYear;
        
        // Start animation loop
        const animationInterval = setInterval(() => {
            // Update frame counter
            frame++;
            
            // Calculate current animation year
            currentAnimYear = startYear + (yearIncrement * frame);
            
            // Check if animation is complete
            if (frame >= totalFrames) {
                // Final frame - set to end year
                currentAnimYear = endYear;
                clearInterval(animationInterval);
                
                // Re-enable play button
                playBtn.disabled = false;
                playBtn.innerHTML = '<i class="fas fa-play me-1"></i> Play Animation';
            }
            
            // Update slider and display
            const displayYear = Math.round(currentAnimYear);
            yearSlider.value = displayYear;
            this.updateSelectedYear(displayYear, frame % 5 === 0); // Update map every 5 frames for performance
        }, 1000 / fps);
    }
    
    /**
     * Update property values based on selected year
     */
    updatePropertyValues() {
        // If timeline is not active, don't modify values
        if (!this.timelineActive) return;
        
        // Signal to the map to refresh with time-adjusted values
        if (typeof window.loadMapDataForYear === 'function') {
            window.loadMapDataForYear(this.selectedYear);
        } else {
            this.refreshMapMarkers();
        }
    }
    
    /**
     * Calculate historical property value for a given year
     * @param {Object} property - Property data object
     * @param {Number} year - Year to calculate value for
     * @returns {Number} Adjusted property value
     */
    calculateHistoricalValue(property, year) {
        // If year is current, return current value
        if (year >= this.currentYear) return property.total_value;
        
        // Get appreciation rate for property type
        const rateKey = property.property_type || 'default';
        const rate = this.appreciationRates[rateKey] || this.appreciationRates.default;
        
        // Calculate years of difference
        const yearsDiff = this.currentYear - year;
        
        // Calculate historical value using compound depreciation
        // V_historical = V_current / (1 + rate)^years
        return property.total_value / Math.pow(1 + rate, yearsDiff);
    }
    
    /**
     * Refresh map markers with time-adjusted values
     */
    refreshMapMarkers() {
        // Custom implementation when loadMapDataForYear is not available
        if (!window.allProperties || !window.markers) return;
        
        // Calculate time-adjusted values for all properties
        const adjustedProperties = window.allProperties.map(property => {
            // Create a copy to avoid modifying original
            const adjustedProperty = { ...property };
            
            // Set historical value
            const originalValue = property.original_value || property.total_value;
            adjustedProperty.total_value = this.calculateHistoricalValue(
                { ...property, total_value: originalValue },
                this.selectedYear
            );
            
            // Store original value if not already set
            if (!adjustedProperty.original_value) {
                adjustedProperty.original_value = originalValue;
            }
            
            return adjustedProperty;
        });
        
        // Update markers with new values
        // This is a simplified version - actual implementation would
        // depend on how your map markers are created and managed
        if (typeof window.updateMarkers === 'function') {
            window.updateMarkers(adjustedProperties);
        }
    }
    
    /**
     * Create a year-over-year value change chart for a property
     * @param {Object} property - Property data object
     * @param {String} containerId - ID of container element for chart
     */
    createValueChangeChart(property, containerId) {
        const container = document.getElementById(containerId);
        if (!container || !window.Chart) return;
        
        // Create canvas if needed
        let canvas = container.querySelector('canvas');
        if (!canvas) {
            canvas = document.createElement('canvas');
            container.appendChild(canvas);
        }
        
        // Generate historical values
        const years = [];
        const values = [];
        
        for (let year = this.baseYear; year <= this.currentYear; year++) {
            years.push(year);
            values.push(this.calculateHistoricalValue(property, year));
        }
        
        // Create chart
        new Chart(canvas, {
            type: 'line',
            data: {
                labels: years,
                datasets: [{
                    label: 'Estimated Property Value',
                    data: values,
                    fill: true,
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: false,
                        ticks: {
                            callback: value => this.formatCurrency(value)
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: context => {
                                return this.formatCurrency(context.raw);
                            }
                        }
                    }
                }
            }
        });
    }
    
    /**
     * Format a number as currency
     * @param {Number} value - Value to format
     * @returns {String} Formatted currency string
     */
    formatCurrency(value) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            maximumFractionDigits: 0
        }).format(value);
    }
}

// Create timeline visualization when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Wait for map to be ready
    const mapReadyCheck = setInterval(() => {
        const map = window.propertyMap; // Assuming map is stored globally
        if (map) {
            clearInterval(mapReadyCheck);
            window.timelineVisualization = new TimeBasedVisualization(map);
        }
    }, 100);
});

// Helper function to load map data for specific year
window.loadMapDataForYear = function(year) {
    // Store selected year globally 
    window.selectedYear = year;
    
    // Refresh map data with year filter
    if (typeof window.loadMapData === 'function') {
        window.loadMapData(true); // Flag to indicate time-based update
    }
};
