/**
 * Assessment Charts - Visualization Component for MCP Assessor Agent API
 * 
 * This script creates interactive charts for visualizing property assessment data
 * using Chart.js. It provides different chart types and filtering capabilities.
 */

class AssessmentCharts {
    constructor() {
        this.charts = {};
        this.initChartContainers();
        this.setupEventListeners();
        this.loadInitialCharts();
    }

    /**
     * Initialize chart containers in the UI
     */
    initChartContainers() {
        // Check if the visualization section already exists
        if (document.getElementById('visualization-section')) {
            return;
        }

        // Create visualization section
        const mainContent = document.querySelector('.container-fluid');
        if (!mainContent) return;

        const vizSection = document.createElement('div');
        vizSection.id = 'visualization-section';
        vizSection.className = 'row mt-5';
        vizSection.innerHTML = `
            <div class="col-12">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h4 class="mb-0">Property Assessment Visualizations</h4>
                    </div>
                    <div class="card-body">
                        <div class="row mb-4">
                            <div class="col-md-3">
                                <div class="form-group">
                                    <label for="dataset-select">Dataset</label>
                                    <select class="form-control" id="dataset-select">
                                        <option value="accounts">Accounts</option>
                                        <option value="improvements">Improvements</option>
                                        <option value="property_images">Property Images</option>
                                        <option value="combined">Combined Data</option>
                                    </select>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="form-group">
                                    <label for="chart-type-select">Chart Type</label>
                                    <select class="form-control" id="chart-type-select">
                                        <option value="bar">Bar Chart</option>
                                        <option value="pie">Pie Chart</option>
                                        <option value="line">Line Chart</option>
                                        <option value="scatter">Scatter Plot</option>
                                    </select>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="form-group">
                                    <label for="dimension-select">Dimension</label>
                                    <select class="form-control" id="dimension-select">
                                        <option value="assessment_year">Assessment Year</option>
                                        <option value="tax_status">Tax Status</option>
                                        <option value="property_city">City</option>
                                    </select>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="form-group">
                                    <label for="measure-select">Measure</label>
                                    <select class="form-control" id="measure-select">
                                        <option value="assessed_value">Assessed Value</option>
                                        <option value="tax_amount">Tax Amount</option>
                                        <option value="count">Count</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-md-6">
                                <button class="btn btn-primary" id="update-chart-btn">Update Chart</button>
                            </div>
                        </div>
                        <div class="row mt-4">
                            <div class="col-md-12">
                                <div class="chart-container" style="position: relative; height:400px; width:100%">
                                    <canvas id="main-chart"></canvas>
                                </div>
                                <div id="chart-loading" class="text-center py-5 d-none">
                                    <div class="spinner-border text-primary" role="status">
                                        <span class="visually-hidden">Loading...</span>
                                    </div>
                                    <p class="mt-2">Loading chart data...</p>
                                </div>
                                <div id="chart-error" class="alert alert-danger mt-3 d-none">
                                    <strong>Error:</strong> Could not load chart data. Please try again or select different parameters.
                                </div>
                                <div id="no-data-message" class="alert alert-info mt-3 d-none">
                                    <strong>No Data:</strong> No data available for the selected parameters. Please try different criteria.
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Insert after the first tab-content
        const tabContent = document.querySelector('.tab-content');
        if (tabContent) {
            tabContent.parentNode.insertBefore(vizSection, tabContent.nextSibling);
        } else {
            mainContent.appendChild(vizSection);
        }
    }

    /**
     * Set up event listeners for the chart controls
     */
    setupEventListeners() {
        const updateBtn = document.getElementById('update-chart-btn');
        if (updateBtn) {
            updateBtn.addEventListener('click', () => this.updateChart());
        }

        // Update dimension options based on dataset
        const datasetSelect = document.getElementById('dataset-select');
        if (datasetSelect) {
            datasetSelect.addEventListener('change', () => this.updateDimensionOptions());
        }

        // Update measure options based on dataset
        const chartTypeSelect = document.getElementById('chart-type-select');
        if (chartTypeSelect) {
            chartTypeSelect.addEventListener('change', () => this.updateMeasureOptions());
        }
    }

    /**
     * Update dimension options based on selected dataset
     */
    updateDimensionOptions() {
        const dataset = document.getElementById('dataset-select').value;
        const dimensionSelect = document.getElementById('dimension-select');
        
        dimensionSelect.innerHTML = '';
        
        let options = [];
        switch (dataset) {
            case 'accounts':
                options = [
                    { value: 'assessment_year', text: 'Assessment Year' },
                    { value: 'tax_status', text: 'Tax Status' },
                    { value: 'property_city', text: 'City' },
                    { value: 'mailing_state', text: 'Mailing State' }
                ];
                break;
            case 'improvements':
                options = [
                    { value: 'year_built', text: 'Year Built' },
                    { value: 'primary_use', text: 'Primary Use' },
                    { value: 'stories', text: 'Stories' }
                ];
                break;
            case 'property_images':
                options = [
                    { value: 'image_type', text: 'Image Type' },
                    { value: 'image_date', text: 'Image Date' },
                    { value: 'file_format', text: 'File Format' }
                ];
                break;
            case 'combined':
                options = [
                    { value: 'assessment_year', text: 'Assessment Year' },
                    { value: 'property_city', text: 'City' },
                    { value: 'primary_use', text: 'Primary Use' },
                    { value: 'year_built', text: 'Year Built' }
                ];
                break;
        }
        
        options.forEach(option => {
            const optElement = document.createElement('option');
            optElement.value = option.value;
            optElement.textContent = option.text;
            dimensionSelect.appendChild(optElement);
        });
        
        this.updateMeasureOptions();
    }

    /**
     * Update measure options based on selected dataset and chart type
     */
    updateMeasureOptions() {
        const dataset = document.getElementById('dataset-select').value;
        const chartType = document.getElementById('chart-type-select').value;
        const measureSelect = document.getElementById('measure-select');
        
        measureSelect.innerHTML = '';
        
        let options = [];
        switch (dataset) {
            case 'accounts':
                options = [
                    { value: 'assessed_value', text: 'Assessed Value' },
                    { value: 'tax_amount', text: 'Tax Amount' },
                    { value: 'count', text: 'Count' }
                ];
                break;
            case 'improvements':
                options = [
                    { value: 'living_area', text: 'Living Area' },
                    { value: 'value', text: 'Value' },
                    { value: 'count', text: 'Count' }
                ];
                break;
            case 'property_images':
                options = [
                    { value: 'file_size', text: 'File Size' },
                    { value: 'count', text: 'Count' }
                ];
                break;
            case 'combined':
                options = [
                    { value: 'assessed_value', text: 'Assessed Value' },
                    { value: 'tax_amount', text: 'Tax Amount' },
                    { value: 'living_area', text: 'Living Area' },
                    { value: 'count', text: 'Count' }
                ];
                break;
        }
        
        // Count is always an option, but scatter plots require numeric values for both axes
        if (chartType === 'scatter') {
            options = options.filter(opt => opt.value !== 'count');
            if (options.length === 0) {
                options = [{ value: 'count', text: 'Count' }];
            }
        }
        
        options.forEach(option => {
            const optElement = document.createElement('option');
            optElement.value = option.value;
            optElement.textContent = option.text;
            measureSelect.appendChild(optElement);
        });
    }

    /**
     * Load initial charts on page load
     */
    loadInitialCharts() {
        this.updateDimensionOptions();
        this.updateChart();
    }

    /**
     * Update the chart based on current selections
     */
    updateChart() {
        const chartLoading = document.getElementById('chart-loading');
        const chartError = document.getElementById('chart-error');
        const noDataMessage = document.getElementById('no-data-message');
        
        // Reset messages
        chartLoading.classList.remove('d-none');
        chartError.classList.add('d-none');
        noDataMessage.classList.add('d-none');
        
        // Get current selections
        const dataset = document.getElementById('dataset-select').value;
        const chartType = document.getElementById('chart-type-select').value;
        const dimension = document.getElementById('dimension-select').value;
        const measure = document.getElementById('measure-select').value;
        
        // Build API URL
        const apiUrl = `/api/chart-data?dataset=${dataset}&chart_type=${chartType}&dimension=${dimension}&measure=${measure}&aggregation=sum&limit=25`;
        
        // Fetch chart data
        fetch(apiUrl)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                chartLoading.classList.add('d-none');
                
                if (!data || !data.data || data.data.length === 0) {
                    noDataMessage.classList.remove('d-none');
                    return;
                }
                
                this.renderChart(data, chartType, dimension, measure);
            })
            .catch(error => {
                console.error('Error loading chart data:', error);
                chartLoading.classList.add('d-none');
                chartError.classList.remove('d-none');
            });
    }

    /**
     * Render the chart with the provided data
     */
    renderChart(data, chartType, dimension, measure) {
        const chartCanvas = document.getElementById('main-chart');
        const ctx = chartCanvas.getContext('2d');
        
        // Destroy existing chart if any
        if (this.charts.mainChart) {
            this.charts.mainChart.destroy();
        }
        
        // Prepare data for the chart
        const labels = data.data.map(item => item.dimension);
        const values = data.data.map(item => item.value);
        
        // Generate colors for the chart
        const colors = this.generateChartColors(labels.length);
        
        // Configure chart options based on chart type
        let chartConfig = {};
        
        switch (chartType) {
            case 'bar':
                chartConfig = {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: this.formatLabel(measure),
                            data: values,
                            backgroundColor: colors,
                            borderColor: colors.map(color => color.replace('0.7', '1')),
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: {
                                    display: true,
                                    text: this.formatLabel(measure)
                                }
                            },
                            x: {
                                title: {
                                    display: true,
                                    text: this.formatLabel(dimension)
                                }
                            }
                        }
                    }
                };
                break;
                
            case 'pie':
                chartConfig = {
                    type: 'pie',
                    data: {
                        labels: labels,
                        datasets: [{
                            data: values,
                            backgroundColor: colors,
                            borderColor: '#ffffff',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'right',
                            },
                            title: {
                                display: true,
                                text: `${this.formatLabel(measure)} by ${this.formatLabel(dimension)}`
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const label = context.label || '';
                                        const value = context.raw;
                                        const total = context.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                                        const percentage = Math.round((value / total) * 100);
                                        return `${label}: ${value} (${percentage}%)`;
                                    }
                                }
                            }
                        }
                    }
                };
                break;
                
            case 'line':
                chartConfig = {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: this.formatLabel(measure),
                            data: values,
                            fill: false,
                            borderColor: 'rgba(54, 162, 235, 1)',
                            tension: 0.1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: {
                                    display: true,
                                    text: this.formatLabel(measure)
                                }
                            },
                            x: {
                                title: {
                                    display: true,
                                    text: this.formatLabel(dimension)
                                }
                            }
                        }
                    }
                };
                break;
                
            case 'scatter':
                // For scatter plots, we need both x and y values to be numeric
                // We'll use the index as x if the dimension is not numeric
                let xValues;
                if (isNaN(parseFloat(labels[0]))) {
                    xValues = labels.map((_, index) => index);
                } else {
                    xValues = labels.map(label => parseFloat(label));
                }
                
                chartConfig = {
                    type: 'scatter',
                    data: {
                        datasets: [{
                            label: `${this.formatLabel(dimension)} vs ${this.formatLabel(measure)}`,
                            data: xValues.map((x, i) => ({ x, y: values[i] })),
                            backgroundColor: 'rgba(54, 162, 235, 0.7)'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: {
                                    display: true,
                                    text: this.formatLabel(measure)
                                }
                            },
                            x: {
                                title: {
                                    display: true,
                                    text: isNaN(parseFloat(labels[0])) ? 'Index' : this.formatLabel(dimension)
                                }
                            }
                        }
                    }
                };
                break;
        }
        
        // Create the chart
        this.charts.mainChart = new Chart(ctx, chartConfig);
    }

    /**
     * Generate an array of colors for the chart
     */
    generateChartColors(count) {
        const baseColors = [
            'rgba(54, 162, 235, 0.7)',   // Blue
            'rgba(255, 99, 132, 0.7)',   // Red
            'rgba(255, 206, 86, 0.7)',   // Yellow
            'rgba(75, 192, 192, 0.7)',   // Green
            'rgba(153, 102, 255, 0.7)',  // Purple
            'rgba(255, 159, 64, 0.7)',   // Orange
            'rgba(199, 199, 199, 0.7)',  // Gray
            'rgba(83, 102, 255, 0.7)',   // Indigo
            'rgba(255, 99, 255, 0.7)',   // Pink
            'rgba(138, 223, 152, 0.7)'   // Light Green
        ];
        
        // If we need more colors than in our base set, generate them
        if (count > baseColors.length) {
            const additionalColors = [];
            for (let i = 0; i < count - baseColors.length; i++) {
                const r = Math.floor(Math.random() * 255);
                const g = Math.floor(Math.random() * 255);
                const b = Math.floor(Math.random() * 255);
                additionalColors.push(`rgba(${r}, ${g}, ${b}, 0.7)`);
            }
            return [...baseColors, ...additionalColors];
        }
        
        return baseColors.slice(0, count);
    }

    /**
     * Format a label for display (convert snake_case to Title Case)
     */
    formatLabel(key) {
        if (!key) return '';
        return key
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }
}

// Initialize charts when DOM is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new AssessmentCharts());
} else {
    new AssessmentCharts();
}
