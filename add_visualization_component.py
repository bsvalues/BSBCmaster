with open('app/templates/query_builder.html', 'r') as file:
    content = file.read()

# Find the results panel
results_panel_start = content.find('<div id="results-panel" class="row mb-4" style="display: none;">')
if results_panel_start != -1:
    # Find the end of the div by matching closing div tags
    opening_count = 1
    closing_count = 0
    end_index = results_panel_start
    while opening_count > closing_count and end_index < len(content) - 5:
        end_index += 1
        if content[end_index:end_index+5] == '</div>':
            closing_count += 1
        elif content[end_index:end_index+4] == '<div':
            opening_count += 1
    
    if end_index < len(content):
        # Insert visualization component after the results panel
        visualization_component = '\n\n<!-- Visualization Component -->\n<div id="visualization-container" class="row mb-4" style="display: none;">\n    <div class="col-md-12">\n        <div class="card bg-dark">\n            <div class="card-header d-flex justify-content-between align-items-center">\n                <span>Data Visualization</span>\n                <div class="btn-group">\n                    <button type="button" class="btn btn-sm btn-outline-info" id="toggle-viz-btn">\n                        <i class="bi bi-bar-chart"></i> Toggle Visualization\n                    </button>\n                </div>\n            </div>\n            <div class="card-body" id="chart-container" style="display: none;">\n                <div class="row mb-3">\n                    <div class="col-md-4">\n                        <label for="chartType" class="form-label">Chart Type:</label>\n                        <select id="chartType" class="form-select">\n                            <option value="bar">Bar Chart</option>\n                            <option value="line">Line Chart</option>\n                            <option value="pie">Pie Chart</option>\n                            <option value="scatter">Scatter Plot</option>\n                        </select>\n                    </div>\n                    <div class="col-md-4">\n                        <label for="xAxis" class="form-label">X Axis:</label>\n                        <select id="xAxis" class="form-select"></select>\n                    </div>\n                    <div class="col-md-4">\n                        <label for="yAxis" class="form-label">Y Axis:</label>\n                        <select id="yAxis" class="form-select"></select>\n                    </div>\n                </div>\n                <div style="height: 400px;">\n                    <canvas id="resultChart"></canvas>\n                </div>\n            </div>\n        </div>\n    </div>\n</div>\n'
        
        modified_content = content[:end_index+5] + visualization_component + content[end_index+5:]
        
        # Write back to the file
        with open('app/templates/query_builder.html', 'w') as file:
            file.write(modified_content)
        
        print("Successfully added visualization component to query_builder.html")
    else:
        print("Could not find the end of the results panel div")
else:
    print("Could not find the results panel div")
