import os

# Check if the file exists
if os.path.exists('templates/map_view_new.html'):
    with open('templates/map_view_new.html', 'r') as file:
        content = file.read()

    # Replace the city options to remove Pasco
    updated_content = content.replace(
        '<option value="Pasco">Pasco</option>',
        ''
    )

    with open('templates/map_view_new.html', 'w') as file:
        file.write(updated_content)
        
    print("Updated city options in map_view_new.html successfully!")
else:
    print("map_view_new.html file not found, skipping update")
