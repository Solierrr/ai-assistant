from pymongo import MongoClient

from src.core.config.settings import settings
from src.infra.database.mongo.client_options import build_mongo_client_options


def get_mongodb_client() -> MongoClient:
    """Return a MongoDB Atlas or local client instance."""
    return MongoClient(
        settings.MONGO_URI,
        **build_mongo_client_options(settings.MONGO_URI),
    )
