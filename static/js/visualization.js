/**
 * MCP Assessor Agent API - Data Visualization Library
 * 
 * This library provides visualization capabilities for the MCP Assessor Agent API,
 * including data tables, charts, and interactive visualizations.
 */

const MCPVisualization = {
    /**
     * Creates a paginated data table for query results
     * @param {string} containerId - ID of the container element
     * @param {object} data - Query result data (rows, columns, metadata)
     * @param {object} options - Additional options like pagination handlers
     */
    createDataTable: function(containerId, data, options = {}) {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`Container with ID ${containerId} not found`);
            return;
        }
        
        // Clear container
        container.innerHTML = '';
        
        // Extract data
        const { rows, columns, metadata } = data;
        
        if (!rows || !columns || rows.length === 0) {
            container.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    No data available for this query.
                </div>
            `;
            return;
        }
        
        // Create table
        const table = document.createElement('table');
        table.className = 'table table-striped table-hover';
        
        // Create table header
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        
        columns.forEach(column => {
            const th = document.createElement('th');
            th.scope = 'col';
            th.textContent = column;
            headerRow.appendChild(th);
        });
        
        thead.appendChild(headerRow);
        table.appendChild(thead);
        
        // Create table body
        const tbody = document.createElement('tbody');
        
        rows.forEach(row => {
            const tr = document.createElement('tr');
            
            columns.forEach(column => {
                const td = document.createElement('td');
                td.textContent = row[column] !== null ? row[column] : 'NULL';
                tr.appendChild(td);
            });
            
            tbody.appendChild(tr);
        });
        
        table.appendChild(tbody);
        container.appendChild(table);
        
        // Add pagination if metadata is available
        if (metadata && metadata.total_pages > 1) {
            const pagination = document.createElement('nav');
            pagination.setAttribute('aria-label', 'Query results pagination');
            
            const ul = document.createElement('ul');
            ul.className = 'pagination justify-content-center';
            
            // Previous button
            const prevLi = document.createElement('li');
            prevLi.className = `page-item ${metadata.current_page === 1 ? 'disabled' : ''}`;
            
            const prevLink = document.createElement('a');
            prevLink.className = 'page-link';
            prevLink.href = '#';
            prevLink.setAttribute('aria-label', 'Previous');
            prevLink.innerHTML = '<span aria-hidden="true">&laquo;</span>';
            
            if (metadata.current_page > 1 && options.onPageChange) {
                prevLink.addEventListener('click', e => {
                    e.preventDefault();
                    options.onPageChange(metadata.current_page - 1);
                });
            }
            
            prevLi.appendChild(prevLink);
            ul.appendChild(prevLi);
            
            // Page numbers
            for (let i = 1; i <= metadata.total_pages; i++) {
                const li = document.createElement('li');
                li.className = `page-item ${i === metadata.current_page ? 'active' : ''}`;
                
                const link = document.createElement('a');
                link.className = 'page-link';
                link.href = '#';
                link.textContent = i;
                
                if (i !== metadata.current_page && options.onPageChange) {
                    link.addEventListener('click', e => {
                        e.preventDefault();
                        options.onPageChange(i);
                    });
                }
                
                li.appendChild(link);
                ul.appendChild(li);
            }
            
            // Next button
            const nextLi = document.createElement('li');
            nextLi.className = `page-item ${metadata.current_page === metadata.total_pages ? 'disabled' : ''}`;
            
            const nextLink = document.createElement('a');
            nextLink.className = 'page-link';
            nextLink.href = '#';
            nextLink.setAttribute('aria-label', 'Next');
            nextLink.innerHTML = '<span aria-hidden="true">&raquo;</span>';
            
            if (metadata.current_page < metadata.total_pages && options.onPageChange) {
                nextLink.addEventListener('click', e => {
                    e.preventDefault();
                    options.onPageChange(metadata.current_page + 1);
                });
            }
            
            nextLi.appendChild(nextLink);
            ul.appendChild(nextLi);
            
            pagination.appendChild(ul);
            container.appendChild(pagination);
        }
        
        // Add metadata info
        if (metadata && metadata.execution_time) {
            const metaInfo = document.createElement('div');
            metaInfo.className = 'mt-2 small text-muted';
            metaInfo.innerHTML = `
                <strong>Execution time:</strong> ${metadata.execution_time.toFixed(3)}s 
                | <strong>Rows:</strong> ${metadata.total_rows || rows.length}
                ${metadata.database_type ? ` | <strong>Database:</strong> ${metadata.database_type}` : ''}
            `;
            container.appendChild(metaInfo);
        }
    },
    
    /**
     * Visualize query results with appropriate charts based on data type
     * @param {string} containerId - ID of the container element
     * @param {object} data - Query result data (rows, columns, metadata)
     */
    visualizeQueryResults: function(containerId, data) {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`Container with ID ${containerId} not found`);
            return;
        }
        
        // Clear container
        container.innerHTML = '';
        
        const { rows, columns } = data;
        
        if (!rows || !columns || rows.length === 0) {
            container.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    No data available for visualization.
                </div>
            `;
            return;
        }
        
        // Determine if we can create a visualization
        const numericColumns = columns.filter(col => 
            rows.length > 0 && 
            rows.some(row => typeof row[col] === 'number' || 
                (typeof row[col] === 'string' && !isNaN(parseFloat(row[col]))))
        );
        
        const dateColumns = columns.filter(col => 
            rows.length > 0 && 
            rows.some(row => {
                const val = row[col];
                return val && (val instanceof Date || 
                    (typeof val === 'string' && !isNaN(Date.parse(val))));
            })
        );
        
        const categoricalColumns = columns.filter(col => 
            rows.length > 0 && 
            !numericColumns.includes(col) && 
            !dateColumns.includes(col) && 
            rows.some(row => row[col] !== null && row[col] !== undefined)
        );
        
        // Create visualization header
        const header = document.createElement('h4');
        header.className = 'mb-3';
        header.textContent = 'Data Visualization';
        container.appendChild(header);
        
        // Create charts container
        const chartsContainer = document.createElement('div');
        chartsContainer.className = 'row';
        container.appendChild(chartsContainer);
        
        // Flag to track if we've created any visualizations
        let visualizationsCreated = false;
        
        // Try creating a bar or line chart if we have numeric + categorical/date columns
        if (numericColumns.length > 0 && (categoricalColumns.length > 0 || dateColumns.length > 0)) {
            visualizationsCreated = true;
            
            const chartType = dateColumns.length > 0 ? 'line' : 'bar';
            const xAxisColumn = dateColumns.length > 0 ? dateColumns[0] : categoricalColumns[0];
            
            // Create chart wrapper
            const chartWrapper = document.createElement('div');
            chartWrapper.className = 'col-12 mb-4';
            chartsContainer.appendChild(chartWrapper);
            
            // Create canvas for Chart.js
            const canvas = document.createElement('canvas');
            canvas.id = `chart-${containerId}`;
            chartWrapper.appendChild(canvas);
            
            // Prepare data for Chart.js
            const chartData = {
                labels: rows.map(row => row[xAxisColumn]),
                datasets: numericColumns.slice(0, 3).map((column, index) => {
                    const colors = ['rgba(75, 192, 192, 0.6)', 'rgba(54, 162, 235, 0.6)', 'rgba(255, 205, 86, 0.6)'];
                    return {
                        label: column,
                        data: rows.map(row => {
                            const val = row[column];
                            return typeof val === 'number' ? val : parseFloat(val);
                        }),
                        backgroundColor: colors[index % colors.length],
                        borderColor: colors[index % colors.length].replace('0.6', '1'),
                        borderWidth: 1
                    };
                })
            };
            
            // Create Chart.js chart
            new Chart(canvas, {
                type: chartType,
                data: chartData,
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    },
                    plugins: {
                        title: {
                            display: true,
                            text: `${chartType === 'line' ? 'Trend' : 'Comparison'} of ${numericColumns.slice(0, 3).join(', ')} by ${xAxisColumn}`
                        }
                    }
                }
            });
        }
        
        // Create a pie chart for categorical distribution
        if (categoricalColumns.length > 0 && rows.length >= 3) {
            visualizationsCreated = true;
            
            const column = categoricalColumns[0];
            
            // Count occurrences of each value
            const countMap = {};
            rows.forEach(row => {
                const val = row[column] || 'Unknown';
                countMap[val] = (countMap[val] || 0) + 1;
            });
            
            // Sort by frequency and take top 8
            const sortedData = Object.entries(countMap)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 8);
            
            // Create chart wrapper
            const chartWrapper = document.createElement('div');
            chartWrapper.className = 'col-md-6 mb-4';
            chartsContainer.appendChild(chartWrapper);
            
            // Create canvas for Chart.js
            const canvas = document.createElement('canvas');
            canvas.id = `pie-chart-${containerId}`;
            chartWrapper.appendChild(canvas);
            
            // Prepare data for Chart.js
            const pieColors = [
                'rgba(255, 99, 132, 0.6)',
                'rgba(54, 162, 235, 0.6)',
                'rgba(255, 206, 86, 0.6)',
                'rgba(75, 192, 192, 0.6)',
                'rgba(153, 102, 255, 0.6)',
                'rgba(255, 159, 64, 0.6)',
                'rgba(199, 199, 199, 0.6)',
                'rgba(83, 102, 255, 0.6)'
            ];
            
            const pieData = {
                labels: sortedData.map(item => item[0]),
                datasets: [{
                    data: sortedData.map(item => item[1]),
                    backgroundColor: pieColors,
                    borderColor: pieColors.map(color => color.replace('0.6', '1')),
                    borderWidth: 1
                }]
            };
            
            // Create Chart.js chart
            new Chart(canvas, {
                type: 'pie',
                data: pieData,
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        title: {
                            display: true,
                            text: `Distribution by ${column}`
                        },
                        legend: {
                            position: 'right',
                            labels: {
                                boxWidth: 12
                            }
                        }
                    }
                }
            });
        }
        
        // Add a simple statistics summary for numeric columns
        if (numericColumns.length > 0) {
            visualizationsCreated = true;
            
            const statsContainer = document.createElement('div');
            statsContainer.className = 'col-md-6 mb-4';
            chartsContainer.appendChild(statsContainer);
            
            const statsCard = document.createElement('div');
            statsCard.className = 'card h-100';
            statsContainer.appendChild(statsCard);
            
            const cardHeader = document.createElement('div');
            cardHeader.className = 'card-header';
            cardHeader.textContent = 'Numeric Field Statistics';
            statsCard.appendChild(cardHeader);
            
            const cardBody = document.createElement('div');
            cardBody.className = 'card-body';
            statsCard.appendChild(cardBody);
            
            // Calculate basic statistics for each numeric column
            numericColumns.slice(0, 4).forEach(column => {
                const values = rows.map(row => {
                    const val = row[column];
                    return typeof val === 'number' ? val : parseFloat(val);
                }).filter(val => !isNaN(val));
                
                if (values.length === 0) return;
                
                const min = Math.min(...values);
                const max = Math.max(...values);
                const sum = values.reduce((a, b) => a + b, 0);
                const avg = sum / values.length;
                
                const columnStats = document.createElement('div');
                columnStats.className = 'mb-3';
                columnStats.innerHTML = `
                    <h6>${column}</h6>
                    <div class="row">
                        <div class="col-6 col-sm-3">
                            <small class="text-muted">Min:</small>
                            <div>${min.toLocaleString()}</div>
                        </div>
                        <div class="col-6 col-sm-3">
                            <small class="text-muted">Max:</small>
                            <div>${max.toLocaleString()}</div>
                        </div>
                        <div class="col-6 col-sm-3">
                            <small class="text-muted">Avg:</small>
                            <div>${avg.toLocaleString(undefined, {maximumFractionDigits: 2})}</div>
                        </div>
                        <div class="col-6 col-sm-3">
                            <small class="text-muted">Count:</small>
                            <div>${values.length.toLocaleString()}</div>
                        </div>
                    </div>
                `;
                cardBody.appendChild(columnStats);
            });
        }
        
        // If no visualizations were created, display a message
        if (!visualizationsCreated) {
            container.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    No suitable visualizations could be generated for this data.
                    Try queries with numeric, date, or categorical columns.
                </div>
            `;
        }
    }
};
