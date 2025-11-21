# config/settings.py
import os

class Config:
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT = os.getenv('FLASK_PORT', 5000)
    DEBUG = os.getenv('FLASK_DEBUG', True)
    DATA_PATH = os.path.join('C:\\Users\\amate\\OneDrive\\Desktop\\NCI101\\CAML2\\data\\locator.json')
