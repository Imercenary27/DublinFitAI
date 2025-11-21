from flask import Blueprint, jsonify, request
from utils.sonitus_client import SonitusClient

api_blueprint = Blueprint('api', __name__)
client = SonitusClient()

@api_blueprint.route('/sensor-data')
def sensor_data():
    serial = request.args.get('serial')
    data_type = request.args.get('type', 'air')
    
    if not serial:
        return jsonify({"error": "Missing serial parameter"}), 400
    
    readings = client.get_readings(serial, data_type)
    
    if not readings:
        return jsonify({"error": "Failed to fetch sensor data"}), 500
    
    processed = process_readings(readings, data_type)
    return jsonify(processed)

def process_readings(data, data_type):
    labels = [entry['datetime'] for entry in data]
    values = [entry['laeq'] for entry in data]
    
    return {
        "type": data_type,
        "labels": labels,
        "values": values,
        "average": sum(values) / len(values),
        "maximum": max(values),
        "minimum": min(values)
    }