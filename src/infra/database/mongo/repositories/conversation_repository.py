from src.infra.database.mongo.collections.collections import Collections
from src.infra.database.mongo.mongodb_client import MongoDBClient


class ConversationRepository:
    def __init__(self):
        db = MongoDBClient.get_database()
        self.collection = db[
            Collections.CONVERSATIONS
        ]

    async def create(
        self,
        data
    ):
        return await self.collection.insert_one(
            data
        )

    async def find_by_id(
        self,
        conversation_id
    ):
        return await self.collection.find_one({
            "conversation_id": conversation_id
        })

    async def update_active_agent(
        self,
        conversation_id,
        agent
    ):
        return await self.collection.update_one(
            {
                "conversation_id": conversation_id
            },
            {
                "$set": {
                    "active_agent": agent
                }
            }
        )