# Traffic Visualization Implementation Steps

## Overview
This guide outlines the steps to implement traffic visualization using the form inputs from the prediction form. The visualization will show color-coded traffic conditions between the start and destination points.

## Prerequisites
- Mapbox access token (public token starting with 'pk.')
- Backend API endpoint for traffic data
- Existing prediction form with start and destination inputs

## Implementation Steps

### 1. Backend API Setup

1. Create a new endpoint in `app.py` for traffic data:
```python
@app.route('/api/traffic', methods=['GET'])
def get_traffic_data():
    start = request.args.get('start')
    destination = request.args.get('destination')
    
    # Example response structure
    return jsonify({
        'route_segments': [
            {
                'start_point': [lat1, lng1],  # Convert addresses to coordinates
                'end_point': [lat2, lng2],
                'traffic_level': 'heavy|medium|light',
                'speed': current_speed,
                'typical_speed': typical_speed
            }
        ]
    })
```

### 2. Frontend Implementation

1. Add Mapbox dependencies to your HTML:
```html
<link href='https://api.mapbox.com/mapbox-gl-js/v2.15.0/mapbox-gl.css' rel='stylesheet' />
<script src='https://api.mapbox.com/mapbox-gl-js/v2.15.0/mapbox-gl.js'></script>
<script src='https://api.mapbox.com/mapbox-gl-js/plugins/mapbox-gl-geocoder/v5.0.0/mapbox-gl-geocoder.min.js'></script>
<link rel='stylesheet' href='https://api.mapbox.com/mapbox-gl-js/plugins/mapbox-gl-geocoder/v5.0.0/mapbox-gl-geocoder.css' type='text/css' />
```

2. Add the map container and legend to your HTML:
```html
<div class="traffic-visualization">
    <div id="traffic-map" class="map-container"></div>
    <div class="traffic-legend">
        <h3>Traffic Conditions</h3>
        <div class="legend-item">
            <span class="color-box heavy"></span>
            <span>Heavy Traffic</span>
        </div>
        <div class="legend-item">
            <span class="color-box medium"></span>
            <span>Moderate Traffic</span>
        </div>
        <div class="legend-item">
            <span class="color-box light"></span>
            <span>Light Traffic</span>
        </div>
    </div>
</div>
```

3. Add CSS styles:
```css
.traffic-visualization {
    position: relative;
    width: 100%;
    margin: 20px 0;
}

.map-container {
    width: 100%;
    height: 500px;
    border-radius: 8px;
}

.traffic-legend {
    background: white;
    padding: 15px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    position: absolute;
    bottom: 20px;
    left: 20px;
    z-index: 1;
}

.legend-item {
    display: flex;
    align-items: center;
    margin: 8px 0;
}

.color-box {
    width: 20px;
    height: 20px;
    margin-right: 10px;
    border-radius: 4px;
}

.heavy { background: #FF0000; }
.medium { background: #FFA500; }
.light { background: #008000; }
```

4. Add JavaScript implementation:
```javascript
// Initialize map
mapboxgl.accessToken = 'YOUR_PUBLIC_ACCESS_TOKEN';
const map = new mapboxgl.Map({
    container: 'traffic-map',
    style: 'mapbox://styles/mapbox/streets-v12',
    center: [-74.5, 40], // Default center
    zoom: 12
});

// Add navigation controls
map.addControl(new mapboxgl.NavigationControl(), 'top-right');

// Function to update traffic visualization
function updateTrafficVisualization(trafficData) {
    if (!map) return;

    // Clear existing layers
    if (map.getLayer('traffic-layer')) {
        map.removeLayer('traffic-layer');
        map.removeSource('traffic-source');
    }

    // Add traffic data as a GeoJSON source
    map.addSource('traffic-source', {
        type: 'geojson',
        data: {
            type: 'FeatureCollection',
            features: trafficData.route_segments.map(segment => ({
                type: 'Feature',
                properties: {
                    traffic_level: segment.traffic_level
                },
                geometry: {
                    type: 'LineString',
                    coordinates: [
                        [segment.start_point[1], segment.start_point[0]],
                        [segment.end_point[1], segment.end_point[0]]
                    ]
                }
            }))
        }
    });

    // Add traffic layer with color coding
    map.addLayer({
        id: 'traffic-layer',
        type: 'line',
        source: 'traffic-source',
        paint: {
            'line-color': [
                'match',
                ['get', 'traffic_level'],
                'heavy', '#FF0000',
                'medium', '#FFA500',
                'light', '#008000',
                '#808080'
            ],
            'line-width': 4,
            'line-opacity': 0.8
        }
    });

    // Fit map to bounds of the route
    const coordinates = trafficData.route_segments.flatMap(segment => [
        [segment.start_point[1], segment.start_point[0]],
        [segment.end_point[1], segment.end_point[0]]
    ]);

    const bounds = coordinates.reduce((bounds, coord) => {
        return bounds.extend(coord);
    }, new mapboxgl.LngLatBounds(coordinates[0], coordinates[0]));

    map.fitBounds(bounds, {
        padding: 50,
        maxZoom: 15
    });
}

// Function to fetch and update traffic data
async function fetchTrafficData(start, destination) {
    try {
        const response = await fetch(`/api/traffic?start=${encodeURIComponent(start)}&destination=${encodeURIComponent(destination)}`);
        const trafficData = await response.json();
        updateTrafficVisualization(trafficData);
    } catch (error) {
        console.error('Error fetching traffic data:', error);
    }
}

// Update form submission handler
document.getElementById('predictionForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const start = document.getElementById('start').value;
    const destination = document.getElementById('destination').value;
    
    // Get prediction as before
    const predictionData = await getPrediction();
    
    // Additionally fetch traffic data
    await fetchTrafficData(start, destination);
    
    // Update UI with prediction
    updatePredictionDisplay(predictionData);
});
```

## Testing Steps

1. Test the backend API:
   - Verify the `/api/traffic` endpoint returns correct data
   - Test with various start and destination points
   - Check error handling

2. Test the frontend implementation:
   - Verify map initialization
   - Test traffic visualization with different routes
   - Check legend display
   - Test responsive design

3. Integration testing:
   - Test form submission with traffic visualization
   - Verify real-time updates
   - Check error handling and loading states

## Common Issues and Solutions

1. Map not loading:
   - Verify Mapbox access token is correct
   - Check network connectivity
   - Ensure proper initialization order

2. Traffic data not displaying:
   - Check API response format
   - Verify coordinate conversion
   - Check layer and source names

3. Performance issues:
   - Implement caching for frequent routes
   - Optimize update frequency
   - Use appropriate zoom levels

## Next Steps

1. Add real-time updates:
   - Implement WebSocket connection
   - Add update interval configuration
   - Add loading indicators

2. Enhance visualization:
   - Add traffic flow animation
   - Include traffic incidents
   - Show alternative routes

3. Improve user experience:
   - Add tooltips for traffic details
   - Implement route selection
   - Add traffic pattern history 