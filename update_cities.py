with open('templates/map_view_fixed.html', 'r') as file:
    content = file.read()

# Replace the city options to remove Pasco
updated_content = content.replace(
    '<option value="all">All Cities</option>\n                                    <option value="Richland">Richland</option>\n                                    <option value="Kennewick">Kennewick</option>\n                                    <option value="Pasco">Pasco</option>\n                                    <option value="West Richland">West Richland</option>\n                                    <option value="Prosser">Prosser</option>',
    '<option value="all">All Cities</option>\n                                    <option value="Richland">Richland</option>\n                                    <option value="Kennewick">Kennewick</option>\n                                    <option value="West Richland">West Richland</option>\n                                    <option value="Prosser">Prosser</option>\n                                    <option value="Benton City">Benton City</option>'
)

with open('templates/map_view_fixed.html', 'w') as file:
    file.write(updated_content)
    
print("Updated city options successfully!")
