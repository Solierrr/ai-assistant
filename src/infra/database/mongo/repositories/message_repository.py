from src.infra.database.mongo.collections.collections import Collections
from src.infra.database.mongo.mongodb_client import MongoDBClient


class MessageRepository:
    def __init__(self):
        db = MongoDBClient.get_database()
        self.collection = db[
            Collections.MESSAGES
        ]

    async def save_message(
        self,
        data
    ):
        return await self.collection.insert_one(
            data
        )

    async def get_messages_by_conversation(
        self,
        conversation_id
    ):
        cursor = self.collection.find({
            "conversation_id": conversation_id
        }).sort("timestamp", 1)
        return await cursor.to_list(length=100)