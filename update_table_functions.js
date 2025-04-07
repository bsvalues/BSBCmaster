// Function to update the property type table
function updatePropertyTypeTable(propertyTypesData) {
    const tableBody = document.getElementById('property-type-table-body');
    tableBody.innerHTML = '';
    
    // Sort data by count (descending)
    propertyTypesData.sort((a, b) => b.count - a.count);
    
    // Add rows to table
    propertyTypesData.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="px-4 py-3 text-left text-sm font-medium text-gray-700">${item.property_type}</td>
            <td class="px-4 py-3 text-center text-sm text-gray-500">${item.count}</td>
            <td class="px-4 py-3 text-right text-sm text-gray-500">${formatCurrency(item.average_value)}</td>
            <td class="px-4 py-3 text-right text-sm text-gray-500">${formatCurrency(item.min_value)}</td>
            <td class="px-4 py-3 text-right text-sm text-gray-500">${formatCurrency(item.max_value)}</td>
            <td class="px-4 py-3 text-center text-sm">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    <svg class="-ml-0.5 mr-1 h-3 w-3 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18"></path>
                    </svg>
                    ${item.annual_change.toFixed(1)}%
                </span>
            </td>
        `;
        tableBody.appendChild(row);
    });
}

// Function to update the city statistics table
function updateCityStatsTable(cityStatsData) {
    const tableBody = document.getElementById('city-stats-table-body');
    tableBody.innerHTML = '';
    
    // Sort data by count (descending)
    cityStatsData.sort((a, b) => b.count - a.count);
    
    // Add rows to table
    cityStatsData.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="px-4 py-3 text-left text-sm font-medium text-gray-700">${item.city}</td>
            <td class="px-4 py-3 text-center text-sm text-gray-500">${item.count}</td>
            <td class="px-4 py-3 text-right text-sm text-gray-500">${formatCurrency(item.average_value)}</td>
            <td class="px-4 py-3 text-center text-sm text-gray-500">${item.most_common_type}</td>
            <td class="px-4 py-3 text-center text-sm">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    <svg class="-ml-0.5 mr-1 h-3 w-3 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18"></path>
                    </svg>
                    ${item.yoy_change.toFixed(1)}%
                </span>
            </td>
        `;
        tableBody.appendChild(row);
    });
}
