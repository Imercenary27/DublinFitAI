# api/models.py
from pydantic import BaseModel

class RecommendationRequest(BaseModel):
    latitude: float
    longitude: float
    radius: float
    preferences: dict

class EnvironmentalData(BaseModel):
    air_quality: dict
    noise_levels: dict
    traffic_data: dict
