/**
 * Enhanced Visualizations JavaScript
 * 
 * This file provides advanced visualization capabilities for the MCP Assessor Agent API,
 * offering a dedicated interface for generating and customizing interactive charts.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Elements in the Visualizations tab
    const vizDataset = document.getElementById('viz-dataset');
    const vizChartType = document.getElementById('viz-chart-type');
    const vizDimension = document.getElementById('viz-dimension');
    const vizMeasure = document.getElementById('viz-measure');
    const vizAggregation = document.getElementById('viz-aggregation');
    const vizLimit = document.getElementById('viz-limit');
    const vizColorScheme = document.getElementById('viz-color-scheme');
    const applyVizBtn = document.getElementById('apply-viz-btn');
    const vizAlert = document.getElementById('viz-alert');
    const vizMessage = document.getElementById('viz-message');
    const vizLoading = document.getElementById('viz-loading');
    
    // Chart instance
    let vizChart = null;
    
    // Field mappings for each dataset
    const fieldMappings = {
        accounts: {
            dimensions: [
                { value: 'assessment_year', label: 'Assessment Year' },
                { value: 'tax_status', label: 'Tax Status' },
                { value: 'mailing_city', label: 'Mailing City' },
                { value: 'mailing_state', label: 'Mailing State' },
                { value: 'property_city', label: 'Property City' }
            ],
            measures: [
                { value: 'assessed_value', label: 'Assessed Value' },
                { value: 'tax_amount', label: 'Tax Amount' },
                { value: 'id', label: 'Count' }
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
        },
        combined: {
            dimensions: [
                { value: 'a.assessment_year', label: 'Assessment Year' },
                { value: 'a.property_city', label: 'Property City' },
                { value: 'i.primary_use', label: 'Primary Use' }
            ],
            measures: [
                { value: 'a.assessed_value', label: 'Assessed Value' },
                { value: 'a.tax_amount', label: 'Tax Amount' },
                { value: 'i.value', label: 'Improvement Value' },
                { value: 'i.living_area', label: 'Living Area' },
                { value: 'p.file_size', label: 'Image Size' },
                { value: 'a.id', label: 'Count' }
            ]
        }
    };
    
    // Color schemes
    const colorSchemes = {
        default: ['#2563eb', '#7c3aed', '#db2777', '#ea580c', '#16a34a', '#ca8a04'],
        viridis: ['#440154', '#433982', '#30678D', '#218F8B', '#36B677', '#8ED542', '#FDE725'],
        plasma: ['#0D0887', '#5D01A6', '#9C179E', '#CC4678', '#ED7953', '#FDB32F', '#F0F921'],
        inferno: ['#000004', '#320A5A', '#781C6D', '#BD3786', '#ED6925', '#FBB32F', '#FCFEA4'],
        magma: ['#000004', '#2C105C', '#711F81', '#B63679', '#EE605E', '#FDAE78', '#FCFDBF']
    };
    
    // Initialize field options when dataset changes
    function updateFieldOptions() {
        const dataset = vizDataset.value;
        const fields = fieldMappings[dataset];
        
        // Clear existing options
        vizDimension.innerHTML = '';
        vizMeasure.innerHTML = '';
        
        // Add dimension options
        fields.dimensions.forEach(dim => {
            const option = document.createElement('option');
            option.value = dim.value;
            option.textContent = dim.label;
            vizDimension.appendChild(option);
        });
        
        // Add measure options
        fields.measures.forEach(measure => {
            const option = document.createElement('option');
            option.value = measure.value;
            option.textContent = measure.label;
            vizMeasure.appendChild(option);
        });
    }
    
    // Initial field options
    if (vizDataset) {
        updateFieldOptions();
        
        // Update options when dataset changes
        vizDataset.addEventListener('change', updateFieldOptions);
    }
    
    // Generate visualization on button click
    if (applyVizBtn) {
        applyVizBtn.addEventListener('click', generateVisualization);
    }
    
    // Generate visualization with current settings
    function generateVisualization() {
        if (!vizDataset || !vizChartType || !vizDimension || !vizMeasure) {
            console.error('Visualization elements not found');
            return;
        }
        
        // Show loading indicator
        vizAlert.style.display = 'none';
        vizLoading.style.display = 'block';
        
        // Get settings
        const dataset = vizDataset.value;
        const chartType = vizChartType.value;
        const dimension = vizDimension.value;
        const measure = vizMeasure.value;
        const aggregation = vizAggregation.value;
        const limit = vizLimit.value;
        const colorScheme = vizColorScheme.value;
        
        // Build query params
        const params = new URLSearchParams({
            dataset: dataset,
            chart_type: chartType,
            dimension: dimension,
            measure: measure,
            aggregation: aggregation,
            limit: limit
        });
        
        // Fetch data from API
        fetch(`/api/chart-data?${params.toString()}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to fetch chart data');
                }
                return response.json();
            })
            .then(data => {
                renderVisualizationChart(data, chartType, colorScheme);
                vizLoading.style.display = 'none';
            })
            .catch(error => {
                console.error('Error fetching chart data:', error);
                vizAlert.style.display = 'block';
                vizMessage.textContent = 'Error loading chart data: ' + error.message;
                vizLoading.style.display = 'none';
            });
    }
    
    // Render chart with the provided data
    function renderVisualizationChart(data, chartType, colorSchemeKey) {
        const ctx = document.getElementById('visualizationChart').getContext('2d');
        const colors = colorSchemes[colorSchemeKey] || colorSchemes.default;
        
        // Destroy existing chart if any
        if (vizChart) {
            vizChart.destroy();
        }
        
        // Prepare chart data
        const chartData = {
            labels: data.labels,
            datasets: [{
                label: data.title,
                data: data.values,
                backgroundColor: chartType === 'line' ? colors[0] : 
                    data.labels.map((_, i) => colors[i % colors.length]),
                borderColor: chartType === 'line' ? colors[0] : 
                    data.labels.map((_, i) => colors[i % colors.length]),
                borderWidth: chartType === 'line' ? 2 : 1,
                fill: chartType === 'line' ? false : undefined,
                pointBackgroundColor: chartType === 'scatter' ? 
                    data.values.map((_, i) => colors[i % colors.length]) : undefined,
                pointBorderColor: chartType === 'scatter' ? 
                    data.values.map((_, i) => colors[i % colors.length]) : undefined,
                pointRadius: chartType === 'scatter' ? 6 : undefined,
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
                            minRotation: 45
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
        vizChart = new Chart(ctx, config);
    }
    
    // Format value based on its type
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
    
    // Visualization tab selection handler
    const visualizationsTab = document.getElementById('visualizations-tab');
    if (visualizationsTab) {
        visualizationsTab.addEventListener('shown.bs.tab', function() {
            // Update visualization options when tab is shown
            updateFieldOptions();
            
            // If chart container exists but no chart yet, generate one with default settings
            if (document.getElementById('visualizationChart') && !vizChart) {
                generateVisualization();
            }
        });
    }
});
