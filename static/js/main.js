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