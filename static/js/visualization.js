/**
 * MCP Assessor Agent API - Data Visualization Module
 */

/**
 * Initialize data visualization feature
 */
function initDataVisualization() {
    // Cache DOM elements
    const visualizationQueryEl = document.getElementById('visualizationQuery');
    const chartTypeEl = document.getElementById('chartType');
    const columnSelectorsEl = document.getElementById('columnSelectors');
    const generateVisualizationBtn = document.getElementById('generateVisualization');
    const runVisualizationQueryBtn = document.getElementById('runVisualizationQuery');
    const chartContainerEl = document.getElementById('chartContainer');
    
    // Store query results for visualization
    let queryResults = [];
    let chartInstance = null;
    
    // Add event listeners
    if (runVisualizationQueryBtn) {
        runVisualizationQueryBtn.addEventListener('click', executeVisualizationQuery);
    }
    
    if (generateVisualizationBtn) {
        generateVisualizationBtn.addEventListener('click', generateVisualization);
    }
    
    if (chartTypeEl) {
        chartTypeEl.addEventListener('change', function() {
            updateColumnSelectors(Object.keys(queryResults[0] || {}));
        });
    }
    
    /**
     * Execute SQL query for visualization
     */
    async function executeVisualizationQuery() {
        const query = visualizationQueryEl.value.trim();
        
        if (!query) {
            displayAlert('Please enter a SQL query', 'danger', chartContainerEl);
            return;
        }
        
        // Display loading state
        chartContainerEl.innerHTML = '<div class="text-center my-5"><div class="spinner-border text-secondary" role="status"></div><p class="mt-2">Executing query...</p></div>';
        
        try {
            const response = await fetch('/api/run-query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'x-api-key': getApiKey()
                },
                body: JSON.stringify({
                    db: 'postgres',  // Default to postgres
                    query: query,
                    page: 1,
                    page_size: 100  // Limit to 100 rows for visualization
                })
            });
            
            const data = await response.json();
            
            if (response.ok && data.status === 'success') {
                if (data.data && data.data.length > 0) {
                    queryResults = data.data;
                    updateColumnSelectors(Object.keys(data.data[0]));
                    
                    // Display success message
                    displayAlert(`Query executed successfully. Retrieved ${data.data.length} rows.`, 'success', chartContainerEl);
                } else {
                    displayAlert('Query executed successfully but returned no data.', 'warning', chartContainerEl);
                }
            } else {
                displayAlert(`Error executing query: ${data.detail || 'Unknown error'}`, 'danger', chartContainerEl);
            }
        } catch (error) {
            displayAlert(`An error occurred: ${error.message}`, 'danger', chartContainerEl);
            console.error('Error:', error);
        }
    }
    
    /**
     * Update column selectors based on query results
     */
    function updateColumnSelectors(columns) {
        if (!columns || columns.length === 0) {
            columnSelectorsEl.innerHTML = '<p class="text-muted small">No columns available</p>';
            return;
        }
        
        const chartType = chartTypeEl.value;
        
        let html = '';
        
        if (chartType === 'bar' || chartType === 'line') {
            html += `
                <div class="mb-2">
                    <label for="xAxisColumn" class="form-label">X-Axis</label>
                    <select class="form-select form-select-sm" id="xAxisColumn">
                        ${columns.map(col => `<option value="${col}">${col}</option>`).join('')}
                    </select>
                </div>
                <div class="mb-2">
                    <label for="yAxisColumn" class="form-label">Y-Axis</label>
                    <select class="form-select form-select-sm" id="yAxisColumn">
                        ${columns.map(col => `<option value="${col}">${col}</option>`).join('')}
                    </select>
                </div>
            `;
        } else if (chartType === 'pie') {
            html += `
                <div class="mb-2">
                    <label for="labelColumn" class="form-label">Labels</label>
                    <select class="form-select form-select-sm" id="labelColumn">
                        ${columns.map(col => `<option value="${col}">${col}</option>`).join('')}
                    </select>
                </div>
                <div class="mb-2">
                    <label for="valueColumn" class="form-label">Values</label>
                    <select class="form-select form-select-sm" id="valueColumn">
                        ${columns.map(col => `<option value="${col}">${col}</option>`).join('')}
                    </select>
                </div>
            `;
        } else if (chartType === 'scatter') {
            html += `
                <div class="mb-2">
                    <label for="xAxisColumn" class="form-label">X-Axis</label>
                    <select class="form-select form-select-sm" id="xAxisColumn">
                        ${columns.map(col => `<option value="${col}">${col}</option>`).join('')}
                    </select>
                </div>
                <div class="mb-2">
                    <label for="yAxisColumn" class="form-label">Y-Axis</label>
                    <select class="form-select form-select-sm" id="yAxisColumn">
                        ${columns.map(col => `<option value="${col}">${col}</option>`).join('')}
                    </select>
                </div>
                <div class="mb-2">
                    <label for="labelColumn" class="form-label">Point Labels (optional)</label>
                    <select class="form-select form-select-sm" id="labelColumn">
                        <option value="">None</option>
                        ${columns.map(col => `<option value="${col}">${col}</option>`).join('')}
                    </select>
                </div>
            `;
        }
        
        columnSelectorsEl.innerHTML = html;
    }
    
    /**
     * Generate visualization based on selected options
     */
    function generateVisualization() {
        if (!queryResults || queryResults.length === 0) {
            displayAlert('Please run a query first to get data for visualization', 'warning', chartContainerEl);
            return;
        }
        
        const chartType = chartTypeEl.value;
        
        // Destroy previous chart instance if it exists
        if (chartInstance) {
            chartInstance.destroy();
        }
        
        try {
            // Generate chart based on selected type
            switch (chartType) {
                case 'bar':
                    const xAxisColumn = document.getElementById('xAxisColumn').value;
                    const yAxisColumn = document.getElementById('yAxisColumn').value;
                    generateBarChart(xAxisColumn, yAxisColumn);
                    break;
                    
                case 'line':
                    const lineXAxisColumn = document.getElementById('xAxisColumn').value;
                    const lineYAxisColumn = document.getElementById('yAxisColumn').value;
                    generateLineChart(lineXAxisColumn, lineYAxisColumn);
                    break;
                    
                case 'pie':
                    const labelColumn = document.getElementById('labelColumn').value;
                    const valueColumn = document.getElementById('valueColumn').value;
                    generatePieChart(labelColumn, valueColumn);
                    break;
                    
                case 'scatter':
                    const scatterXAxisColumn = document.getElementById('xAxisColumn').value;
                    const scatterYAxisColumn = document.getElementById('yAxisColumn').value;
                    const scatterLabelColumn = document.getElementById('labelColumn').value;
                    generateScatterPlot(scatterXAxisColumn, scatterYAxisColumn, scatterLabelColumn);
                    break;
                    
                default:
                    displayAlert('Invalid chart type selected', 'danger', chartContainerEl);
            }
        } catch (error) {
            displayAlert(`Error generating chart: ${error.message}`, 'danger', chartContainerEl);
            console.error('Error generating chart:', error);
        }
    }
    
    /**
     * Generate bar chart
     */
    function generateBarChart(xAxisColumn, yAxisColumn) {
        // Prepare data
        const labels = queryResults.map(row => row[xAxisColumn]);
        const data = queryResults.map(row => parseFloat(row[yAxisColumn]) || 0);
        
        // Prepare canvas
        const canvas = prepareChartCanvas();
        
        // Create chart
        chartInstance = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: yAxisColumn,
                    data: data,
                    backgroundColor: generateColors(data.length),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: `${yAxisColumn} by ${xAxisColumn}`
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: yAxisColumn
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: xAxisColumn
                        }
                    }
                }
            }
        });
    }
    
    /**
     * Generate line chart
     */
    function generateLineChart(xAxisColumn, yAxisColumn) {
        // Sort data by x-axis for line chart
        queryResults.sort((a, b) => {
            const valA = a[xAxisColumn];
            const valB = b[xAxisColumn];
            
            // Try to compare as numbers first
            const numA = parseFloat(valA);
            const numB = parseFloat(valB);
            
            if (!isNaN(numA) && !isNaN(numB)) {
                return numA - numB;
            }
            
            // Fall back to string comparison
            return String(valA).localeCompare(String(valB));
        });
        
        // Prepare data
        const labels = queryResults.map(row => row[xAxisColumn]);
        const data = queryResults.map(row => parseFloat(row[yAxisColumn]) || 0);
        
        // Prepare canvas
        const canvas = prepareChartCanvas();
        
        // Create chart
        chartInstance = new Chart(canvas, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: yAxisColumn,
                    data: data,
                    fill: false,
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: `${yAxisColumn} by ${xAxisColumn}`
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: yAxisColumn
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: xAxisColumn
                        }
                    }
                }
            }
        });
    }
    
    /**
     * Generate pie chart
     */
    function generatePieChart(labelColumn, valueColumn) {
        // Prepare data
        const labels = queryResults.map(row => row[labelColumn]);
        const data = queryResults.map(row => parseFloat(row[valueColumn]) || 0);
        
        // Prepare canvas
        const canvas = prepareChartCanvas();
        
        // Create chart
        chartInstance = new Chart(canvas, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: generateColors(data.length)
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: `${valueColumn} by ${labelColumn}`
                    },
                    legend: {
                        position: 'right'
                    }
                }
            }
        });
    }
    
    /**
     * Generate scatter plot
     */
    function generateScatterPlot(xAxisColumn, yAxisColumn, labelColumn) {
        // Prepare data
        const data = queryResults.map(row => ({
            x: parseFloat(row[xAxisColumn]) || 0,
            y: parseFloat(row[yAxisColumn]) || 0,
            label: labelColumn ? row[labelColumn] : null
        }));
        
        // Prepare canvas
        const canvas = prepareChartCanvas();
        
        // Create chart
        chartInstance = new Chart(canvas, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: `${yAxisColumn} vs ${xAxisColumn}`,
                    data: data,
                    backgroundColor: 'rgba(75, 192, 192, 0.6)',
                    pointRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: `${yAxisColumn} vs ${xAxisColumn}`
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const point = data[context.dataIndex];
                                let label = point.label ? point.label + ': ' : '';
                                label += `(${point.x}, ${point.y})`;
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        title: {
                            display: true,
                            text: yAxisColumn
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: xAxisColumn
                        }
                    }
                }
            }
        });
    }
    
    /**
     * Prepare canvas for chart
     */
    function prepareChartCanvas() {
        // Clear container
        chartContainerEl.innerHTML = '';
        
        // Create canvas
        const canvas = document.createElement('canvas');
        canvas.id = 'visualizationChart';
        chartContainerEl.appendChild(canvas);
        
        return canvas;
    }
    
    /**
     * Generate colors for chart elements
     */
    function generateColors(count) {
        const colors = [
            'rgba(54, 162, 235, 0.7)',
            'rgba(255, 99, 132, 0.7)',
            'rgba(255, 206, 86, 0.7)',
            'rgba(75, 192, 192, 0.7)',
            'rgba(153, 102, 255, 0.7)',
            'rgba(255, 159, 64, 0.7)',
            'rgba(199, 199, 199, 0.7)',
            'rgba(83, 102, 255, 0.7)',
            'rgba(40, 159, 64, 0.7)',
            'rgba(210, 199, 199, 0.7)'
        ];
        
        // If we need more colors than in our predefined array, generate them
        if (count > colors.length) {
            for (let i = colors.length; i < count; i++) {
                const r = Math.floor(Math.random() * 255);
                const g = Math.floor(Math.random() * 255);
                const b = Math.floor(Math.random() * 255);
                colors.push(`rgba(${r}, ${g}, ${b}, 0.7)`);
            }
        }
        
        return colors.slice(0, count);
    }
    
    /**
     * Display alert message
     */
    function displayAlert(message, type, container) {
        container.innerHTML = `
            <div class="alert alert-${type}" role="alert">
                ${message}
            </div>
        `;
    }
    
    /**
     * Get API key from input
     */
    function getApiKey() {
        // Try to get API key from localStorage or a form input
        // For demo purposes, use the development key
        return 'devkey_secure_123';
    }
}

// Initialize visualization when document is loaded
document.addEventListener('DOMContentLoaded', function() {
    initDataVisualization();
});