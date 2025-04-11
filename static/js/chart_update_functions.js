// Initialize chart instances
let propertyTypeChart = null;
let valueDistributionChart = null;
let valueTrendsChart = null;

// Helper function to format currency values
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

// Function to update the property type chart
function updatePropertyTypeChart(propertyTypes) {
    try {
        console.log("Updating property type chart with data:", propertyTypes);
        const canvas = document.getElementById('property-type-chart');
        if (!canvas) {
            console.error("Property type chart canvas not found");
            return;
        }
        
        const ctx = canvas.getContext('2d');
        
        // Prepare data for chart
        const labels = propertyTypes.map(item => item.property_type);
        const counts = propertyTypes.map(item => item.count);
        const values = propertyTypes.map(item => item.average_value);
        
        // Destroy existing chart if it exists
        if (propertyTypeChart) {
            propertyTypeChart.destroy();
        }
        
        // Create animated gradient background
        const blueGradient = ctx.createLinearGradient(0, 0, 0, 400);
        blueGradient.addColorStop(0, 'rgba(59, 130, 246, 0.8)');
        blueGradient.addColorStop(1, 'rgba(59, 130, 246, 0.2)');
        
        const greenGradient = ctx.createLinearGradient(0, 0, 0, 400);
        greenGradient.addColorStop(0, 'rgba(16, 185, 129, 0.8)');
        greenGradient.addColorStop(1, 'rgba(16, 185, 129, 0.2)');
        
        // Create new chart with animations
        propertyTypeChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Count',
                        data: counts,
                        backgroundColor: blueGradient,
                        borderColor: 'rgba(59, 130, 246, 1)',
                        borderWidth: 1,
                        borderRadius: 6,
                        yAxisID: 'y',
                        hoverBackgroundColor: 'rgba(59, 130, 246, 0.9)'
                    },
                    {
                        label: 'Average Value',
                        data: values,
                        backgroundColor: greenGradient,
                        borderColor: 'rgba(16, 185, 129, 1)',
                        borderWidth: 1,
                        borderRadius: 6,
                        type: 'bar',
                        yAxisID: 'y1',
                        hoverBackgroundColor: 'rgba(16, 185, 129, 0.9)'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 1000,
                    easing: 'easeOutQuart'
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            padding: 20,
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleFont: {
                            size: 14,
                            weight: 'bold'
                        },
                        bodyFont: {
                            size: 13
                        },
                        padding: 15,
                        cornerRadius: 8,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.datasetIndex === 1) {
                                    label += formatCurrency(context.raw);
                                } else {
                                    label += context.raw;
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Count',
                            font: {
                                size: 13,
                                weight: 'bold'
                            },
                            color: 'rgba(59, 130, 246, 0.9)'
                        },
                        ticks: {
                            font: {
                                size: 11
                            },
                            padding: 8
                        },
                        grid: {
                            drawBorder: false,
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    },
                    y1: {
                        beginAtZero: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Average Value',
                            font: {
                                size: 13,
                                weight: 'bold'
                            },
                            color: 'rgba(16, 185, 129, 0.9)'
                        },
                        ticks: {
                            font: {
                                size: 11
                            },
                            padding: 8,
                            callback: function(value) {
                                return formatCurrency(value);
                            }
                        },
                        grid: {
                            display: false
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            font: {
                                size: 11
                            },
                            padding: 8
                        }
                    }
                }
            }
        });
    } catch (e) {
        console.error("Error in updatePropertyTypeChart:", e);
    }
}

// Function to update the value distribution chart
function updateValueDistributionChart(valueDistribution) {
    try {
        console.log("Updating value distribution chart with data:", valueDistribution);
        const canvas = document.getElementById('value-distribution-chart');
        if (!canvas) {
            console.error("Value distribution chart canvas not found");
            return;
        }
        
        const ctx = canvas.getContext('2d');
        
        // Prepare data for chart
        const labels = Object.keys(valueDistribution);
        const data = Object.values(valueDistribution);
        
        // Destroy existing chart if it exists
        if (valueDistributionChart) {
            valueDistributionChart.destroy();
        }
    
        // Generate enhanced colors with more transparency for better visual effect
        const colors = [
            'rgba(59, 130, 246, 0.75)',   // Blue
            'rgba(16, 185, 129, 0.75)',   // Green
            'rgba(245, 158, 11, 0.75)',   // Yellow
            'rgba(239, 68, 68, 0.75)',    // Red
            'rgba(139, 92, 246, 0.75)'    // Purple
        ];
        
        // Create new chart with enhanced visuals and animations
        valueDistributionChart = new Chart(ctx, {
            type: 'doughnut', // Changed from pie to doughnut for modern look
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: colors,
                    borderColor: colors.map(color => color.replace('0.75', '1')),
                    borderWidth: 2,
                    hoverOffset: 15,
                    borderRadius: 4,
                    spacing: 3, // Add spacing between segments
                    hoverBorderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '60%', // Doughnut hole size
                animation: {
                    animateRotate: true,
                    animateScale: true,
                    duration: 1200,
                    easing: 'easeOutQuart' 
                },
                layout: {
                    padding: 15
                },
                plugins: {
                    legend: {
                        position: 'right',
                        align: 'center',
                        labels: {
                            usePointStyle: true,
                            padding: 15,
                            font: {
                                size: 12
                            },
                            generateLabels: function(chart) {
                                // Get default labels
                                const original = Chart.overrides.pie.plugins.legend.labels.generateLabels(chart);
                                
                                // Add percentage to each label
                                original.forEach((label, i) => {
                                    const value = chart.data.datasets[0].data[i];
                                    const total = chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                                    const percentage = Math.round((value / total) * 100);
                                    label.text = `${label.text} (${percentage}%)`;
                                });
                                
                                return original;
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleFont: {
                            size: 14,
                            weight: 'bold'
                        },
                        bodyFont: {
                            size: 13
                        },
                        padding: 15,
                        cornerRadius: 8,
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.raw;
                                const total = data.reduce((a, b) => a + b, 0);
                                const percentage = Math.round((value / total) * 100);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    } catch (e) {
        console.error("Error in updateValueDistributionChart:", e);
    }
}

// Function to update the value trends chart
function updateValueTrendsChart(trendsData) {
    try {
        console.log("Updating value trends chart with data:", trendsData);
        const canvas = document.getElementById('value-trends-chart');
        if (!canvas) {
            console.error("Value trends chart canvas not found");
            return;
        }
        
        const ctx = canvas.getContext('2d');
        
        // Destroy existing chart if it exists
        if (valueTrendsChart) {
            valueTrendsChart.destroy();
        }
        
        // Generate modernized colors
        const colors = [
            'rgba(59, 130, 246, 1)',   // Blue
            'rgba(16, 185, 129, 1)',   // Green
            'rgba(245, 158, 11, 1)',   // Yellow
            'rgba(239, 68, 68, 1)',    // Red
            'rgba(139, 92, 246, 1)'    // Purple
        ];
        
        // Create enhanced datasets with better gradients
        const datasets = trendsData.datasets.map((dataset, index) => {
            const gradientFill = ctx.createLinearGradient(0, 0, 0, 400);
            const color = colors[index % colors.length];
            const colorBase = color.replace('1)', '');
            
            gradientFill.addColorStop(0, colorBase + '0.3)');
            gradientFill.addColorStop(1, colorBase + '0.02)');
            
            return {
                label: dataset.label,
                data: dataset.data,
                borderColor: color,
                backgroundColor: gradientFill,
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: color,
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 5,
                pointHoverRadius: 7,
                pointHoverBackgroundColor: color,
                pointHoverBorderColor: '#fff',
                pointHoverBorderWidth: 2
            };
        });
        
        // Create new chart with enhanced animations and interactions
        valueTrendsChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: trendsData.labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 1400,
                    easing: 'easeOutQuart'
                },
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: {
                        position: 'top',
                        align: 'center',
                        labels: {
                            usePointStyle: true,
                            padding: 20,
                            font: {
                                size: 12
                            },
                            boxWidth: 10,
                            boxHeight: 10
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleFont: {
                            size: 14,
                            weight: 'bold'
                        },
                        bodyFont: {
                            size: 13
                        },
                        padding: 15,
                        cornerRadius: 8,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                // Calculate percentage increase from first year
                                const dataPoints = context.dataset.data;
                                const currentValue = context.raw;
                                const firstValue = dataPoints[0];
                                
                                if (context.dataIndex > 0 && firstValue > 0) {
                                    const percentChange = ((currentValue - firstValue) / firstValue * 100).toFixed(1);
                                    const changeString = percentChange >= 0 ? `+${percentChange}%` : `${percentChange}%`;
                                    return `${label}${currentValue} (${changeString} from first year)`;
                                }
                                
                                return `${label}${currentValue}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Properties',
                            font: {
                                size: 13,
                                weight: 'bold'
                            },
                            color: 'rgba(59, 130, 246, 0.9)'
                        },
                        ticks: {
                            font: {
                                size: 11
                            },
                            padding: 8
                        },
                        grid: {
                            drawBorder: false,
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            font: {
                                size: 12,
                                weight: 'bold'
                            },
                            padding: 10
                        }
                    }
                }
            }
        });
    } catch (e) {
        console.error("Error in updateValueTrendsChart:", e);
    }
}