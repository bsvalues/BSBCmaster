/**
 * MCP Assessor Agent API - Frontend JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // Check API health on page load
    updateDatabaseStatus();
    
    // Set up refresh button listener
    const refreshButton = document.getElementById('refresh-status');
    if (refreshButton) {
        refreshButton.addEventListener('click', updateDatabaseStatus);
    }
    
    // Load API documentation if available
    loadApiDocumentation();
    
    // Set up periodic health checks
    setInterval(updateDatabaseStatus, 30000); // Every 30 seconds
});

/**
 * Update the API and database status indicators
 */
function updateDatabaseStatus() {
    fetch('/api/health')
        .then(response => response.json())
        .then(data => {
            // Update overall status
            const statusBadge = document.getElementById('status-badge');
            if (data.status === 'success') {
                statusBadge.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i>Healthy';
                statusBadge.className = 'badge bg-success';
            } else {
                statusBadge.innerHTML = '<i class="bi bi-x-circle-fill me-1"></i>Unhealthy';
                statusBadge.className = 'badge bg-danger';
            }
            
            // Update database connection statuses
            const postgresStatus = document.getElementById('postgres-status');
            if (data.database_status && data.database_status.postgres) {
                postgresStatus.innerHTML = '<i class="bi bi-database-check me-1"></i>Connected';
                postgresStatus.className = 'badge bg-success';
            } else {
                postgresStatus.innerHTML = '<i class="bi bi-database-x me-1"></i>Disconnected';
                postgresStatus.className = 'badge bg-danger';
            }
            
            const mssqlStatus = document.getElementById('mssql-status');
            if (data.database_status && data.database_status.mssql) {
                mssqlStatus.innerHTML = '<i class="bi bi-database-check me-1"></i>Connected';
                mssqlStatus.className = 'badge bg-success';
            } else {
                mssqlStatus.innerHTML = '<i class="bi bi-database-x me-1"></i>Disconnected';
                mssqlStatus.className = 'badge bg-warning';
                // MSSQL is optional in this application, so use warning instead of danger
            }
        })
        .catch(error => {
            console.error('Error checking API health:', error);
            const statusBadge = document.getElementById('status-badge');
            if (statusBadge) {
                statusBadge.innerHTML = '<i class="bi bi-exclamation-triangle-fill me-1"></i>Error';
                statusBadge.className = 'badge bg-danger';
            }
            
            const postgresStatus = document.getElementById('postgres-status');
            if (postgresStatus) {
                postgresStatus.innerHTML = '<i class="bi bi-question-circle-fill me-1"></i>Unknown';
                postgresStatus.className = 'badge bg-secondary';
            }
            
            const mssqlStatus = document.getElementById('mssql-status');
            if (mssqlStatus) {
                mssqlStatus.innerHTML = '<i class="bi bi-question-circle-fill me-1"></i>Unknown';
                mssqlStatus.className = 'badge bg-secondary';
            }
        });
}

/**
 * Load API documentation from the /api/docs endpoint
 */
function loadApiDocumentation() {
    fetch('/api/docs')
        .then(response => response.json())
        .then(data => {
            // Update version
            const versionBadge = document.querySelector('.badge.bg-secondary');
            if (versionBadge && data.version) {
                versionBadge.textContent = 'v' + data.version;
            }
            
            // Update description
            const descElement = document.querySelector('p.lead.text-muted');
            if (descElement && data.description) {
                descElement.textContent = data.description;
            }
            
            // If there are endpoints defined in the documentation
            if (data.endpoints && Array.isArray(data.endpoints)) {
                console.log('Found ' + data.endpoints.length + ' API endpoints in documentation');
                
                // Update auth header name if provided
                if (data.authentication && data.authentication.header) {
                    const authHeaderElements = document.querySelectorAll('code:contains("' + data.authentication.header + '")');
                    authHeaderElements.forEach(element => {
                        // No need to update as we're already passing this from Flask
                    });
                }
                
                // Add authenticated badges to endpoints
                data.endpoints.forEach(endpoint => {
                    if (endpoint.auth_required) {
                        // No need to update as we're already setting this in the template
                    }
                });
            }
            
            // Update database status if provided
            if (data.db_connections) {
                updateDatabaseStatusFromData(data);
            }
        })
        .catch(error => {
            console.error('Error loading API documentation:', error);
        });
}

/**
 * Helper function to update database status from API data
 */
function updateDatabaseStatusFromData(data) {
    // Only update if the health data is available
    if (data.status && data.database_status) {
        // Update overall status
        const statusBadge = document.getElementById('status-badge');
        if (statusBadge) {
            if (data.status === 'success') {
                statusBadge.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i>Healthy';
                statusBadge.className = 'badge bg-success';
            } else {
                statusBadge.innerHTML = '<i class="bi bi-x-circle-fill me-1"></i>Unhealthy';
                statusBadge.className = 'badge bg-danger';
            }
        }
        
        // Update database connection statuses
        const postgresStatus = document.getElementById('postgres-status');
        if (postgresStatus && data.database_status.postgres !== undefined) {
            if (data.database_status.postgres) {
                postgresStatus.innerHTML = '<i class="bi bi-database-check me-1"></i>Connected';
                postgresStatus.className = 'badge bg-success';
            } else {
                postgresStatus.innerHTML = '<i class="bi bi-database-x me-1"></i>Disconnected';
                postgresStatus.className = 'badge bg-danger';
            }
        }
        
        const mssqlStatus = document.getElementById('mssql-status');
        if (mssqlStatus && data.database_status.mssql !== undefined) {
            if (data.database_status.mssql) {
                mssqlStatus.innerHTML = '<i class="bi bi-database-check me-1"></i>Connected';
                mssqlStatus.className = 'badge bg-success';
            } else {
                mssqlStatus.innerHTML = '<i class="bi bi-database-x me-1"></i>Disconnected';
                mssqlStatus.className = 'badge bg-warning';
            }
        }
    }
}

/**
 * Initialize tabs and pills for code examples
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tabs and pills
    const codeExampleTabs = document.querySelectorAll('[data-bs-toggle="tab"], [data-bs-toggle="pill"]');
    codeExampleTabs.forEach(tab => {
        tab.addEventListener('shown.bs.tab', function (event) {
            console.log('Tab activated:', event.target.id);
        });
        
        // Create Bootstrap tab objects
        if (typeof bootstrap !== 'undefined') {
            new bootstrap.Tab(tab);
        }
    });
    
    // Syntax highlighting (if we add a library later)
    const codeBlocks = document.querySelectorAll('pre code');
    if (codeBlocks.length > 0) {
        console.log(`Found ${codeBlocks.length} code blocks for syntax highlighting`);
        // If we add a syntax highlighting library later, initialize it here
    }
    
    // Initialize the database schema viewer
    loadDatabaseSchema();
    
    // Set up refresh schema button
    const refreshSchemaButton = document.getElementById('refresh-schema');
    if (refreshSchemaButton) {
        refreshSchemaButton.addEventListener('click', loadDatabaseSchema);
    }
    
    // Initialize the query builder
    initQueryBuilder();
    
    // Initialize natural language to SQL feature
    initNaturalLanguageToSQL();
    
    // Initialize data visualization
    initDataVisualization();
});

/**
 * Load database schema information and populate the schema viewer
 */
function loadDatabaseSchema() {
    const tableListContainer = document.getElementById('schema-table-list');
    const tableDetailsContainer = document.getElementById('table-details');
    
    if (!tableListContainer || !tableDetailsContainer) return;
    
    // Show loading spinner
    tableListContainer.innerHTML = `
        <div class="d-flex justify-content-center p-3">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>
    `;
    
    // Reset table details
    tableDetailsContainer.innerHTML = `
        <div class="text-center text-muted">
            <i class="bi bi-arrow-left-circle fs-4"></i>
            <p>Select a table to view its structure</p>
        </div>
    `;
    
    // Fetch schema summary from API (this is a public endpoint for demonstration)
    fetch('/api/schema-summary?db=postgres')
        .then(response => {
            if (!response.ok) {
                if (response.status === 401 || response.status === 403) {
                    throw new Error('Authentication required. Please provide a valid API key.');
                }
                throw new Error('Failed to load schema information');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success' && data.summary && Array.isArray(data.summary)) {
                // Clear loading spinner
                tableListContainer.innerHTML = '';
                
                // Sort tables alphabetically
                const sortedTables = [...data.summary].sort();
                
                // Create table list
                sortedTables.forEach(tableName => {
                    const tableItem = document.createElement('a');
                    tableItem.href = '#';
                    tableItem.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
                    tableItem.innerHTML = `
                        <span>
                            <i class="bi bi-table me-2"></i>
                            ${tableName}
                        </span>
                        <i class="bi bi-chevron-right"></i>
                    `;
                    
                    tableItem.addEventListener('click', (e) => {
                        e.preventDefault();
                        loadTableDetails(tableName);
                        
                        // Update active state
                        document.querySelectorAll('#schema-table-list .list-group-item').forEach(item => {
                            item.classList.remove('active');
                        });
                        tableItem.classList.add('active');
                    });
                    
                    tableListContainer.appendChild(tableItem);
                });
                
                // Display message if no tables found
                if (sortedTables.length === 0) {
                    tableListContainer.innerHTML = `
                        <div class="text-center text-muted p-3">
                            <i class="bi bi-exclamation-circle fs-4"></i>
                            <p>No tables found in the database</p>
                        </div>
                    `;
                }
            } else {
                throw new Error('Invalid schema data received');
            }
        })
        .catch(error => {
            tableListContainer.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    ${error.message}
                </div>
                <div class="text-center mt-3">
                    <button id="retry-schema" class="btn btn-sm btn-outline-primary">
                        <i class="bi bi-arrow-repeat me-1"></i>
                        Retry
                    </button>
                </div>
            `;
            
            // Add retry button listener
            const retryButton = document.getElementById('retry-schema');
            if (retryButton) {
                retryButton.addEventListener('click', loadDatabaseSchema);
            }
        });
}

/**
 * Load detailed information about a specific table
 */
function loadTableDetails(tableName) {
    const tableDetailsContainer = document.getElementById('table-details');
    if (!tableDetailsContainer) return;
    
    // Show loading state
    tableDetailsContainer.innerHTML = `
        <div class="d-flex justify-content-center p-3">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <span class="ms-2">Loading table structure...</span>
        </div>
    `;
    
    // Fetch detailed schema information for the selected table
    fetch('/api/discover-schema?db=postgres')
        .then(response => {
            if (!response.ok) {
                if (response.status === 401 || response.status === 403) {
                    throw new Error('Authentication required. Please provide a valid API key.');
                }
                throw new Error('Failed to load table details');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success' && data.db_schema && Array.isArray(data.db_schema)) {
                // Filter schema items for the selected table
                const tableColumns = data.db_schema.filter(item => item.table_name === tableName);
                
                if (tableColumns.length > 0) {
                    // Sort columns by name
                    tableColumns.sort((a, b) => a.column_name.localeCompare(b.column_name));
                    
                    // Build table details HTML
                    let detailsHtml = `
                        <h5 class="mb-3">
                            <i class="bi bi-table me-2"></i>
                            ${tableName}
                        </h5>
                        <div class="table-responsive">
                            <table class="table table-sm table-striped">
                                <thead>
                                    <tr>
                                        <th>Column</th>
                                        <th>Type</th>
                                    </tr>
                                </thead>
                                <tbody>
                    `;
                    
                    tableColumns.forEach(column => {
                        detailsHtml += `
                            <tr>
                                <td>${column.column_name}</td>
                                <td><code>${column.data_type}</code></td>
                            </tr>
                        `;
                    });
                    
                    detailsHtml += `
                                </tbody>
                            </table>
                        </div>
                        <div class="mt-3">
                            <div class="alert alert-secondary">
                                <strong>Example query:</strong>
                                <pre class="mb-0"><code>SELECT * FROM ${tableName} LIMIT 10;</code></pre>
                            </div>
                        </div>
                    `;
                    
                    tableDetailsContainer.innerHTML = detailsHtml;
                } else {
                    tableDetailsContainer.innerHTML = `
                        <div class="alert alert-warning">
                            <i class="bi bi-exclamation-circle me-2"></i>
                            No columns found for table "${tableName}"
                        </div>
                    `;
                }
            } else {
                throw new Error('Invalid schema data received');
            }
        })
        .catch(error => {
            tableDetailsContainer.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    ${error.message}
                </div>
            `;
        });
}

/**
 * Initialize the query builder component
 */
function initQueryBuilder() {
    const tableSelect = document.getElementById('queryBuilderTable');
    const columnsSelect = document.getElementById('queryBuilderColumns');
    const limitInput = document.getElementById('queryBuilderLimit');
    const addConditionBtn = document.getElementById('addCondition');
    const conditionsContainer = document.getElementById('queryConditions');
    const generatedQueryEl = document.getElementById('generatedQuery');
    const runQueryBtn = document.getElementById('runQuery');
    const copyQueryBtn = document.getElementById('copyQuery');
    const queryResultsContainer = document.getElementById('queryResults');
    
    if (!tableSelect || !columnsSelect) return;
    
    // Global state for query builder
    const queryState = {
        selectedTable: '',
        selectedColumns: [],
        conditions: [],
        limit: 10,
        tableSchema: {}
    };
    
    // Fetch tables for the dropdown
    fetch('/api/schema-summary?db=postgres')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to load schema information');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success' && data.summary && Array.isArray(data.summary)) {
                // Clear existing options
                tableSelect.innerHTML = '';
                
                // Add default option
                const defaultOption = document.createElement('option');
                defaultOption.value = '';
                defaultOption.textContent = 'Select a table';
                tableSelect.appendChild(defaultOption);
                
                // Sort tables alphabetically
                const sortedTables = [...data.summary].sort();
                
                // Add table options
                sortedTables.forEach(tableName => {
                    const option = document.createElement('option');
                    option.value = tableName;
                    option.textContent = tableName;
                    tableSelect.appendChild(option);
                });
                
                // Display message if no tables found
                if (sortedTables.length === 0) {
                    const option = document.createElement('option');
                    option.value = '';
                    option.textContent = 'No tables available';
                    option.disabled = true;
                    tableSelect.innerHTML = '';
                    tableSelect.appendChild(option);
                }
            } else {
                throw new Error('Invalid schema data received');
            }
        })
        .catch(error => {
            console.error('Error loading tables:', error);
            tableSelect.innerHTML = `<option value="" disabled>Error loading tables</option>`;
        });
    
    // Table select change handler
    tableSelect.addEventListener('change', function() {
        const selectedTable = this.value;
        queryState.selectedTable = selectedTable;
        
        // Reset columns selection
        columnsSelect.innerHTML = '';
        columnsSelect.disabled = true;
        
        // Reset conditions
        resetConditions();
        
        // Update generated query
        updateGeneratedQuery();
        
        if (selectedTable) {
            // Fetch columns for the selected table
            fetch('/api/discover-schema?db=postgres')
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Failed to load table details');
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.status === 'success' && data.db_schema && Array.isArray(data.db_schema)) {
                        // Filter and sort columns for the selected table
                        const tableColumns = data.db_schema
                            .filter(item => item.table_name === selectedTable)
                            .sort((a, b) => a.column_name.localeCompare(b.column_name));
                        
                        // Store in state for later use
                        queryState.tableSchema[selectedTable] = tableColumns;
                        
                        // Enable columns select
                        columnsSelect.disabled = false;
                        columnsSelect.innerHTML = '';
                        
                        // Add columns to select
                        tableColumns.forEach(column => {
                            const option = document.createElement('option');
                            option.value = column.column_name;
                            option.textContent = `${column.column_name} (${column.data_type})`;
                            columnsSelect.appendChild(option);
                        });
                        
                        // Enable add condition button
                        addConditionBtn.disabled = false;
                        
                        // Enable and update condition dropdowns
                        updateConditionColumns(selectedTable, tableColumns);
                    } else {
                        throw new Error('Invalid schema data received');
                    }
                })
                .catch(error => {
                    console.error('Error loading columns:', error);
                    columnsSelect.innerHTML = `<option value="" disabled>Error loading columns</option>`;
                });
        }
    });
    
    // Columns select change handler
    columnsSelect.addEventListener('change', function() {
        // Get selected options
        const selectedOptions = Array.from(this.selectedOptions).map(option => option.value);
        queryState.selectedColumns = selectedOptions;
        
        // Update generated query
        updateGeneratedQuery();
    });
    
    // Limit input change handler
    limitInput.addEventListener('input', function() {
        let value = parseInt(this.value, 10);
        
        // Validate limits
        if (isNaN(value) || value < 1) {
            value = 1;
        } else if (value > 100) {
            value = 100;
        }
        
        this.value = value;
        queryState.limit = value;
        
        // Update generated query
        updateGeneratedQuery();
    });
    
    // Add condition button
    addConditionBtn.addEventListener('click', function() {
        addCondition();
    });
    
    // Run query button
    runQueryBtn.addEventListener('click', function() {
        const query = generatedQueryEl.textContent;
        runSqlQuery(query);
    });
    
    // Copy query button
    copyQueryBtn.addEventListener('click', function() {
        const query = generatedQueryEl.textContent;
        navigator.clipboard.writeText(query)
            .then(() => {
                // Change button text temporarily
                const originalText = copyQueryBtn.innerHTML;
                copyQueryBtn.innerHTML = '<i class="bi bi-check"></i> Copied!';
                
                setTimeout(() => {
                    copyQueryBtn.innerHTML = originalText;
                }, 2000);
            })
            .catch(err => {
                console.error('Failed to copy query: ', err);
                alert('Failed to copy query to clipboard.');
            });
    });
    
    // Function to add a new condition row
    function addCondition() {
        const conditionRow = document.createElement('div');
        conditionRow.className = 'row g-2 mb-2 condition-row';
        
        // Get the table columns
        const tableColumns = queryState.tableSchema[queryState.selectedTable] || [];
        
        conditionRow.innerHTML = `
            <div class="col-md-4">
                <select class="form-select condition-column">
                    <option value="">Select column</option>
                    ${tableColumns.map(col => `<option value="${col.column_name}">${col.column_name}</option>`).join('')}
                </select>
            </div>
            <div class="col-md-3">
                <select class="form-select condition-operator">
                    <option value="=">=</option>
                    <option value="!=">!=</option>
                    <option value=">">></option>
                    <option value="<"><</option>
                    <option value=">=">>=</option>
                    <option value="<="><=</option>
                    <option value="LIKE">LIKE</option>
                    <option value="IN">IN</option>
                </select>
            </div>
            <div class="col-md-4">
                <input type="text" class="form-control condition-value" placeholder="Value">
            </div>
            <div class="col-md-1">
                <button type="button" class="btn btn-outline-danger btn-sm remove-condition">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        `;
        
        // Add event listener for remove button
        const removeBtn = conditionRow.querySelector('.remove-condition');
        removeBtn.addEventListener('click', function() {
            conditionRow.remove();
            updateConditions();
            updateGeneratedQuery();
        });
        
        // Add event listeners for column and operator changes
        const columnSelect = conditionRow.querySelector('.condition-column');
        const operatorSelect = conditionRow.querySelector('.condition-operator');
        const valueInput = conditionRow.querySelector('.condition-value');
        
        columnSelect.addEventListener('change', function() {
            updateConditions();
            updateGeneratedQuery();
        });
        
        operatorSelect.addEventListener('change', function() {
            updateConditions();
            updateGeneratedQuery();
        });
        
        valueInput.addEventListener('input', function() {
            updateConditions();
            updateGeneratedQuery();
        });
        
        // Append to container
        conditionsContainer.appendChild(conditionRow);
        
        // Update conditions array
        updateConditions();
        updateGeneratedQuery();
    }
    
    // Function to reset all conditions
    function resetConditions() {
        // Keep the first row but disable inputs
        const firstRow = conditionsContainer.querySelector('.condition-row');
        if (firstRow) {
            const columnSelect = firstRow.querySelector('.condition-column');
            const valueInput = firstRow.querySelector('.condition-value');
            const removeBtn = firstRow.querySelector('.remove-condition');
            
            columnSelect.innerHTML = '<option value="">Select column</option>';
            columnSelect.disabled = true;
            valueInput.disabled = true;
            removeBtn.disabled = true;
            
            // Remove all other rows
            const rows = conditionsContainer.querySelectorAll('.condition-row');
            for (let i = 1; i < rows.length; i++) {
                rows[i].remove();
            }
        }
        
        addConditionBtn.disabled = true;
        queryState.conditions = [];
    }
    
    // Function to update condition columns based on selected table
    function updateConditionColumns(tableName, columns) {
        const conditionRows = conditionsContainer.querySelectorAll('.condition-row');
        
        conditionRows.forEach(row => {
            const columnSelect = row.querySelector('.condition-column');
            const valueInput = row.querySelector('.condition-value');
            const removeBtn = row.querySelector('.remove-condition');
            
            // Enable inputs
            columnSelect.disabled = false;
            valueInput.disabled = false;
            removeBtn.disabled = false;
            
            // Save current selection
            const currentValue = columnSelect.value;
            
            // Clear and rebuild options
            columnSelect.innerHTML = '<option value="">Select column</option>';
            
            // Add column options
            columns.forEach(column => {
                const option = document.createElement('option');
                option.value = column.column_name;
                option.textContent = column.column_name;
                columnSelect.appendChild(option);
            });
            
            // Restore selection if it still exists
            if (currentValue && columns.some(col => col.column_name === currentValue)) {
                columnSelect.value = currentValue;
            }
        });
    }
    
    // Function to update conditions state from UI
    function updateConditions() {
        const conditionRows = conditionsContainer.querySelectorAll('.condition-row');
        const conditions = [];
        
        conditionRows.forEach(row => {
            const column = row.querySelector('.condition-column').value;
            const operator = row.querySelector('.condition-operator').value;
            const value = row.querySelector('.condition-value').value;
            
            if (column && value) {
                conditions.push({ column, operator, value });
            }
        });
        
        queryState.conditions = conditions;
    }
    
    // Function to update the generated SQL query
    function updateGeneratedQuery() {
        if (!queryState.selectedTable) {
            generatedQueryEl.textContent = '-- Select a table to generate a query';
            runQueryBtn.disabled = true;
            copyQueryBtn.disabled = true;
            return;
        }
        
        // Build query
        let query = 'SELECT ';
        
        // Add columns
        if (queryState.selectedColumns.length === 0) {
            query += '*';
        } else {
            query += queryState.selectedColumns.join(', ');
        }
        
        // Add table
        query += ` FROM ${queryState.selectedTable}`;
        
        // Add conditions
        if (queryState.conditions.length > 0) {
            query += ' WHERE ';
            
            queryState.conditions.forEach((condition, index) => {
                if (index > 0) {
                    query += ' AND ';
                }
                
                // Format the value based on operator
                let formattedValue = '';
                if (condition.operator === 'LIKE') {
                    // Add wildcards if not present
                    if (!condition.value.includes('%')) {
                        formattedValue = `'%${condition.value}%'`;
                    } else {
                        formattedValue = `'${condition.value}'`;
                    }
                } else if (condition.operator === 'IN') {
                    // Parse comma-separated values
                    const values = condition.value.split(',').map(v => v.trim());
                    formattedValue = `(${values.map(v => isNaN(v) ? `'${v}'` : v).join(', ')})`;
                } else {
                    // Regular value
                    formattedValue = isNaN(condition.value) ? `'${condition.value}'` : condition.value;
                }
                
                query += `${condition.column} ${condition.operator} ${formattedValue}`;
            });
        }
        
        // Add limit
        query += ` LIMIT ${queryState.limit};`;
        
        // Update UI
        generatedQueryEl.textContent = query;
        runQueryBtn.disabled = false;
        copyQueryBtn.disabled = false;
    }
    
    // Function to run SQL query and display results
    function runSqlQuery(query) {
        queryResultsContainer.innerHTML = `
            <div class="d-flex justify-content-center p-3">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <span class="ms-2">Executing query...</span>
            </div>
        `;
        
        // Execute query through the API
        fetch('/api/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                db: 'postgres',
                query: query
            })
        })
        .then(response => {
            if (!response.ok) {
                if (response.status === 400) {
                    return response.json().then(err => {
                        throw new Error(err.detail || 'Query execution failed');
                    });
                }
                throw new Error('Failed to execute query');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                displayQueryResults(data);
            } else {
                throw new Error('Query execution failed');
            }
        })
        .catch(error => {
            queryResultsContainer.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    ${error.message}
                </div>
            `;
        });
    }
    
    // Function to display query results
    function displayQueryResults(data) {
        if (!data.data || data.data.length === 0) {
            queryResultsContainer.innerHTML = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle me-2"></i>
                    Query executed successfully, but no results were returned.
                </div>
            `;
            return;
        }
        
        // Get column names from first result
        const columns = Object.keys(data.data[0]);
        
        // Build table HTML
        let html = `
            <div class="card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="mb-0">Results</h5>
                    <span class="badge bg-secondary">${data.count} records total</span>
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-sm table-striped table-hover mb-0">
                            <thead>
                                <tr>
                                    ${columns.map(col => `<th>${col}</th>`).join('')}
                                </tr>
                            </thead>
                            <tbody>
        `;
        
        // Add data rows
        data.data.forEach(row => {
            html += '<tr>';
            columns.forEach(col => {
                const value = row[col] === null ? '<em class="text-muted">null</em>' : row[col];
                html += `<td>${value}</td>`;
            });
            html += '</tr>';
        });
        
        html += `
                            </tbody>
                        </table>
                    </div>
                </div>
        `;
        
        // Add pagination if available
        if (data.pagination) {
            const { page, total_pages, has_prev, has_next } = data.pagination;
            
            html += `
                <div class="card-footer d-flex justify-content-between align-items-center">
                    <div>
                        Page ${page} of ${total_pages}
                    </div>
                    <nav>
                        <ul class="pagination pagination-sm mb-0">
                            <li class="page-item ${!has_prev ? 'disabled' : ''}">
                                <a class="page-link" href="#" ${has_prev ? 'data-page="' + (page - 1) + '"' : ''}>
                                    <i class="bi bi-chevron-left"></i>
                                </a>
                            </li>
                            <li class="page-item ${!has_next ? 'disabled' : ''}">
                                <a class="page-link" href="#" ${has_next ? 'data-page="' + (page + 1) + '"' : ''}>
                                    <i class="bi bi-chevron-right"></i>
                                </a>
                            </li>
                        </ul>
                    </nav>
                </div>
            `;
        }
        
        html += '</div>';
        
        // Update UI
        queryResultsContainer.innerHTML = html;
        
        // Add pagination event listeners
        const paginationLinks = queryResultsContainer.querySelectorAll('.page-link[data-page]');
        paginationLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const page = parseInt(this.dataset.page, 10);
                
                // Clone the current query state and update page
                const paginatedQuery = {
                    db: 'postgres',
                    query: generatedQueryEl.textContent,
                    page: page,
                    page_size: queryState.limit
                };
                
                // Execute paginated query
                fetch('/api/query', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(paginatedQuery)
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        displayQueryResults(data);
                    }
                })
                .catch(error => {
                    console.error('Error with pagination:', error);
                });
            });
        });
    }
}

/**
 * Initialize natural language to SQL feature
 */
function initNaturalLanguageToSQL() {
    const nlPromptTextarea = document.getElementById('nlPrompt');
    const translateButton = document.getElementById('translateNL');
    const autoExecuteCheckbox = document.getElementById('autoExecuteNL');
    const nlResultsContainer = document.getElementById('nlResults');
    
    if (!nlPromptTextarea || !translateButton) return;
    
    // Add event listeners
    translateButton.addEventListener('click', function() {
        translateNaturalLanguage();
    });
    
    // Allow Enter key to submit
    nlPromptTextarea.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && e.ctrlKey) {
            e.preventDefault();
            translateNaturalLanguage();
        }
    });
    
    function translateNaturalLanguage() {
        const prompt = nlPromptTextarea.value.trim();
        
        if (!prompt) {
            nlResultsContainer.innerHTML = `
                <div class="alert alert-warning">
                    <i class="bi bi-exclamation-circle me-2"></i>
                    Please enter a question or description in natural language.
                </div>
            `;
            return;
        }
        
        // Show loading state
        nlResultsContainer.innerHTML = `
            <div class="d-flex justify-content-center p-3">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <span class="ms-2">Translating to SQL...</span>
            </div>
        `;
        
        // Call API to translate natural language to SQL
        fetch('/api/nl-to-sql', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                db: 'postgres',
                prompt: prompt
            })
        })
        .then(response => {
            if (!response.ok) {
                if (response.status === 400) {
                    return response.json().then(err => {
                        throw new Error(err.detail || 'Translation failed');
                    });
                }
                throw new Error('Failed to translate natural language');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success' && data.sql) {
                displaySqlTranslation(data.sql);
                
                // Auto-execute if checkbox is checked
                if (autoExecuteCheckbox.checked) {
                    executeTranslatedQuery(data.sql);
                }
            } else {
                throw new Error('Translation failed');
            }
        })
        .catch(error => {
            nlResultsContainer.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    ${error.message}
                </div>
            `;
        });
    }
    
    function displaySqlTranslation(sql) {
        nlResultsContainer.innerHTML = `
            <div class="card mb-3">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="mb-0">Generated SQL</h5>
                    <div>
                        <button type="button" class="btn btn-sm btn-outline-secondary me-2" id="copyNLQuery">
                            <i class="bi bi-clipboard"></i> Copy
                        </button>
                        <button type="button" class="btn btn-sm btn-primary" id="runNLQuery">
                            <i class="bi bi-lightning"></i> Run Query
                        </button>
                    </div>
                </div>
                <div class="card-body bg-dark">
                    <pre class="mb-0 text-light"><code>${sql}</code></pre>
                </div>
            </div>
            <div id="nlQueryResults"></div>
        `;
        
        // Add event listeners to buttons
        document.getElementById('copyNLQuery').addEventListener('click', function() {
            navigator.clipboard.writeText(sql)
                .then(() => {
                    const originalText = this.innerHTML;
                    this.innerHTML = '<i class="bi bi-check"></i> Copied!';
                    
                    setTimeout(() => {
                        this.innerHTML = originalText;
                    }, 2000);
                })
                .catch(err => {
                    console.error('Failed to copy query: ', err);
                    alert('Failed to copy query to clipboard.');
                });
        });
        
        document.getElementById('runNLQuery').addEventListener('click', function() {
            executeTranslatedQuery(sql);
        });
    }
    
    function executeTranslatedQuery(sql) {
        const resultsContainer = document.getElementById('nlQueryResults');
        
        if (!resultsContainer) return;
        
        // Show loading state
        resultsContainer.innerHTML = `
            <div class="d-flex justify-content-center p-3">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <span class="ms-2">Executing query...</span>
            </div>
        `;
        
        // Execute query through the API
        fetch('/api/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                db: 'postgres',
                query: sql
            })
        })
        .then(response => {
            if (!response.ok) {
                if (response.status === 400) {
                    return response.json().then(err => {
                        throw new Error(err.detail || 'Query execution failed');
                    });
                }
                throw new Error('Failed to execute query');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                displayQueryResults(data, resultsContainer);
            } else {
                throw new Error('Query execution failed');
            }
        })
        .catch(error => {
            resultsContainer.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    ${error.message}
                </div>
            `;
        });
    }
    
    function displayQueryResults(data, container) {
        if (!data.data || data.data.length === 0) {
            container.innerHTML = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle me-2"></i>
                    Query executed successfully, but no results were returned.
                </div>
            `;
            return;
        }
        
        // Get column names from first result
        const columns = Object.keys(data.data[0]);
        
        // Build table HTML
        let html = `
            <div class="card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="mb-0">Results</h5>
                    <span class="badge bg-secondary">${data.count} records total</span>
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-sm table-striped table-hover mb-0">
                            <thead>
                                <tr>
                                    ${columns.map(col => `<th>${col}</th>`).join('')}
                                </tr>
                            </thead>
                            <tbody>
        `;
        
        // Add data rows
        data.data.forEach(row => {
            html += '<tr>';
            columns.forEach(col => {
                const value = row[col] === null ? '<em class="text-muted">null</em>' : row[col];
                html += `<td>${value}</td>`;
            });
            html += '</tr>';
        });
        
        html += `
                            </tbody>
                        </table>
                    </div>
                </div>
        `;
        
        // Add pagination if available
        if (data.pagination) {
            const { page, total_pages, has_prev, has_next } = data.pagination;
            
            html += `
                <div class="card-footer d-flex justify-content-between align-items-center">
                    <div>
                        Page ${page} of ${total_pages}
                    </div>
                    <nav>
                        <ul class="pagination pagination-sm mb-0">
                            <li class="page-item ${!has_prev ? 'disabled' : ''}">
                                <a class="page-link" href="#" ${has_prev ? 'data-page="' + (page - 1) + '"' : ''}>
                                    <i class="bi bi-chevron-left"></i>
                                </a>
                            </li>
                            <li class="page-item ${!has_next ? 'disabled' : ''}">
                                <a class="page-link" href="#" ${has_next ? 'data-page="' + (page + 1) + '"' : ''}>
                                    <i class="bi bi-chevron-right"></i>
                                </a>
                            </li>
                        </ul>
                    </nav>
                </div>
            `;
        }
        
        html += '</div>';
        
        // Update container
        container.innerHTML = html;
        
        // Add pagination event listeners
        const paginationLinks = container.querySelectorAll('.page-link[data-page]');
        paginationLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const page = parseInt(this.dataset.page, 10);
                
                // Get the current query from the code block
                const currentQuery = document.querySelector('#nlResults pre code').textContent;
                
                // Execute paginated query
                fetch('/api/query', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        db: 'postgres',
                        query: currentQuery,
                        page: page,
                        page_size: 10
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        displayQueryResults(data, container);
                    }
                })
                .catch(error => {
                    console.error('Error with pagination:', error);
                });
            });
        });
    }
}