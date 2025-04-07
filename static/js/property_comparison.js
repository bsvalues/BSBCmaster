/**
 * Interactive Property Comparison
 * 
 * This module provides functionality to compare multiple properties
 * side by side with interactive visualization of differences.
 */
class PropertyComparison {
    /**
     * Initialize property comparison
     * @param {Object} map - Leaflet map instance
     */
    constructor(map) {
        this.map = map;
        this.comparisonActive = false;
        this.selectedProperties = [];
        this.maxSelections = 4;
        
        this.comparisonPanel = this.createComparisonPanel();
        
        // Initialize toggle button
        this.setupToggleButton();
    }
    
    /**
     * Setup the toggle button to show/hide the comparison panel
     */
    setupToggleButton() {
        const toggleBtn = document.getElementById('toggle-comparison');
        if (!toggleBtn) return;
        
        toggleBtn.addEventListener('click', () => {
            this.toggleComparisonMode();
        });
    }
    
    /**
     * Toggle comparison mode on/off
     */
    toggleComparisonMode() {
        this.comparisonActive = !this.comparisonActive;
        
        // Update toggle button state
        const toggleBtn = document.getElementById('toggle-comparison');
        if (toggleBtn) {
            toggleBtn.classList.toggle('active', this.comparisonActive);
        }
        
        // Show/hide comparison panel
        if (this.comparisonPanel) {
            this.comparisonPanel.style.display = this.comparisonActive ? 'block' : 'none';
        }
        
        // Reset selections if turning off
        if (!this.comparisonActive) {
            this.clearSelections();
        } else {
            // Show selection instructions
            this.updateComparisonPanel();
        }
        
        // Notify user about mode change
        showToast(
            this.comparisonActive 
                ? 'Property comparison mode activated. Click on markers to select properties.' 
                : 'Property comparison mode deactivated.',
            'info'
        );
    }
    
    /**
     * Create the comparison panel element
     * @returns {HTMLElement} The comparison panel
     */
    createComparisonPanel() {
        // Check if panel already exists
        let panel = document.getElementById('property-comparison-panel');
        if (panel) return panel;
        
        // Create new panel
        panel = document.createElement('div');
        panel.id = 'property-comparison-panel';
        panel.className = 'property-comparison-panel card shadow-sm';
        panel.style.display = 'none';
        
        panel.innerHTML = `
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5 class="mb-0">Property Comparison</h5>
                <div>
                    <button class="btn btn-sm btn-outline-secondary me-2" id="clear-comparison">
                        Clear
                    </button>
                    <button class="btn btn-sm btn-outline-danger" id="close-comparison">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
            <div class="card-body" id="comparison-content">
                <p class="text-center text-muted">
                    Select up to ${this.maxSelections} properties to compare
                </p>
            </div>
        `;
        
        // Add to map container
        const mapContainer = document.getElementById('map-container');
        if (mapContainer) {
            mapContainer.appendChild(panel);
            
            // Add event listeners
            document.getElementById('close-comparison').addEventListener('click', () => {
                this.toggleComparisonMode();
            });
            
            document.getElementById('clear-comparison').addEventListener('click', () => {
                this.clearSelections();
                this.updateComparisonPanel();
            });
        }
        
        return panel;
    }
    
    /**
     * Add or remove a property from the comparison
     * @param {Object} property - Property data object
     * @returns {Boolean} True if property was added, false if removed
     */
    togglePropertySelection(property) {
        if (!this.comparisonActive) return false;
        
        // Check if property is already selected
        const index = this.selectedProperties.findIndex(p => 
            p.parcel_id === property.parcel_id
        );
        
        if (index !== -1) {
            // Remove if already selected
            this.selectedProperties.splice(index, 1);
            return false;
        } else {
            // Add if under max selections
            if (this.selectedProperties.length < this.maxSelections) {
                this.selectedProperties.push(property);
                return true;
            } else {
                // Max selections reached
                showToast(`Maximum of ${this.maxSelections} properties can be selected for comparison.`, 'warning');
                return false;
            }
        }
    }
    
    /**
     * Clear all selected properties
     */
    clearSelections() {
        this.selectedProperties = [];
    }
    
    /**
     * Check if a property is currently selected
     * @param {Object} property - Property data object
     * @returns {Boolean} True if property is selected
     */
    isPropertySelected(property) {
        return this.selectedProperties.some(p => p.parcel_id === property.parcel_id);
    }
    
    /**
     * Update the comparison panel with current selections
     */
    updateComparisonPanel() {
        const contentEl = document.getElementById('comparison-content');
        if (!contentEl) return;
        
        if (this.selectedProperties.length === 0) {
            contentEl.innerHTML = `
                <p class="text-center text-muted">
                    Select up to ${this.maxSelections} properties to compare
                </p>
            `;
            return;
        }
        
        // Create comparison table
        let html = `
            <div class="table-responsive">
                <table class="table table-sm comparison-table">
                    <thead>
                        <tr>
                            <th>Property</th>
                            ${this.selectedProperties.map((_, i) => 
                                `<th class="text-center">Property ${i + 1}</th>`
                            ).join('')}
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        // Row for parcel IDs
        html += `
            <tr>
                <td>Parcel ID</td>
                ${this.selectedProperties.map(prop => 
                    `<td class="text-center">${prop.parcel_id || '-'}</td>`
                ).join('')}
            </tr>
        `;
        
        // Row for property values with visual comparison
        html += `
            <tr>
                <td>Total Value</td>
                ${this.createValueComparisonCells(this.selectedProperties.map(p => p.total_value))}
            </tr>
        `;
        
        // Row for property types
        html += `
            <tr>
                <td>Property Type</td>
                ${this.selectedProperties.map(prop => 
                    `<td class="text-center">${prop.property_type || '-'}</td>`
                ).join('')}
            </tr>
        `;
        
        // Row for cities
        html += `
            <tr>
                <td>City</td>
                ${this.selectedProperties.map(prop => 
                    `<td class="text-center">${prop.city || '-'}</td>`
                ).join('')}
            </tr>
        `;
        
        // Row for built date if available
        html += `
            <tr>
                <td>Year Built</td>
                ${this.selectedProperties.map(prop => 
                    `<td class="text-center">${prop.year_built || '-'}</td>`
                ).join('')}
            </tr>
        `;
        
        // Row for land area if available
        if (this.selectedProperties.some(p => p.land_area)) {
            html += `
                <tr>
                    <td>Land Area</td>
                    ${this.createComparisonCells(this.selectedProperties.map(p => p.land_area), 'sq ft')}
                </tr>
            `;
        }
        
        // Close table
        html += `
                    </tbody>
                </table>
            </div>
            
            <div class="comparison-chart mt-3">
                <canvas id="comparison-value-chart"></canvas>
            </div>
        `;
        
        contentEl.innerHTML = html;
        
        // Create chart
        this.createComparisonChart();
    }
    
    /**
     * Create cells for value comparison with visual indicators
     * @param {Array} values - Array of property values
     * @returns {String} HTML for table cells
     */
    createValueComparisonCells(values) {
        const maxValue = Math.max(...values.filter(v => v !== null && v !== undefined));
        
        return values.map(val => {
            if (val === null || val === undefined) return '<td class="text-center">-</td>';
            
            const percent = maxValue > 0 ? (val / maxValue) * 100 : 0;
            const formattedValue = this.formatCurrency(val);
            
            return `
                <td class="text-center">
                    ${formattedValue}
                    <div class="value-bar-container mt-1">
                        <div class="value-bar" style="width: ${percent}%"></div>
                    </div>
                </td>
            `;
        }).join('');
    }
    
    /**
     * Create cells for general numeric comparison
     * @param {Array} values - Array of values to compare
     * @param {String} unit - Optional unit to display
     * @returns {String} HTML for table cells
     */
    createComparisonCells(values, unit = '') {
        const validValues = values.filter(v => v !== null && v !== undefined);
        const maxValue = validValues.length > 0 ? Math.max(...validValues) : 0;
        
        return values.map(val => {
            if (val === null || val === undefined) return '<td class="text-center">-</td>';
            
            const percent = maxValue > 0 ? (val / maxValue) * 100 : 0;
            
            return `
                <td class="text-center">
                    ${val.toLocaleString()} ${unit}
                    <div class="value-bar-container mt-1">
                        <div class="value-bar" style="width: ${percent}%"></div>
                    </div>
                </td>
            `;
        }).join('');
    }
    
    /**
     * Create a chart to visualize property value comparison
     */
    createComparisonChart() {
        const canvas = document.getElementById('comparison-value-chart');
        if (!canvas || !window.Chart) return;
        
        // Prepare data
        const labels = this.selectedProperties.map((p, i) => `Property ${i + 1}`);
        const values = this.selectedProperties.map(p => p.total_value || 0);
        
        // Create chart
        new Chart(canvas, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Property Value ($)',
                    data: values,
                    backgroundColor: [
                        'rgba(54, 162, 235, 0.7)',
                        'rgba(75, 192, 192, 0.7)',
                        'rgba(153, 102, 255, 0.7)',
                        'rgba(255, 159, 64, 0.7)'
                    ],
                    borderColor: [
                        'rgba(54, 162, 235, 1)',
                        'rgba(75, 192, 192, 1)',
                        'rgba(153, 102, 255, 1)',
                        'rgba(255, 159, 64, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
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

// Create comparison tool when map is ready
document.addEventListener('DOMContentLoaded', () => {
    const mapReadyCheck = setInterval(() => {
        const map = window.propertyMap; // Assuming map is stored globally
        if (map) {
            clearInterval(mapReadyCheck);
            window.propertyComparison = new PropertyComparison(map);
        }
    }, 100);
});
