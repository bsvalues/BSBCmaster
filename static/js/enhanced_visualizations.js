/**
 * MCP Assessor Agent API - Enhanced Visualization Library
 * This file provides advanced chart generation capabilities for the query builder
 * and visualization components using Chart.js.
 */

// Initialize namespace
window.enhancedViz = window.enhancedViz || {};

(function(exports) {
    'use strict';

    // Color palettes for different chart types
    const COLOR_PALETTES = {
        default: [
            'rgba(54, 162, 235, 0.7)',  // Blue
            'rgba(255, 99, 132, 0.7)',   // Red
            'rgba(255, 206, 86, 0.7)',   // Yellow
            'rgba(75, 192, 192, 0.7)',   // Green
            'rgba(153, 102, 255, 0.7)',  // Purple
            'rgba(255, 159, 64, 0.7)',   // Orange
            'rgba(199, 199, 199, 0.7)',  // Gray
            'rgba(83, 102, 255, 0.7)',   // Indigo
            'rgba(140, 99, 132, 0.7)',   // Pink
            'rgba(210, 199, 199, 0.7)',  // Light Gray
        ],
        property: [
            'rgba(41, 128, 185, 0.7)',   // Blue
            'rgba(192, 57, 43, 0.7)',    // Red
            'rgba(39, 174, 96, 0.7)',    // Green
            'rgba(142, 68, 173, 0.7)',   // Purple
            'rgba(243, 156, 18, 0.7)',   // Orange
            'rgba(44, 62, 80, 0.7)',     // Dark Blue
            'rgba(127, 140, 141, 0.7)',  // Gray
            'rgba(22, 160, 133, 0.7)',   // Teal
            'rgba(211, 84, 0, 0.7)',     // Dark Orange
            'rgba(52, 73, 94, 0.7)'      // Navy
        ],
        sales: [
            'rgba(46, 204, 113, 0.7)',   // Green
            'rgba(231, 76, 60, 0.7)',    // Red
            'rgba(52, 152, 219, 0.7)',   // Blue
            'rgba(155, 89, 182, 0.7)',   // Purple
            'rgba(241, 196, 15, 0.7)',   // Yellow
            'rgba(26, 188, 156, 0.7)',   // Turquoise
            'rgba(230, 126, 34, 0.7)',   // Orange
            'rgba(149, 165, 166, 0.7)',  // Gray
            'rgba(192, 57, 43, 0.7)',    // Dark Red
            'rgba(41, 128, 185, 0.7)'    // Dark Blue
        ]
    };

    // Border colors (darker versions of fill colors)
    const BORDER_COLORS = COLOR_PALETTES.default.map(color => color.replace('0.7', '1'));

    /**
     * Helper function to get percentage change between two values
     * @param {number} oldValue - The old value
     * @param {number} newValue - The new value
     * @returns {number} - The percentage change
     */
    function getPercentageChange(oldValue, newValue) {
        if (oldValue === 0) return newValue === 0 ? 0 : 100;
        return ((newValue - oldValue) / Math.abs(oldValue)) * 100;
    }

    /**
     * Helper function to format currency values
     * @param {number} value - The value to format
     * @returns {string} - Formatted currency string
     */
    function formatCurrency(value) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(value);
    }

    /**
     * Helper function to format percentage values
     * @param {number} value - The value to format
     * @returns {string} - Formatted percentage string
     */
    function formatPercentage(value) {
        return new Intl.NumberFormat('en-US', {
            style: 'percent',
            minimumFractionDigits: 1,
            maximumFractionDigits: 1
        }).format(value / 100);
    }

    /**
     * Helper function to determine if a column is a date column
     * @param {string} columnName - The column name to check
     * @returns {boolean} - True if column appears to be a date
     */
    function isDateColumn(columnName) {
        return /date|time|created|updated|year/i.test(columnName);
    }

    /**
     * Helper function to determine if a column is likely to contain property values
     * @param {string} columnName - The column name to check
     * @returns {boolean} - True if column appears to contain value information
     */
    function isValueColumn(columnName) {
        return /value|price|cost|amount|assessment/i.test(columnName);
    }

    /**
     * Helper function to determine if a column is likely to contain property types
     * @param {string} columnName - The column name to check
     * @returns {boolean} - True if column appears to contain property type information
     */
    function isPropertyTypeColumn(columnName) {
        return /type|category|classification|zone|use/i.test(columnName);
    }

    /**
     * Helper function to parse dates from various formats
     * @param {string} dateStr - The date string to parse
     * @returns {Date|null} - Parsed date or null if invalid
     */
    function parseDate(dateStr) {
        if (!dateStr) return null;
        
        // If it's already a Date object
        if (dateStr instanceof Date) return dateStr;
        
        // Handle various date formats
        let parsedDate;
        
        try {
            // Try built-in parsing first
            parsedDate = new Date(dateStr);
            
            // Check if valid
            if (isNaN(parsedDate.getTime())) {
                // Try different format variations
                if (/^\d{4}-\d{2}-\d{2}/.test(dateStr)) {
                    // ISO format YYYY-MM-DD
                    const parts = dateStr.split(/[-T :]/);
                    parsedDate = new Date(
                        parseInt(parts[0]),
                        parseInt(parts[1]) - 1,
                        parseInt(parts[2])
                    );
                } else if (/^\d{1,2}\/\d{1,2}\/\d{4}/.test(dateStr)) {
                    // MM/DD/YYYY format
                    const parts = dateStr.split(/[/ :]/);
                    parsedDate = new Date(
                        parseInt(parts[2]),
                        parseInt(parts[0]) - 1,
                        parseInt(parts[1])
                    );
                } else if (/^\d{1,2}-\d{1,2}-\d{4}/.test(dateStr)) {
                    // MM-DD-YYYY format
                    const parts = dateStr.split(/[- :]/);
                    parsedDate = new Date(
                        parseInt(parts[2]),
                        parseInt(parts[0]) - 1,
                        parseInt(parts[1])
                    );
                }
            }
        } catch (e) {
            console.error('Error parsing date:', e);
            return null;
        }
        
        return isNaN(parsedDate.getTime()) ? null : parsedDate;
    }

    /**
     * Helper function to get a property from row by possible field names
     * @param {Object} row - Data row
     * @param {Array<string>} possibleFields - Possible field names
     * @param {*} defaultValue - Default value if no field is found
     * @returns {*} - The value found or default value
     */
    function getProperty(row, possibleFields, defaultValue = null) {
        for (const field of possibleFields) {
            if (row[field] !== undefined) {
                return row[field];
            }
        }
        return defaultValue;
    }

    /**
     * Helper function to find an appropriate column from dataset
     * @param {Array<Object>} data - Dataset
     * @param {Array<string>} keywords - Keywords to look for in column names
     * @returns {string|null} - Found column name or null
     */
    function findColumn(data, keywords) {
        if (!data || data.length === 0) return null;
        
        const columns = Object.keys(data[0]);
        
        // First try exact matches with keywords
        for (const keyword of keywords) {
            const exactMatch = columns.find(col => 
                col.toLowerCase() === keyword.toLowerCase()
            );
            
            if (exactMatch) return exactMatch;
        }
        
        // Then try partial matches
        for (const keyword of keywords) {
            const partialMatch = columns.find(col => 
                col.toLowerCase().includes(keyword.toLowerCase())
            );
            
            if (partialMatch) return partialMatch;
        }
        
        return null;
    }

    /**
     * Helper function to group data by a specified field
     * @param {Array<Object>} data - Dataset
     * @param {string} groupField - Field to group by
     * @param {string} valueField - Field to aggregate
     * @param {string} aggregation - Aggregation method (sum, avg, count)
     * @returns {Object} - Grouped data
     */
    function groupData(data, groupField, valueField, aggregation = 'sum') {
        const grouped = {};
        
        data.forEach(row => {
            const groupKey = String(row[groupField] || 'Unknown');
            const value = parseFloat(row[valueField]) || 0;
            
            if (!grouped[groupKey]) {
                grouped[groupKey] = {
                    sum: 0,
                    count: 0,
                    values: []
                };
            }
            
            grouped[groupKey].sum += value;
            grouped[groupKey].count++;
            grouped[groupKey].values.push(value);
        });
        
        // Calculate aggregated values
        Object.keys(grouped).forEach(key => {
            const group = grouped[key];
            
            switch (aggregation.toLowerCase()) {
                case 'avg':
                    group.result = group.sum / group.count;
                    break;
                case 'count':
                    group.result = group.count;
                    break;
                case 'min':
                    group.result = Math.min(...group.values);
                    break;
                case 'max':
                    group.result = Math.max(...group.values);
                    break;
                case 'sum':
                default:
                    group.result = group.sum;
                    break;
            }
        });
        
        return grouped;
    }

    /**
     * Creates a bar chart for property values
     * @param {string} selector - CSS selector for the canvas
     * @param {Array<Object>} data - Dataset
     * @param {string} categoryField - Field for X axis
     * @param {string} valueField - Field for Y axis
     * @returns {Object} - Chart.js instance
     */
    exports.createPropertyValueBarChart = function(selector, data, categoryField, valueField) {
        const canvas = document.querySelector(selector);
        if (!canvas || !data || data.length === 0) return null;
        
        const ctx = canvas.getContext('2d');
        
        // Group data by category
        const groupedData = groupData(data, categoryField, valueField, 'sum');
        
        // Extract labels and values
        const labels = Object.keys(groupedData);
        const values = labels.map(label => groupedData[label].result);
        
        // Determine if this is a monetary value field
        const isMonetary = isValueColumn(valueField);
        
        // Create the chart
        return new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: `${valueField} by ${categoryField}`,
                    data: values,
                    backgroundColor: COLOR_PALETTES.property.slice(0, values.length),
                    borderColor: COLOR_PALETTES.property.map(color => color.replace('0.7', '1')),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (isMonetary) {
                                    label += formatCurrency(context.raw);
                                } else {
                                    label += context.raw.toLocaleString();
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                if (isMonetary) {
                                    return formatCurrency(value);
                                }
                                return value.toLocaleString();
                            }
                        }
                    }
                }
            }
        });
    };

    /**
     * Creates a pie chart for property distribution
     * @param {string} selector - CSS selector for the canvas
     * @param {Array<Object>} data - Dataset
     * @param {string} typeField - Field for categories
     * @param {string} valueField - Field for values (optional)
     * @returns {Object} - Chart.js instance
     */
    exports.createPropertyDistributionPieChart = function(selector, data, typeField, valueField = null) {
        const canvas = document.querySelector(selector);
        if (!canvas || !data || data.length === 0) return null;
        
        const ctx = canvas.getContext('2d');
        
        // Process the data
        let labels, values;
        
        if (valueField) {
            // Group by type and sum values
            const groupedData = groupData(data, typeField, valueField, 'sum');
            labels = Object.keys(groupedData);
            values = labels.map(label => groupedData[label].result);
        } else {
            // Just count occurrences of each type
            const countMap = {};
            data.forEach(row => {
                const type = String(row[typeField] || 'Unknown');
                countMap[type] = (countMap[type] || 0) + 1;
            });
            
            labels = Object.keys(countMap);
            values = Object.values(countMap);
        }
        
        // Create the chart
        return new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: COLOR_PALETTES.property.slice(0, values.length),
                    borderColor: COLOR_PALETTES.property.map(color => color.replace('0.7', '1')),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.raw;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                
                                if (valueField && isValueColumn(valueField)) {
                                    return `${label}: ${formatCurrency(value)} (${percentage}%)`;
                                }
                                return `${label}: ${value.toLocaleString()} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    };

    /**
     * Creates a doughnut chart
     * @param {string} selector - CSS selector for the canvas
     * @param {Array<Object>} data - Dataset
     * @param {string} categoryField - Field for categories
     * @param {string} valueField - Field for values
     * @returns {Object} - Chart.js instance
     */
    exports.createDoughnutChart = function(selector, data, categoryField, valueField) {
        const canvas = document.querySelector(selector);
        if (!canvas || !data || data.length === 0) return null;
        
        const ctx = canvas.getContext('2d');
        
        // Group data by category
        const groupedData = groupData(data, categoryField, valueField, 'sum');
        
        // Extract labels and values
        const labels = Object.keys(groupedData);
        const values = labels.map(label => groupedData[label].result);
        
        // Create the chart
        return new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: COLOR_PALETTES.default.slice(0, values.length),
                    borderColor: BORDER_COLORS.slice(0, values.length),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.raw;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                
                                if (isValueColumn(valueField)) {
                                    return `${label}: ${formatCurrency(value)} (${percentage}%)`;
                                }
                                return `${label}: ${value.toLocaleString()} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    };

    /**
     * Creates a scatter plot
     * @param {string} selector - CSS selector for the canvas
     * @param {Array<Object>} data - Dataset
     * @param {string} xField - Field for X axis
     * @param {string} yField - Field for Y axis
     * @param {string} groupField - Field for grouping points (optional)
     * @returns {Object} - Chart.js instance
     */
    exports.createScatterPlot = function(selector, data, xField, yField, groupField = null) {
        const canvas = document.querySelector(selector);
        if (!canvas || !data || data.length === 0) return null;
        
        const ctx = canvas.getContext('2d');
        
        // Process the data
        let datasets;
        
        if (groupField) {
            // Group data points by the group field
            const groupedPoints = {};
            
            data.forEach(row => {
                const x = parseFloat(row[xField]) || 0;
                const y = parseFloat(row[yField]) || 0;
                const group = String(row[groupField] || 'Unknown');
                
                if (!groupedPoints[group]) {
                    groupedPoints[group] = [];
                }
                
                groupedPoints[group].push({ x, y });
            });
            
            // Create datasets for each group
            datasets = Object.keys(groupedPoints).map((group, index) => ({
                label: group,
                data: groupedPoints[group],
                backgroundColor: COLOR_PALETTES.default[index % COLOR_PALETTES.default.length],
                borderColor: BORDER_COLORS[index % BORDER_COLORS.length],
                pointRadius: 5,
                pointHoverRadius: 7
            }));
        } else {
            // Single dataset with all points
            const points = data.map(row => ({
                x: parseFloat(row[xField]) || 0,
                y: parseFloat(row[yField]) || 0
            }));
            
            datasets = [{
                label: `${yField} vs ${xField}`,
                data: points,
                backgroundColor: COLOR_PALETTES.default[0],
                borderColor: BORDER_COLORS[0],
                pointRadius: 5,
                pointHoverRadius: 7
            }];
        }
        
        // Create the chart
        return new Chart(ctx, {
            type: 'scatter',
            data: {
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.dataset.label || '';
                                const x = context.parsed.x;
                                const y = context.parsed.y;
                                
                                if (isValueColumn(yField)) {
                                    return `${label}: (${x}, ${formatCurrency(y)})`;
                                }
                                return `${label}: (${x}, ${y})`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'linear',
                        position: 'bottom',
                        title: {
                            display: true,
                            text: xField
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: yField
                        },
                        ticks: {
                            callback: function(value) {
                                if (isValueColumn(yField)) {
                                    return formatCurrency(value);
                                }
                                return value;
                            }
                        }
                    }
                }
            }
        });
    };

    /**
     * Creates a stacked bar chart
     * @param {string} selector - CSS selector for the canvas
     * @param {Array<Object>} data - Dataset
     * @param {string} categoryField - Field for X axis
     * @param {Array<string>} valueFields - Array of fields to stack
     * @param {Array<string>} labels - Labels for each value field
     * @returns {Object} - Chart.js instance
     */
    exports.createStackedBarChart = function(selector, data, categoryField, valueFields, labels) {
        const canvas = document.querySelector(selector);
        if (!canvas || !data || data.length === 0) return null;
        
        const ctx = canvas.getContext('2d');
        
        // Group data by category
        const categories = [...new Set(data.map(row => String(row[categoryField] || 'Unknown')))];
        
        // Create datasets for each value field
        const datasets = valueFields.map((field, index) => {
            // Calculate values for each category
            const values = categories.map(category => {
                const categoryRows = data.filter(row => String(row[categoryField] || 'Unknown') === category);
                return categoryRows.reduce((sum, row) => sum + (parseFloat(row[field]) || 0), 0);
            });
            
            return {
                label: labels[index] || field,
                data: values,
                backgroundColor: COLOR_PALETTES.default[index % COLOR_PALETTES.default.length],
                stack: 'Stack 0'
            };
        });
        
        // Create the chart
        return new Chart(ctx, {
            type: 'bar',
            data: {
                labels: categories,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.dataset.label || '';
                                const value = context.raw;
                                
                                if (isValueColumn(valueFields[context.datasetIndex])) {
                                    return `${label}: ${formatCurrency(value)}`;
                                }
                                return `${label}: ${value.toLocaleString()}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: categoryField
                        }
                    },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Value'
                        },
                        ticks: {
                            callback: function(value) {
                                if (valueFields.some(isValueColumn)) {
                                    return formatCurrency(value);
                                }
                                return value.toLocaleString();
                            }
                        }
                    }
                }
            }
        });
    };

    /**
     * Creates a time series chart
     * @param {string} selector - CSS selector for the canvas
     * @param {Array<Object>} data - Dataset
     * @param {string} timeField - Field for time/date
     * @param {string} valueField - Field for values
     * @param {string} groupField - Field for grouping time series (optional)
     * @returns {Object} - Chart.js instance
     */
    exports.createTimeSeriesChart = function(selector, data, timeField, valueField, groupField = null) {
        const canvas = document.querySelector(selector);
        if (!canvas || !data || data.length === 0) return null;
        
        const ctx = canvas.getContext('2d');
        
        // Process the data
        let datasets;
        
        // Helper to sort date points
        const sortByDate = (a, b) => {
            const dateA = parseDate(a.x);
            const dateB = parseDate(b.x);
            return dateA - dateB;
        };
        
        if (groupField) {
            // Group data points by the group field
            const groupedPoints = {};
            
            data.forEach(row => {
                const date = row[timeField];
                const value = parseFloat(row[valueField]) || 0;
                const group = String(row[groupField] || 'Unknown');
                
                if (!groupedPoints[group]) {
                    groupedPoints[group] = [];
                }
                
                groupedPoints[group].push({ x: date, y: value });
            });
            
            // Sort points by date for each group
            Object.keys(groupedPoints).forEach(group => {
                groupedPoints[group].sort(sortByDate);
            });
            
            // Create datasets for each group
            datasets = Object.keys(groupedPoints).map((group, index) => ({
                label: group,
                data: groupedPoints[group],
                backgroundColor: COLOR_PALETTES.default[index % COLOR_PALETTES.default.length],
                borderColor: BORDER_COLORS[index % BORDER_COLORS.length],
                borderWidth: 2,
                fill: false,
                tension: 0.1
            }));
        } else {
            // Single dataset with all points
            const points = data.map(row => ({
                x: row[timeField],
                y: parseFloat(row[valueField]) || 0
            })).sort(sortByDate);
            
            datasets = [{
                label: valueField,
                data: points,
                backgroundColor: COLOR_PALETTES.default[0],
                borderColor: BORDER_COLORS[0],
                borderWidth: 2,
                fill: false,
                tension: 0.1
            }];
        }
        
        // Create the chart
        return new Chart(ctx, {
            type: 'line',
            data: {
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.dataset.label || '';
                                const value = context.parsed.y;
                                
                                if (isValueColumn(valueField)) {
                                    return `${label}: ${formatCurrency(value)}`;
                                }
                                return `${label}: ${value.toLocaleString()}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'month',
                            displayFormats: {
                                month: 'MMM yyyy'
                            }
                        },
                        title: {
                            display: true,
                            text: timeField
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: valueField
                        },
                        ticks: {
                            callback: function(value) {
                                if (isValueColumn(valueField)) {
                                    return formatCurrency(value);
                                }
                                return value.toLocaleString();
                            }
                        }
                    }
                }
            }
        });
    };

})(window.enhancedViz);

// Initialize visualization library
document.addEventListener('DOMContentLoaded', function() {
    console.log('Enhanced Visualization Library loaded');
    
    // Listen for Chart.js load to add plugins
    const checkChartJsReady = setInterval(function() {
        if (window.Chart) {
            console.log('Chart.js detected, initializing plugins');
            clearInterval(checkChartJsReady);
            
            // Add Chart.js plugins if needed
            
            // Initialize any global visualizations
        }
    }, 100);
});
