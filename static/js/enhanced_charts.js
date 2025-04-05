/**
 * Enhanced Assessment Charts JavaScript
 * 
 * This file provides advanced chart functionality for the MCP Assessor Agent API,
 * supporting multiple chart types, interactive filtering, and chart exports.
 */
console.log("Enhanced Charts JS loaded");

class EnhancedAssessmentCharts {
    constructor() {
        console.log("EnhancedAssessmentCharts constructor called");
        // Elements from the main chart widget
        this.chartContainer = document.getElementById('chartContainer');
        this.chartDataset = document.getElementById('chartDataset');
        this.chartType = document.getElementById('chartType');
        this.chartDimension = document.getElementById('chartDimension');
        this.chartMeasure = document.getElementById('chartMeasure');
        this.chartAggregation = document.getElementById('chartAggregation');
        this.chartLimit = document.getElementById('chartLimit');
        this.generateChartBtn = document.getElementById('generateChart');
        this.chartAlert = document.getElementById('chartAlert');
        this.chartMessage = document.getElementById('chartMessage');
        this.chartLoading = document.getElementById('chartLoading');
        this.chartCanvas = document.getElementById('assessmentChart');
        
        // Export buttons
        this.exportPngBtn = document.getElementById('exportChartPNG');
        this.exportJpgBtn = document.getElementById('exportChartJPG');
        this.exportDataBtn = document.getElementById('exportChartData');
        
        // Filter elements
        this.filterElements = {
            city: document.getElementById('cityFilter'),
            propertyType: document.getElementById('propertyTypeFilter'),
            minValue: document.getElementById('valueRangeMin'),
            maxValue: document.getElementById('valueRangeMax'),
            imageType: document.getElementById('imageTypeFilter'),
            improvementCode: document.getElementById('improvementCodeFilter'),
            year: document.getElementById('yearFilter'),
            sortOrder: document.getElementById('sortOrder')
        };
        this.applyFiltersBtn = document.getElementById('applyFilters');
        
        // Chart instance
        this.chart = null;
        this.currentChartData = null;
        
        // Field mappings for each dataset
        this.fieldMappings = {
            accounts: {
                dimensions: [
                    { value: 'owner_name', label: 'Owner Name' },
                    { value: 'assessment_year', label: 'Assessment Year' },
                    { value: 'tax_status', label: 'Tax Status' },
                    { value: 'mailing_city', label: 'Mailing City' },
                    { value: 'mailing_state', label: 'Mailing State' },
                    { value: 'mailing_zip', label: 'Mailing ZIP' }
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
                    { value: "EXTRACT(YEAR FROM image_date)", label: 'Image Year' }
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
                    { value: 'IMPR_CODE', label: 'Improvement Code' },
                    { value: 'YEAR_BUILT', label: 'Year Built' },
                    { value: 'FLOOR(LIVING_AREA / 500) * 500', label: 'Living Area Range' }
                ],
                measures: [
                    { value: 'IMPR_VALUE', label: 'Improvement Value' },
                    { value: 'LIVING_AREA', label: 'Living Area' },
                    { value: 'NUM_STORIES', label: 'Number of Stories' },
                    { value: 'id', label: 'Count' }
                ]
            }
        };
        
        // Color palette for charts
        this.colors = [
            '#2563eb', '#7c3aed', '#db2777', '#ea580c', 
            '#16a34a', '#ca8a04', '#475569', '#9f1239',
            '#3b82f6', '#8b5cf6', '#ec4899', '#f97316',
            '#22c55e', '#eab308', '#64748b', '#be123c'
        ];
        
        this.init();
    }
    
    init() {
        console.log("EnhancedAssessmentCharts init() called");
        if (!this.generateChartBtn || !this.chartContainer) {
            console.error('Chart elements not found');
            return;
        }
        
        // Initialize chart generator button
        this.generateChartBtn.addEventListener('click', () => this.generateChart());
        
        // Initialize export buttons
        if (this.exportPngBtn) {
            this.exportPngBtn.addEventListener('click', () => this.exportChart('png'));
        }
        if (this.exportJpgBtn) {
            this.exportJpgBtn.addEventListener('click', () => this.exportChart('jpg'));
        }
        if (this.exportDataBtn) {
            this.exportDataBtn.addEventListener('click', () => this.exportChartData());
        }
        
        // Initialize filter button
        if (this.applyFiltersBtn) {
            this.applyFiltersBtn.addEventListener('click', () => this.applyFilters());
        }
        
        // Update field options when dataset changes
        if (this.chartDataset) {
            this.chartDataset.addEventListener('change', () => this.updateFieldOptions());
        }
        
        // Initialize field options
        this.updateFieldOptions();
        
        // Initial chart generation with default values
        setTimeout(() => this.generateChart(), 500);
    }
    
    updateFieldOptions() {
        if (!this.chartDataset || !this.chartDimension || !this.chartMeasure) {
            return;
        }
        
        const dataset = this.chartDataset.value;
        const fields = this.fieldMappings[dataset];
        
        if (!fields) {
            console.error(`No field mappings found for dataset: ${dataset}`);
            return;
        }
        
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
        console.log("generateChart called");
        if (!this.chartDataset || !this.chartType || !this.chartDimension || !this.chartMeasure) {
            console.error('Chart form elements not found');
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
        const limit = this.chartLimit ? parseInt(this.chartLimit.value) : 25;
        
        // Build query parameters
        const params = new URLSearchParams({
            dataset: dataset,
            chart_type: chartType,
            dimension: dimension,
            measure: measure,
            aggregation: aggregation,
            limit: limit
        });
        
        // Apply any active filters
        const filters = this.getActiveFilters();
        if (Object.keys(filters).length > 0) {
            params.append('filters', JSON.stringify(filters));
        }
        
        // Fetch chart data from API
        fetch(`/api/chart-data?${params.toString()}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Failed to fetch chart data: ${response.status} ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                this.currentChartData = data;
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
    
    getActiveFilters() {
        const filters = {};
        
        // Only add filters that have values
        if (this.filterElements.city && this.filterElements.city.value) {
            filters.mailing_city = this.filterElements.city.value;
        }
        
        if (this.filterElements.propertyType && this.filterElements.propertyType.value) {
            filters.property_type = this.filterElements.propertyType.value;
        }
        
        if (this.filterElements.imageType && this.filterElements.imageType.value) {
            filters.image_type = this.filterElements.imageType.value;
        }
        
        if (this.filterElements.improvementCode && this.filterElements.improvementCode.value) {
            filters.impr_code = this.filterElements.improvementCode.value;
        }
        
        if (this.filterElements.year && this.filterElements.year.value) {
            filters.assessment_year = this.filterElements.year.value;
        }
        
        // Add numeric range filters if they exist
        if (this.filterElements.minValue && this.filterElements.minValue.value) {
            filters.min_value = parseFloat(this.filterElements.minValue.value);
        }
        
        if (this.filterElements.maxValue && this.filterElements.maxValue.value) {
            filters.max_value = parseFloat(this.filterElements.maxValue.value);
        }
        
        return filters;
    }
    
    applyFilters() {
        this.generateChart();
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
    
    renderChart(data, chartType) {
        console.log("renderChart called with data:", data);
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
        let title = '';
        let valueType = 'number';
        
        if (data.chart_data && data.chart_data.data) {
            // New API format
            labels = data.chart_data.data.map(item => item.dimension || 'Unknown');
            values = data.chart_data.data.map(item => item.value || 0);
            title = `${data.chart_data.dimension} by ${data.chart_data.measure}`;
            
            // Determine value type based on measure
            if (data.chart_data.measure.toLowerCase().includes('value')) {
                valueType = 'currency';
            } else if (data.chart_data.measure.toLowerCase().includes('size')) {
                valueType = 'filesize';
            }
        } else if (data.labels && data.values) {
            // Legacy format
            labels = data.labels;
            values = data.values;
            title = data.title || 'Chart Data';
            valueType = data.valueType || 'number';
        } else if (Array.isArray(data)) {
            // Direct array format
            labels = data.map(item => item.dimension || 'Unknown');
            values = data.map(item => item.value || 0);
            title = 'Chart Data';
        }
        
        // Format data for different chart types
        const chartData = {
            labels: labels,
            datasets: [{
                label: title,
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
        
        // Chart configuration with responsive options
        const config = {
            type: chartType,
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: title,
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    },
                    legend: {
                        display: ['pie', 'doughnut', 'polarArea'].includes(chartType),
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
                                    label += formatValue(context.parsed.y, valueType);
                                } else if (context.parsed !== undefined) {
                                    label += formatValue(context.parsed, valueType);
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: !['pie', 'doughnut', 'polarArea'].includes(chartType) ? {
                    x: {
                        title: {
                            display: true,
                            text: data.chart_data?.dimension || 'Category',
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
                            text: data.chart_data?.measure || 'Value',
                            font: {
                                weight: 'bold'
                            }
                        },
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return formatValue(value, valueType);
                            }
                        }
                    }
                } : undefined
            }
        };
        
        console.log("Creating chart with config:", config);
        
        // Create chart
        try {
            this.chart = new Chart(ctx, config);
            console.log("Chart created successfully");
        } catch (err) {
            console.error("Error creating chart:", err);
            this.chartAlert.style.display = 'block';
            this.chartMessage.textContent = 'Error creating chart: ' + err.message;
            this.chartLoading.style.display = 'none';
        }
    }
    
    exportChart(format) {
        if (!this.chart) {
            alert('Please generate a chart first');
            return;
        }
        
        // Get chart as data URL
        const dataURL = this.chart.toBase64Image(format === 'jpg' ? 'image/jpeg' : 'image/png');
        
        // Create a download link
        const link = document.createElement('a');
        link.download = `assessment_chart.${format}`;
        link.href = dataURL;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
    
    exportChartData() {
        if (!this.currentChartData) {
            alert('Please generate a chart first');
            return;
        }
        
        // Create CSV content
        let csvContent = 'data:text/csv;charset=utf-8,';
        
        // Add header row
        csvContent += 'Category,Value\n';
        
        // Add data rows
        if (this.currentChartData.chart_data && this.currentChartData.chart_data.data) {
            this.currentChartData.chart_data.data.forEach(item => {
                csvContent += `${item.dimension},${item.value}\n`;
            });
        } else if (this.currentChartData.labels && this.currentChartData.values) {
            for (let i = 0; i < this.currentChartData.labels.length; i++) {
                csvContent += `${this.currentChartData.labels[i]},${this.currentChartData.values[i]}\n`;
            }
        }
        
        // Create a download link
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement('a');
        link.download = 'chart_data.csv';
        link.href = encodedUri;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

// Helper function to format values
function formatValue(value, type) {
    if (!value && value !== 0) return 'N/A';
    
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
    console.log("DOMContentLoaded in enhanced_charts.js");
    // Initialize enhanced assessment charts
    const enhancedCharts = new EnhancedAssessmentCharts();
    
    // Add to window for debugging
    window.enhancedCharts = enhancedCharts;
});
