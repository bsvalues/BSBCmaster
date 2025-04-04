/**
 * MCP Assessor Agent API - Frontend JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // Check API health on page load
    updateDatabaseStatus();
    
    // Set up refresh button listener
    const refreshButton = document.getElementById('refresh-status');
    if (refreshButton) {
        refreshButton.addEventListener('click', updateDatabaseStatus);
    }
    
    // Load API documentation if available
    loadApiDocumentation();
    
    // Set up periodic health checks
    setInterval(updateDatabaseStatus, 30000); // Every 30 seconds
});

/**
 * Update the API and database status indicators
 */
function updateDatabaseStatus() {
    fetch('/api/health')
        .then(response => response.json())
        .then(data => {
            // Update overall status
            const statusBadge = document.getElementById('status-badge');
            if (data.status === 'ok') {
                statusBadge.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i>Healthy';
                statusBadge.className = 'badge bg-success';
            } else {
                statusBadge.innerHTML = '<i class="bi bi-x-circle-fill me-1"></i>Unhealthy';
                statusBadge.className = 'badge bg-danger';
            }
            
            // Update database connection statuses
            const postgresStatus = document.getElementById('postgres-status');
            if (data.db_connections.postgres) {
                postgresStatus.innerHTML = '<i class="bi bi-database-check me-1"></i>Connected';
                postgresStatus.className = 'badge bg-success';
            } else {
                postgresStatus.innerHTML = '<i class="bi bi-database-x me-1"></i>Disconnected';
                postgresStatus.className = 'badge bg-danger';
            }
            
            const mssqlStatus = document.getElementById('mssql-status');
            if (data.db_connections.mssql) {
                mssqlStatus.innerHTML = '<i class="bi bi-database-check me-1"></i>Connected';
                mssqlStatus.className = 'badge bg-success';
            } else {
                mssqlStatus.innerHTML = '<i class="bi bi-database-x me-1"></i>Disconnected';
                mssqlStatus.className = 'badge bg-warning';
                // MSSQL is optional in this application, so use warning instead of danger
            }
        })
        .catch(error => {
            console.error('Error checking API health:', error);
            const statusBadge = document.getElementById('status-badge');
            if (statusBadge) {
                statusBadge.innerHTML = '<i class="bi bi-exclamation-triangle-fill me-1"></i>Error';
                statusBadge.className = 'badge bg-danger';
            }
            
            const postgresStatus = document.getElementById('postgres-status');
            if (postgresStatus) {
                postgresStatus.innerHTML = '<i class="bi bi-question-circle-fill me-1"></i>Unknown';
                postgresStatus.className = 'badge bg-secondary';
            }
            
            const mssqlStatus = document.getElementById('mssql-status');
            if (mssqlStatus) {
                mssqlStatus.innerHTML = '<i class="bi bi-question-circle-fill me-1"></i>Unknown';
                mssqlStatus.className = 'badge bg-secondary';
            }
        });
}

/**
 * Load API documentation from the /api/docs endpoint
 */
function loadApiDocumentation() {
    fetch('/api/docs')
        .then(response => response.json())
        .then(data => {
            // Update version
            const versionBadge = document.querySelector('.badge.bg-secondary');
            if (versionBadge && data.version) {
                versionBadge.textContent = 'v' + data.version;
            }
            
            // Update description
            const descElement = document.querySelector('p.lead.text-muted');
            if (descElement && data.description) {
                descElement.textContent = data.description;
            }
            
            // If there are endpoints defined in the documentation
            if (data.endpoints && Array.isArray(data.endpoints)) {
                console.log('Found ' + data.endpoints.length + ' API endpoints in documentation');
                
                // Update auth header name if provided
                if (data.authentication && data.authentication.header) {
                    const authHeaderElements = document.querySelectorAll('code:contains("' + data.authentication.header + '")');
                    authHeaderElements.forEach(element => {
                        // No need to update as we're already passing this from Flask
                    });
                }
                
                // Add authenticated badges to endpoints
                data.endpoints.forEach(endpoint => {
                    if (endpoint.auth_required) {
                        // No need to update as we're already setting this in the template
                    }
                });
            }
            
            // Update database status if provided
            if (data.db_connections) {
                updateDatabaseStatusFromData(data);
            }
        })
        .catch(error => {
            console.error('Error loading API documentation:', error);
        });
}

/**
 * Helper function to update database status from API data
 */
function updateDatabaseStatusFromData(data) {
    // Only update if the health data is available
    if (data.status && data.db_connections) {
        // Update overall status
        const statusBadge = document.getElementById('status-badge');
        if (statusBadge) {
            if (data.status === 'ok') {
                statusBadge.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i>Healthy';
                statusBadge.className = 'badge bg-success';
            } else {
                statusBadge.innerHTML = '<i class="bi bi-x-circle-fill me-1"></i>Unhealthy';
                statusBadge.className = 'badge bg-danger';
            }
        }
        
        // Update database connection statuses
        const postgresStatus = document.getElementById('postgres-status');
        if (postgresStatus && data.db_connections.postgres !== undefined) {
            if (data.db_connections.postgres) {
                postgresStatus.innerHTML = '<i class="bi bi-database-check me-1"></i>Connected';
                postgresStatus.className = 'badge bg-success';
            } else {
                postgresStatus.innerHTML = '<i class="bi bi-database-x me-1"></i>Disconnected';
                postgresStatus.className = 'badge bg-danger';
            }
        }
        
        const mssqlStatus = document.getElementById('mssql-status');
        if (mssqlStatus && data.db_connections.mssql !== undefined) {
            if (data.db_connections.mssql) {
                mssqlStatus.innerHTML = '<i class="bi bi-database-check me-1"></i>Connected';
                mssqlStatus.className = 'badge bg-success';
            } else {
                mssqlStatus.innerHTML = '<i class="bi bi-database-x me-1"></i>Disconnected';
                mssqlStatus.className = 'badge bg-warning';
            }
        }
    }
}

/**
 * Initialize tabs and pills for code examples
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tabs and pills
    const codeExampleTabs = document.querySelectorAll('[data-bs-toggle="tab"], [data-bs-toggle="pill"]');
    codeExampleTabs.forEach(tab => {
        tab.addEventListener('shown.bs.tab', function (event) {
            console.log('Tab activated:', event.target.id);
        });
        
        // Create Bootstrap tab objects
        if (typeof bootstrap !== 'undefined') {
            new bootstrap.Tab(tab);
        }
    });
    
    // Syntax highlighting (if we add a library later)
    const codeBlocks = document.querySelectorAll('pre code');
    if (codeBlocks.length > 0) {
        console.log(`Found ${codeBlocks.length} code blocks for syntax highlighting`);
        // If we add a syntax highlighting library later, initialize it here
    }
    
    // Initialize the database schema viewer
    loadDatabaseSchema();
    
    // Set up refresh schema button
    const refreshSchemaButton = document.getElementById('refresh-schema');
    if (refreshSchemaButton) {
        refreshSchemaButton.addEventListener('click', loadDatabaseSchema);
    }
});

/**
 * Load database schema information and populate the schema viewer
 */
function loadDatabaseSchema() {
    const tableListContainer = document.getElementById('schema-table-list');
    const tableDetailsContainer = document.getElementById('table-details');
    
    if (!tableListContainer || !tableDetailsContainer) return;
    
    // Show loading spinner
    tableListContainer.innerHTML = `
        <div class="d-flex justify-content-center p-3">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>
    `;
    
    // Reset table details
    tableDetailsContainer.innerHTML = `
        <div class="text-center text-muted">
            <i class="bi bi-arrow-left-circle fs-4"></i>
            <p>Select a table to view its structure</p>
        </div>
    `;
    
    // Fetch schema summary from API (this is a public endpoint for demonstration)
    fetch('/api/schema-summary?db=postgres')
        .then(response => {
            if (!response.ok) {
                if (response.status === 401 || response.status === 403) {
                    throw new Error('Authentication required. Please provide a valid API key.');
                }
                throw new Error('Failed to load schema information');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success' && data.summary && Array.isArray(data.summary)) {
                // Clear loading spinner
                tableListContainer.innerHTML = '';
                
                // Sort tables alphabetically
                const sortedTables = [...data.summary].sort();
                
                // Create table list
                sortedTables.forEach(tableName => {
                    const tableItem = document.createElement('a');
                    tableItem.href = '#';
                    tableItem.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
                    tableItem.innerHTML = `
                        <span>
                            <i class="bi bi-table me-2"></i>
                            ${tableName}
                        </span>
                        <i class="bi bi-chevron-right"></i>
                    `;
                    
                    tableItem.addEventListener('click', (e) => {
                        e.preventDefault();
                        loadTableDetails(tableName);
                        
                        // Update active state
                        document.querySelectorAll('#schema-table-list .list-group-item').forEach(item => {
                            item.classList.remove('active');
                        });
                        tableItem.classList.add('active');
                    });
                    
                    tableListContainer.appendChild(tableItem);
                });
                
                // Display message if no tables found
                if (sortedTables.length === 0) {
                    tableListContainer.innerHTML = `
                        <div class="text-center text-muted p-3">
                            <i class="bi bi-exclamation-circle fs-4"></i>
                            <p>No tables found in the database</p>
                        </div>
                    `;
                }
            } else {
                throw new Error('Invalid schema data received');
            }
        })
        .catch(error => {
            tableListContainer.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    ${error.message}
                </div>
                <div class="text-center mt-3">
                    <button id="retry-schema" class="btn btn-sm btn-outline-primary">
                        <i class="bi bi-arrow-repeat me-1"></i>
                        Retry
                    </button>
                </div>
            `;
            
            // Add retry button listener
            const retryButton = document.getElementById('retry-schema');
            if (retryButton) {
                retryButton.addEventListener('click', loadDatabaseSchema);
            }
        });
}

/**
 * Load detailed information about a specific table
 */
function loadTableDetails(tableName) {
    const tableDetailsContainer = document.getElementById('table-details');
    if (!tableDetailsContainer) return;
    
    // Show loading state
    tableDetailsContainer.innerHTML = `
        <div class="d-flex justify-content-center p-3">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <span class="ms-2">Loading table structure...</span>
        </div>
    `;
    
    // Fetch detailed schema information for the selected table
    fetch('/api/discover-schema?db=postgres')
        .then(response => {
            if (!response.ok) {
                if (response.status === 401 || response.status === 403) {
                    throw new Error('Authentication required. Please provide a valid API key.');
                }
                throw new Error('Failed to load table details');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success' && data.db_schema && Array.isArray(data.db_schema)) {
                // Filter schema items for the selected table
                const tableColumns = data.db_schema.filter(item => item.table_name === tableName);
                
                if (tableColumns.length > 0) {
                    // Sort columns by name
                    tableColumns.sort((a, b) => a.column_name.localeCompare(b.column_name));
                    
                    // Build table details HTML
                    let detailsHtml = `
                        <h5 class="mb-3">
                            <i class="bi bi-table me-2"></i>
                            ${tableName}
                        </h5>
                        <div class="table-responsive">
                            <table class="table table-sm table-striped">
                                <thead>
                                    <tr>
                                        <th>Column</th>
                                        <th>Type</th>
                                    </tr>
                                </thead>
                                <tbody>
                    `;
                    
                    tableColumns.forEach(column => {
                        detailsHtml += `
                            <tr>
                                <td>${column.column_name}</td>
                                <td><code>${column.data_type}</code></td>
                            </tr>
                        `;
                    });
                    
                    detailsHtml += `
                                </tbody>
                            </table>
                        </div>
                        <div class="mt-3">
                            <div class="alert alert-secondary">
                                <strong>Example query:</strong>
                                <pre class="mb-0"><code>SELECT * FROM ${tableName} LIMIT 10;</code></pre>
                            </div>
                        </div>
                    `;
                    
                    tableDetailsContainer.innerHTML = detailsHtml;
                } else {
                    tableDetailsContainer.innerHTML = `
                        <div class="alert alert-warning">
                            <i class="bi bi-exclamation-circle me-2"></i>
                            No columns found for table "${tableName}"
                        </div>
                    `;
                }
            } else {
                throw new Error('Invalid schema data received');
            }
        })
        .catch(error => {
            tableDetailsContainer.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    ${error.message}
                </div>
            `;
        });
}