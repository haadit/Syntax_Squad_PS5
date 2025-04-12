import joblib
import pandas as pd
import numpy as np
from datetime import datetime
import os
import logging
from utils import calculate_distance, calculate_average_speed, calculate_road_complexity
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='model_predictions.log'
)
logger = logging.getLogger(__name__)

# Cache for model and its timestamp
_model_cache = {
    'model': None,
    'last_loaded': 0,
    'refresh_interval': 300  # Refresh model every 5 minutes
}

def load_model(force_refresh=False):
    """Load the trained model with caching and periodic refresh"""
    try:
        current_time = time.time()
        
        # Check if model needs refresh
        if (_model_cache['model'] is None or 
            force_refresh or 
            current_time - _model_cache['last_loaded'] > _model_cache['refresh_interval']):
            
            model_path = os.path.join('models', 'best_model.pkl')
            _model_cache['model'] = joblib.load(model_path)
            _model_cache['last_loaded'] = current_time
            logger.info("Model refreshed successfully")
        
        return _model_cache['model']
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}")
        raise

def get_traffic_multiplier(hour_of_day, day_of_week, route_type, distance_km):
    """Calculate traffic multiplier with improved distance-based factors"""
    try:
        # Base multiplier
        traffic_multiplier = 1.0
        
        # Distance-based base multiplier
        if distance_km < 5:
            traffic_multiplier *= 1.3  # Short routes have more stops/turns
        elif distance_km < 10:
            traffic_multiplier *= 1.2
        elif distance_km < 15:
            traffic_multiplier *= 1.1
        else:
            traffic_multiplier *= 1.0  # Long routes often use highways
        
        # Peak hours with distance consideration
        morning_peak = (hour_of_day >= 7 and hour_of_day <= 10)
        evening_peak = (hour_of_day >= 17 and hour_of_day <= 20)
        is_peak_hour = morning_peak or evening_peak
        
        # Weekend adjustment
        is_weekend = day_of_week.lower() in ['saturday', 'sunday']
        
        # Route type specific adjustments
        route_multipliers = {
            'IT Hub': 1.3,
            'Commercial': 1.2,
            'Mixed': 1.25,
            'Residential': 1.1
        }
        route_multiplier = route_multipliers.get(route_type, 1.2)
        
        # Apply multipliers based on conditions
        if is_peak_hour:
            if is_weekend:
                if distance_km < 10:
                    traffic_multiplier += 0.4  # Short routes more affected
                else:
                    traffic_multiplier += 0.3
            else:
                if distance_km < 10:
                    traffic_multiplier += 0.9  # Short routes heavily affected during weekday peaks
                else:
                    traffic_multiplier += 0.7
        elif hour_of_day <= 5 or hour_of_day >= 22:  # Night hours
            traffic_multiplier -= 0.4
        elif is_weekend:
            if distance_km < 10:
                traffic_multiplier += 0.3
            else:
                traffic_multiplier += 0.2
        
        # Apply route type multiplier
        traffic_multiplier *= route_multiplier
        
        # Add real-time variation
        time_of_day_factor = 1.0
        if morning_peak:
            time_of_day_factor = 1.2
        elif evening_peak:
            time_of_day_factor = 1.3
        
        traffic_multiplier *= time_of_day_factor
        
        # Add small random variation for real-time conditions
        random_factor = 1 + (np.random.random() * 0.2 - 0.1)
        traffic_multiplier *= random_factor
        
        logger.info(f"Traffic multiplier: {traffic_multiplier:.2f} for {route_type} route ({distance_km} km)")
        return traffic_multiplier
    except Exception as e:
        logger.error(f"Error calculating traffic multiplier: {str(e)}")
        return 1.0

def predict_travel_time(start_point, destination, day_of_week, departure_time, route_type=None):
    """Make prediction using the trained model with improved accuracy"""
    try:
        # Load model (with potential refresh)
        model = load_model()
        
        # Parse departure time
        hour_of_day = int(departure_time.split(':')[0])
        
        # Calculate distance with area type consideration
        distance = calculate_distance(start_point, destination, route_type)
        
        # Get traffic multiplier with distance consideration
        traffic_multiplier = get_traffic_multiplier(hour_of_day, day_of_week, route_type, distance)
        
        # Calculate average speed with distance consideration
        avg_speed = calculate_average_speed(traffic_multiplier, route_type, distance)
        
        # Create feature dictionary with improved features
        features = {
            'day_of_week': [day_of_week],
            'month': [datetime.now().strftime('%B')],
            'hour_of_day': [hour_of_day],
            'is_weekend': [int(day_of_week.lower() in ['saturday', 'sunday'])],
            'is_peak_hour': [int((hour_of_day >= 7 and hour_of_day <= 10) or (hour_of_day >= 17 and hour_of_day <= 20))],
            'traffic_multiplier': [traffic_multiplier],
            'distance_km': [distance],
            'base_speed': [avg_speed],
            'noise_multiplier': [1.0 + (np.random.random() * 0.1 - 0.05)],
            'is_morning': [int(hour_of_day >= 6 and hour_of_day <= 12)],
            'is_evening': [int(hour_of_day >= 16 and hour_of_day <= 20)],
            'is_night': [int(hour_of_day <= 5 or hour_of_day >= 22)],
            'traffic_distance': [distance * traffic_multiplier],
            'speed_kmh': [avg_speed],
            'traffic_speed': [avg_speed / traffic_multiplier],
            'weekend_traffic': [int(day_of_week.lower() in ['saturday', 'sunday']) * traffic_multiplier],
            'peak_traffic': [int((hour_of_day >= 7 and hour_of_day <= 10) or (hour_of_day >= 17 and hour_of_day <= 20)) * traffic_multiplier],
            'quarter': [f'Q{(datetime.now().month-1)//3 + 1}'],
            'week_of_year': [datetime.now().isocalendar()[1]]
        }
        
        # Convert to DataFrame
        df = pd.DataFrame(features)
        
        # Make prediction
        base_prediction = model.predict(df)[0]
        
        # Distance-based prediction adjustments
        if distance < 5:
            # Short trips have more variability
            variability = 0.20
        elif distance < 10:
            variability = 0.15
        else:
            # Longer trips tend to be more predictable
            variability = 0.10
            
        # Add real-time variability
        random_adjustment = 1 + (np.random.random() * variability * 2 - variability)
        prediction = base_prediction * random_adjustment
        
        # Calculate realistic bounds based on distance and conditions
        min_speed = 8 if distance < 5 else (12 if distance < 15 else 15)  # km/h
        max_speed = 35 if distance < 5 else (45 if distance < 15 else 55)  # km/h
        
        min_time = (distance / max_speed) * 60  # minutes
        max_time = (distance / min_speed) * 60  # minutes
        
        # Ensure prediction is within realistic bounds
        prediction = max(min_time, min(prediction, max_time))
        
        # Add traffic light and intersection delays
        num_intersections = max(1, int(distance / 0.5))  # Estimate one intersection every 500m
        intersection_delay = 0.5  # minutes per intersection
        total_intersection_delay = num_intersections * intersection_delay
        
        prediction += total_intersection_delay
        
        # Round to nearest minute
        prediction = round(prediction)
        
        logger.info(f"Final prediction: {prediction} minutes for {distance:.1f} km journey")
        return prediction
    except Exception as e:
        logger.error(f"Error making prediction: {str(e)}")
        raise 