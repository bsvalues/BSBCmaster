with open('templates/statistics_dashboard_new.html', 'r') as file:
    content = file.read()

# Replace the city list to remove Pasco
updated_content = content.replace(
    "labels: ['Richland', 'Kennewick', 'Pasco', 'West Richland', 'Benton City']",
    "labels: ['Richland', 'Kennewick', 'West Richland', 'Benton City', 'Prosser']"
)

with open('templates/statistics_dashboard_new.html', 'w') as file:
    file.write(updated_content)
    
print("Updated statistics dashboard city lists successfully!")
