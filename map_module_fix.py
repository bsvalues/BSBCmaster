def get_map_data():
    """Handle GET request for map data with enhanced visualization options."""
    data_source = request.args.get('data_source', 'accounts')
    value_filter = request.args.get('value_filter', 'all')
    city = request.args.get('city', None)
    visualization_mode = request.args.get('visualization', request.args.get('mode', 'markers'))
    clustering = request.args.get('clustering', 'false').lower() == 'true'
    grid_size = float(request.args.get('grid_size', '0.01'))
    
    # Get property types if provided
    property_types_param = request.args.get('property_types', None)
    property_types = property_types_param.split(',') if property_types_param else None
    
    # Get property data with filters
    stats, bounds, properties = get_property_data(
        data_source=data_source,
        value_filter=value_filter,
        city=city,
        property_types=property_types
    )
    
    # Generate response based on visualization mode
    if visualization_mode == 'heatmap':
        # Generate heatmap data
        heatmap_data = prepare_heatmap_data(properties)
        # Also include geojson for fallback
        geojson = convert_to_geojson(properties)
        response_data = {
            'statistics': stats,
            'bounds': bounds,
            'heatmap': heatmap_data,
            'geojson': geojson,
            'visualization': 'heatmap'
        }
    elif visualization_mode == 'clusters' or (clustering and len(properties) > 20):
        # Generate clusters for better performance with large datasets
        geojson = generate_clusters(properties, grid_size)
        response_data = {
            'statistics': stats,
            'bounds': bounds,
            'geojson': geojson,
            'visualization': 'clusters'
        }
    else:
        # Convert to regular GeoJSON for small datasets or marker mode
        geojson = convert_to_geojson(properties)
        response_data = {
            'statistics': stats,
            'bounds': bounds,
            'geojson': geojson,
            'visualization': 'markers'
        }
    
    # Return JSON response
    return jsonify(response_data)
