// Helper functions to extract data from the API response
function getMostExpensivePropertyValue(stats) {
    try {
        // Find the property type with highest average value
        let highestAvg = 0;
        if (stats && stats.property_type_statistics) {
            Object.values(stats.property_type_statistics).forEach(type => {
                if (type.average_value > highestAvg) {
                    highestAvg = type.average_value;
                }
            });
        }
        return highestAvg;
    } catch (e) {
        console.error("Error in getMostExpensivePropertyValue:", e);
        return 0;
    }
}

function getHighestValue(stats) {
    try {
        // Find the highest property value across all types
        let highest = 0;
        if (stats && stats.property_type_statistics) {
            Object.values(stats.property_type_statistics).forEach(type => {
                if (type.max_value > highest) {
                    highest = type.max_value;
                }
            });
        }
        return highest;
    } catch (e) {
        console.error("Error in getHighestValue:", e);
        return 0;
    }
}

function getHighestValuePropertyType(stats) {
    try {
        // Find which property type has the highest value property
        let highest = 0;
        let highestType = '';
        if (stats && stats.property_type_statistics) {
            Object.entries(stats.property_type_statistics).forEach(([type, data]) => {
                if (data.max_value > highest) {
                    highest = data.max_value;
                    highestType = type;
                }
            });
        }
        return highestType;
    } catch (e) {
        console.error("Error in getHighestValuePropertyType:", e);
        return 'N/A';
    }
}

function getMostCommonPropertyType(stats) {
    try {
        // Find the most common property type by count
        let highestCount = 0;
        let commonType = '';
        if (stats && stats.property_type_statistics) {
            Object.entries(stats.property_type_statistics).forEach(([type, data]) => {
                if (data.count > highestCount) {
                    highestCount = data.count;
                    commonType = type;
                }
            });
        }
        return commonType;
    } catch (e) {
        console.error("Error in getMostCommonPropertyType:", e);
        return 'N/A';
    }
}

function getMostCommonPropertyTypeCount(stats) {
    try {
        // Get the count of the most common property type
        let highestCount = 0;
        if (stats && stats.property_type_statistics) {
            Object.values(stats.property_type_statistics).forEach(data => {
                if (data.count > highestCount) {
                    highestCount = data.count;
                }
            });
        }
        return highestCount;
    } catch (e) {
        console.error("Error in getMostCommonPropertyTypeCount:", e);
        return 0;
    }
}

function getPropertyTypesForChart(stats) {
    try {
        // Convert property type statistics to format needed for chart
        if (!stats || !stats.property_type_statistics) {
            console.error("Missing property_type_statistics in data");
            return [];
        }
        
        return Object.entries(stats.property_type_statistics).map(([type, data]) => {
            return {
                property_type: type,
                count: data.count,
                average_value: data.average_value
            };
        });
    } catch (e) {
        console.error("Error in getPropertyTypesForChart:", e);
        return [];
    }
}

function createValueTrendsFromDistribution(distribution) {
    try {
        // Validate input
        if (!distribution || typeof distribution !== 'object') {
            console.error("Invalid value distribution data:", distribution);
            return { labels: [], datasets: [] };
        }
        
        // Create synthetic trend data since we don't have year-over-year data
        // This is just for display purposes
        const currentYear = new Date().getFullYear();
        
        // Generate years array
        const years = [currentYear-2, currentYear-1, currentYear];
        
        // Generate datasets from value distribution ranges
        const datasets = Object.keys(distribution).map((range, i) => {
            // Create a somewhat realistic trend for each value range
            const baseValue = distribution[range] || 0;
            const growth = 0.05 + (Math.random() * 0.1); // 5-15% growth
            
            return {
                label: range,
                data: [
                    Math.round(baseValue / (1 + growth*2)),
                    Math.round(baseValue / (1 + growth)),
                    baseValue
                ]
            };
        });
        
        return {
            labels: years,
            datasets: datasets
        };
    } catch (e) {
        console.error("Error in createValueTrendsFromDistribution:", e);
        return { labels: [], datasets: [] };
    }
}

function createPropertyTypesTableData(propertyTypeStats) {
    try {
        // Convert property statistics to table format
        if (!propertyTypeStats) {
            console.error("Missing propertyTypeStats in data");
            return [];
        }
        
        return Object.entries(propertyTypeStats).map(([type, data]) => {
            return {
                property_type: type,
                count: data.count || 0,
                average_value: data.average_value || 0,
                min_value: data.min_value || 0,
                max_value: data.max_value || 0,
                annual_change: 3.5 + (Math.random() * 5) // Random 3.5-8.5% for demo
            };
        });
    } catch (e) {
        console.error("Error in createPropertyTypesTableData:", e);
        return [];
    }
}

function createCityStatsTableData(cityStats) {
    try {
        // Convert city statistics to table format
        if (!cityStats) {
            console.error("Missing cityStats in data");
            return [];
        }
        
        return Object.entries(cityStats).map(([city, data]) => {
            // Find most common property type in this city
            let mostCommonType = '';
            let highestCount = 0;
            
            if (data.property_types) {
                Object.entries(data.property_types).forEach(([type, count]) => {
                    if (count > highestCount) {
                        highestCount = count;
                        mostCommonType = type;
                    }
                });
            }
            
            return {
                city: city,
                count: data.count || 0,
                average_value: data.average_value || 0,
                most_common_type: mostCommonType,
                yoy_change: 2.8 + (Math.random() * 4) // Random 2.8-6.8% for demo
            };
        });
    } catch (e) {
        console.error("Error in createCityStatsTableData:", e);
        return [];
    }
}