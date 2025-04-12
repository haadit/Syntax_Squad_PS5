# Supabase Integration for User Authentication and Prediction History

## 1. Supabase Setup

### 1.1 Create Supabase Project
1. Go to [Supabase](https://supabase.com/) and sign up/login
2. Click "New Project"
3. Fill in project details:
   - Name: `traffic-prediction`
   - Database Password: (create a secure password)
   - Region: (choose closest to your users)
4. Wait for project initialization

### 1.2 Get Project Credentials
1. Go to Project Settings > API
2. Note down:
   - Project URL
   - anon/public key
   - service_role key (keep this secret)

## 2. Database Schema Setup

### 2.1 Create Tables
Run these SQL commands in Supabase SQL Editor:

```sql
-- Users table (automatically created by Supabase Auth)
-- No need to create manually

-- Predictions History table
CREATE TABLE prediction_history (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    start_point TEXT NOT NULL,
    destination TEXT NOT NULL,
    predicted_time FLOAT NOT NULL,
    actual_time FLOAT,
    day_of_week TEXT NOT NULL,
    departure_time TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    traffic_level TEXT NOT NULL,
    route_type TEXT,
    distance_km FLOAT
);

-- User Preferences table
CREATE TABLE user_preferences (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    preferred_route_type TEXT,
    notification_enabled BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);
```

### 2.2 Set Up Row Level Security (RLS)
```sql
-- Enable RLS
ALTER TABLE prediction_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Users can view their own prediction history"
    ON prediction_history FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own prediction history"
    ON prediction_history FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view their own preferences"
    ON user_preferences FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own preferences"
    ON user_preferences FOR UPDATE
    USING (auth.uid() = user_id);
```

## 3. Backend Implementation

### 3.1 Install Required Packages
```bash
pip install supabase python-dotenv
```

### 3.2 Create Environment File
Create `.env` file in your backend directory:
```
SUPABASE_URL=your_project_url
SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_role_key
```

### 3.3 Create Supabase Client
Create `supabase_client.py`:
```python
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)
```

### 3.4 Update User Authentication
Modify `app.py` to include authentication endpoints:

```python
from flask import Flask, request, jsonify, session
from supabase_client import supabase
import jwt
from datetime import datetime, timedelta

# Add these routes to your existing app.py

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
```

### 3.5 Update Prediction Endpoint
Modify your existing prediction endpoint to save history:

```python
@app.route('/predict', methods=['POST'])
def predict():
    try:
        # Get auth token from header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"error": "No authorization token"}), 401
            
        token = auth_header.split(' ')[1]
        
        # Verify token and get user
        user = supabase.auth.get_user(token)
        if not user:
            return jsonify({"error": "Invalid token"}), 401
            
        data = request.get_json()
        start_point = data.get('start_point')
        destination = data.get('destination')
        day_of_week = data.get('day_of_week')
        departure_time = data.get('departure_time')
        
        # Get prediction
        prediction = predict_travel_time(
            start_point=start_point,
            destination=destination,
            day_of_week=day_of_week,
            departure_time=departure_time
        )
        
        # Save to prediction history
        supabase.table('prediction_history').insert({
            "user_id": user.id,
            "start_point": start_point,
            "destination": destination,
            "predicted_time": prediction,
            "day_of_week": day_of_week,
            "departure_time": departure_time,
            "traffic_level": get_traffic_level(prediction, 30)  # Assuming 30 is typical time
        }).execute()
        
        return jsonify({
            'predicted_time': prediction,
            'units': 'minutes'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### 3.6 Add Prediction History Endpoint
```python
@app.route('/predictions/history', methods=['GET'])
def get_prediction_history():
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"error": "No authorization token"}), 401
            
        token = auth_header.split(' ')[1]
        user = supabase.auth.get_user(token)
        if not user:
            return jsonify({"error": "Invalid token"}), 401
            
        # Get prediction history
        response = supabase.table('prediction_history')\
            .select("*")\
            .eq('user_id', user.id)\
            .order('created_at', desc=True)\
            .execute()
            
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

## 4. Frontend Implementation

### 4.1 Install Supabase Client
```bash
npm install @supabase/supabase-js
```

### 4.2 Create Supabase Client
```javascript
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.REACT_APP_SUPABASE_URL
const supabaseAnonKey = process.env.REACT_APP_SUPABASE_ANON_KEY

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

### 4.3 Add Authentication Components
Create login and registration forms, and implement the authentication flow using Supabase client methods.

### 4.4 Update API Calls
Modify your existing API calls to include the authentication token:
```javascript
const getPrediction = async (data) => {
  const { data: { session } } = await supabase.auth.getSession()
  
  const response = await fetch('/api/predict', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${session.access_token}`
    },
    body: JSON.stringify(data)
  })
  
  return response.json()
}
```

## 5. Testing

1. Test user registration and login
2. Verify prediction history is being saved
3. Check that users can only access their own data
4. Test error handling for invalid tokens
5. Verify RLS policies are working correctly

## 6. Security Considerations

1. Always use HTTPS
2. Store sensitive keys in environment variables
3. Implement rate limiting
4. Add input validation
5. Use secure session management
6. Implement proper error handling
7. Regularly update dependencies
8. Monitor for suspicious activities

## 7. Next Steps

1. Implement user preferences
2. Add email verification
3. Create admin dashboard
4. Add data analytics
5. Implement password reset functionality
6. Add social login options
7. Create user profile management
8. Implement notification system 