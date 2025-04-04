with open('app/templates/query_builder.html', 'r') as file:
    content = file.read()

# Add the storage of results for visualization
modified_content = content.replace(
    '        function displayResults(data) {\n            // Update pagination state',
    '        function displayResults(data) {\n            // Store results globally for visualization and export\n            window.lastResults = data;\n            \n            // Update pagination state'
)

# Write back to the file
with open('app/templates/query_builder.html', 'w') as file:
    file.write(modified_content)

print("Successfully modified query_builder.html")
