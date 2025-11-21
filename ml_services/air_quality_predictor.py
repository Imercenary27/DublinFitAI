# ml_services/air_quality_predictor.py
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

class AirQualityPredictor:
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.trained = False
        
    def train(self, historical_data):
        """Train the model on historical air quality data."""
        X = historical_data[['latitude', 'longitude', 'time_of_day', 
                             'day_of_week', 'temperature', 'humidity', 
                             'wind_speed', 'traffic_volume']]
        y = historical_data['air_quality_index']
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42)
        
        self.model.fit(X_train, y_train)
        self.trained = True
        
        # Calculate and return model performance metrics
        score = self.model.score(X_test, y_test)
        return {'r2_score': score}
    
    def predict(self, location_data):
        """Predict air quality for locations without sensors."""
        if not self.trained:
            raise ValueError("Model must be trained before making predictions")
        
        predictions = self.model.predict(location_data)
        return predictions
