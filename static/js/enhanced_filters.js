/**
 * Enhanced Property Filtering
 * 
 * This module provides advanced filtering capabilities for property data visualization,
 * including multi-criteria filters, saved filters, and dynamic filter suggestions.
 */

class EnhancedPropertyFilters {
    /**
     * Initialize enhanced property filters
     * @param {Object} mapInstance - The Leaflet map instance
     * @param {Function} dataRefreshCallback - Callback function to refresh data with filters
     * @param {Object} options - Configuration options
     */
    constructor(mapInstance, dataRefreshCallback, options = {}) {
        this.map = mapInstance;
        this.dataRefreshCallback = dataRefreshCallback;
        this.activeFilters = {};
        this.savedFilters = [];
        this.filterHistory = [];
        this.filterContainer = null;
        
        // Configure options with defaults
        this.options = {
            storageKey: options.storageKey || 'property_filters',
            maxSavedFilters: options.maxSavedFilters || 5,
            maxFilterHistory: options.maxFilterHistory || 10,
            suggestionsEnabled: options.suggestionsEnabled !== undefined ? options.suggestionsEnabled : true,
            controlPosition: options.controlPosition || 'topleft'
        };
        
        // Load saved filters from localStorage
        this._loadSavedFilters();
        
        // Initialize filter control
        this._initializeFilterControl();
    }
    
    /**
     * Apply a filter to the property data
     * @param {string} type - Filter type
     * @param {string} operator - Filter operator
     * @param {*} value - Filter value
     * @param {boolean} refresh - Whether to refresh data immediately
     */
    applyFilter(type, operator, value, refresh = true) {
        // Create filter key
        const filterKey = `${type}:${operator}`;
        
        // Add to active filters
        this.activeFilters[filterKey] = value;
        
        // Add to filter history
        this._addToFilterHistory({
            type,
            operator,
            value
        });
        
        // Update filter display
        this._updateFilterDisplay();
        
        // Refresh data if requested
        if (refresh) {
            this.refreshData();
        }
    }
    
    /**
     * Remove a filter
     * @param {string} filterKey - Filter key to remove
     * @param {boolean} refresh - Whether to refresh data immediately
     */
    removeFilter(filterKey, refresh = true) {
        // Remove from active filters
        if (this.activeFilters[filterKey]) {
            delete this.activeFilters[filterKey];
        }
        
        // Update filter display
        this._updateFilterDisplay();
        
        // Refresh data if requested
        if (refresh) {
            this.refreshData();
        }
    }
    
    /**
     * Clear all active filters
     * @param {boolean} refresh - Whether to refresh data immediately
     */
    clearFilters(refresh = true) {
        // Clear active filters
        this.activeFilters = {};
        
        // Update filter display
        this._updateFilterDisplay();
        
        // Refresh data if requested
        if (refresh) {
            this.refreshData();
        }
    }
    
    /**
     * Save current filter set
     * @param {string} name - Name for the saved filter set
     * @returns {boolean} Whether the filter was saved successfully
     */
    saveCurrentFilters(name) {
        // Don't save if no active filters
        if (Object.keys(this.activeFilters).length === 0) {
            return false;
        }
        
        // Create saved filter object
        const savedFilter = {
            id: Date.now().toString(),
            name: name || `Filter ${this.savedFilters.length + 1}`,
            filters: { ...this.activeFilters },
            created: new Date().toISOString()
        };
        
        // Add to saved filters
        this.savedFilters.unshift(savedFilter);
        
        // Limit number of saved filters
        if (this.savedFilters.length > this.options.maxSavedFilters) {
            this.savedFilters = this.savedFilters.slice(0, this.options.maxSavedFilters);
        }
        
        // Save to localStorage
        this._saveSavedFilters();
        
        // Update filter display
        this._updateSavedFiltersDisplay();
        
        return true;
    }
    
    /**
     * Load a saved filter set
     * @param {string} filterId - ID of the saved filter to load
     */
    loadSavedFilter(filterId) {
        // Find the saved filter
        const savedFilter = this.savedFilters.find(f => f.id === filterId);
        if (!savedFilter) return;
        
        // Apply the saved filters
        this.activeFilters = { ...savedFilter.filters };
        
        // Update filter display
        this._updateFilterDisplay();
        
        // Refresh data
        this.refreshData();
    }
    
    /**
     * Delete a saved filter set
     * @param {string} filterId - ID of the saved filter to delete
     */
    deleteSavedFilter(filterId) {
        // Remove the saved filter
        this.savedFilters = this.savedFilters.filter(f => f.id !== filterId);
        
        // Save to localStorage
        this._saveSavedFilters();
        
        // Update filter display
        this._updateSavedFiltersDisplay();
    }
    
    /**
     * Get filter suggestions based on current data and filters
     * @returns {Array} Array of filter suggestions
     */
    getFilterSuggestions() {
        // This would typically use the current dataset and filter history
        // to suggest relevant filters based on patterns and property distributions
        
        // For demonstration, return some static suggestions
        return [
            { type: 'property_type', operator: 'equals', value: 'Residential', label: 'Residential Properties' },
            { type: 'assessed_value', operator: 'greater_than', value: 500000, label: 'Premium Properties (>$500K)' },
            { type: 'property_city', operator: 'equals', value: 'Richland', label: 'Richland Properties' }
        ];
    }
    
    /**
     * Refresh data with current filters
     */
    refreshData() {
        // Convert active filters to query parameters
        const filterParams = this._convertFiltersToParams();
        
        // Call the refresh callback with filter parameters
        if (this.dataRefreshCallback) {
            this.dataRefreshCallback(filterParams);
        }
    }
    
    /**
     * Initialize the filter control
     * @private
     */
    _initializeFilterControl() {
        // Create a custom Leaflet control for filters
        this.filterContainer = L.control({ position: this.options.controlPosition });
        
        this.filterContainer.onAdd = (map) => {
            const container = L.DomUtil.create('div', 'enhanced-filters-control');
            container.innerHTML = `
                <div class="filters-header">
                    <h6>Enhanced Filters</h6>
                    <button class="filters-toggle" title="Toggle filters"><i class="fas fa-filter"></i></button>
                </div>
                <div class="filters-content">
                    <div class="active-filters">
                        <div class="filters-section-header">
                            <h7>Active Filters</h7>
                            <button class="clear-filters-btn" title="Clear all filters">Clear All</button>
                        </div>
                        <div class="active-filters-list">
                            <div class="no-filters-message">No active filters</div>
                        </div>
                    </div>
                    
                    <div class="filter-builder">
                        <div class="filters-section-header">
                            <h7>Add Filter</h7>
                        </div>
                        <div class="filter-builder-form">
                            <select class="filter-type-select">
                                <option value="property_type">Property Type</option>
                                <option value="assessed_value">Assessed Value</option>
                                <option value="property_city">City</option>
                                <option value="tax_status">Tax Status</option>
                            </select>
                            <select class="filter-operator-select">
                                <option value="equals">Equals</option>
                                <option value="not_equals">Not Equals</option>
                                <option value="greater_than">Greater Than</option>
                                <option value="less_than">Less Than</option>
                                <option value="contains">Contains</option>
                            </select>
                            <input type="text" class="filter-value-input" placeholder="Value">
                            <button class="add-filter-btn">Add</button>
                        </div>
                    </div>
                    
                    <div class="saved-filters">
                        <div class="filters-section-header">
                            <h7>Saved Filters</h7>
                            <button class="save-current-filters-btn" title="Save current filters">Save Current</button>
                        </div>
                        <div class="saved-filters-list"></div>
                    </div>
                    
                    <div class="filter-suggestions">
                        <div class="filters-section-header">
                            <h7>Suggested Filters</h7>
                        </div>
                        <div class="filter-suggestions-list"></div>
                    </div>
                </div>
            `;
            
            // Prevent map interactions when using the control
            L.DomEvent.disableClickPropagation(container);
            L.DomEvent.disableScrollPropagation(container);
            
            // Add event listeners
            setTimeout(() => {
                // Toggle filter panel
                const toggleButton = container.querySelector('.filters-toggle');
                if (toggleButton) {
                    toggleButton.addEventListener('click', () => {
                        container.classList.toggle('filters-collapsed');
                    });
                }
                
                // Clear filters button
                const clearButton = container.querySelector('.clear-filters-btn');
                if (clearButton) {
                    clearButton.addEventListener('click', () => {
                        this.clearFilters(true);
                    });
                }
                
                // Add filter button
                const addFilterButton = container.querySelector('.add-filter-btn');
                if (addFilterButton) {
                    addFilterButton.addEventListener('click', () => {
                        const type = container.querySelector('.filter-type-select').value;
                        const operator = container.querySelector('.filter-operator-select').value;
                        const value = container.querySelector('.filter-value-input').value;
                        
                        if (value) {
                            this.applyFilter(type, operator, value, true);
                            container.querySelector('.filter-value-input').value = '';
                        }
                    });
                }
                
                // Save current filters button
                const saveButton = container.querySelector('.save-current-filters-btn');
                if (saveButton) {
                    saveButton.addEventListener('click', () => {
                        const name = prompt('Enter a name for this filter set:', `Filter ${this.savedFilters.length + 1}`);
                        if (name) {
                            this.saveCurrentFilters(name);
                        }
                    });
                }
            }, 100);
            
            // Initialize displays
            this._updateFilterDisplay();
            this._updateSavedFiltersDisplay();
            this._updateFilterSuggestions();
            
            return container;
        };
    }
    
    /**
     * Add the filter control to the map
     */
    addTo(map) {
        if (this.filterContainer) {
            this.filterContainer.addTo(map || this.map);
        }
    }
    
    /**
     * Remove the filter control from the map
     */
    remove() {
        if (this.filterContainer) {
            this.filterContainer.remove();
        }
    }
    
    /**
     * Update the active filters display
     * @private
     */
    _updateFilterDisplay() {
        const container = this.filterContainer ? this.filterContainer.getContainer() : null;
        if (!container) return;
        
        const activeFiltersList = container.querySelector('.active-filters-list');
        if (!activeFiltersList) return;
        
        // Clear existing filters
        activeFiltersList.innerHTML = '';
        
        // Get active filters
        const filterKeys = Object.keys(this.activeFilters);
        
        if (filterKeys.length === 0) {
            // Show no filters message
            activeFiltersList.innerHTML = '<div class="no-filters-message">No active filters</div>';
            return;
        }
        
        // Add each active filter
        filterKeys.forEach(key => {
            const [type, operator] = key.split(':');
            const value = this.activeFilters[key];
            
            const filterElement = document.createElement('div');
            filterElement.className = 'active-filter';
            filterElement.innerHTML = `
                <span class="filter-description">${this._formatFilterDescription(type, operator, value)}</span>
                <button class="remove-filter-btn" data-filter-key="${key}" title="Remove filter">&times;</button>
            `;
            
            // Add click handler for remove button
            const removeButton = filterElement.querySelector('.remove-filter-btn');
            if (removeButton) {
                removeButton.addEventListener('click', () => {
                    this.removeFilter(key, true);
                });
            }
            
            activeFiltersList.appendChild(filterElement);
        });
    }
    
    /**
     * Update the saved filters display
     * @private
     */
    _updateSavedFiltersDisplay() {
        const container = this.filterContainer ? this.filterContainer.getContainer() : null;
        if (!container) return;
        
        const savedFiltersList = container.querySelector('.saved-filters-list');
        if (!savedFiltersList) return;
        
        // Clear existing saved filters
        savedFiltersList.innerHTML = '';
        
        if (this.savedFilters.length === 0) {
            // Show no saved filters message
            savedFiltersList.innerHTML = '<div class="no-filters-message">No saved filters</div>';
            return;
        }
        
        // Add each saved filter
        this.savedFilters.forEach(filter => {
            const filterElement = document.createElement('div');
            filterElement.className = 'saved-filter';
            
            // Format date
            let formattedDate;
            try {
                const date = new Date(filter.created);
                formattedDate = date.toLocaleDateString();
            } catch (e) {
                formattedDate = 'Unknown';
            }
            
            // Count filters
            const filterCount = Object.keys(filter.filters).length;
            
            filterElement.innerHTML = `
                <div class="saved-filter-header">
                    <span class="saved-filter-name">${filter.name}</span>
                    <span class="saved-filter-count">${filterCount} filter${filterCount !== 1 ? 's' : ''}</span>
                </div>
                <div class="saved-filter-info">
                    <span class="saved-filter-date">${formattedDate}</span>
                    <div class="saved-filter-actions">
                        <button class="load-filter-btn" data-filter-id="${filter.id}" title="Load filter">Apply</button>
                        <button class="delete-filter-btn" data-filter-id="${filter.id}" title="Delete filter">Delete</button>
                    </div>
                </div>
            `;
            
            // Add click handlers
            const loadButton = filterElement.querySelector('.load-filter-btn');
            if (loadButton) {
                loadButton.addEventListener('click', () => {
                    this.loadSavedFilter(filter.id);
                });
            }
            
            const deleteButton = filterElement.querySelector('.delete-filter-btn');
            if (deleteButton) {
                deleteButton.addEventListener('click', () => {
                    if (confirm(`Delete saved filter "${filter.name}"?`)) {
                        this.deleteSavedFilter(filter.id);
                    }
                });
            }
            
            savedFiltersList.appendChild(filterElement);
        });
    }
    
    /**
     * Update the filter suggestions display
     * @private
     */
    _updateFilterSuggestions() {
        if (!this.options.suggestionsEnabled) return;
        
        const container = this.filterContainer ? this.filterContainer.getContainer() : null;
        if (!container) return;
        
        const suggestionsList = container.querySelector('.filter-suggestions-list');
        if (!suggestionsList) return;
        
        // Clear existing suggestions
        suggestionsList.innerHTML = '';
        
        // Get suggestions
        const suggestions = this.getFilterSuggestions();
        
        if (suggestions.length === 0) {
            // Show no suggestions message
            suggestionsList.innerHTML = '<div class="no-filters-message">No suggestions available</div>';
            return;
        }
        
        // Add each suggestion
        suggestions.forEach(suggestion => {
            const suggestionElement = document.createElement('div');
            suggestionElement.className = 'filter-suggestion';
            suggestionElement.innerHTML = `
                <span class="filter-suggestion-label">${suggestion.label}</span>
                <button class="apply-suggestion-btn" title="Apply suggestion">Apply</button>
            `;
            
            // Add click handler
            const applyButton = suggestionElement.querySelector('.apply-suggestion-btn');
            if (applyButton) {
                applyButton.addEventListener('click', () => {
                    this.applyFilter(suggestion.type, suggestion.operator, suggestion.value, true);
                });
            }
            
            suggestionsList.appendChild(suggestionElement);
        });
    }
    
    /**
     * Format a filter description for display
     * @param {string} type - Filter type
     * @param {string} operator - Filter operator
     * @param {*} value - Filter value
     * @returns {string} Formatted description
     * @private
     */
    _formatFilterDescription(type, operator, value) {
        // Format type
        let formattedType;
        switch (type) {
            case 'property_type':
                formattedType = 'Property Type';
                break;
            case 'assessed_value':
                formattedType = 'Assessed Value';
                break;
            case 'property_city':
                formattedType = 'City';
                break;
            case 'tax_status':
                formattedType = 'Tax Status';
                break;
            default:
                formattedType = type.replace(/_/g, ' ');
        }
        
        // Format operator
        let formattedOperator;
        switch (operator) {
            case 'equals':
                formattedOperator = 'is';
                break;
            case 'not_equals':
                formattedOperator = 'is not';
                break;
            case 'greater_than':
                formattedOperator = 'is greater than';
                break;
            case 'less_than':
                formattedOperator = 'is less than';
                break;
            case 'contains':
                formattedOperator = 'contains';
                break;
            default:
                formattedOperator = operator.replace(/_/g, ' ');
        }
        
        // Format value
        let formattedValue = value;
        if (type === 'assessed_value') {
            // Format as currency
            try {
                formattedValue = new Intl.NumberFormat('en-US', {
                    style: 'currency',
                    currency: 'USD',
                    maximumFractionDigits: 0
                }).format(parseFloat(value));
            } catch (e) {
                // Use original value if parsing fails
            }
        }
        
        // Combine into description
        return `${formattedType} ${formattedOperator} ${formattedValue}`;
    }
    
    /**
     * Convert active filters to query parameters
     * @returns {Object} Object with query parameters
     * @private
     */
    _convertFiltersToParams() {
        const params = {};
        
        // Process each active filter
        Object.entries(this.activeFilters).forEach(([key, value]) => {
            const [type, operator] = key.split(':');
            
            // Handle different filter types and operators
            switch (type) {
                case 'property_type':
                    if (operator === 'equals') {
                        params.property_types = value;
                    }
                    break;
                    
                case 'assessed_value':
                    if (operator === 'greater_than') {
                        params.value_filter = `${value}+`;
                    } else if (operator === 'less_than') {
                        params.value_filter = `0-${value}`;
                    }
                    break;
                    
                case 'property_city':
                    if (operator === 'equals') {
                        params.city = value;
                    }
                    break;
                    
                // Add more cases for other filter types
            }
        });
        
        return params;
    }
    
    /**
     * Add a filter to the history
     * @param {Object} filter - Filter object
     * @private
     */
    _addToFilterHistory(filter) {
        // Add to history
        this.filterHistory.unshift({
            ...filter,
            timestamp: new Date().toISOString()
        });
        
        // Limit history size
        if (this.filterHistory.length > this.options.maxFilterHistory) {
            this.filterHistory = this.filterHistory.slice(0, this.options.maxFilterHistory);
        }
    }
    
    /**
     * Load saved filters from localStorage
     * @private
     */
    _loadSavedFilters() {
        try {
            const savedFilters = localStorage.getItem(this.options.storageKey);
            if (savedFilters) {
                this.savedFilters = JSON.parse(savedFilters);
            }
        } catch (e) {
            console.error('Error loading saved filters:', e);
            this.savedFilters = [];
        }
    }
    
    /**
     * Save filters to localStorage
     * @private
     */
    _saveSavedFilters() {
        try {
            localStorage.setItem(this.options.storageKey, JSON.stringify(this.savedFilters));
        } catch (e) {
            console.error('Error saving filters:', e);
        }
    }
}
