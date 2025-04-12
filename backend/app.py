from flask import Flask, request, jsonify
from flask_cors import CORS
from model import predict_travel_time
from dotenv import load_dotenv
import os
import requests
from typing import List, Tuple
from datetime import datetime
from supabase_client import supabase
from supabase import create_client

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:5173", "http://localhost:5174"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
        "supports_credentials": True,
        "expose_headers": ["Content-Type", "Authorization"],
        "max_age": 3600
    }
})

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# Mapbox access token for geocoding
# Load environment variables from .env file
load_dotenv()

MAPBOX_ACCESS_TOKEN = os.environ.get('MAPBOX_ACCESS_TOKEN')

# Authentication endpoints
@app.route('/auth/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        
        return jsonify({"message": "Registration successful"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        return jsonify({
            "access_token": response.session.access_token,
            "user": response.user
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 401

@app.route('/auth/logout', methods=['POST'])
def logout():
    try:
        supabase.auth.sign_out()
        return jsonify({"message": "Logged out successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

def get_coordinates(address: str) -> Tuple[float, float]:
    """Convert address to coordinates using Mapbox Geocoding API."""
    try:
        # URL encode the address
        encoded_address = requests.utils.quote(address)
        response = requests.get(
            f'https://api.mapbox.com/geocoding/v5/mapbox.places/{encoded_address}.json',
            params={
                'access_token': MAPBOX_ACCESS_TOKEN,
                'limit': 1,
                'country': 'in'  # Focus on India
            }
        )
        
        if response.status_code != 200:
            print(f"Mapbox API error: {response.status_code} - {response.text}")
            return None, None
            
        data = response.json()
        if not data.get('features') or len(data['features']) == 0:
            print(f"No results found for address: {address}")
            return None, None
            
        # Return [longitude, latitude] as per Mapbox convention
        return data['features'][0]['center'][0], data['features'][0]['center'][1]
    except Exception as e:
        print(f"Error geocoding address {address}: {str(e)}")
        return None, None

def get_traffic_level(predicted_time: float, typical_time: float) -> str:
    """Determine traffic level based on predicted vs typical travel time."""
    ratio = predicted_time / typical_time
    if ratio > 1.5:
        return 'heavy'
    elif ratio > 1.2:
        return 'medium'
    else:
        return 'light'

def get_current_day_time():
    """Get current day of week and time in required format."""
    now = datetime.now()
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_of_week = days[now.weekday()]
    current_time = now.strftime('%H:%M')
    return day_of_week, current_time

@app.route('/api/traffic', methods=['GET'])
def get_traffic_data():
    try:
        start = request.args.get('start')
        destination = request.args.get('destination')
        
        if not start or not destination:
            return jsonify({'error': 'Missing start or destination'}), 400
            
        # Get coordinates for start and destination
        start_lng, start_lat = get_coordinates(start)
        dest_lng, dest_lat = get_coordinates(destination)
        
        if not all([start_lat, start_lng, dest_lat, dest_lng]):
            return jsonify({
                'error': 'Could not find coordinates for one or both locations',
                'details': {
                    'start_found': bool(start_lat and start_lng),
                    'destination_found': bool(dest_lat and dest_lng)
                }
            }), 400
            
        # Get current day and time
        day_of_week, current_time = get_current_day_time()
        
        # Get typical travel time (you might want to calculate this based on historical data)
        typical_time = 30  # Example typical time in minutes
        
        # Get predicted travel time using current time
        prediction = predict_travel_time(
            start_point=start,
            destination=destination,
            day_of_week=day_of_week,
            departure_time=current_time
        )
        
        # Determine traffic level based on predicted time
        now = datetime.now()
        current_hour = now.hour
        is_peak_hour = (current_hour >= 7 and current_hour <= 10) or (current_hour >= 17 and current_hour <= 20)
        is_weekend = now.weekday() >= 5  # Saturday or Sunday
        
        # Use predicted time to determine traffic level
        if is_peak_hour and prediction > typical_time * 1.3:  # 30% more than typical time during peak
            traffic_level = 'peak'  # Red
        elif is_weekend and prediction > typical_time * 1.2:  # 20% more than typical time on weekends
            traffic_level = 'normal'  # Yellow
        else:
            traffic_level = 'light'  # Green
        
        # Return traffic data
        return jsonify({
            'route_segments': [
                {
                    'start_point': [start_lat, start_lng],
                    'end_point': [dest_lat, dest_lng],
                    'traffic_level': traffic_level,
                    'speed': 60,  # Example speed in km/h
                    'typical_speed': 60,  # Example typical speed
                    'current_time': current_time,
                    'day_of_week': day_of_week
                }
            ]
        })
        
    except Exception as e:
        print(f"Error in get_traffic_data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/predict', methods=['POST'])
def predict():
    try:
        # Get auth token from header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"error": "No authorization token"}), 401
            
        token = auth_header.split(' ')[1]
        
        try:
            # Verify token and get user
            user = supabase.auth.get_user(token)
            if not user:
                return jsonify({"error": "Invalid token"}), 401
        except Exception as auth_error:
            print(f"Authentication error: {str(auth_error)}")
            return jsonify({"error": "Authentication failed"}), 401
            
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        start_point = data.get('start_point')
        destination = data.get('destination')
        day_of_week = data.get('day_of_week')
        departure_time = data.get('departure_time')
        
        if not all([start_point, destination, day_of_week, departure_time]):
            return jsonify({"error": "Missing required fields"}), 400
            
        # Get prediction
        prediction = predict_travel_time(
            start_point=start_point,
            destination=destination,
            day_of_week=day_of_week,
            departure_time=departure_time
        )
        
        # Store prediction in database using service role
        try:
            # Create a new Supabase client with service role key
            service_supabase = create_client(
                os.environ.get("SUPABASE_URL"),
                os.environ.get("SUPABASE_SERVICE_KEY")
            )
            
            service_supabase.table('predictions').insert({
                'user_id': user.user.id,
                'start_point': start_point,
                'destination': destination,
                'day_of_week': day_of_week,
                'departure_time': departure_time,
                'predicted_time': prediction,
                'created_at': datetime.now().isoformat()
            }).execute()
        except Exception as db_error:
            print(f"Database error: {str(db_error)}")
            # Continue even if database insert fails
            
        return jsonify({
            'predicted_time': prediction,
            'start_point': start_point,
            'destination': destination,
            'day_of_week': day_of_week,
            'departure_time': departure_time
        })
        
    except Exception as e:
        print(f"Prediction error: {str(e)}")
        return jsonify({"error": "Failed to process prediction"}), 500

@app.route('/predictions/history', methods=['GET'])
def get_prediction_history():

    try:
        # Get auth token from header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"error": "No authorization token"}), 401
            
        token = auth_header.split(' ')[1]
        
        try:
            # Verify token and get user
            user = supabase.auth.get_user(token)
            if not user:
                return jsonify({"error": "Invalid token"}), 401
                
            # Get prediction history using service role client
            service_supabase = create_client(
                os.environ.get("SUPABASE_URL"),
                os.environ.get("SUPABASE_SERVICE_KEY")
            )
            
            response = service_supabase.table('predictions')\
                .select('*')\
                .eq('user_id', user.user.id)\
                .order('created_at', desc=True)\
                .execute()
                
            print("\nFetched predictions array:")
            for prediction in response.data:
                print(f"- ID: {prediction.get('id')}, Start: {prediction.get('start_point')}, Destination: {prediction.get('destination')}, Time: {prediction.get('predicted_time')}")
            print(f"Total predictions found: {len(response.data)}\n")
                
            return jsonify(response.data), 200
            
        except Exception as auth_error:
            print(f"Authentication error: {str(auth_error)}")
            return jsonify({"error": "Authentication failed"}), 401
            
    except Exception as e:
        print(f"History error: {str(e)}")
        return jsonify({"error": "Failed to fetch prediction history"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)