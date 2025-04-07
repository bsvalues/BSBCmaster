// Helper functions to extract data from the API response
function getMostExpensivePropertyValue(stats) {
    // Find the property type with highest average value
    let highestAvg = 0;
    Object.values(stats.property_type_statistics).forEach(type => {
        if (type.average_value > highestAvg) {
            highestAvg = type.average_value;
        }
    });
    return highestAvg;
}

function getHighestValue(stats) {
    // Find the highest property value across all types
    let highest = 0;
    Object.values(stats.property_type_statistics).forEach(type => {
        if (type.max_value > highest) {
            highest = type.max_value;
        }
    });
    return highest;
}

function getHighestValuePropertyType(stats) {
    // Find which property type has the highest value property
    let highest = 0;
    let highestType = '';
    Object.entries(stats.property_type_statistics).forEach(([type, data]) => {
        if (data.max_value > highest) {
            highest = data.max_value;
            highestType = type;
        }
    });
    return highestType;
}

function getMostCommonPropertyType(stats) {
    // Find the most common property type by count
    let highestCount = 0;
    let commonType = '';
    Object.entries(stats.property_type_statistics).forEach(([type, data]) => {
        if (data.count > highestCount) {
            highestCount = data.count;
            commonType = type;
        }
    });
    return commonType;
}

function getMostCommonPropertyTypeCount(stats) {
    // Get the count of the most common property type
    let highestCount = 0;
    Object.values(stats.property_type_statistics).forEach(data => {
        if (data.count > highestCount) {
            highestCount = data.count;
        }
    });
    return highestCount;
}

function getPropertyTypesForChart(stats) {
    // Convert property type statistics to format needed for chart
    return Object.entries(stats.property_type_statistics).map(([type, data]) => {
        return {
            property_type: type,
            count: data.count,
            average_value: data.average_value
        };
    });
}

function createValueTrendsFromDistribution(distribution) {
    // Create synthetic trend data since we don't have year-over-year data
    // This is just for display purposes
    const currentYear = new Date().getFullYear();
    return {
        labels: [currentYear-2, currentYear-1, currentYear],
        datasets: Object.keys(distribution).map((range, i) => {
            // Create a somewhat realistic trend for each value range
            const baseValue = distribution[range];
            const growth = 0.05 + (Math.random() * 0.1); // 5-15% growth
            
            return {
                label: range,
                data: [
                    Math.round(baseValue / (1 + growth*2)),
                    Math.round(baseValue / (1 + growth)),
                    baseValue
                ]
            };
        })
    };
}

function createPropertyTypesTableData(propertyTypeStats) {
    // Convert property statistics to table format
    return Object.entries(propertyTypeStats).map(([type, data]) => {
        return {
            property_type: type,
            count: data.count,
            average_value: data.average_value,
            min_value: data.min_value,
            max_value: data.max_value,
            annual_change: 3.5 + (Math.random() * 5) // Random 3.5-8.5% for demo
        };
    });
}

function createCityStatsTableData(cityStats) {
    // Convert city statistics to table format
    return Object.entries(cityStats).map(([city, data]) => {
        // Find most common property type in this city
        let mostCommonType = '';
        let highestCount = 0;
        
        Object.entries(data.property_types || {}).forEach(([type, count]) => {
            if (count > highestCount) {
                highestCount = count;
                mostCommonType = type;
            }
        });
        
        return {
            city: city,
            count: data.count,
            average_value: data.average_value,
            most_common_type: mostCommonType,
            yoy_change: 2.8 + (Math.random() * 4) // Random 2.8-6.8% for demo
        };
    });
}
