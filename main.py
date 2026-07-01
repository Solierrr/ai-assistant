from dotenv import load_dotenv
load_dotenv()

from src.infra.database.mongo.mongodb_client import MongoDBClient
from src.infra.database.mongo.indexes.create_indexes import create_indexes
from time import sleep
import asyncio


async def startup():
    await MongoDBClient.connect()
    await create_indexes()


def run_chat():
    from langchain_core.messages import HumanMessage
    from src.workflow.graph.graph import app_fluxo

    while True:
        try:
            user_input = input("\n\033[94m> ")
            print("\033[0m", end="")
            if user_input.lower() in ("sair", "fim", "quit"):
                fim = "Encerrando"
                for c in range(4):
                    print(fim + "." * (c))
                    if c != 3:
                        sleep(1)
                break

            estado_inicial = {
                "messages": [HumanMessage(content=user_input)],
                "rota": "",
                "pii_map": {},
                "agentes_chamados": []
            }

            estado_final = app_fluxo.invoke(
                estado_inicial,
                config={"configurable": {"thread_id": "id"}}
            )

            print(f"{estado_final['messages'][-1].content}")

        except Exception as e:
            print(f"Ocorreu um erro: {e}")


if __name__ == "__main__":
    asyncio.run(startup())
    run_chat()
