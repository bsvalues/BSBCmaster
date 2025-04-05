/**
 * Enhanced Visualizations for MCP Assessor Agent API
 * 
 * This file provides advanced visualization capabilities for assessment data.
 */

class AssessmentDataVisualizer {
    constructor() {
        this.chartInstances = {};
        this.availableDatasets = ['accounts', 'improvements', 'property_images', 'combined'];
        this.availableChartTypes = ['bar', 'line', 'pie', 'scatter'];
        this.dataCache = {};
    }

    /**
     * Initialize visualization elements
     * @param {string} containerId - ID of the container element
     */
    initialize(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return false;

        // Create chart selection UI
        this.createChartControls(container);
        
        return true;
    }

    /**
     * Create chart selection and filtering UI
     * @param {HTMLElement} container - Container element
     */
    createChartControls(container) {
        // Create row for controls
        const controlsRow = document.createElement('div');
        controlsRow.className = 'row mb-4';
        
        // Dataset selection
        const datasetCol = document.createElement('div');
        datasetCol.className = 'col-md-3';
        
        const datasetGroup = document.createElement('div');
        datasetGroup.className = 'form-group';
        
        const datasetLabel = document.createElement('label');
        datasetLabel.textContent = 'Dataset';
        datasetLabel.className = 'form-label';
        
        const datasetSelect = document.createElement('select');
        datasetSelect.className = 'form-select';
        datasetSelect.id = 'dataset-select';
        
        this.availableDatasets.forEach(dataset => {
            const option = document.createElement('option');
            option.value = dataset;
            option.textContent = dataset.charAt(0).toUpperCase() + dataset.slice(1);
            datasetSelect.appendChild(option);
        });
        
        datasetGroup.appendChild(datasetLabel);
        datasetGroup.appendChild(datasetSelect);
        datasetCol.appendChild(datasetGroup);
        
        // Chart type selection
        const chartTypeCol = document.createElement('div');
        chartTypeCol.className = 'col-md-3';
        
        const chartTypeGroup = document.createElement('div');
        chartTypeGroup.className = 'form-group';
        
        const chartTypeLabel = document.createElement('label');
        chartTypeLabel.textContent = 'Chart Type';
        chartTypeLabel.className = 'form-label';
        
        const chartTypeSelect = document.createElement('select');
        chartTypeSelect.className = 'form-select';
        chartTypeSelect.id = 'chart-type-select';
        
        this.availableChartTypes.forEach(chartType => {
            const option = document.createElement('option');
            option.value = chartType;
            option.textContent = chartType.charAt(0).toUpperCase() + chartType.slice(1);
            chartTypeSelect.appendChild(option);
        });
        
        chartTypeGroup.appendChild(chartTypeLabel);
        chartTypeGroup.appendChild(chartTypeSelect);
        chartTypeCol.appendChild(chartTypeGroup);
        
        // Dimension selection
        const dimensionCol = document.createElement('div');
        dimensionCol.className = 'col-md-3';
        
        const dimensionGroup = document.createElement('div');
        dimensionGroup.className = 'form-group';
        
        const dimensionLabel = document.createElement('label');
        dimensionLabel.textContent = 'Dimension';
        dimensionLabel.className = 'form-label';
        
        const dimensionSelect = document.createElement('select');
        dimensionSelect.className = 'form-select';
        dimensionSelect.id = 'dimension-select';
        
        dimensionGroup.appendChild(dimensionLabel);
        dimensionGroup.appendChild(dimensionSelect);
        dimensionCol.appendChild(dimensionGroup);
        
        // Measure selection
        const measureCol = document.createElement('div');
        measureCol.className = 'col-md-3';
        
        const measureGroup = document.createElement('div');
        measureGroup.className = 'form-group';
        
        const measureLabel = document.createElement('label');
        measureLabel.textContent = 'Measure';
        measureLabel.className = 'form-label';
        
        const measureSelect = document.createElement('select');
        measureSelect.className = 'form-select';
        measureSelect.id = 'measure-select';
        
        measureGroup.appendChild(measureLabel);
        measureGroup.appendChild(measureSelect);
        measureCol.appendChild(measureGroup);
        
        // Add all to controls row
        controlsRow.appendChild(datasetCol);
        controlsRow.appendChild(chartTypeCol);
        controlsRow.appendChild(dimensionCol);
        controlsRow.appendChild(measureCol);
        
        // Add controls row to container
        container.appendChild(controlsRow);
        
        // Create canvas for chart
        const chartRow = document.createElement('div');
        chartRow.className = 'row';
        
        const chartCol = document.createElement('div');
        chartCol.className = 'col-12';
        
        const chartCanvas = document.createElement('canvas');
        chartCanvas.id = 'visualization-chart';
        chartCanvas.style.width = '100%';
        chartCanvas.style.height = '400px';
        
        chartCol.appendChild(chartCanvas);
        chartRow.appendChild(chartCol);
        container.appendChild(chartRow);
        
        // Add event listeners
        datasetSelect.addEventListener('change', () => this.handleDatasetChange());
        chartTypeSelect.addEventListener('change', () => this.updateVisualization());
        dimensionSelect.addEventListener('change', () => this.updateVisualization());
        measureSelect.addEventListener('change', () => this.updateVisualization());
        
        // Initial load of schema for first dataset
        this.handleDatasetChange();
    }

    /**
     * Handle dataset change by loading schema
     */
    handleDatasetChange() {
        const dataset = document.getElementById('dataset-select').value;
        this.loadDatasetSchema(dataset);
    }

    /**
     * Load dataset schema to populate dimension and measure dropdowns
     * @param {string} dataset - Selected dataset
     */
    loadDatasetSchema(dataset) {
        // Mock schema data for demonstration
        const schemaMap = {
            'accounts': {
                dimensions: ['owner_name', 'account_id', 'classification'],
                measures: ['assessed_value', 'land_value', 'building_value']
            },
            'improvements': {
                dimensions: ['improvement_type', 'year_built', 'quality'],
                measures: ['square_footage', 'value', 'bed_count', 'bath_count']
            },
            'property_images': {
                dimensions: ['image_type', 'capture_date', 'account_id'],
                measures: ['image_count', 'file_size']
            },
            'combined': {
                dimensions: ['owner_name', 'classification', 'improvement_type'],
                measures: ['assessed_value', 'land_value', 'building_value', 'square_footage']
            }
        };
        
        // Get schema for selected dataset
        const schema = schemaMap[dataset] || { dimensions: [], measures: [] };
        
        // Populate dimension dropdown
        const dimensionSelect = document.getElementById('dimension-select');
        dimensionSelect.innerHTML = '';
        
        schema.dimensions.forEach(dimension => {
            const option = document.createElement('option');
            option.value = dimension;
            option.textContent = dimension.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
            dimensionSelect.appendChild(option);
        });
        
        // Populate measure dropdown
        const measureSelect = document.getElementById('measure-select');
        measureSelect.innerHTML = '';
        
        schema.measures.forEach(measure => {
            const option = document.createElement('option');
            option.value = measure;
            option.textContent = measure.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
            measureSelect.appendChild(option);
        });
        
        // Update visualization
        this.updateVisualization();
    }

    /**
     * Update the visualization based on selected options
     */
    updateVisualization() {
        const dataset = document.getElementById('dataset-select').value;
        const chartType = document.getElementById('chart-type-select').value;
        const dimension = document.getElementById('dimension-select').value;
        const measure = document.getElementById('measure-select').value;
        
        // Check if we have all required selections
        if (!dataset || !chartType || !dimension || !measure) {
            return;
        }
        
        // Fetch data and create visualization
        this.fetchChartData(dataset, chartType, dimension, measure);
    }

    /**
     * Fetch chart data from API
     * @param {string} dataset - Selected dataset
     * @param {string} chartType - Selected chart type
     * @param {string} dimension - Selected dimension
     * @param {string} measure - Selected measure
     */
    fetchChartData(dataset, chartType, dimension, measure) {
        // Construct API URL
        const apiUrl = `/api/chart-data?dataset=${dataset}&chart_type=${chartType}&dimension=${dimension}&measure=${measure}&aggregation=sum`;
        
        // Show loading state
        this.showLoading();
        
        // Fetch data
        fetch(apiUrl)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Cache the data
                    this.dataCache[apiUrl] = data;
                    
                    // Create visualization
                    this.createChart(chartType, data.data, dimension, measure);
                } else {
                    this.showError(data.message || 'Failed to load chart data');
                }
            })
            .catch(error => {
                console.error('Error fetching chart data:', error);
                this.showError('An error occurred while fetching chart data');
            });
    }

    /**
     * Show loading state
     */
    showLoading() {
        const canvas = document.getElementById('visualization-chart');
        const ctx = canvas.getContext('2d');
        
        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Draw loading text
        ctx.font = '16px Arial';
        ctx.fillStyle = '#888';
        ctx.textAlign = 'center';
        ctx.fillText('Loading...', canvas.width / 2, canvas.height / 2);
    }

    /**
     * Show error message
     * @param {string} message - Error message
     */
    showError(message) {
        const canvas = document.getElementById('visualization-chart');
        const ctx = canvas.getContext('2d');
        
        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Draw error text
        ctx.font = '16px Arial';
        ctx.fillStyle = '#ff6666';
        ctx.textAlign = 'center';
        ctx.fillText(`Error: ${message}`, canvas.width / 2, canvas.height / 2);
    }

    /**
     * Create chart visualization
     * @param {string} chartType - Type of chart to create
     * @param {Array} data - Chart data
     * @param {string} dimension - Dimension field
     * @param {string} measure - Measure field
     */
    createChart(chartType, data, dimension, measure) {
        const canvas = document.getElementById('visualization-chart');
        
        // Destroy existing chart if any
        if (this.chartInstances['main']) {
            this.chartInstances['main'].destroy();
        }
        
        // Prepare data for chart
        const labels = data.map(item => item[dimension] || 'Unknown');
        const values = data.map(item => item[measure] || 0);
        
        // Create color array
        const colors = this.generateColors(data.length);
        
        // Create chart configuration
        const config = {
            type: chartType,
            data: {
                labels: labels,
                datasets: [{
                    label: measure.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' '),
                    data: values,
                    backgroundColor: colors.map(color => color.replace('1)', '0.7)')),
                    borderColor: colors,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: `${measure.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')} by ${dimension.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}`
                    },
                    legend: {
                        display: chartType === 'pie' || chartType === 'doughnut'
                    }
                }
            }
        };
        
        // Customize chart based on type
        if (chartType === 'bar') {
            config.options.scales = {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: measure.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: dimension.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
                    }
                }
            };
        } else if (chartType === 'line') {
            config.data.datasets[0].fill = false;
            config.data.datasets[0].tension = 0.1;
            config.options.scales = {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: measure.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: dimension.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
                    }
                }
            };
        } else if (chartType === 'pie' || chartType === 'doughnut') {
            // No scales for pie/doughnut charts
            config.options.scales = undefined;
        } else if (chartType === 'scatter') {
            // For scatter plot, convert data to x/y coordinates
            config.data.labels = null;
            config.data.datasets[0].data = data.map((item, index) => ({
                x: index + 1, // Use index as x-coordinate since we don't have another measure
                y: item[measure] || 0
            }));
            config.options.scales = {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: measure.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: dimension.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
                    }
                }
            };
        }
        
        // Create the chart
        this.chartInstances['main'] = new Chart(canvas, config);
    }

    /**
     * Generate colors for chart elements
     * @param {number} count - Number of colors needed
     * @returns {Array} Array of color strings
     */
    generateColors(count) {
        const colors = [];
        for (let i = 0; i < count; i++) {
            const hue = (i * 137) % 360; // Use golden angle for better distribution
            colors.push(`rgba(${Math.floor(Math.random() * 200)}, ${Math.floor(Math.random() * 200)}, ${Math.floor(Math.random() * 200)}, 1)`);
        }
        return colors;
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the visualization page
    const visualizationContainer = document.getElementById('visualization-container');
    if (visualizationContainer) {
        const visualizer = new AssessmentDataVisualizer();
        visualizer.initialize('visualization-container');
        
        // Make available globally
        window.assessmentVisualizer = visualizer;
    }
});
