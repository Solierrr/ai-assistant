import os

from pymongo import MongoClient


def get_mongodb_client() -> MongoClient:
    """Return a MongoDB Atlas or local client instance."""
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    return MongoClient(uri)
