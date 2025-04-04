/**
 * Initialize data visualization components
 */
function initDataVisualization() {
    // Check if we have the visualization library
    if (typeof MCPVisualization === 'undefined') {
        console.warn('MCPVisualization library not loaded');
        return;
    }
    
    // Set up visualization for query results
    const runSqlBtn = document.getElementById('runSqlBtn');
    if (runSqlBtn) {
        // Replace the original click handler with our enhanced one
        runSqlBtn.addEventListener('click', function() {
            const query = document.getElementById('sqlQuery').value;
            const dbType = document.getElementById('sqlDbType').value;
            const resultContainer = document.getElementById('sqlResult');
            const visualizationContainer = document.getElementById('sqlVisualization');
            
            if (!query) {
                resultContainer.innerHTML = `
                    <div class="alert alert-danger">
                        <strong>Error:</strong> Please enter a SQL query
                    </div>
                `;
                return;
            }
            
            // Show loading indicator
            resultContainer.innerHTML = `
                <div class="d-flex justify-content-center">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <span class="ms-2">Executing query...</span>
                </div>
            `;
            
            if (visualizationContainer) {
                visualizationContainer.innerHTML = '';
            }
            
            // Fetch API key from hidden field or storage
            const API_KEY = 'mcp_assessor_api_default_key_2024_secure_random_token_987654321';
            
            // Call the API
            fetch('/api/run-query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': API_KEY
                },
                body: JSON.stringify({
                    query: query,
                    db_type: dbType,
                    page: 1,
                    page_size: 10
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Query execution failed: ' + response.statusText);
                }
                return response.json();
            })
            .then(data => {
                // Display results as table
                MCPVisualization.createDataTable('sqlResult', data, {
                    onPageChange: (newPage) => {
                        // Fetch data for the new page
                        fetch('/api/run-query', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-API-Key': API_KEY
                            },
                            body: JSON.stringify({
                                query: query,
                                db_type: dbType,
                                page: newPage,
                                page_size: 10
                            })
                        })
                        .then(response => response.json())
                        .then(newData => {
                            // Update the table with new data
                            MCPVisualization.createDataTable('sqlResult', newData, {
                                onPageChange: (newPage) => this.onPageChange(newPage)
                            });
                        })
                        .catch(error => {
                            console.error('Error fetching page data:', error);
                        });
                    }
                });
                
                // Create visualizations if container exists
                if (visualizationContainer && data.rows && data.rows.length > 0) {
                    MCPVisualization.visualizeQueryResults('sqlVisualization', data);
                }
            })
            .catch(error => {
                resultContainer.innerHTML = `
                    <div class="alert alert-danger">
                        <strong>Error:</strong> ${error.message}
                    </div>
                `;
                
                if (visualizationContainer) {
                    visualizationContainer.innerHTML = '';
                }
            });
        });
    }
    
    // Set up visualization for parameterized queries
    const runParamBtn = document.getElementById('runParamBtn');
    if (runParamBtn) {
        runParamBtn.addEventListener('click', function() {
            const query = document.getElementById('paramQuery').value;
            const dbType = document.getElementById('paramDbType').value;
            const paramsStr = document.getElementById('parameters').value;
            const resultContainer = document.getElementById('paramResult');
            const visualizationContainer = document.getElementById('paramVisualization');
            
            if (!query) {
                resultContainer.innerHTML = `
                    <div class="alert alert-danger">
                        <strong>Error:</strong> Please enter a SQL query
                    </div>
                `;
                return;
            }
            
            // Parse parameters from JSON string
            let params;
            try {
                params = JSON.parse(paramsStr);
            } catch (e) {
                resultContainer.innerHTML = `
                    <div class="alert alert-danger">
                        <strong>Error:</strong> Invalid JSON format for parameters
                    </div>
                `;
                return;
            }
            
            // Show loading indicator
            resultContainer.innerHTML = `
                <div class="d-flex justify-content-center">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <span class="ms-2">Executing parameterized query...</span>
                </div>
            `;
            
            if (visualizationContainer) {
                visualizationContainer.innerHTML = '';
            }
            
            // Fetch API key from hidden field or storage
            const API_KEY = 'mcp_assessor_api_default_key_2024_secure_random_token_987654321';
            
            // Call the API
            fetch('/api/parameterized-query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': API_KEY
                },
                body: JSON.stringify({
                    query: query,
                    db_type: dbType,
                    parameters: params,
                    page: 1,
                    page_size: 10
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Query execution failed: ' + response.statusText);
                }
                return response.json();
            })
            .then(data => {
                // Display results as table
                MCPVisualization.createDataTable('paramResult', data);
                
                // Create visualizations if container exists
                if (visualizationContainer && data.rows && data.rows.length > 0) {
                    MCPVisualization.visualizeQueryResults('paramVisualization', data);
                }
            })
            .catch(error => {
                resultContainer.innerHTML = `
                    <div class="alert alert-danger">
                        <strong>Error:</strong> ${error.message}
                    </div>
                `;
                
                if (visualizationContainer) {
                    visualizationContainer.innerHTML = '';
                }
            });
        });
    }
}

// Initialize visualizations when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initDataVisualization();
});
