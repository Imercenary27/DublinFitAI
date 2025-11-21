# utils/data_validators.py
from pydantic import BaseModel, confloat

class CoordinateValidator(BaseModel):
    latitude: confloat(ge=-90, le=90)
    longitude: confloat(ge=-180, le=180)
