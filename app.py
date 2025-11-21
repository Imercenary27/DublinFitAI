# app.py - Flask application entry point
from functools import lru_cache
import json
import math
import os
import time
from flask import Flask, current_app, render_template, request, jsonify
import requests
import osmnx as ox
from api.routes import api_blueprint
from ml_services.route_planner import  OSMRoutePlanner
from utils.geospatial import calculate_distance

app = Flask(__name__)
app.register_blueprint(api_blueprint, url_prefix='/api')
app.config['OWM_API_KEY'] = 'yourApiKeyhere' #482e1'

@app.route('/')
def index():
    return render_template('index.html')
@app.route('/weather')
def weather():
    return render_template('weather.html')



@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
    return response

@app.route('/api/sensor-proxy', methods=['POST'])
def sensor_proxy():
    try:
        data = request.json
        endpoint = data['endpoint']
        params = {
            'username': 'dublincityapi',
            'password': 'Xpa5vAQ9ki',
            'monitor': data['serial'],
            'start': data['start'],
            'end': data['end']
        }
        
        response = requests.post(
            f'https://data.smartdublin.ie/sonitus-api/api/{endpoint}',
            data=params
        )
        
        response.raise_for_status()
        return jsonify(response.json())
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/calculate-route', methods=['POST'])
def calculate_route():
    try:
        data = request.get_json()
        lat = float(data['latitude'])
        lng = float(data['longitude'])
        distance = float(data.get('distance', 5000))  # Default 5km
        
        planner = OSMRoutePlanner()
        
        # Get pedestrian paths from OSM
        elements = planner.get_osm_footways((lat, lng), distance)
        
        if not elements:
            return jsonify({
                "coordinates": planner.create_fallback_route((lat, lng), distance),
                "distance": distance,
                "is_fallback": True
            })
            
        # Build and analyze graph
        G = planner.build_pedestrian_graph(elements)
        route_nodes = planner.find_optimal_loop(G, (lat, lng), distance)
        
        # Convert nodes to coordinates
        route_coords = [(node[0], node[1]) for node in route_nodes]
        
        return jsonify({
            "coordinates": route_coords,
            "distance": sum(calculate_distance(*a, *b) for a,b in zip(route_coords[:-1], route_coords[1:]))
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/road-network')
def road_network():
    try:
        # Get parameters from request with defaults
        lat = request.args.get('lat', default=53.3498, type=float)
        lng = request.args.get('lng', default=-6.2603, type=float)
        radius_km = request.args.get('radius', default=5, type=float)

        # Overpass API query to get roads
        overpass_query = f"""
        [out:json];
        way(around:{radius_km*1000},{lat},{lng})["highway"];
        (._;>;);
        out body geom;
        """
        
        response = requests.post(
            "https://overpass-api.de/api/interpreter",
            data=overpass_query,
            headers={'Content-Type': 'text/plain'},
            timeout=30
        )
        response.raise_for_status()
        
        elements = response.json()['elements']
        
        # Process OSM data into GeoJSON format
        features = []
        nodes = {}
        
        # First collect all nodes
        for element in elements:
            if element['type'] == 'node':
                nodes[element['id']] = [element['lon'], element['lat']]
        
        # Then process ways
        for element in elements:
            if element['type'] == 'way':
                coordinates = []
                for node_id in element.get('nodes', []):
                    if node_id in nodes:
                        coordinates.append(nodes[node_id])
                
                if len(coordinates) > 1:
                    features.append({
                        "type": "Feature",
                        "properties": {
                            "highway": element['tags'].get('highway', ''),
                            "name": element['tags'].get('name', 'Unnamed Road'),
                            "osm_id": element['id']
                        },
                        "geometry": {
                            "type": "LineString",
                            "coordinates": coordinates
                        }
                    })

        return jsonify({
            "type": "FeatureCollection",
            "features": features
        })
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            "error": f"OSM API request failed: {str(e)}",
            "type": "FeatureCollection",
            "features": []
        }), 502
    except Exception as e:
        return jsonify({
            "error": f"Server error: {str(e)}",
            "type": "FeatureCollection",
            "features": []
        }), 500

@app.route('/map')
def map_view():
    # Load monitors from your data file
    import json
    with open('C:\\Users\\amate\\OneDrive\\Desktop\\NCI101\\CAML2\\data\\locator.json') as f:
        monitors = json.load(f)
    return render_template('map.html', monitors=monitors,owm_api_key=app.config['OWM_API_KEY'])

@app.route('/profile')
def user_profile():
    return render_template('profile.html')
@app.route('/api/walking-trails')
def get_walking_trails():
    try:
        # Specify encoding explicitly and handle BOM if present
        with open('C:\\Users\\amate\\OneDrive\\Desktop\\NCI101\\CAML2\\data\\Walking_Trails_SDCC.geojson', 
                 'r', encoding='utf-8-sig') as f:
            trails_data = json.load(f)
        return jsonify(trails_data)
    except UnicodeDecodeError:
        # Fallback to latin-1 if UTF-8 fails
        try:
            with open('C:\\Users\\amate\\OneDrive\\Desktop\\NCI101\\CAML2\\data\\Walking_Trails_SDCC.geojson',
                     'r', encoding='latin-1') as f:
                trails_data = json.load(f)
            return jsonify(trails_data)
        except Exception as e:
            current_app.logger.error(f"Fallback encoding failed: {str(e)}")
            return jsonify({"error": "Failed to decode file with both UTF-8 and Latin-1 encodings"}), 500
    except Exception as e:
        current_app.logger.error(f"General error loading trails: {str(e)}")
        return jsonify({"error": str(e)}), 500

WEATHER_API_KEY = "YourAPIKeyHere"
ORS_API_KEY = "YourApiKeyHere"

# API endpoints
AQI_API_URL = "http://api.openweathermap.org/data/2.5/air_pollution"
WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"
ORS_DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/foot-walking/geojson"

# Cache API responses
@lru_cache(maxsize=128)
def get_aqi_data(lat, lon):
    """Fetch air quality data from OpenWeather API"""
    params = {
        "lat": lat,
        "lon": lon,
        "appid": WEATHER_API_KEY
    }
    
    try:
        response = requests.get(AQI_API_URL, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching AQI data: {response.status_code}")
            return None
    except Exception as e:
        print(f"Exception fetching AQI data: {e}")
        return None

@lru_cache(maxsize=128)
def get_weather_data(lat, lon):
    """Fetch weather data from OpenWeather API"""
    params = {
        "lat": lat,
        "lon": lon,
        "units": "metric",
        "appid": WEATHER_API_KEY
    }
    
    try:
        response = requests.get(WEATHER_API_URL, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching weather data: {response.status_code}")
            return None
    except Exception as e:
        print(f"Exception fetching weather data: {e}")
        return None

def get_surrounding_points(lat, lon, radius_meters=1000):
    """Generate points in cardinal directions around the given coordinates"""
    directions = [
        (0, 1),    # North
        (1, 0),    # East
        (0, -1),   # South
        (-1, 0)    # West
    ]
    
    points = []
    for dx, dy in directions:
        # Convert meters to approximate lat/lon changes
        dlat = (dy * radius_meters) / 111320  # 1 degree latitude is approximately 111320 meters
        dlon = (dx * radius_meters) / (111320 * math.cos(math.radians(lat)))
        
        new_lat = lat + dlat
        new_lon = lon + dlon
        points.append((new_lat, new_lon))
    
    return points

def evaluate_location(aqi_data, weather_data):
    """Evaluate a location based on AQI and temperature data"""
    if not aqi_data or not weather_data:
        return 0, None, None, None
    
    try:
        if 'list' not in aqi_data or not aqi_data['list']:
            return 0, None, None, None
            
        aqi = aqi_data["list"][0]["main"]["aqi"]
        components = aqi_data["list"][0]["components"]
        temp = weather_data["main"]["temp"]
        
        # Lower AQI is better (1 is best, 5 is worst)
        aqi_score = (6 - aqi) / 5  # Normalize to 0-1 range
        
        # Temperature score (ideal around 20-25°C)
        temp_ideal = 22
        temp_score = max(0, 1 - (abs(temp - temp_ideal) / 15))
        
        # Component evaluation weights
        component_weights = {
            "pm2_5": 0.4,   # Fine particulate matter
            "pm10": 0.2,    # Coarse particulate matter
            "no2": 0.15,    # Nitrogen dioxide
            "o3": 0.15,     # Ozone
            "co": 0.05,     # Carbon monoxide
            "so2": 0.05     # Sulfur dioxide
        }
        
        # Normalize component values based on health guidelines
        component_scores = {
            "pm2_5": max(0, 1 - (components["pm2_5"] / 10)), 
            "pm10": max(0, 1 - (components["pm10"] / 20)),
            "no2": max(0, 1 - (components["no2"] / 25)),
            "o3": max(0, 1 - (components["o3"] / 100)),
            "co": max(0, 1 - (components["co"] / 4000)),
            "so2": max(0, 1 - (components["so2"] / 40))
        }
        
        # Calculate weighted component score
        component_score = sum(component_scores[comp] * weight for comp, weight in component_weights.items())
        
        # Combined score (higher is better)
        combined_score = (
            aqi_score * 0.4 +
            component_score * 0.4 +
            temp_score * 0.2
        )
        
        return combined_score, aqi, temp, components
    except Exception as e:
        print(f"Error evaluating location: {e}")
        return 0, None, None, None

def get_route_from_ors(start_coords, end_coords):
    """Get route from OpenRouteService API following actual walkable roads"""
    # IMPORTANT FIX: The API key should be sent as the 'Authorization' header value, without any prefix
    headers = {
        'Accept': 'application/json, application/geo+json, application/gpx+xml',
        'Authorization': ORS_API_KEY,
        'Content-Type': 'application/json'
    }
    
    # IMPORTANT FIX: Coordinates format must be [longitude, latitude]
    body = {
        "coordinates": [[start_coords[1], start_coords[0]], [end_coords[1], end_coords[0]]]
    }
    
    try:
        print(f"Sending request to ORS API: {ORS_DIRECTIONS_URL}")
        print(f"Headers: {headers}")
        print(f"Body: {body}")
        
        # Add a small delay to avoid rate limiting
        time.sleep(0.5)
        
        response = requests.post(ORS_DIRECTIONS_URL, json=body, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"OpenRouteService API error: {response.status_code}, {response.text}")
            
            # If API fails, implement a fallback method
            if response.status_code == 403 or response.status_code == 429:
                print("API quota exceeded or unauthorized. Using fallback direct line route.")
                return create_fallback_route(start_coords, end_coords)
            
            return None
    except Exception as e:
        print(f"Exception in OpenRouteService API call: {e}")
        return None

def create_fallback_route(start_coords, end_coords):
    """Create a fallback route when API fails - simple line with waypoints"""
    # Calculate distance between points
    lat1, lon1 = start_coords
    lat2, lon2 = end_coords
    
    # Create a straight line with multiple points for visualization
    num_points = 5  # Number of points in the line
    
    # Generate intermediate points
    points = []
    for i in range(num_points):
        factor = i / (num_points - 1)
        lat = lat1 + (lat2 - lat1) * factor
        lon = lon1 + (lon2 - lon1) * factor
        points.append([lon, lat])
    
    # Calculate approximate distance
    distance = haversine_distance(lat1, lon1, lat2, lon2)
    
    # Create a GeoJSON-like response
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": points
            },
            "properties": {
                "summary": {
                    "distance": distance,
                    "duration": distance / 1.4  # Assume walking speed of 1.4 m/s
                }
            }
        }]
    }

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great-circle distance between two points in meters"""
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371000  # Radius of earth in meters
    return c * r

def find_optimal_routes(start_lat, start_lon, target_distance):
    """Find optimal routes based on AQI and temperature data"""
    # Start point
    start_point = (start_lat, start_lon)
    
    # Get surrounding points
    direction_points = get_surrounding_points(start_lat, start_lon, 1000)
    
    # Evaluate each direction
    direction_scores = []
    
    for point in direction_points:
        aqi_data = get_aqi_data(point[0], point[1])
        weather_data = get_weather_data(point[0], point[1])
        score, aqi, temp, components = evaluate_location(aqi_data, weather_data)
        
        direction_scores.append({
            "point": point,
            "score": score,
            "aqi": aqi,
            "temp": temp,
            "components": components
        })
    
    # Sort by score (higher is better)
    direction_scores.sort(key=lambda x: x["score"] if x["score"] is not None else 0, reverse=True)
    
    best_routes = []
    total_distance = 0
    max_segments = 4  # Max segments to keep route reasonable
    
    # Start with the highest-scoring direction
    current_point = start_point
    segments = 0
    
    while total_distance < target_distance and segments < max_segments:
        # Get the best direction that hasn't been used yet
        if not direction_scores:
            break
            
        best_direction = direction_scores[0]["point"]
        route_info = {"direction": best_direction, "score": direction_scores[0]["score"]}
        
        # Get route from current point to this direction
        route_data = get_route_from_ors(current_point, best_direction)
        
        # Remove this direction from options
        direction_scores.pop(0)
        
        if route_data and 'features' in route_data and len(route_data['features']) > 0:
            # Extract route geometry and properties
            route_geometry = route_data['features'][0]['geometry']
            route_properties = route_data['features'][0]['properties']
            segment_distance = route_properties['summary']['distance']
            segment_duration = route_properties['summary']['duration']
            
            # Add segment info
            route_info["distance"] = segment_distance
            route_info["duration"] = segment_duration
            route_info["geometry"] = route_geometry
            
            # Update total distance
            total_distance += segment_distance
            
            # Add this segment to our routes
            best_routes.append(route_info)
            
            # Update current point for next segment
            last_coord = route_geometry['coordinates'][-1]
            current_point = (last_coord[1], last_coord[0])
            
            segments += 1
    
    # Add a route back to the start
    if segments > 0 and current_point != start_point:
        route_back = get_route_from_ors(current_point, start_point)
        
        if route_back and 'features' in route_back and len(route_back['features']) > 0:
            # Extract route geometry and properties
            back_geometry = route_back['features'][0]['geometry']
            back_properties = route_back['features'][0]['properties']
            back_distance = back_properties['summary']['distance']
            back_duration = back_properties['summary']['duration']
            
            # Add segment info
            best_routes.append({
                "direction": start_point,
                "score": None,  # No score for return trip
                "distance": back_distance,
                "duration": back_duration,
                "geometry": back_geometry
            })
            
            # Update total distance
            total_distance += back_distance
    
    # If we have routes, combine them
    if best_routes:
        # Initialize with the first route's coordinates
        all_coordinates = best_routes[0]["geometry"]["coordinates"]
        
        # Add coordinates from subsequent routes (skipping the first point to avoid duplicates)
        for i in range(1, len(best_routes)):
            segment_coords = best_routes[i]["geometry"]["coordinates"]
            all_coordinates.extend(segment_coords[1:])  # Skip first point to avoid duplication
        
        # Convert to [lat, lon] for the frontend
        points = [(coord[1], coord[0]) for coord in all_coordinates]
        
        # Sample significant points for AQI and temperature data
        sampled_data = []
        
        # Always include start, end, and some intermediate points
        samples = min(6, len(points))
        sample_indices = [0]  # Always include start
        
        if samples > 2:
            step = len(points) // (samples - 1)
            for i in range(1, samples - 1):
                sample_indices.append(i * step)
        
        sample_indices.append(len(points) - 1)  # Always include end
        
        # Get environmental data for sample points
        for idx in sample_indices:
            point = points[idx]
            aqi_data = get_aqi_data(point[0], point[1])
            weather_data = get_weather_data(point[0], point[1])
            score, aqi, temp, components = evaluate_location(aqi_data, weather_data)
            
            sampled_data.append({
                "lat": point[0],
                "lon": point[1],
                "aqi": aqi,
                "temp": temp,
                "components": components,
                "score": score
            })
        
        # Calculate total distance and duration
        total_distance = sum(route["distance"] for route in best_routes)
        total_duration = sum(route["duration"] for route in best_routes)
        
        return {
            "route": points,
            "route_data": sampled_data,
            "distance": total_distance,
            "duration": total_duration
        }
    
    # Fallback if no routes found
    return create_simple_route(start_lat, start_lon, target_distance)

def create_simple_route(start_lat, start_lon, target_distance):
    """Create a simple circular route when API fails"""
    print("Creating simple circular route as fallback")
    
    # Create a circular route around the starting point
    num_points = 8
    radius = target_distance / (2 * math.pi)
    
    points = []
    for i in range(num_points + 1):  # +1 to close the circle
        angle = 2 * math.pi * i / num_points
        dlat = math.sin(angle) * radius / 111320
        dlon = math.cos(angle) * radius / (111320 * math.cos(math.radians(start_lat)))
        
        lat = start_lat + dlat
        lon = start_lon + dlon
        points.append((lat, lon))
    
    # Add environmental data for key points
    route_data = []
    for i in range(0, len(points), 2):  # Sample every other point
        point = points[i]
        aqi_data = get_aqi_data(point[0], point[1])
        weather_data = get_weather_data(point[0], point[1])
        score, aqi, temp, components = evaluate_location(aqi_data, weather_data)
        
        route_data.append({
            "lat": point[0],
            "lon": point[1],
            "aqi": aqi,
            "temp": temp,
            "components": components,
            "score": score
        })
    
    # Approximate distance and duration
    distance = target_distance
    duration = distance / 1.4  # Assume walking speed of 1.4 m/s
    
    return {
        "route": points,
        "route_data": route_data,
        "distance": distance,
        "duration": duration,
        "is_fallback": True
    }



@app.route('/find_route', methods=['POST'])
def find_route():
    data = request.json
    lat = float(data.get('lat'))
    lon = float(data.get('lon'))
    target_distance = int(data.get('target_distance', 5000))
    
    try:
        # Find optimal route
        route_result = find_optimal_routes(lat, lon, target_distance)
        
        if route_result:
            return jsonify(route_result)
        else:
            # Fallback to simple route if optimal route fails
            fallback_route = create_simple_route(lat, lon, target_distance)
            fallback_route["message"] = "Using fallback route due to API limitations"
            return jsonify(fallback_route)
    
    except Exception as e:
        print(f"Error finding route: {e}")
        return jsonify({
            "error": "Failed to find route",
            "message": str(e)
        }), 500





if __name__ == '__main__':
    app.run(debug=True)
