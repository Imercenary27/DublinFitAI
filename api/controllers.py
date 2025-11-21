# api/controllers.py
from flask import jsonify
from data_services.sonitus_service import SonitusService
from data_services.traffic_service import TrafficService
from ml_services.route_recommender import RouteRecommender

class ApiController:
    def __init__(self):
        self.sonitus = SonitusService()
        self.traffic = TrafficService()
        self.recommender = RouteRecommender()

    def get_recommendations(self, lat, lng, radius):
        # Get environmental data
        air_quality = self.sonitus.get_air_quality(lat, lng, radius)
        noise_levels = self.sonitus.get_noise_levels(lat, lng, radius)
        traffic_data = self.traffic.get_traffic_data(lat, lng, radius)
        
        # Get recommendations
        return self.recommender.generate_recommendations(
            air_quality,
            noise_levels,
            traffic_data
        )
