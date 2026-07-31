import asyncio
from uuid import uuid4

from dotenv import load_dotenv
from src.infra.database.mongo.indexes.create_indexes import create_indexes
from src.infra.database.mongo.mongodb_client import MongoDBClient
from src.workflow.runner import execute_turn

load_dotenv()


async def startup():
    await MongoDBClient.connect()
    await create_indexes()


async def run_chat():
    from src.workflow.graph.graph import compiled_app
    conversation_id = str(uuid4())

    while True:
        try:
            user_input = input("\n\033[94m> ")
            print("\033[0m", end="")
            if user_input.lower() in ("sair", "fim", "quit"):
                fim = "Encerrando"
                for c in range(4):
                    print(fim + "." * c)
                    if c != 3:
                        await asyncio.sleep(1)
                break

            final_state = await execute_turn(
                conversation_id,
                user_input,
                compiled_app,
            )

            print(f"{final_state['messages'][-1].content}")

        except (ConnectionError, TimeoutError, ValueError, RuntimeError) as error:
            print(f"Ocorreu um erro: {error}")


if __name__ == "__main__":
    async def main():
        await startup()
        await run_chat()


    asyncio.run(main())
