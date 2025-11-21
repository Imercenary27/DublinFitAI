# utils/sonitus_client.py
import requests
from datetime import datetime, timedelta
import time

class SonitusClient:
    def __init__(self):
        self.base_url = "https://data.smartdublin.ie/sonitus-api/api/"
        self.auth = {
            "username": "dublincityapi",
            "password": "Xpa5vAQ9ki"
        }

    def _get_unix_timestamps(self, hours=24):
        end = datetime.now()
        start = end - timedelta(hours=hours)
        return int(start.timestamp()), int(end.timestamp())

    def get_readings(self, monitor_serial, reading_type='air', hours=24):
        endpoint = "hourly-averages" if reading_type == 'air' else "noise-averages"
        start, end = self._get_unix_timestamps(hours)
        
        params = {
            **self.auth,
            "monitor": monitor_serial,
            "start": start,
            "end": end
        }
        
        try:
            response = requests.get(f"{self.base_url}{endpoint}", params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            return None
