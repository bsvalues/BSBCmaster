// Function to update the property type chart
function updatePropertyTypeChart(propertyTypes) {
    const ctx = document.getElementById('property-type-chart').getContext('2d');
    
    // Prepare data for chart
    const labels = propertyTypes.map(item => item.property_type);
    const counts = propertyTypes.map(item => item.count);
    const values = propertyTypes.map(item => item.average_value);
    
    // Destroy existing chart if it exists
    if (propertyTypeChart) {
        propertyTypeChart.destroy();
    }
    
    // Create new chart
    propertyTypeChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Count',
                    data: counts,
                    backgroundColor: 'rgba(59, 130, 246, 0.6)',
                    borderColor: 'rgba(59, 130, 246, 1)',
                    borderWidth: 1,
                    borderRadius: 4,
                    yAxisID: 'y'
                },
                {
                    label: 'Average Value',
                    data: values,
                    backgroundColor: 'rgba(16, 185, 129, 0.6)',
                    borderColor: 'rgba(16, 185, 129, 1)',
                    borderWidth: 1,
                    borderRadius: 4,
                    type: 'bar',
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15
                    }
                },
                tooltip: {
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
                        text: 'Count'
                    },
                    grid: {
                        drawBorder: false
                    }
                },
                y1: {
                    beginAtZero: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Average Value'
                    },
                    grid: {
                        display: false
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

// Function to update the value distribution chart
function updateValueDistributionChart(valueDistribution) {
    const ctx = document.getElementById('value-distribution-chart').getContext('2d');
    
    // Prepare data for chart
    const labels = Object.keys(valueDistribution);
    const data = Object.values(valueDistribution);
    
    // Destroy existing chart if it exists
    if (valueDistributionChart) {
        valueDistributionChart.destroy();
    }
    
    // Generate colors
    const colors = [
        'rgba(59, 130, 246, 0.6)',   // Blue
        'rgba(16, 185, 129, 0.6)',   // Green
        'rgba(245, 158, 11, 0.6)',   // Yellow
        'rgba(239, 68, 68, 0.6)',    // Red
        'rgba(139, 92, 246, 0.6)'    // Purple
    ];
    
    // Create new chart
    valueDistributionChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderColor: colors.map(color => color.replace('0.6', '1')),
                borderWidth: 1,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        usePointStyle: true,
                        padding: 15
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw;
                            const percentage = Math.round((value / data.reduce((a, b) => a + b, 0)) * 100);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// Function to update the value trends chart
function updateValueTrendsChart(trendsData) {
    const ctx = document.getElementById('value-trends-chart').getContext('2d');
    
    // Destroy existing chart if it exists
    if (valueTrendsChart) {
        valueTrendsChart.destroy();
    }
    
    // Generate colors
    const colors = [
        'rgba(59, 130, 246, 1)',   // Blue
        'rgba(16, 185, 129, 1)',   // Green
        'rgba(245, 158, 11, 1)',   // Yellow
        'rgba(239, 68, 68, 1)',    // Red
        'rgba(139, 92, 246, 1)'    // Purple
    ];
    
    // Create datasets
    const datasets = trendsData.datasets.map((dataset, index) => {
        return {
            label: dataset.label,
            data: dataset.data,
            borderColor: colors[index % colors.length],
            backgroundColor: colors[index % colors.length].replace('1)', '0.1)'),
            borderWidth: 2,
            fill: true,
            tension: 0.4
        };
    });
    
    // Create new chart
    valueTrendsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: trendsData.labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            label += context.raw;
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
                        text: 'Number of Properties'
                    },
                    grid: {
                        drawBorder: false
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}
