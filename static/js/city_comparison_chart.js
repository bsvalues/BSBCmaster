// Function to create a detailed city comparison chart
function updateCityComparisonChart(cityStatistics) {
    try {
        console.log("Updating city comparison chart with data:", cityStatistics);
        const canvas = document.getElementById('city-comparison-chart');
        if (!canvas) {
            console.error("City comparison chart canvas not found");
            return;
        }
        
        const ctx = canvas.getContext('2d');
        
        // Prepare data for chart
        const cities = Object.keys(cityStatistics);
        const avgValues = cities.map(city => cityStatistics[city].average_value);
        const propertyCounts = cities.map(city => cityStatistics[city].count);
        
        // Destroy existing chart if it exists
        if (window.cityComparisonChart) {
            window.cityComparisonChart.destroy();
        }
        
        // Create gradient for average values
        const blueGradient = ctx.createLinearGradient(0, 0, 0, 400);
        blueGradient.addColorStop(0, 'rgba(59, 130, 246, 0.7)');
        blueGradient.addColorStop(1, 'rgba(59, 130, 246, 0.2)');
        
        // Create new chart with animations
        window.cityComparisonChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: cities,
                datasets: [
                    {
                        label: 'Average Property Value',
                        data: avgValues,
                        backgroundColor: blueGradient,
                        borderColor: 'rgba(59, 130, 246, 1)',
                        borderWidth: 1,
                        borderRadius: 6,
                        yAxisID: 'y',
                        hoverBackgroundColor: 'rgba(59, 130, 246, 0.9)'
                    },
                    {
                        label: 'Property Count',
                        data: propertyCounts,
                        type: 'line',
                        yAxisID: 'y1',
                        borderColor: 'rgba(16, 185, 129, 1)',
                        backgroundColor: 'rgba(16, 185, 129, 0.2)',
                        borderWidth: 3,
                        pointBackgroundColor: 'rgba(16, 185, 129, 1)',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointRadius: 5,
                        tension: 0.3,
                        fill: true
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
                                if (context.datasetIndex === 0) {
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
                            text: 'Average Value',
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
                            padding: 8,
                            callback: function(value) {
                                return formatCurrency(value);
                            }
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
                            text: 'Property Count',
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
                            padding: 8
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
        
        console.log("City comparison chart created successfully");
    } catch (e) {
        console.error("Error in updateCityComparisonChart:", e);
    }
}

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