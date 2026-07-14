from pymongo import AsyncMongoClient
from src.core.config.settings import settings


class MongoDBClient:

    client = None
    database = None

    @classmethod
    async def connect(cls):
        cls.client = AsyncMongoClient(
            settings.MONGO_URI
        )

        cls.database = cls.client[
            settings.MONGO_DB
        ]
        print("MongoDB conectado!")

    @classmethod
    def get_database(cls):
        return cls.database
