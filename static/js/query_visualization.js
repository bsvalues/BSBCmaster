/**
 * Query Visualization JavaScript
 * 
 * This file provides visualization capabilities for SQL query results.
 */

class QueryVisualizer {
    constructor(canvasId = 'queryVisualization') {
        this.canvas = document.getElementById(canvasId);
        this.chart = null;
    }
    
    /**
     * Analyze data to determine if it can be visualized
     * 
     * @param {Array} data - Array of objects (query results)
     * @returns {Object} Visualization options including categorical and numerical columns
     */
    analyzeData(data) {
        if (!data || data.length === 0) {
            return {
                canVisualize: false,
                reason: 'No data to visualize'
            };
        }
        
        // Get sample row and extract column information
        const sampleRow = data[0];
        const columns = Object.keys(sampleRow);
        
        // Analyze column types
        const columnTypes = {};
        const categoricalColumns = [];
        const numericalColumns = [];
        const dateColumns = [];
        
        // Analyze first row to determine potential column types
        columns.forEach(col => {
            const value = sampleRow[col];
            
            if (value === null || value === undefined) {
                // Can't determine type from null/undefined
                columnTypes[col] = 'unknown';
            } else if (typeof value === 'number') {
                columnTypes[col] = 'number';
                numericalColumns.push(col);
            } else if (typeof value === 'string') {
                // Check if it's a date string
                if (!isNaN(Date.parse(value)) && value.match(/^\d{4}-\d{2}-\d{2}|^\d{2}\/\d{2}\/\d{4}/)) {
                    columnTypes[col] = 'date';
                    dateColumns.push(col);
                } else {
                    // Count distinct values to determine if categorical
                    const distinctValues = new Set(data.map(row => row[col])).size;
                    
                    // If number of distinct values is small relative to data size, it's likely categorical
                    if (distinctValues <= Math.min(20, data.length / 5)) {
                        columnTypes[col] = 'categorical';
                        categoricalColumns.push(col);
                    } else {
                        columnTypes[col] = 'text';
                    }
                }
            } else if (value instanceof Date) {
                columnTypes[col] = 'date';
                dateColumns.push(col);
            } else {
                columnTypes[col] = typeof value;
            }
        });
        
        // Determine if data is visualizable
        const canVisualize = (
            (categoricalColumns.length > 0 && numericalColumns.length > 0) || // Category + number
            (dateColumns.length > 0 && numericalColumns.length > 0) // Time series
        );
        
        return {
            canVisualize,
            columnTypes,
            categoricalColumns,
            numericalColumns,
            dateColumns,
            recommendedVisualizations: this.recommendVisualizations(categoricalColumns, numericalColumns, dateColumns, data.length)
        };
    }
    
    /**
     * Recommend visualization types based on data characteristics
     */
    recommendVisualizations(categoricalColumns, numericalColumns, dateColumns, rowCount) {
        const recommendations = [];
        
        if (categoricalColumns.length > 0 && numericalColumns.length > 0) {
            // Category + number: bar, pie, radar charts
            recommendations.push({
                type: 'bar',
                suitability: 'high',
                description: 'Bar chart comparing numerical values across categories',
                dimensions: {
                    x: categoricalColumns[0],
                    y: numericalColumns[0]
                }
            });
            
            // Only recommend pie charts for limited categories
            if (rowCount <= 10) {
                recommendations.push({
                    type: 'pie',
                    suitability: 'medium',
                    description: 'Pie chart showing proportion across categories',
                    dimensions: {
                        labels: categoricalColumns[0],
                        values: numericalColumns[0]
                    }
                });
            }
        }
        
        if (dateColumns.length > 0 && numericalColumns.length > 0) {
            // Time series: line, area charts
            recommendations.push({
                type: 'line',
                suitability: 'high',
                description: 'Line chart showing trends over time',
                dimensions: {
                    x: dateColumns[0],
                    y: numericalColumns[0]
                }
            });
        }
        
        if (numericalColumns.length >= 2) {
            // Two numerical columns: scatter plot
            recommendations.push({
                type: 'scatter',
                suitability: 'medium',
                description: 'Scatter plot showing relationship between two numerical variables',
                dimensions: {
                    x: numericalColumns[0],
                    y: numericalColumns[1]
                }
            });
        }
        
        return recommendations;
    }
    
    /**
     * Create a visualization based on the data and specified options
     * 
     * @param {Array} data - Array of objects (query results)
     * @param {String} chartType - Type of chart to create
     * @param {Object} options - Visualization options including dimensions
     */
    createVisualization(data, chartType = 'bar', options = {}) {
        // Default options
        const defaultOptions = {
            xAxis: null,
            yAxis: null,
            limit: 50, // Limit number of data points
            title: 'Query Results',
            colors: [
                'rgba(75, 192, 192, 0.7)',
                'rgba(255, 99, 132, 0.7)',
                'rgba(54, 162, 235, 0.7)',
                'rgba(255, 206, 86, 0.7)',
                'rgba(153, 102, 255, 0.7)'
            ]
        };
        
        // Merge options
        options = { ...defaultOptions, ...options };
        
        // Analyze data
        const analysis = this.analyzeData(data);
        
        if (!analysis.canVisualize) {
            console.error('Data cannot be visualized:', analysis.reason);
            return null;
        }
        
        // Default dimensions if not specified
        if (!options.xAxis) {
            options.xAxis = analysis.categoricalColumns.length > 0 ? 
                analysis.categoricalColumns[0] : 
                (analysis.dateColumns.length > 0 ? analysis.dateColumns[0] : null);
        }
        
        if (!options.yAxis) {
            options.yAxis = analysis.numericalColumns.length > 0 ? 
                analysis.numericalColumns[0] : null;
        }
        
        // If we can't determine axes, we can't visualize
        if (!options.xAxis || !options.yAxis) {
            console.error('Cannot determine axes for visualization');
            return null;
        }
        
        // Limit data points if needed
        let visualData = data;
        if (data.length > options.limit) {
            visualData = data.slice(0, options.limit);
        }
        
        // Extract axis values
        const labels = visualData.map(row => row[options.xAxis]);
        const values = visualData.map(row => row[options.yAxis]);
        
        // Destroy existing chart if any
        if (this.chart) {
            this.chart.destroy();
        }
        
        // Create chart configuration
        const chartConfig = {
            type: chartType,
            data: {
                labels: labels,
                datasets: [{
                    label: options.yAxis,
                    data: values,
                    backgroundColor: options.colors[0],
                    borderColor: options.colors[0].replace('0.7', '1'),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: options.title
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `${options.yAxis}: ${context.raw}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: options.yAxis
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: options.xAxis
                        }
                    }
                }
            }
        };
        
        // Customize specific chart types
        if (chartType === 'pie' || chartType === 'doughnut') {
            // Pie charts don't have axes
            delete chartConfig.options.scales;
            
            // Use all colors for different segments
            chartConfig.data.datasets[0].backgroundColor = options.colors;
            chartConfig.data.datasets[0].borderColor = options.colors.map(color => color.replace('0.7', '1'));
        } else if (chartType === 'line') {
            // Line charts need different styling
            chartConfig.data.datasets[0].fill = false;
            chartConfig.data.datasets[0].tension = 0.1;
        } else if (chartType === 'scatter') {
            // Scatter plots need special handling
            chartConfig.data.labels = null; // No labels for scatter
            chartConfig.data.datasets[0].data = visualData.map(row => ({
                x: row[options.xAxis],
                y: row[options.yAxis]
            }));
            chartConfig.options.scales.x.type = 'linear'; // Force linear scale
        }
        
        // Create chart
        const ctx = this.canvas.getContext('2d');
        this.chart = new Chart(ctx, chartConfig);
        
        return this.chart;
    }
}

// Initialize on load
document.addEventListener('DOMContentLoaded', function() {
    // Create global instance if canvas exists
    const visualizationCanvas = document.getElementById('queryVisualization');
    if (visualizationCanvas) {
        window.queryVisualizer = new QueryVisualizer('queryVisualization');
    }
});
