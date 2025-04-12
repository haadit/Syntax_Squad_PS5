import React, { useState } from 'react';
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { format } from 'date-fns';
import { motion } from 'framer-motion';

// Fix for default marker icons in Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

const API_URL = 'http://localhost:8000';

const LocationMarker = ({ position, setPosition }) => {
  useMapEvents({
    click(e) {
      setPosition(e.latlng);
    },
  });

  return position ? <Marker position={position} /> : null;
};

const MapComponent = ({ position, setPosition, title }) => (
  <div className="space-y-3">
    <h3 className="text-xl font-semibold text-gray-800">{title}</h3>
    <div className="map-container">
      <MapContainer
        center={[12.9716, 77.5946]}
        zoom={12}
        className="h-full w-full"
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        />
        <LocationMarker position={position} setPosition={setPosition} />
      </MapContainer>
    </div>
    {position && (
      <p className="text-sm text-gray-600">
        Selected: {position.lat.toFixed(4)}, {position.lng.toFixed(4)}
      </p>
    )}
  </div>
);

const ETAPredictor = () => {
  const [homeLocation, setHomeLocation] = useState(null);
  const [officeLocation, setOfficeLocation] = useState(null);
  const [departureTime, setDepartureTime] = useState(format(new Date(), "yyyy-MM-dd'T'HH:mm"));
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const calculateConfidenceInterval = (eta) => {
    const margin = eta * 0.1;
    return {
      lower: Math.max(0, Math.round(eta - margin)),
      upper: Math.round(eta + margin)
    };
  };

  const handlePredict = async () => {
    if (!homeLocation || !officeLocation) {
      setError('Please select both home and office locations');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_URL}/predict`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({
          home_location: {
            latitude: homeLocation.lat,
            longitude: homeLocation.lng,
          },
          office_location: {
            latitude: officeLocation.lat,
            longitude: officeLocation.lng,
          },
          departure_time: departureTime.replace('T', ' '),
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || 'Failed to get prediction');
      }

      const data = await response.json();
      setPrediction(data);
    } catch (err) {
      setError(err.message);
      console.error('Prediction error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="py-8">
      <div className="container-width">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white/90 backdrop-blur-sm rounded-xl shadow-lg p-8"
        >
          <h2 className="text-2xl font-bold text-gray-900 mb-8">ETA Predictor</h2>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            <MapComponent
              position={homeLocation}
              setPosition={setHomeLocation}
              title="Home Location"
            />
            <MapComponent
              position={officeLocation}
              setPosition={setOfficeLocation}
              title="Office Location"
            />
          </div>

          <div className="mb-8">
            <label className="block text-gray-700 text-sm font-semibold mb-2">
              Departure Time
            </label>
            <input
              type="datetime-local"
              value={departureTime}
              onChange={(e) => setDepartureTime(e.target.value)}
              className="input-field"
            />
          </div>

          <button
            onClick={handlePredict}
            disabled={loading || !homeLocation || !officeLocation}
            className={`btn w-full ${loading || !homeLocation || !officeLocation ? 'btn-disabled' : 'btn-primary'}`}
          >
            {loading ? 'Calculating ETA...' : 'Predict ETA'}
          </button>

          {error && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mt-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg"
            >
              {error}
            </motion.div>
          )}

          {prediction && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-8"
            >
              <h3 className="text-xl font-semibold text-gray-800 mb-6">Prediction Results</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="prediction-card">
                  <p className="prediction-label">Predicted ETA</p>
                  <p className="prediction-value">
                    {Math.round(prediction.predicted_eta_minutes)} min
                  </p>
                  <div className="mt-2">
                    <p className="text-sm text-gray-500 mb-1">
                      95% Confidence Interval
                    </p>
                    <p className="confidence-interval">
                      {calculateConfidenceInterval(prediction.predicted_eta_minutes).lower} - {calculateConfidenceInterval(prediction.predicted_eta_minutes).upper} minutes
                    </p>
                  </div>
                </div>
                <div className="prediction-card">
                  <p className="prediction-label">Trip Details</p>
                  <p className="prediction-value">
                    {prediction.distance_km.toFixed(1)} km
                  </p>
                  <div className="space-y-2 text-sm text-gray-600">
                    <p>Departure: {new Date(prediction.departure_time).toLocaleTimeString()}</p>
                    <p>Day: {prediction.day_of_week}</p>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </motion.div>
      </div>
    </div>
  );
};

export default ETAPredictor; 