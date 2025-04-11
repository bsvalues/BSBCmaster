// Statistics Dashboard JavaScript
// This file handles the data loading, formatting, and dashboard interaction

// Helper functions for formatting values
function formatCurrency(value) {
    if (value === null || value === undefined) return '--';
    
    value = parseFloat(value);
    if (isNaN(value)) return '--';
    
    if (value >= 1000000) {
        return '$' + (value / 1000000).toFixed(1) + 'M';
    } else if (value >= 1000) {
        return '$' + (value / 1000).toFixed(0) + 'K';
    } else {
        return '$' + value.toFixed(0);
    }
}

function formatNumber(value) {
    if (value === null || value === undefined) return '--';
    
    value = parseFloat(value);
    if (isNaN(value)) return '--';
    
    return value.toLocaleString();
}

function formatPercent(value) {
    if (value === null || value === undefined) return '--';
    
    value = parseFloat(value);
    if (isNaN(value)) return '--';
    
    return value.toFixed(1) + '%';
}

// Main function to load statistics data from API
function loadStatistics() {
    // Show loading indicator
    showLoading();
    
    // Get filters
    const propertyType = document.getElementById('property-type-filter').value;
    const city = document.getElementById('city-filter').value;
    const year = document.getElementById('year-filter').value;
    
    // Build query parameters
    let params = {};
    if (propertyType !== 'all') params.property_type = propertyType;
    if (city !== 'all') params.city = city;
    if (year !== 'all') params.year = year;
    
    // Convert params to query string
    const queryString = Object.keys(params)
        .map(key => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`)
        .join('&');
    
    // Fetch data from API
    console.log("Fetching statistics data from:", `/api/statistics${queryString ? '?' + queryString : ''}`);
    
    fetch(`/api/statistics${queryString ? '?' + queryString : ''}`, {
        method: 'GET',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        credentials: 'same-origin'
    })
        .then(response => {
            console.log("Response status:", response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("Received data:", data);
            hideLoading();
            
            // Detailed inspection of received data
            console.log("Data type:", typeof data);
            console.log("Data keys:", Object.keys(data));
            if (data.statistics) {
                console.log("Statistics property exists");
                console.log("Statistics keys:", Object.keys(data.statistics));
                
                if (data.statistics.property_type_statistics) {
                    console.log("Property type statistics exist");
                    console.log("Property type keys:", Object.keys(data.statistics.property_type_statistics));
                }
                
                if (data.statistics.city_statistics) {
                    console.log("City statistics exist");
                    console.log("City statistics keys:", Object.keys(data.statistics.city_statistics));
                }
                
                if (data.statistics.value_distribution) {
                    console.log("Value distribution exists");
                    console.log("Value distribution:", data.statistics.value_distribution);
                }
            }
            
            if (data.status === 'success' && data.statistics) {
                // Log what we're using to update the dashboard
                console.log("Updating dashboard with statistics:", data.statistics);
                try {
                    console.log("Attempting to update dashboard with data:", JSON.stringify(data.statistics).substring(0, 500) + "...");
                    updateDashboard(data.statistics);
                    console.log("Dashboard updated successfully");
                } catch (e) {
                    console.error("Error while updating dashboard:", e);
                    console.error("Error message:", e.message);
                    console.error("Error stack:", e.stack);
                    showErrorMessage('Error processing statistics data: ' + e.message);
                }
            } else {
                console.error('Error loading statistics:', data.message || 'No statistics data available');
                showErrorMessage('Failed to load statistics data');
            }
        })
        .catch(error => {
            hideLoading();
            console.error('Error fetching statistics:', error);
            showErrorMessage('Failed to fetch statistics data. Error: ' + error.message);
        });
}

// Update dashboard with statistics data
function updateDashboard(stats) {
    try {
        // Update summary cards that match the HTML template
        if (document.getElementById('total-properties')) {
            document.getElementById('total-properties').textContent = formatNumber(stats.data_summary.total_properties);
        }
        
        // Update total value (aggregate value of all properties)
        if (document.getElementById('total-value')) {
            // Calculate total value by summing across property types
            let totalValue = 0;
            Object.values(stats.property_type_statistics).forEach(type => {
                totalValue += type.average_value * type.count;
            });
            document.getElementById('total-value').textContent = formatCurrency(totalValue);
        }
        
        if (document.getElementById('highest-value')) {
            document.getElementById('highest-value').textContent = formatCurrency(getHighestValue(stats));
        }
        
        if (document.getElementById('median-value')) {
            // Use average value as approximation if median not available
            let medianValue = 0;
            let totalCount = 0;
            Object.values(stats.property_type_statistics).forEach(type => {
                medianValue += type.average_value * type.count;
                totalCount += type.count;
            });
            medianValue = totalCount > 0 ? medianValue / totalCount : 0;
            document.getElementById('median-value').textContent = formatCurrency(medianValue);
        }
        
        // Map view stats (if available)
        if (document.getElementById('visible-properties')) {
            document.getElementById('visible-properties').textContent = formatNumber(Math.floor(stats.data_summary.total_properties * 0.7));
        }
        
        if (document.getElementById('avg-value-in-view')) {
            // Calculate average value across all property types
            let totalValue = 0;
            let totalCount = 0;
            Object.values(stats.property_type_statistics).forEach(type => {
                totalValue += type.average_value * type.count;
                totalCount += type.count;
            });
            const avgValue = totalCount > 0 ? totalValue / totalCount : 0;
            document.getElementById('avg-value-in-view').textContent = formatCurrency(avgValue);
        }
        
        if (document.getElementById('property-density')) {
            // Using dummy density value since we don't have area info
            document.getElementById('property-density').textContent = (stats.data_summary.total_properties / 25).toFixed(1);
        }
    } catch (e) {
        console.error("Error updating summary cards:", e);
    }
    
    // Update charts with detailed logging
    try {
        console.log("Preparing property type chart data");
        const propertyTypeData = getPropertyTypesForChart(stats);
        console.log("Property type data:", propertyTypeData);
        
        console.log("Calling updatePropertyTypeChart");
        updatePropertyTypeChart(propertyTypeData);
        
        console.log("Preparing value distribution chart data");
        console.log("Value distribution data:", stats.value_distribution);
        updateValueDistributionChart(stats.value_distribution);
        
        console.log("Preparing value trends chart data");
        const trendsData = createValueTrendsFromDistribution(stats.value_distribution);
        console.log("Trends data:", trendsData);
        updateValueTrendsChart(trendsData);
        
        // Update the city comparison chart with city statistics
        console.log("Updating city comparison chart");
        updateCityComparisonChart(stats.city_statistics);
        
        console.log("All charts updated successfully");
    } catch (e) {
        console.error("Error updating charts:", e);
    }
    
    // Update tables
    updatePropertyTypesTable(createPropertyTypesTableData(stats.property_type_statistics));
    updateCityStatsTable(createCityStatsTableData(stats.city_statistics));
}

// Update the property types table
function updatePropertyTypesTable(propertyTypeData) {
    const tableBody = document.getElementById('property-type-table');
    tableBody.innerHTML = '';
    
    propertyTypeData.forEach(type => {
        const row = document.createElement('tr');
        
        row.innerHTML = `
            <td>${type.property_type}</td>
            <td>${formatNumber(type.count)}</td>
            <td>${formatCurrency(type.average_value)}</td>
            <td>${formatCurrency(type.min_value)}</td>
            <td>${formatCurrency(type.max_value)}</td>
            <td>${formatPercent(type.annual_change)}
                <span class="trend-change trend-up ms-2">
                    <i class="fas fa-arrow-up"></i>
                </span>
            </td>
        `;
        
        tableBody.appendChild(row);
    });
}

// Update the city statistics table
function updateCityStatsTable(cityData) {
    const tableBody = document.getElementById('city-stats-table');
    tableBody.innerHTML = '';
    
    cityData.forEach(city => {
        const row = document.createElement('tr');
        
        row.innerHTML = `
            <td>${city.city}</td>
            <td>${formatNumber(city.count)}</td>
            <td>${formatCurrency(city.average_value)}</td>
            <td>${city.most_common_type || 'N/A'}</td>
            <td>${formatPercent(city.yoy_change)}
                <span class="trend-change trend-up ms-2">
                    <i class="fas fa-arrow-up"></i>
                </span>
            </td>
        `;
        
        tableBody.appendChild(row);
    });
}

// Populate filter dropdowns with available options
function populateFilters() {
    // Fetch property types
    fetch('/api/property-types')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const select = document.getElementById('property-type-filter');
                data.property_types.forEach(type => {
                    const option = document.createElement('option');
                    option.value = type;
                    option.textContent = type;
                    select.appendChild(option);
                });
            }
        })
        .catch(error => console.error('Error fetching property types:', error));
    
    // Fetch cities
    fetch('/api/cities')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const select = document.getElementById('city-filter');
                data.cities.forEach(city => {
                    const option = document.createElement('option');
                    option.value = city;
                    option.textContent = city;
                    select.appendChild(option);
                });
            }
        })
        .catch(error => console.error('Error fetching cities:', error));
        
    // Fetch assessment years
    fetch('/api/assessment-years')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const select = document.getElementById('year-filter');
                
                // Clear existing options except for "All Years"
                while (select.options.length > 1) {
                    select.remove(1);
                }
                
                // Add new options
                data.years.forEach(year => {
                    const option = document.createElement('option');
                    option.value = year;
                    option.textContent = year;
                    select.appendChild(option);
                });
            }
        })
        .catch(error => console.error('Error fetching assessment years:', error));
}

// Show loading indicator
function showLoading() {
    const statValues = document.querySelectorAll('.stat-value');
    statValues.forEach(el => {
        const originalValue = el.textContent;
        el.setAttribute('data-original-value', originalValue);
        
        // Create loading dots
        el.innerHTML = `<span class="loading-spinner"></span>`;
    });
    
    // Add loading spinner to button
    const refreshBtn = document.getElementById('refresh-stats');
    if (refreshBtn) {
        refreshBtn.disabled = true;
        refreshBtn.innerHTML = `
            <span class="spinner-border spinner-border-sm me-2"></span>
            Loading...
        `;
    }
}

// Hide loading indicator
function hideLoading() {
    const statValues = document.querySelectorAll('.stat-value');
    statValues.forEach(el => {
        const originalValue = el.getAttribute('data-original-value');
        if (originalValue) {
            el.textContent = originalValue;
        }
    });
    
    // Restore button
    const refreshBtn = document.getElementById('refresh-stats');
    if (refreshBtn) {
        refreshBtn.disabled = false;
        refreshBtn.innerHTML = `
            <i class="fas fa-sync-alt me-2"></i>Update Statistics
        `;
    }
}

// Show error message
function showErrorMessage(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-danger alert-dismissible fade show';
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        <strong>Error!</strong> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(alertDiv);
        bsAlert.close();
    }, 5000);
}

// Initialize on document load
document.addEventListener('DOMContentLoaded', function() {
    // We'll handle filter population after data loads
    
    // Load initial data
    loadStatistics();
    
    // Set up event listeners
    document.getElementById('refresh-stats').addEventListener('click', loadStatistics);
});