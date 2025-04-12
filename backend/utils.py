import math
import logging
import pandas as pd
import numpy as np
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='model_predictions.log'
)
logger = logging.getLogger(__name__)

def calculate_road_complexity(distance, area_type=None):
    """Calculate road complexity factor based on distance and area type"""
    try:
        # Base complexity (roads are never straight)
        base_factor = 1.2
        
        # Distance-based complexity
        if distance < 5:  # Short urban routes have more turns
            complexity = base_factor + 0.3
        elif distance < 10:
            complexity = base_factor + 0.25
        elif distance < 15:
            complexity = base_factor + 0.2
        else:  # Longer routes tend to use highways more
            complexity = base_factor + 0.15
            
        # Area-based adjustments
        area_factors = {
            'IT Hub': 1.1,  # More direct routes
            'Commercial': 1.2,  # More intersections
            'Residential': 1.25,  # More turns and small roads
            'Mixed': 1.15  # Moderate complexity
        }
        
        if area_type:
            complexity *= area_factors.get(area_type, 1.0)
            
        return complexity
    except Exception as e:
        logger.error(f"Error calculating road complexity: {str(e)}")
        return 1.2

def calculate_distance(start_point, destination, area_type=None):
    """Calculate distance between points with improved real-world adjustments"""
    try:
        if not isinstance(start_point, tuple) or not isinstance(destination, tuple):
            logger.warning("Invalid coordinate format. Using fallback distance.")
            return 10.0
        
        lat1, lon1 = start_point
        lat2, lon2 = destination
        
        # Convert coordinates to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula for straight-line distance
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371  # Earth's radius in kilometers
        straight_distance = round(c * r, 2)
        
        # Calculate road complexity factor
        complexity = calculate_road_complexity(straight_distance, area_type)
        
        # Apply complexity factor
        real_distance = straight_distance * complexity
        
        # Add micro-variations based on time of day
        hour = datetime.now().hour
        if 7 <= hour <= 10 or 16 <= hour <= 19:  # Peak hours
            # During peak hours, drivers might take alternate routes
            real_distance *= (1 + (np.random.random() * 0.15))
        
        logger.info(f"Calculated distance: {real_distance:.2f} km (straight: {straight_distance:.2f} km)")
        return round(real_distance, 2)
    except Exception as e:
        logger.error(f"Error calculating distance: {str(e)}")
        return 10.0

def calculate_average_speed(traffic_multiplier, route_type=None, distance=None):
    """Calculate average speed with distance-based adjustments"""
    try:
        # Base speeds adjusted for different route lengths
        short_distance_speeds = {
            'IT Hub': 22,
            'Commercial': 25,
            'Mixed': 23,
            'Residential': 30
        }
        
        medium_distance_speeds = {
            'IT Hub': 28,
            'Commercial': 32,
            'Mixed': 30,
            'Residential': 35
        }
        
        long_distance_speeds = {
            'IT Hub': 35,
            'Commercial': 40,
            'Mixed': 38,
            'Residential': 45
        }
        
        # Select speed table based on distance
        if distance is None:
            speed_table = medium_distance_speeds
        elif distance < 5:
            speed_table = short_distance_speeds
        elif distance < 15:
            speed_table = medium_distance_speeds
        else:
            speed_table = long_distance_speeds
        
        # Get base speed for route type
        base_speed = speed_table.get(route_type, 30)
        
        # Apply traffic multiplier
        speed = base_speed / traffic_multiplier
        
        # Speed bounds based on distance
        if distance is not None:
            if distance < 5:
                min_speed, max_speed = 10, 40
            elif distance < 15:
                min_speed, max_speed = 15, 50
            else:
                min_speed, max_speed = 20, 60
        else:
            min_speed, max_speed = 15, 50
        
        # Time-based adjustments
        hour = datetime.now().hour
        if hour >= 22 or hour <= 5:  # Night time
            speed *= 1.3
            max_speed *= 1.2
        elif hour in [7, 8, 9, 17, 18, 19]:  # Peak hours
            speed *= 0.7
            max_speed *= 0.8
        
        # Weather impact (simplified - could be expanded with real weather data)
        weather_factor = 1.0 + (np.random.random() * 0.1 - 0.05)
        speed *= weather_factor
        
        # Final bounds check
        final_speed = max(min_speed, min(speed, max_speed))
        
        logger.info(f"Calculated speed: {final_speed:.2f} km/h for {route_type} route ({distance if distance else 'unknown'} km)")
        return round(final_speed, 2)
    except Exception as e:
        logger.error(f"Error calculating speed: {str(e)}")
        return 25  # Default fallback speed 