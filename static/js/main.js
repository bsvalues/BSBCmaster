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
            const statusBadge = document.getElementById('api-status');
            if (data.status === 'ok') {
                statusBadge.textContent = 'Healthy';
                statusBadge.className = 'badge bg-success';
            } else {
                statusBadge.textContent = 'Unhealthy';
                statusBadge.className = 'badge bg-danger';
            }
            
            // Update database connection statuses
            const postgresStatus = document.getElementById('postgres-status');
            postgresStatus.textContent = data.db_connections.postgres ? 'Connected' : 'Disconnected';
            postgresStatus.className = 'badge ' + (data.db_connections.postgres ? 'bg-success' : 'bg-danger');
            
            const mssqlStatus = document.getElementById('mssql-status');
            mssqlStatus.textContent = data.db_connections.mssql ? 'Connected' : 'Disconnected';
            mssqlStatus.className = 'badge ' + (data.db_connections.mssql ? 'bg-success' : 'bg-danger');
        })
        .catch(error => {
            console.error('Error checking API health:', error);
            const statusBadge = document.getElementById('api-status');
            if (statusBadge) {
                statusBadge.textContent = 'Error';
                statusBadge.className = 'badge bg-danger';
            }
            
            const postgresStatus = document.getElementById('postgres-status');
            if (postgresStatus) {
                postgresStatus.textContent = 'Unknown';
                postgresStatus.className = 'badge bg-secondary';
            }
            
            const mssqlStatus = document.getElementById('mssql-status');
            if (mssqlStatus) {
                mssqlStatus.textContent = 'Unknown';
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
            const versionBadge = document.querySelector('.badge.bg-info');
            if (versionBadge && data.version) {
                versionBadge.textContent = 'v' + data.version;
            }
            
            // Update description
            const descElement = document.querySelector('p.text-light-emphasis');
            if (descElement && data.description) {
                descElement.textContent = data.description;
            }
            
            // If there are endpoints defined in the documentation
            if (data.endpoints && Array.isArray(data.endpoints)) {
                console.log('Found ' + data.endpoints.length + ' API endpoints in documentation');
            }
        })
        .catch(error => {
            console.error('Error loading API documentation:', error);
        });
}