// Fix for the map JavaScript that properly handles the GeoJSON structure
const mapData = fetch('/api/map/data')
  .then(response => response.json())
  .then(data => {
    console.log('Raw map data:', data);
    
    // Check if data has the correct structure
    if (!data.geojson || !data.geojson.features || data.geojson.features.length === 0) {
      console.log('No property data available');
      return;
    }
    
    // Convert GeoJSON features to properties array
    const properties = data.geojson.features.map(feature => {
      return {
        ...feature.properties,
        latitude: feature.geometry.coordinates[1],
        longitude: feature.geometry.coordinates[0]
      };
    });
    
    console.log('Converted properties:', properties);
    return properties;
  })
  .catch(error => {
    console.error('Error loading map data:', error);
  });
