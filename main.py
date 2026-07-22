import asyncio
from time import sleep

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from src.infra.database.mongo.indexes.create_indexes import create_indexes
from src.infra.database.mongo.mongodb_client import MongoDBClient

load_dotenv()


async def startup():
    await MongoDBClient.connect()
    await create_indexes()


def run_chat():
    from src.workflow.graph.graph import compiled_app

    while True:
        try:
            user_input = input("\n\033[94m> ")
            print("\033[0m", end="")
            if user_input.lower() in ("sair", "fim", "quit"):
                fim = "Encerrando"
                for c in range(4):
                    print(fim + "." * c)
                    if c != 3:
                        sleep(1)
                break

            initial_state = {
                "messages": [HumanMessage(content=user_input)],
                "route": "",
                "pii_map": {},
                "called_agents": [],
            }

            final_state = compiled_app.invoke(
                initial_state,
                config={"configurable": {"thread_id": "id"}},
            )

            print(f"{final_state['messages'][-1].content}")

        except Exception as e:
            print(f"Ocorreu um erro: {e}")


if __name__ == "__main__":
    asyncio.run(startup())
    run_chat()
