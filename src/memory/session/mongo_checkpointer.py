from langgraph.checkpoint.mongodb import MongoDBSaver
from src.infra.database.mongodb_client import obter_cliente_mongodb

def criar_checkpointer_mongo() -> MongoDBSaver:
    """Inicializa o gerenciador de persistência de curto prazo no MongoDB."""
    cliente = obter_cliente_mongodb()
    
    checkpointer = MongoDBSaver(
        client=cliente,
        db_name="assessor_inteligente",
        collection_name="checkpoints_conversas"
    )
    return checkpointer