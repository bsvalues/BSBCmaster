/**
 * Real-time Property Data Updates
 * 
 * This module provides functionality for real-time property data updates,
 * including polling for changes and updating map layers.
 */

class RealtimeUpdates {
    /**
     * Initialize real-time updates
     * @param {Object} mapInstance - The Leaflet map instance
     * @param {Object} options - Configuration options
     */
    constructor(mapInstance, options = {}) {
        this.map = mapInstance;
        this.updatesLayer = L.layerGroup();
        this.notificationContainer = null;
        this.lastSyncTime = new Date();
        this.pollingInterval = null;
        this.lastNotificationId = 0;
        this.isActive = false;
        
        // Configure options with defaults
        this.options = {
            pollingFrequency: options.pollingFrequency || 60000, // 1 minute
            notificationsEnabled: options.notificationsEnabled !== undefined ? options.notificationsEnabled : true,
            autoSync: options.autoSync !== undefined ? options.autoSync : true,
            updateHandler: options.updateHandler || this._defaultUpdateHandler.bind(this),
            notificationPosition: options.notificationPosition || 'bottomright'
        };
        
        // Initialize notification container
        if (this.options.notificationsEnabled) {
            this._initializeNotifications();
        }
    }
    
    /**
     * Start real-time updates
     */
    start() {
        if (this.isActive) return;
        
        this.isActive = true;
        
        // Add updates layer to map
        this.map.addLayer(this.updatesLayer);
        
        // Show notifications if enabled
        if (this.options.notificationsEnabled && this.notificationContainer) {
            this.notificationContainer.addTo(this.map);
        }
        
        // Fetch initial updates
        this._fetchUpdates();
        
        // Start polling for updates
        this.pollingInterval = setInterval(() => {
            this._fetchUpdates();
        }, this.options.pollingFrequency);
        
        // Show a notification that real-time updates are enabled
        this._showNotification({
            type: 'info',
            message: 'Real-time updates enabled',
            timestamp: new Date().toISOString()
        });
    }
    
    /**
     * Stop real-time updates
     */
    stop() {
        if (!this.isActive) return;
        
        this.isActive = false;
        
        // Clear polling interval
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
        
        // Remove updates layer from map
        this.map.removeLayer(this.updatesLayer);
        
        // Remove notifications if visible
        if (this.notificationContainer) {
            this.notificationContainer.remove();
        }
        
        // Show a notification that real-time updates are disabled
        this._showNotification({
            type: 'info',
            message: 'Real-time updates disabled',
            timestamp: new Date().toISOString()
        }, true);
    }
    
    /**
     * Toggle real-time updates on/off
     * @returns {boolean} New state
     */
    toggle() {
        if (this.isActive) {
            this.stop();
        } else {
            this.start();
        }
        
        return this.isActive;
    }
    
    /**
     * Manually trigger a data sync
     * @param {string} syncType - Type of sync to trigger ('property_values', 'property_sales', 'tax_data', 'all')
     * @returns {Promise} Promise resolving to the sync result
     */
    triggerSync(syncType = 'all') {
        return fetch('/api/realtime/sync', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                type: syncType
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this._showNotification({
                    type: 'success',
                    message: `Sync triggered: ${syncType}`,
                    timestamp: data.timestamp
                });
                
                // Fetch updates after sync
                setTimeout(() => {
                    this._fetchUpdates();
                }, 1000);
            } else {
                this._showNotification({
                    type: 'error',
                    message: `Sync failed: ${data.message}`,
                    timestamp: new Date().toISOString()
                });
            }
            
            return data;
        })
        .catch(error => {
            console.error('Error triggering sync:', error);
            
            this._showNotification({
                type: 'error',
                message: 'Failed to trigger sync',
                timestamp: new Date().toISOString()
            });
            
            throw error;
        });
    }
    
    /**
     * Fetch property data updates
     * @private
     */
    _fetchUpdates() {
        // Build URL with query parameters
        const url = new URL('/api/realtime/updates', window.location.origin);
        url.searchParams.append('since', this.lastSyncTime.toISOString());
        url.searchParams.append('limit', 20);
        
        // Fetch updates
        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.updates && data.updates.length > 0) {
                    // Process updates
                    this.options.updateHandler(data.updates);
                    
                    // Update last sync time
                    this.lastSyncTime = new Date();
                    
                    // Show notification about new updates
                    this._showNotification({
                        type: 'updates',
                        message: `${data.updates.length} new property updates`,
                        timestamp: this.lastSyncTime.toISOString(),
                        details: {
                            count: data.updates.length,
                            types: this._countUpdateTypes(data.updates)
                        }
                    });
                }
            })
            .catch(error => {
                console.error('Error fetching updates:', error);
            });
            
        // Fetch notifications
        this._fetchNotifications();
    }
    
    /**
     * Fetch property notifications
     * @private
     */
    _fetchNotifications() {
        // Only fetch if notifications are enabled
        if (!this.options.notificationsEnabled) return;
        
        // Build URL with query parameters
        const url = new URL('/api/realtime/notifications', window.location.origin);
        url.searchParams.append('since_id', this.lastNotificationId);
        url.searchParams.append('limit', 5);
        
        // Fetch notifications
        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.notifications && data.notifications.length > 0) {
                    // Get the highest notification ID
                    const maxId = Math.max(...data.notifications.map(n => n.id));
                    this.lastNotificationId = Math.max(this.lastNotificationId, maxId);
                    
                    // Show notifications
                    data.notifications.forEach(notification => {
                        this._showNotification(notification);
                    });
                }
            })
            .catch(error => {
                console.error('Error fetching notifications:', error);
            });
    }
    
    /**
     * Initialize notifications container
     * @private
     */
    _initializeNotifications() {
        // Create a custom Leaflet control for notifications
        this.notificationContainer = L.control({ position: this.options.notificationPosition });
        
        this.notificationContainer.onAdd = (map) => {
            const container = L.DomUtil.create('div', 'realtime-notifications');
            container.innerHTML = `
                <div class="notifications-header">
                    <h6>Real-time Updates</h6>
                    <button class="notifications-toggle" title="Toggle notifications"><i class="fas fa-bell"></i></button>
                </div>
                <div class="notifications-list"></div>
            `;
            
            // Prevent map interactions when using the control
            L.DomEvent.disableClickPropagation(container);
            L.DomEvent.disableScrollPropagation(container);
            
            // Add event listeners
            setTimeout(() => {
                const toggleButton = container.querySelector('.notifications-toggle');
                
                if (toggleButton) {
                    toggleButton.addEventListener('click', () => {
                        container.classList.toggle('notifications-collapsed');
                    });
                }
            }, 100);
            
            return container;
        };
    }
    
    /**
     * Show a notification
     * @param {Object} notification - Notification object
     * @param {boolean} temporary - Whether to show a temporary notification
     * @private
     */
    _showNotification(notification, temporary = false) {
        // Skip if notifications are disabled
        if (!this.options.notificationsEnabled && !temporary) return;
        
        // Create notification element if container exists
        if (this.notificationContainer) {
            const container = this.notificationContainer.getContainer();
            if (!container) return;
            
            const notificationsList = container.querySelector('.notifications-list');
            if (!notificationsList) return;
            
            // Create notification element
            const notificationElement = document.createElement('div');
            notificationElement.className = `notification notification-${notification.type || 'info'}`;
            
            // Format timestamp
            let formattedTime;
            try {
                const timestamp = new Date(notification.timestamp);
                formattedTime = timestamp.toLocaleTimeString();
            } catch (e) {
                formattedTime = 'Now';
            }
            
            // Create notification content
            notificationElement.innerHTML = `
                <div class="notification-header">
                    <span class="notification-type">${this._formatNotificationType(notification.type || 'info')}</span>
                    <span class="notification-time">${formattedTime}</span>
                </div>
                <div class="notification-message">${notification.message}</div>
                ${notification.details ? `
                <div class="notification-details">
                    ${this._formatNotificationDetails(notification.details)}
                </div>
                ` : ''}
            `;
            
            // Add to notification list
            notificationsList.prepend(notificationElement);
            
            // Limit number of notifications
            const notifications = notificationsList.querySelectorAll('.notification');
            if (notifications.length > 5) {
                for (let i = 5; i < notifications.length; i++) {
                    notifications[i].remove();
                }
            }
            
            // Auto-remove temporary notifications
            if (temporary) {
                setTimeout(() => {
                    notificationElement.classList.add('notification-hiding');
                    setTimeout(() => {
                        notificationElement.remove();
                    }, 500);
                }, 5000);
            }
            
            // Add hiding animation after delay
            setTimeout(() => {
                notificationElement.classList.add('notification-visible');
            }, 10);
        }
        
        // Also log to console
        console.log(`[Realtime] ${notification.message}`);
    }
    
    /**
     * Format notification type for display
     * @param {string} type - Notification type
     * @returns {string} Formatted type
     * @private
     */
    _formatNotificationType(type) {
        switch (type) {
            case 'info':
                return '<i class="fas fa-info-circle"></i> Info';
            case 'success':
                return '<i class="fas fa-check-circle"></i> Success';
            case 'error':
                return '<i class="fas fa-exclamation-circle"></i> Error';
            case 'updates':
                return '<i class="fas fa-sync"></i> Updates';
            case 'property_values':
                return '<i class="fas fa-home"></i> Values';
            case 'property_sales':
                return '<i class="fas fa-tags"></i> Sales';
            case 'tax_data':
                return '<i class="fas fa-file-invoice-dollar"></i> Tax Data';
            default:
                return '<i class="fas fa-bell"></i> Notification';
        }
    }
    
    /**
     * Format notification details for display
     * @param {Object} details - Notification details
     * @returns {string} Formatted details HTML
     * @private
     */
    _formatNotificationDetails(details) {
        if (!details) return '';
        
        // Handle different types of details
        if (details.count !== undefined && details.types) {
            // Update notification with type counts
            let typesHtml = '';
            for (const [type, count] of Object.entries(details.types)) {
                typesHtml += `<div class="detail-item"><span>${this._formatUpdateType(type)}</span><span>${count}</span></div>`;
            }
            
            return typesHtml;
        } else if (details.sync_type) {
            // Sync notification
            return `<div class="detail-item"><span>Type</span><span>${details.sync_type}</span></div>`;
        }
        
        // Generic details
        let detailsHtml = '';
        for (const [key, value] of Object.entries(details)) {
            detailsHtml += `<div class="detail-item"><span>${key}</span><span>${value}</span></div>`;
        }
        
        return detailsHtml;
    }
    
    /**
     * Format update type for display
     * @param {string} type - Update type
     * @returns {string} Formatted type
     * @private
     */
    _formatUpdateType(type) {
        switch (type) {
            case 'property_value':
                return 'Values';
            case 'property_sale':
                return 'Sales';
            case 'tax_data':
                return 'Tax Data';
            default:
                return type;
        }
    }
    
    /**
     * Count update types
     * @param {Array} updates - Array of update objects
     * @returns {Object} Object with type counts
     * @private
     */
    _countUpdateTypes(updates) {
        const typeCounts = {};
        
        updates.forEach(update => {
            const type = update.type || 'unknown';
            typeCounts[type] = (typeCounts[type] || 0) + 1;
        });
        
        return typeCounts;
    }
    
    /**
     * Default update handler - highlights updated properties on the map
     * @param {Array} updates - Array of update objects
     * @private
     */
    _defaultUpdateHandler(updates) {
        // Clear existing highlight markers
        this.updatesLayer.clearLayers();
        
        // Process each update
        updates.forEach(update => {
            // Find the property on the map and highlight it
            // This is a simplified version - in practice, you would need to
            // find the actual property by ID and highlight it
            if (update.latitude && update.longitude) {
                // If the update has coordinates, create a highlight marker
                const marker = L.circleMarker([update.latitude, update.longitude], {
                    radius: 20,
                    color: this._getUpdateTypeColor(update.type),
                    weight: 3,
                    opacity: 0.8,
                    fill: false,
                    className: 'update-highlight'
                });
                
                // Add to layer
                this.updatesLayer.addLayer(marker);
                
                // Auto-remove after animation
                setTimeout(() => {
                    marker.remove();
                }, 5000);
            }
        });
    }
    
    /**
     * Get color for update type
     * @param {string} type - Update type
     * @returns {string} Color code
     * @private
     */
    _getUpdateTypeColor(type) {
        switch (type) {
            case 'property_value':
                return '#3498db'; // Blue
            case 'property_sale':
                return '#2ecc71'; // Green
            case 'tax_data':
                return '#f39c12'; // Orange
            default:
                return '#95a5a6'; // Gray
        }
    }
}
