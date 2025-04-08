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
    fetch(`/api/statistics${queryString ? '?' + queryString : ''}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            hideLoading();
            if (data.status === 'success') {
                updateDashboard(data.statistics);
            } else {
                console.error('Error loading statistics:', data.message);
                showErrorMessage('Failed to load statistics data');
            }
        })
        .catch(error => {
            hideLoading();
            console.error('Error fetching statistics:', error);
            showErrorMessage('Failed to fetch statistics data');
        });
}

// Update dashboard with statistics data
function updateDashboard(stats) {
    // Update summary cards
    document.getElementById('total-properties').textContent = formatNumber(stats.data_summary.total_properties);
    document.getElementById('avg-value').textContent = formatCurrency(stats.property_type_statistics.Residential?.average_value || 0);
    document.getElementById('highest-value').textContent = formatCurrency(getHighestValue(stats));
    
    // Update property type info
    const mostCommonType = getMostCommonPropertyType(stats);
    document.getElementById('common-type').textContent = mostCommonType || 'N/A';
    document.getElementById('common-type-count').textContent = `${formatNumber(getMostCommonPropertyTypeCount(stats))} properties`;
    
    // Update highest value property type
    const highestPropertyType = getHighestValuePropertyType(stats);
    document.getElementById('highest-property-type').textContent = highestPropertyType || 'N/A';
    
    // Update charts
    const propertyTypeData = getPropertyTypesForChart(stats);
    updatePropertyTypeChart(propertyTypeData);
    updateValueDistributionChart(stats.value_distribution);
    updateValueTrendsChart(createValueTrendsFromDistribution(stats.value_distribution));
    
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
    // Populate filters
    populateFilters();
    
    // Load initial data
    loadStatistics();
    
    // Set up event listeners
    document.getElementById('refresh-stats').addEventListener('click', loadStatistics);
});