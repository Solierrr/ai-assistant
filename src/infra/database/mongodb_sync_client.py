import certifi
from pymongo import MongoClient

from src.core.config.settings import settings


def get_mongodb_client() -> MongoClient:
    """Return a MongoDB Atlas or local client instance."""
    return MongoClient(settings.MONGO_URI, tlsCAFile=certifi.where())
