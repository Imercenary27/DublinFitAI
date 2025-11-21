# data_services/sonitus_service.py
import json
from typing import List, Dict
from config.settings import Config

class SonitusService:
    def __init__(self):
        self.data = self._load_data()
        
    def _load_data(self):
        with open(Config.DATA_PATH) as f:
            return json.load(f)
    
    def get_air_quality(self, lat: float, lng: float, radius: float) -> List[Dict]:
        return self._filter_stations('air', lat, lng, radius)
    
    def get_noise_levels(self, lat: float, lng: float, radius: float) -> List[Dict]:
        return self._filter_stations('noise', lat, lng, radius)
    
    def _filter_stations(self, station_type: str, lat: float, lng: float, radius: float):
        # Implementation for filtering stations within radius
        pass
