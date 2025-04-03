/**
 * MCP Assessor Agent API - Frontend JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // Check API health on page load
    updateDatabaseStatus();
    
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
            const statusBadge = document.getElementById('status-badge');
            statusBadge.textContent = 'Error';
            statusBadge.className = 'badge bg-danger';
            
            const dbStatuses = document.querySelectorAll('#db-status .badge');
            dbStatuses.forEach(badge => {
                badge.textContent = 'Unknown';
                badge.className = 'badge bg-secondary';
            });
        });
}