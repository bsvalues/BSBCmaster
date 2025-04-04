/**
 * Query Visualization Helper Functions
 * This file contains functions for visualizing query results
 */

// Create chart from query results
function createVisualizationFromResults(data, container) {
    if (!data || !data.data || data.data.length === 0) {
        container.innerHTML = '<div class="alert alert-info">No data available for visualization</div>';
        return;
    }

    // Check if data can be visualized
    const numericColumns = getNumericColumns(data.data);
    const dateColumns = getDateColumns(data.data);
    const textColumns = getTextColumns(data.data);

    // Clear container
    container.innerHTML = '';

    // Create visualization selector
    const selectorDiv = document.createElement('div');
    selectorDiv.className = 'mb-3';
    selectorDiv.innerHTML = `
        <div class="form-row">
            <div class="col-md-4 mb-2">
                <label for="chartType" class="form-label">Chart Type:</label>
                <select id="chartType" class="form-select">
                    <option value="bar">Bar Chart</option>
                    <option value="line">Line Chart</option>
                    <option value="pie">Pie Chart</option>
                    <option value="scatter">Scatter Plot</option>
                </select>
            </div>
            <div class="col-md-4 mb-2">
                <label for="xAxis" class="form-label">X Axis:</label>
                <select id="xAxis" class="form-select"></select>
            </div>
            <div class="col-md-4 mb-2">
                <label for="yAxis" class="form-label">Y Axis:</label>
                <select id="yAxis" class="form-select"></select>
            </div>
        </div>
    `;
    container.appendChild(selectorDiv);

    // Create canvas for chart
    const canvasDiv = document.createElement('div');
    canvasDiv.className = 'mt-3';
    canvasDiv.style.height = '400px';
    canvasDiv.innerHTML = '<canvas id="resultChart"></canvas>';
    container.appendChild(canvasDiv);

    // Populate selectors
    const xAxisSelect = document.getElementById('xAxis');
    const yAxisSelect = document.getElementById('yAxis');
    const chartTypeSelect = document.getElementById('chartType');

    // Get column names
    const columns = Object.keys(data.data[0]);

    // Add options for X-axis (prefer text/date columns first)
    [...textColumns, ...dateColumns, ...numericColumns, ...columns.filter(c => 
        !textColumns.includes(c) && !dateColumns.includes(c) && !numericColumns.includes(c)
    )].forEach(column => {
        const option = document.createElement('option');
        option.value = column;
        option.textContent = column;
        xAxisSelect.appendChild(option);
    });

    // Add options for Y-axis (prefer numeric columns first)
    [...numericColumns, ...columns.filter(c => !numericColumns.includes(c))].forEach(column => {
        const option = document.createElement('option');
        option.value = column;
        option.textContent = column;
        yAxisSelect.appendChild(option);
    });

    // Set default selections if possible
    if (textColumns.length > 0 && numericColumns.length > 0) {
        xAxisSelect.value = textColumns[0];
        yAxisSelect.value = numericColumns[0];
    } else if (dateColumns.length > 0 && numericColumns.length > 0) {
        xAxisSelect.value = dateColumns[0];
        yAxisSelect.value = numericColumns[0];
    } else if (columns.length >= 2) {
        xAxisSelect.value = columns[0];
        yAxisSelect.value = columns[1];
    }

    // Create initial chart
    let chart = createChart(
        data.data,
        chartTypeSelect.value,
        xAxisSelect.value,
        yAxisSelect.value
    );

    // Add event listeners to update chart
    chartTypeSelect.addEventListener('change', updateChart);
    xAxisSelect.addEventListener('change', updateChart);
    yAxisSelect.addEventListener('change', updateChart);

    function updateChart() {
        if (chart) {
            chart.destroy();
        }
        chart = createChart(
            data.data,
            chartTypeSelect.value,
            xAxisSelect.value,
            yAxisSelect.value
        );
    }
}

// Create a chart based on data and selected options
function createChart(data, chartType, xAxisColumn, yAxisColumn) {
    const ctx = document.getElementById('resultChart').getContext('2d');
    
    // Extract data for the chart
    const labels = data.map(row => row[xAxisColumn]);
    const values = data.map(row => row[yAxisColumn]);
    
    // Check if Y values are numeric
    const areValuesNumeric = values.every(val => !isNaN(Number(val)));
    
    // If values are not numeric, count occurrences for bar/pie chart
    let processedData;
    let processedLabels;
    
    if (!areValuesNumeric && (chartType === 'bar' || chartType === 'pie')) {
        const countMap = {};
        values.forEach(val => {
            countMap[val] = (countMap[val] || 0) + 1;
        });
        
        processedLabels = Object.keys(countMap);
        processedData = Object.values(countMap);
    } else {
        processedLabels = labels;
        processedData = values.map(val => isNaN(Number(val)) ? 0 : Number(val));
    }
    
    // Choose colors for the chart
    const backgroundColors = [
        'rgba(54, 162, 235, 0.5)',
        'rgba(255, 99, 132, 0.5)',
        'rgba(255, 206, 86, 0.5)',
        'rgba(75, 192, 192, 0.5)',
        'rgba(153, 102, 255, 0.5)',
        'rgba(255, 159, 64, 0.5)',
        'rgba(199, 199, 199, 0.5)',
        'rgba(83, 102, 255, 0.5)',
        'rgba(40, 159, 64, 0.5)',
        'rgba(210, 199, 199, 0.5)',
    ];
    
    // Create appropriate chart based on type
    let chartConfig = {
        type: chartType,
        data: {
            labels: processedLabels,
            datasets: [{
                label: yAxisColumn,
                data: processedData,
                backgroundColor: chartType === 'pie' || chartType === 'polarArea' 
                    ? backgroundColors.slice(0, processedData.length) 
                    : backgroundColors[0],
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    };
    
    // Remove scales for pie chart
    if (chartType === 'pie') {
        delete chartConfig.options.scales;
    }
    
    return new Chart(ctx, chartConfig);
}

// Get numeric columns from data
function getNumericColumns(data) {
    const numericColumns = [];
    if (!data || data.length === 0) return numericColumns;
    
    const firstRow = data[0];
    for (const column in firstRow) {
        // Check if all values in this column are numeric
        const isNumeric = data.every(row => {
            const val = row[column];
            return val === null || val === undefined || !isNaN(Number(val));
        });
        
        if (isNumeric) numericColumns.push(column);
    }
    
    return numericColumns;
}

// Get date columns from data
function getDateColumns(data) {
    const dateColumns = [];
    if (!data || data.length === 0) return dateColumns;
    
    const firstRow = data[0];
    for (const column in firstRow) {
        // Check if column name suggests a date
        if (column.toLowerCase().includes('date') || 
            column.toLowerCase().includes('time') ||
            column.toLowerCase().includes('created') ||
            column.toLowerCase().includes('updated')) {
            dateColumns.push(column);
        }
    }
    
    return dateColumns;
}

// Get text columns from data
function getTextColumns(data) {
    const textColumns = [];
    if (!data || data.length === 0) return textColumns;
    
    const firstRow = data[0];
    for (const column in firstRow) {
        // Check if column contains text values
        const isText = data.some(row => {
            const val = row[column];
            return val !== null && typeof val === 'string' && isNaN(Number(val));
        });
        
        if (isText) textColumns.push(column);
    }
    
    return textColumns;
}
