from src.infra.database.mongo.mongodb_client import MongoDBClient


async def create_indexes():
    db = MongoDBClient.get_database()

    await db.conversations.create_index(
        "conversation_id",
        unique=True
    )

    await db.messages.create_index(
        "conversation_id"
    )

    await db.messages.create_index(
        "timestamp"
    )
    print("Indexes criados!")