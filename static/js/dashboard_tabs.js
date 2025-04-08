/**
 * Dashboard Tabs Module
 * 
 * This module handles the tab navigation on the statistics dashboard.
 * It allows users to switch between different dashboard views.
 */

// When the document is loaded, set up tab navigation
document.addEventListener('DOMContentLoaded', function() {
    // Set up tab click handlers
    const tabs = document.querySelectorAll('.dashboard-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const tabId = this.getAttribute('data-tab');
            switchToTab(tabId);
        });
    });
    
    // Population charts
    initializePopulationCharts();
    
    // Community comparison charts
    initializePropertyComparisonCharts();
    
    // Year on year growth chart
    initializeYearlyGrowthChart();
});

/**
 * Switch to a specific tab
 */
function switchToTab(tabId) {
    // Deactivate all tabs
    document.querySelectorAll('.dashboard-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Deactivate all tab contents
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    // Activate the selected tab
    document.querySelector(`.dashboard-tab[data-tab="${tabId}"]`).classList.add('active');
    
    // Activate the selected tab content
    document.getElementById(`${tabId}-tab`).classList.add('active');
    
    // Initialize map if switching to map view
    if (tabId === 'map-view' && typeof initializeMap === 'function') {
        setTimeout(() => {
            initializeMap();
        }, 100);
    }
}

/**
 * Initialize population charts
 */
function initializePopulationCharts() {
    // Gender distribution chart
    const genderCtx = document.getElementById('gender-distribution-chart');
    if (genderCtx) {
        new Chart(genderCtx, {
            type: 'pie',
            data: {
                labels: ['Male', 'Female'],
                datasets: [{
                    data: [104632, 102928],
                    backgroundColor: [
                        'rgba(59, 130, 246, 0.8)',
                        'rgba(236, 72, 153, 0.8)'
                    ],
                    borderColor: [
                        'rgba(59, 130, 246, 1)',
                        'rgba(236, 72, 153, 1)'
                    ],
                    borderWidth: 1,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.label || '';
                                let value = context.raw || 0;
                                let total = context.dataset.data.reduce((acc, val) => acc + val, 0);
                                let percentage = ((value / total) * 100).toFixed(1);
                                return `${label}: ${value.toLocaleString()} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Age distribution chart
    const ageCtx = document.getElementById('age-distribution-chart');
    if (ageCtx) {
        new Chart(ageCtx, {
            type: 'bar',
            data: {
                labels: ['Under 5', '5 to 17', '18 to 24', '25 to 44', '45 to 64', 'Over 65'],
                datasets: [
                    {
                        label: 'Male',
                        data: [3500, 12600, 8500, 24800, 20100, 11500],
                        backgroundColor: 'rgba(59, 130, 246, 0.7)',
                        borderColor: 'rgba(59, 130, 246, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Female',
                        data: [3400, 12100, 8200, 24300, 19800, 11400],
                        backgroundColor: 'rgba(236, 72, 153, 0.7)',
                        borderColor: 'rgba(236, 72, 153, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                let value = context.raw || 0;
                                return `${label}: ${value.toLocaleString()}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Age Group'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Population'
                        }
                    }
                }
            }
        });
    }
}

/**
 * Initialize property comparison charts
 */
function initializePropertyComparisonCharts() {
    // Property type comparison chart
    const comparisonCtx = document.getElementById('property-comparison-chart');
    if (comparisonCtx) {
        new Chart(comparisonCtx, {
            type: 'radar',
            data: {
                labels: ['Value', 'Count', 'Growth Rate', 'Demand', 'Tax Rate'],
                datasets: [
                    {
                        label: 'Residential',
                        data: [75, 95, 80, 85, 70],
                        backgroundColor: 'rgba(59, 130, 246, 0.2)',
                        borderColor: 'rgba(59, 130, 246, 1)',
                        borderWidth: 2,
                        pointBackgroundColor: 'rgba(59, 130, 246, 1)',
                        pointBorderColor: '#fff',
                        pointHoverBackgroundColor: '#fff',
                        pointHoverBorderColor: 'rgba(59, 130, 246, 1)'
                    },
                    {
                        label: 'Commercial',
                        data: [90, 70, 65, 60, 85],
                        backgroundColor: 'rgba(249, 115, 22, 0.2)',
                        borderColor: 'rgba(249, 115, 22, 1)',
                        borderWidth: 2,
                        pointBackgroundColor: 'rgba(249, 115, 22, 1)',
                        pointBorderColor: '#fff',
                        pointHoverBackgroundColor: '#fff',
                        pointHoverBorderColor: 'rgba(249, 115, 22, 1)'
                    },
                    {
                        label: 'Agricultural',
                        data: [40, 80, 50, 30, 65],
                        backgroundColor: 'rgba(16, 185, 129, 0.2)',
                        borderColor: 'rgba(16, 185, 129, 1)',
                        borderWidth: 2,
                        pointBackgroundColor: 'rgba(16, 185, 129, 1)',
                        pointBorderColor: '#fff',
                        pointHoverBackgroundColor: '#fff',
                        pointHoverBorderColor: 'rgba(16, 185, 129, 1)'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        angleLines: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        },
                        pointLabels: {
                            font: {
                                size: 12,
                                weight: 'bold'
                            }
                        },
                        suggestedMin: 0,
                        suggestedMax: 100
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                let value = context.raw || 0;
                                return `${label}: ${value}/100`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Average values by property type chart
    const avgValuesCtx = document.getElementById('avg-values-chart');
    if (avgValuesCtx) {
        new Chart(avgValuesCtx, {
            type: 'bar',
            data: {
                labels: ['Residential', 'Commercial', 'Agricultural', 'Industrial', 'Multifamily'],
                datasets: [{
                    label: 'Average Property Value',
                    data: [367500, 743250, 215400, 1254300, 865750],
                    backgroundColor: [
                        'rgba(59, 130, 246, 0.7)',
                        'rgba(249, 115, 22, 0.7)',
                        'rgba(16, 185, 129, 0.7)',
                        'rgba(139, 92, 246, 0.7)',
                        'rgba(234, 179, 8, 0.7)'
                    ],
                    borderColor: [
                        'rgba(59, 130, 246, 1)',
                        'rgba(249, 115, 22, 1)',
                        'rgba(16, 185, 129, 1)',
                        'rgba(139, 92, 246, 1)',
                        'rgba(234, 179, 8, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let value = context.raw || 0;
                                return `Average Value: ${formatCurrency(value)}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return formatCurrency(value);
                            }
                        }
                    }
                }
            }
        });
    }
}

/**
 * Initialize yearly growth chart
 */
function initializeYearlyGrowthChart() {
    const growthCtx = document.getElementById('yearly-growth-chart');
    if (growthCtx) {
        new Chart(growthCtx, {
            type: 'line',
            data: {
                labels: ['2020 Q1', '2020 Q2', '2020 Q3', '2020 Q4', '2021 Q1', '2021 Q2', '2021 Q3', '2021 Q4', '2022 Q1', '2022 Q2', '2022 Q3', '2022 Q4', '2023 Q1', '2023 Q2', '2023 Q3', '2023 Q4', '2024 Q1', '2024 Q2'],
                datasets: [
                    {
                        label: 'Residential',
                        data: [2.1, 1.8, 2.4, 3.1, 3.8, 4.2, 5.1, 5.6, 6.3, 5.8, 4.9, 4.3, 3.7, 3.5, 3.2, 3.0, 2.8, 3.1],
                        borderColor: 'rgba(59, 130, 246, 1)',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Commercial',
                        data: [1.5, 1.2, 0.9, 1.3, 1.7, 2.1, 2.5, 2.9, 3.2, 3.5, 3.1, 2.8, 2.6, 2.3, 2.0, 1.8, 1.6, 2.1],
                        borderColor: 'rgba(249, 115, 22, 1)',
                        backgroundColor: 'rgba(249, 115, 22, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'All Properties',
                        data: [1.9, 1.6, 2.1, 2.6, 3.2, 3.7, 4.2, 4.8, 5.2, 5.1, 4.5, 3.9, 3.4, 3.1, 2.8, 2.6, 2.4, 2.8],
                        borderColor: 'rgba(16, 185, 129, 1)',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        tension: 0.4,
                        fill: true,
                        borderWidth: 3,
                        borderDash: [5, 5]
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
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                let value = context.raw || 0;
                                return `${label}: ${value}% growth`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        },
                        title: {
                            display: true,
                            text: 'Growth Rate (%)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Quarter'
                        }
                    }
                }
            }
        });
    }
}

// Format currency helper function
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