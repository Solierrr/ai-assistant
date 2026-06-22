import os
from pymongo import MongoClient

def obter_cliente_mongodb() -> MongoClient:
    """Retorna uma instância única de cliente do MongoDB Atlas ou Local."""
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    return MongoClient(uri)