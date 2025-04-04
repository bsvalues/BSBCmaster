with open('app/templates/query_builder.html', 'r') as file:
    content = file.read()

# Find the document ready function to add our visualization code
document_ready_start = content.find('document.addEventListener(\'DOMContentLoaded\', function() {')

if document_ready_start != -1:
    # Find the end of the document ready function
    script_end = content.find('</script>', document_ready_start)
    if script_end != -1:
        # Look for the last closing brace before the script end
        last_brace = content.rfind('});', document_ready_start, script_end)
        
        if last_brace != -1:
            # Visualization code to be added
            visualization_js = """
        // Visualization code
        const toggleVizBtn = document.getElementById('toggle-viz-btn');
        const chartContainer = document.getElementById('chart-container');
        const visualizationContainer = document.getElementById('visualization-container');
        
        if (toggleVizBtn) {
            toggleVizBtn.addEventListener('click', function() {
                const isHidden = chartContainer.style.display === 'none';
                chartContainer.style.display = isHidden ? 'block' : 'none';
                
                if (isHidden && window.lastResults && window.lastResults.data) {
                    updateChartSelectors();
                    updateChart();
                }
            });
        }
        
        // Chart selectors
        const chartTypeSelect = document.getElementById('chartType');
        const xAxisSelect = document.getElementById('xAxis');
        const yAxisSelect = document.getElementById('yAxis');
        
        if (chartTypeSelect && xAxisSelect && yAxisSelect) {
            chartTypeSelect.addEventListener('change', updateChart);
            xAxisSelect.addEventListener('change', updateChart);
            yAxisSelect.addEventListener('change', updateChart);
        }
        
        // Update chart selectors
        function updateChartSelectors() {
            if (!window.lastResults || !window.lastResults.data || window.lastResults.data.length === 0) {
                return;
            }
            
            // Clear existing options
            xAxisSelect.innerHTML = '';
            yAxisSelect.innerHTML = '';
            
            // Get data columns
            const data = window.lastResults.data;
            const columns = Object.keys(data[0]);
            
            // Get column types
            const numericColumns = getNumericColumns(data);
            const dateColumns = getDateColumns(data);
            const textColumns = getTextColumns(data);
            
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
        
        // Chart instance
        let chartInstance = null;
        
        // Update chart based on selections
        function updateChart() {
            if (!window.lastResults || !window.lastResults.data || window.lastResults.data.length === 0) {
                return;
            }
            
            // Get chart parameters
            const chartType = chartTypeSelect.value;
            const xColumn = xAxisSelect.value;
            const yColumn = yAxisSelect.value;
            
            // Get canvas context
            const ctx = document.getElementById('resultChart').getContext('2d');
            
            // Extract data for chart
            const data = window.lastResults.data;
            const labels = data.map(row => row[xColumn]);
            const values = data.map(row => row[yColumn]);
            
            // Check if values are numeric
            const areValuesNumeric = values.every(val => !isNaN(Number(val)));
            
            // Process data based on type
            let processedLabels, processedData;
            
            if (!areValuesNumeric && (chartType === 'bar' || chartType === 'pie')) {
                // Count occurrences for non-numeric values
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
            
            // Choose colors
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
            
            // Create chart config
            const chartConfig = {
                type: chartType,
                data: {
                    labels: processedLabels,
                    datasets: [{
                        label: yColumn,
                        data: processedData,
                        backgroundColor: chartType === 'pie' ? 
                            backgroundColors.slice(0, processedData.length) : 
                            backgroundColors[0],
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
            
            // Destroy previous chart if exists
            if (chartInstance) {
                chartInstance.destroy();
            }
            
            // Create new chart
            chartInstance = new Chart(ctx, chartConfig);
        }
        
        // Show visualization container when results are displayed
        function showVisualization() {
            if (window.lastResults && window.lastResults.data && window.lastResults.data.length > 0) {
                visualizationContainer.style.display = 'flex';
            }
        }
            """
            
            # Add visualization code to displayResults function
            display_results_function = content.find('function displayResults(data) {')
            if display_results_function != -1:
                display_results_end = content.find('};', display_results_function)
                if display_results_end != -1:
                    # Add code to show visualization after displaying results
                    visualization_call = """
            // Show visualization options if there's data
            if (data.data && data.data.length > 0) {
                document.getElementById('visualization-container').style.display = 'flex';
            }
"""
                    modified_content = content[:display_results_end] + visualization_call + content[display_results_end:]
                    
                    # Add the main visualization functions to the document ready function
                    modified_content = modified_content[:last_brace] + visualization_js + modified_content[last_brace:]
                    
                    # Write back to the file
                    with open('app/templates/query_builder.html', 'w') as file:
                        file.write(modified_content)
                    
                    print("Successfully added visualization JavaScript to query_builder.html")
                else:
                    print("Could not find the end of the displayResults function")
            else:
                print("Could not find the displayResults function")
        else:
            print("Could not find the end of the document ready function")
    else:
        print("Could not find the end of the script tag")
else:
    print("Could not find the document ready function")
