from pymongo import AsyncMongoClient

from src.core.config.settings import settings
from src.infra.database.mongo.client_options import build_mongo_client_options


class MongoDBClient:

    client = None
    database = None

    @classmethod
    async def connect(cls):
        cls.client = AsyncMongoClient(
            settings.MONGO_URI,
            **build_mongo_client_options(settings.MONGO_URI),
        )

        cls.database = cls.client[settings.MONGO_DB]
        print("MongoDB conectado!")

    @classmethod
    def get_database(cls):
        return cls.database
