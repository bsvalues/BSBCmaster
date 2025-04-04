/**
 * MCP Assessor Agent API - Data Visualization Module
 * 
 * This module provides visualization capabilities for real estate assessment data.
 * It includes functions for creating charts, maps, and other visualizations.
 */

// Visualization namespace
const MCPVisualization = (function() {
    
    // Configuration
    const config = {
        colors: {
            primary: '#0d6efd',
            secondary: '#6c757d',
            success: '#198754',
            danger: '#dc3545',
            warning: '#ffc107',
            info: '#0dcaf0',
            light: '#f8f9fa',
            dark: '#212529'
        },
        chart: {
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial',
            fontSize: 12,
            backgroundColor: '#212529',
            textColor: '#f8f9fa'
        }
    };

    /**
     * Create a bar chart using Chart.js
     * 
     * @param {string} elementId - The ID of the canvas element
     * @param {Array} labels - The labels for the chart
     * @param {Array} data - The data values for the chart
     * @param {string} title - The title of the chart
     * @param {Object} options - Additional options for the chart
     * @returns {Object} The created chart instance
     */
    function createBarChart(elementId, labels, data, title, options = {}) {
        const ctx = document.getElementById(elementId).getContext('2d');
        
        // Default options
        const defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: config.chart.textColor
                    }
                },
                title: {
                    display: true,
                    text: title,
                    color: config.chart.textColor,
                    font: {
                        size: 16
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: config.chart.textColor
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: config.chart.textColor
                    }
                }
            }
        };
        
        // Merge options
        const mergedOptions = { ...defaultOptions, ...options };
        
        // Create chart
        return new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: title,
                    data: data,
                    backgroundColor: config.colors.primary,
                    borderColor: config.colors.primary,
                    borderWidth: 1
                }]
            },
            options: mergedOptions
        });
    }
    
    /**
     * Create a pie chart using Chart.js
     * 
     * @param {string} elementId - The ID of the canvas element
     * @param {Array} labels - The labels for the chart
     * @param {Array} data - The data values for the chart
     * @param {string} title - The title of the chart
     * @param {Object} options - Additional options for the chart
     * @returns {Object} The created chart instance
     */
    function createPieChart(elementId, labels, data, title, options = {}) {
        const ctx = document.getElementById(elementId).getContext('2d');
        
        // Generate colors based on the number of data points
        const backgroundColors = generateColorPalette(data.length);
        
        // Default options
        const defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: config.chart.textColor
                    }
                },
                title: {
                    display: true,
                    text: title,
                    color: config.chart.textColor,
                    font: {
                        size: 16
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            }
        };
        
        // Merge options
        const mergedOptions = { ...defaultOptions, ...options };
        
        // Create chart
        return new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    label: title,
                    data: data,
                    backgroundColor: backgroundColors,
                    borderColor: backgroundColors.map(color => adjustColorBrightness(color, -20)),
                    borderWidth: 1
                }]
            },
            options: mergedOptions
        });
    }
    
    /**
     * Create a line chart using Chart.js
     * 
     * @param {string} elementId - The ID of the canvas element
     * @param {Array} labels - The labels for the chart
     * @param {Array} data - The data values for the chart
     * @param {string} title - The title of the chart
     * @param {Object} options - Additional options for the chart
     * @returns {Object} The created chart instance
     */
    function createLineChart(elementId, labels, data, title, options = {}) {
        const ctx = document.getElementById(elementId).getContext('2d');
        
        // Default options
        const defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: config.chart.textColor
                    }
                },
                title: {
                    display: true,
                    text: title,
                    color: config.chart.textColor,
                    font: {
                        size: 16
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: config.chart.textColor
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: config.chart.textColor
                    }
                }
            }
        };
        
        // Merge options
        const mergedOptions = { ...defaultOptions, ...options };
        
        // Create chart
        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: title,
                    data: data,
                    backgroundColor: 'rgba(13, 110, 253, 0.2)',
                    borderColor: config.colors.primary,
                    borderWidth: 2,
                    tension: 0.1,
                    fill: true
                }]
            },
            options: mergedOptions
        });
    }
    
    /**
     * Create a data table using the query results
     * 
     * @param {string} elementId - The ID of the element to append the table to
     * @param {Object} queryResult - The query result object from the API
     * @param {Object} options - Additional options for the table
     */
    function createDataTable(elementId, queryResult, options = {}) {
        const element = document.getElementById(elementId);
        
        // Clear the element
        element.innerHTML = '';
        
        // Check if there are rows to display
        if (!queryResult.rows || queryResult.rows.length === 0) {
            element.innerHTML = '<div class="alert alert-info">No data available</div>';
            return;
        }
        
        // Get the column names from the first row
        const columns = Object.keys(queryResult.rows[0]);
        
        // Create table container with responsive wrapper
        const tableContainer = document.createElement('div');
        tableContainer.className = 'table-responsive';
        
        // Create table
        const table = document.createElement('table');
        table.className = 'table table-dark table-striped table-hover';
        
        // Create table header
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        
        // Add header cells
        columns.forEach(column => {
            const th = document.createElement('th');
            th.textContent = formatColumnName(column);
            headerRow.appendChild(th);
        });
        
        thead.appendChild(headerRow);
        table.appendChild(thead);
        
        // Create table body
        const tbody = document.createElement('tbody');
        
        // Add rows
        queryResult.rows.forEach(row => {
            const tr = document.createElement('tr');
            
            // Add cells
            columns.forEach(column => {
                const td = document.createElement('td');
                
                // Format the value based on its type
                let value = row[column];
                
                if (value === null) {
                    td.innerHTML = '<span class="text-muted">NULL</span>';
                } else if (typeof value === 'boolean') {
                    td.innerHTML = value ? '<span class="badge bg-success">True</span>' : '<span class="badge bg-danger">False</span>';
                } else if (typeof value === 'number') {
                    // Format numbers with commas for thousands
                    if (column.toLowerCase().includes('price') || column.toLowerCase().includes('value')) {
                        td.textContent = '$' + value.toLocaleString();
                    } else {
                        td.textContent = value.toLocaleString();
                    }
                } else if (typeof value === 'string' && (column.toLowerCase().includes('date') || column.toLowerCase().includes('time'))) {
                    // Format dates nicely
                    try {
                        const date = new Date(value);
                        td.textContent = date.toLocaleDateString();
                    } catch (e) {
                        td.textContent = value;
                    }
                } else {
                    td.textContent = value;
                }
                
                tr.appendChild(td);
            });
            
            tbody.appendChild(tr);
        });
        
        table.appendChild(tbody);
        tableContainer.appendChild(table);
        
        // Add pagination if there are multiple pages
        if (queryResult.total_pages > 1) {
            const pagination = createPagination(queryResult.page, queryResult.total_pages, options.onPageChange);
            element.appendChild(pagination);
        }
        
        // Append table to element
        element.appendChild(tableContainer);
        
        // Add metadata about the query
        const metadataDiv = document.createElement('div');
        metadataDiv.className = 'mt-3 text-muted small';
        metadataDiv.innerHTML = `
            <strong>Total rows:</strong> ${queryResult.total_rows} | 
            <strong>Execution time:</strong> ${queryResult.execution_time.toFixed(3)}s
        `;
        element.appendChild(metadataDiv);
    }
    
    /**
     * Create a pagination component
     * 
     * @param {number} currentPage - The current page number
     * @param {number} totalPages - The total number of pages
     * @param {Function} onPageChange - Callback function when page changes
     * @returns {HTMLElement} The pagination element
     */
    function createPagination(currentPage, totalPages, onPageChange) {
        const paginationContainer = document.createElement('nav');
        paginationContainer.setAttribute('aria-label', 'Data pagination');
        
        const paginationList = document.createElement('ul');
        paginationList.className = 'pagination justify-content-center';
        
        // Previous button
        const prevItem = document.createElement('li');
        prevItem.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
        
        const prevLink = document.createElement('a');
        prevLink.className = 'page-link';
        prevLink.href = '#';
        prevLink.setAttribute('aria-label', 'Previous');
        prevLink.innerHTML = '<span aria-hidden="true">&laquo;</span>';
        
        if (currentPage > 1) {
            prevLink.addEventListener('click', e => {
                e.preventDefault();
                onPageChange(currentPage - 1);
            });
        }
        
        prevItem.appendChild(prevLink);
        paginationList.appendChild(prevItem);
        
        // Page numbers
        const maxPages = 5; // Maximum number of page links to show
        let startPage = Math.max(1, currentPage - Math.floor(maxPages / 2));
        let endPage = Math.min(totalPages, startPage + maxPages - 1);
        
        // Adjust start page if end page is maxPages
        if (endPage - startPage + 1 < maxPages && startPage > 1) {
            startPage = Math.max(1, endPage - maxPages + 1);
        }
        
        // First page
        if (startPage > 1) {
            const firstItem = document.createElement('li');
            firstItem.className = 'page-item';
            
            const firstLink = document.createElement('a');
            firstLink.className = 'page-link';
            firstLink.href = '#';
            firstLink.textContent = '1';
            
            firstLink.addEventListener('click', e => {
                e.preventDefault();
                onPageChange(1);
            });
            
            firstItem.appendChild(firstLink);
            paginationList.appendChild(firstItem);
            
            // Ellipsis
            if (startPage > 2) {
                const ellipsisItem = document.createElement('li');
                ellipsisItem.className = 'page-item disabled';
                
                const ellipsisLink = document.createElement('a');
                ellipsisLink.className = 'page-link';
                ellipsisLink.href = '#';
                ellipsisLink.textContent = '...';
                
                ellipsisItem.appendChild(ellipsisLink);
                paginationList.appendChild(ellipsisItem);
            }
        }
        
        // Page numbers
        for (let i = startPage; i <= endPage; i++) {
            const pageItem = document.createElement('li');
            pageItem.className = `page-item ${i === currentPage ? 'active' : ''}`;
            
            const pageLink = document.createElement('a');
            pageLink.className = 'page-link';
            pageLink.href = '#';
            pageLink.textContent = i;
            
            if (i !== currentPage) {
                pageLink.addEventListener('click', e => {
                    e.preventDefault();
                    onPageChange(i);
                });
            }
            
            pageItem.appendChild(pageLink);
            paginationList.appendChild(pageItem);
        }
        
        // Last page
        if (endPage < totalPages) {
            // Ellipsis
            if (endPage < totalPages - 1) {
                const ellipsisItem = document.createElement('li');
                ellipsisItem.className = 'page-item disabled';
                
                const ellipsisLink = document.createElement('a');
                ellipsisLink.className = 'page-link';
                ellipsisLink.href = '#';
                ellipsisLink.textContent = '...';
                
                ellipsisItem.appendChild(ellipsisLink);
                paginationList.appendChild(ellipsisItem);
            }
            
            const lastItem = document.createElement('li');
            lastItem.className = 'page-item';
            
            const lastLink = document.createElement('a');
            lastLink.className = 'page-link';
            lastLink.href = '#';
            lastLink.textContent = totalPages;
            
            lastLink.addEventListener('click', e => {
                e.preventDefault();
                onPageChange(totalPages);
            });
            
            lastItem.appendChild(lastLink);
            paginationList.appendChild(lastItem);
        }
        
        // Next button
        const nextItem = document.createElement('li');
        nextItem.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
        
        const nextLink = document.createElement('a');
        nextLink.className = 'page-link';
        nextLink.href = '#';
        nextLink.setAttribute('aria-label', 'Next');
        nextLink.innerHTML = '<span aria-hidden="true">&raquo;</span>';
        
        if (currentPage < totalPages) {
            nextLink.addEventListener('click', e => {
                e.preventDefault();
                onPageChange(currentPage + 1);
            });
        }
        
        nextItem.appendChild(nextLink);
        paginationList.appendChild(nextItem);
        
        paginationContainer.appendChild(paginationList);
        return paginationContainer;
    }
    
    /**
     * Format a column name for display
     * 
     * @param {string} columnName - The raw column name
     * @returns {string} The formatted column name
     */
    function formatColumnName(columnName) {
        // Replace underscores with spaces
        let formatted = columnName.replace(/_/g, ' ');
        
        // Capitalize each word
        formatted = formatted.replace(/\b\w/g, char => char.toUpperCase());
        
        return formatted;
    }
    
    /**
     * Generate a color palette with the specified number of colors
     * 
     * @param {number} count - The number of colors to generate
     * @returns {Array} An array of color strings
     */
    function generateColorPalette(count) {
        const baseColors = [
            config.colors.primary,
            config.colors.success,
            config.colors.danger,
            config.colors.warning,
            config.colors.info,
            '#fd7e14', // orange
            '#6f42c1', // purple
            '#20c997', // teal
            '#e83e8c', // pink
            '#17a2b8'  // cyan
        ];
        
        // If we need fewer colors than the base palette, return a subset
        if (count <= baseColors.length) {
            return baseColors.slice(0, count);
        }
        
        // Otherwise, generate additional colors by adjusting the brightness of the base colors
        const colors = [...baseColors];
        
        let currentIndex = 0;
        while (colors.length < count) {
            const baseColor = baseColors[currentIndex % baseColors.length];
            const brightness = 20 * (Math.floor(currentIndex / baseColors.length) + 1);
            colors.push(adjustColorBrightness(baseColor, brightness));
            currentIndex++;
        }
        
        return colors;
    }
    
    /**
     * Adjust the brightness of a color
     * 
     * @param {string} color - The color in hex format (#RRGGBB)
     * @param {number} percent - The percentage to adjust the brightness (negative for darker, positive for lighter)
     * @returns {string} The adjusted color in hex format
     */
    function adjustColorBrightness(color, percent) {
        let R = parseInt(color.substring(1, 3), 16);
        let G = parseInt(color.substring(3, 5), 16);
        let B = parseInt(color.substring(5, 7), 16);
        
        R = parseInt(R * (100 + percent) / 100);
        G = parseInt(G * (100 + percent) / 100);
        B = parseInt(B * (100 + percent) / 100);
        
        R = (R < 255) ? R : 255;
        G = (G < 255) ? G : 255;
        B = (B < 255) ? B : 255;
        
        R = Math.max(0, R).toString(16).padStart(2, '0');
        G = Math.max(0, G).toString(16).padStart(2, '0');
        B = Math.max(0, B).toString(16).padStart(2, '0');
        
        return `#${R}${G}${B}`;
    }
    
    /**
     * Create visualizations based on the query results
     * 
     * @param {string} containerElementId - The ID of the container element
     * @param {Object} queryResult - The query result object from the API
     */
    function visualizeQueryResults(containerElementId, queryResult) {
        const container = document.getElementById(containerElementId);
        
        // Clear the container
        container.innerHTML = '';
        
        // Check if there are rows to visualize
        if (!queryResult.rows || queryResult.rows.length === 0) {
            container.innerHTML = '<div class="alert alert-info">No data available for visualization</div>';
            return;
        }
        
        // Create visualization container
        const visualizationContainer = document.createElement('div');
        visualizationContainer.className = 'visualization-container mt-4';
        
        // Determine what kind of visualizations would be appropriate
        const columns = Object.keys(queryResult.rows[0]);
        const numericColumns = columns.filter(col => 
            !col.toLowerCase().includes('id') && 
            typeof queryResult.rows[0][col] === 'number'
        );
        
        const dateColumns = columns.filter(col => 
            (col.toLowerCase().includes('date') || col.toLowerCase().includes('time')) &&
            typeof queryResult.rows[0][col] === 'string'
        );
        
        const categoryColumns = columns.filter(col => 
            typeof queryResult.rows[0][col] === 'string' && 
            !dateColumns.includes(col)
        );
        
        // Create visualizations based on available column types
        
        // 1. Bar chart for a numeric column grouped by a category
        if (numericColumns.length > 0 && categoryColumns.length > 0) {
            // Choose the first numeric and category columns
            const numericColumn = numericColumns[0];
            const categoryColumn = categoryColumns[0];
            
            // Group data by the category
            const groupedData = {};
            queryResult.rows.forEach(row => {
                const category = row[categoryColumn] || 'Unknown';
                if (!groupedData[category]) {
                    groupedData[category] = 0;
                }
                groupedData[category] += row[numericColumn] || 0;
            });
            
            // Prepare data for chart
            const labels = Object.keys(groupedData);
            const data = Object.values(groupedData);
            
            // Create chart container
            const chartContainer = document.createElement('div');
            chartContainer.className = 'chart-container';
            chartContainer.style.height = '300px';
            chartContainer.style.marginBottom = '2rem';
            
            // Create canvas
            const canvas = document.createElement('canvas');
            canvas.id = 'bar-chart';
            chartContainer.appendChild(canvas);
            
            // Add to visualization container
            visualizationContainer.appendChild(chartContainer);
            
            // Once the DOM is updated, create the chart
            setTimeout(() => {
                createBarChart(
                    'bar-chart',
                    labels,
                    data,
                    `${formatColumnName(numericColumn)} by ${formatColumnName(categoryColumn)}`
                );
            }, 0);
        }
        
        // 2. Line chart for a numeric column over time
        if (numericColumns.length > 0 && dateColumns.length > 0) {
            // Choose the first numeric and date columns
            const numericColumn = numericColumns[0];
            const dateColumn = dateColumns[0];
            
            // Sort data by date
            const sortedData = [...queryResult.rows].sort((a, b) => 
                new Date(a[dateColumn]) - new Date(b[dateColumn])
            );
            
            // Prepare data for chart
            const labels = sortedData.map(row => 
                new Date(row[dateColumn]).toLocaleDateString()
            );
            const data = sortedData.map(row => row[numericColumn]);
            
            // Create chart container
            const chartContainer = document.createElement('div');
            chartContainer.className = 'chart-container';
            chartContainer.style.height = '300px';
            chartContainer.style.marginBottom = '2rem';
            
            // Create canvas
            const canvas = document.createElement('canvas');
            canvas.id = 'line-chart';
            chartContainer.appendChild(canvas);
            
            // Add to visualization container
            visualizationContainer.appendChild(chartContainer);
            
            // Once the DOM is updated, create the chart
            setTimeout(() => {
                createLineChart(
                    'line-chart',
                    labels,
                    data,
                    `${formatColumnName(numericColumn)} over time`
                );
            }, 0);
        }
        
        // 3. Pie chart for distribution of a category
        if (categoryColumns.length > 0) {
            // Choose the first category column
            const categoryColumn = categoryColumns[0];
            
            // Count occurrences of each category
            const categoryCounts = {};
            queryResult.rows.forEach(row => {
                const category = row[categoryColumn] || 'Unknown';
                if (!categoryCounts[category]) {
                    categoryCounts[category] = 0;
                }
                categoryCounts[category]++;
            });
            
            // Prepare data for chart
            const labels = Object.keys(categoryCounts);
            const data = Object.values(categoryCounts);
            
            // Create chart container
            const chartContainer = document.createElement('div');
            chartContainer.className = 'chart-container';
            chartContainer.style.height = '300px';
            chartContainer.style.marginBottom = '2rem';
            
            // Create canvas
            const canvas = document.createElement('canvas');
            canvas.id = 'pie-chart';
            chartContainer.appendChild(canvas);
            
            // Add to visualization container
            visualizationContainer.appendChild(chartContainer);
            
            // Once the DOM is updated, create the chart
            setTimeout(() => {
                createPieChart(
                    'pie-chart',
                    labels,
                    data,
                    `Distribution of ${formatColumnName(categoryColumn)}`
                );
            }, 0);
        }
        
        // Add to the container
        container.appendChild(visualizationContainer);
    }
    
    // Return public API
    return {
        createBarChart,
        createPieChart,
        createLineChart,
        createDataTable,
        visualizeQueryResults
    };
})();