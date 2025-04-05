/**
 * Assessment Charts JavaScript
 * 
 * This file provides interactive data visualization capabilities for the MCP Assessor Agent API,
 * supporting dynamic chart generation for assessment data.
 */
console.log("Assessment Charts JS loaded");

class AssessmentCharts {
    constructor() {
        console.log("AssessmentCharts constructor called");
        // Elements from the main chart widget
        this.chartContainer = document.getElementById('chartContainer');
        this.chartDataset = document.getElementById('chartDataset');
        this.chartType = document.getElementById('chartType');
        this.chartDimension = document.getElementById('chartDimension');
        this.chartMeasure = document.getElementById('chartMeasure');
        this.chartAggregation = document.getElementById('chartAggregation');
        this.chartAlert = document.getElementById('chartAlert');
        this.chartMessage = document.getElementById('chartMessage');
        this.chartLoading = document.getElementById('chartLoading');
        this.chartCanvas = document.getElementById('assessmentChart');
        this.generateChartBtn = document.getElementById('generateChart');
        
        // Chart instance
        this.chart = null;
        
        // Field mappings for each dataset
        this.fieldMappings = {
            accounts: {
                dimensions: [
                    { value: 'owner_name', label: 'Owner Name' },
                    { value: 'assessment_year', label: 'Assessment Year' },
                    { value: 'tax_status', label: 'Tax Status' },
                    { value: 'mailing_city', label: 'Mailing City' },
                    { value: 'mailing_state', label: 'Mailing State' },
                    { value: 'property_city', label: 'Property City' }
                ],
                measures: [
                    { value: 'id', label: 'Count' },
                    { value: 'assessed_value', label: 'Assessed Value' },
                    { value: 'tax_amount', label: 'Tax Amount' }
                ]
            },
            property_images: {
                dimensions: [
                    { value: 'image_type', label: 'Image Type' },
                    { value: 'file_format', label: 'File Format' },
                    { value: 'EXTRACT(YEAR FROM image_date)', label: 'Image Year' }
                ],
                measures: [
                    { value: 'file_size', label: 'File Size' },
                    { value: 'width', label: 'Width' },
                    { value: 'height', label: 'Height' },
                    { value: 'id', label: 'Count' }
                ]
            },
            improvements: {
                dimensions: [
                    { value: 'year_built', label: 'Year Built' },
                    { value: 'primary_use', label: 'Primary Use' },
                    { value: 'FLOOR(living_area / 500) * 500', label: 'Living Area Range' }
                ],
                measures: [
                    { value: 'value', label: 'Value' },
                    { value: 'living_area', label: 'Living Area' },
                    { value: 'stories', label: 'Stories' },
                    { value: 'id', label: 'Count' }
                ]
            }
        };
        
        // Color palette for charts
        this.colors = [
            '#2563eb', '#7c3aed', '#db2777', '#ea580c', 
            '#16a34a', '#ca8a04', '#475569', '#9f1239'
        ];
        
        this.init();
    }
    
    init() {
        if (!this.chartContainer) {
            console.error('Chart container not found');
            return;
        }
        
        // Initialize generate chart button if available
        if (this.generateChartBtn) {
            this.generateChartBtn.addEventListener('click', () => {
                this.generateChart();
            });
        }
        
        // Update field options when dataset changes
        if (this.chartDataset) {
            this.chartDataset.addEventListener('change', () => this.updateFieldOptions());
        }
        
        // Generate chart when settings change
        const chartControls = [this.chartType, this.chartDimension, this.chartMeasure, this.chartAggregation];
        chartControls.forEach(control => {
            if (control) {
                control.addEventListener('change', () => this.generateChart());
            }
        });
        
        // Initialize field options
        this.updateFieldOptions();
    }
    
    updateFieldOptions() {
        if (!this.chartDataset || !this.chartDimension || !this.chartMeasure) {
            return;
        }
        
        const dataset = this.chartDataset.value;
        const fields = this.fieldMappings[dataset];
        
        // Clear existing options
        this.chartDimension.innerHTML = '';
        this.chartMeasure.innerHTML = '';
        
        // Add dimension options
        fields.dimensions.forEach(dim => {
            const option = document.createElement('option');
            option.value = dim.value;
            option.textContent = dim.label;
            this.chartDimension.appendChild(option);
        });
        
        // Add measure options
        fields.measures.forEach(measure => {
            const option = document.createElement('option');
            option.value = measure.value;
            option.textContent = measure.label;
            this.chartMeasure.appendChild(option);
        });
    }
    
    generateChart() {
        if (!this.chartDataset || !this.chartType || !this.chartDimension || !this.chartMeasure) {
            return;
        }
        
        // Show loading indicator
        this.chartAlert.style.display = 'none';
        this.chartLoading.style.display = 'block';
        
        // Get chart settings
        const dataset = this.chartDataset.value;
        const chartType = this.chartType.value;
        const dimension = this.chartDimension.value;
        const measure = this.chartMeasure.value;
        const aggregation = this.chartAggregation.value;
        
        // Build query parameters
        const params = new URLSearchParams({
            dataset: dataset,
            chart_type: chartType,
            dimension: dimension,
            measure: measure,
            aggregation: aggregation,
            limit: 25 // Default limit
        });
        
        // Fetch chart data from API
        fetch(`/api/chart-data?${params.toString()}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to fetch chart data');
                }
                return response.json();
            })
            .then(data => {
                this.renderChart(data, chartType);
                this.chartLoading.style.display = 'none';
            })
            .catch(error => {
                console.error('Error fetching chart data:', error);
                this.chartAlert.style.display = 'block';
                this.chartMessage.textContent = 'Error loading chart data: ' + error.message;
                this.chartLoading.style.display = 'none';
            });
    }
    
    renderChart(data, chartType) {
        if (!this.chartCanvas) {
            console.error('Chart canvas not found');
            return;
        }
        
        const ctx = this.chartCanvas.getContext('2d');
        
        // Destroy existing chart if any
        if (this.chart) {
            this.chart.destroy();
        }
        
        // Prepare chart data based on the response format
        let labels = [];
        let values = [];
        
        if (data.chart_data && data.chart_data.data) {
            // New API format
            labels = data.chart_data.data.map(item => item.dimension || 'Unknown');
            values = data.chart_data.data.map(item => item.value || 0);
        } else if (data.labels && data.values) {
            // Legacy format
            labels = data.labels;
            values = data.values;
        } else if (Array.isArray(data)) {
            // Direct array format
            labels = data.map(item => item.dimension || 'Unknown');
            values = data.map(item => item.value || 0);
        }
        
        // Format data for different chart types
        const chartData = {
            labels: labels,
            datasets: [{
                label: data.chart_data?.measure || data.title || 'Value',
                data: values,
                backgroundColor: this.getBackgroundColors(chartType, labels.length),
                borderColor: this.getBorderColors(chartType, labels.length),
                borderWidth: this.getBorderWidth(chartType),
                fill: chartType === 'line' || chartType === 'radar' ? 0.3 : undefined,
                tension: chartType === 'line' ? 0.3 : undefined, // Add curve to lines
                pointBackgroundColor: chartType === 'scatter' ? this.colors.map(c => c + '80') : undefined,
                pointBorderColor: chartType === 'scatter' ? this.colors : undefined,
                pointRadius: chartType === 'scatter' ? 6 : 4,
                pointHoverRadius: chartType === 'scatter' ? 10 : 6
            }]
        };
        
        // Chart configuration
        const config = {
            type: chartType,
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: data.title,
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    },
                    legend: {
                        display: chartType === 'pie',
                        position: 'right'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== undefined) {
                                    label += formatValue(context.parsed.y, data.valueType);
                                } else if (context.parsed !== undefined) {
                                    label += formatValue(context.parsed, data.valueType);
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: chartType !== 'pie' ? {
                    x: {
                        title: {
                            display: true,
                            text: data.xAxisLabel || 'Category',
                            font: {
                                weight: 'bold'
                            }
                        },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 0
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: data.yAxisLabel || 'Value',
                            font: {
                                weight: 'bold'
                            }
                        },
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return formatValue(value, data.valueType);
                            }
                        }
                    }
                } : undefined
            }
        };
        
        // Create chart
        this.chart = new Chart(ctx, config);
    }
    
    getBackgroundColors(chartType, count) {
        if (chartType === 'line' || chartType === 'radar') {
            // For line charts, use semi-transparent color
            return this.colors[0] + '40'; // Add alpha transparency
        } else if (chartType === 'scatter') {
            // For scatter plots, use semi-transparent colors for all points
            return Array(count).fill().map((_, i) => this.colors[i % this.colors.length] + '80');
        } else {
            // For other charts, use the color palette
            return Array(count).fill().map((_, i) => this.colors[i % this.colors.length]);
        }
    }
    
    getBorderColors(chartType, count) {
        if (chartType === 'line' || chartType === 'radar') {
            return this.colors[0];
        } else if (chartType === 'scatter') {
            return Array(count).fill().map((_, i) => this.colors[i % this.colors.length]);
        } else {
            return Array(count).fill().map((_, i) => this.colors[i % this.colors.length]);
        }
    }
    
    getBorderWidth(chartType) {
        if (chartType === 'line' || chartType === 'radar') {
            return 3;
        } else if (chartType === 'scatter') {
            return 2;
        } else {
            return 1;
        }
    }
}

// Helper function to format values
function formatValue(value, type) {
    if (type === 'currency') {
        return '$' + value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    } else if (type === 'number') {
        return value.toLocaleString('en-US');
    } else if (type === 'percent') {
        return value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + '%';
    } else if (type === 'filesize') {
        if (value >= 1048576) {
            return (value / 1048576).toLocaleString('en-US', { maximumFractionDigits: 2 }) + ' MB';
        } else if (value >= 1024) {
            return (value / 1024).toLocaleString('en-US', { maximumFractionDigits: 2 }) + ' KB';
        } else {
            return value.toLocaleString('en-US') + ' bytes';
        }
    }
    return value;
}

// Initialize charts when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize assessment charts
    const charts = new AssessmentCharts();
});
