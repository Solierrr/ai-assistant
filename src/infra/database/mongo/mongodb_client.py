from motor.motor_asyncio import AsyncIOMotorClient
from src.core.config.settings import settings


class MongoDBClient:

    client = None
    database = None

    @classmethod
    async def connect(cls):
        cls.client = AsyncIOMotorClient(
            settings.MONGO_URI
        )

        cls.database = cls.client[
            settings.MONGO_DB
        ]
        print("MongoDB conectado!")

    @classmethod
    def get_database(cls):
        return cls.database