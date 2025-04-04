with open('app/templates/query_builder.html', 'r') as file:
    content = file.read()

# Add Chart.js to scripts block
modified_content = content.replace(
    '{% block scripts %}\n<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/codemirror.min.js"></script>',
    '{% block scripts %}\n<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/codemirror.min.js"></script>\n<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>'
)

# Write back to the file
with open('app/templates/query_builder.html', 'w') as file:
    file.write(modified_content)

print("Successfully added Chart.js to query_builder.html")
