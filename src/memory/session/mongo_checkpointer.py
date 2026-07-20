from langgraph.checkpoint.mongodb import MongoDBSaver
from src.infra.database.mongodb_sync_client import get_mongodb_client

def create_mongo_checkpointer() -> MongoDBSaver:
    """Inicializa o gerenciador de persistência de curto prazo no MongoDB."""
    client = get_mongodb_client()
    
    checkpointer = MongoDBSaver(
        client=client,
        db_name="assessor_inteligente",
        collection_name="checkpoints_conversas"
    )
    return checkpointer
