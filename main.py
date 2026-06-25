from dotenv import load_dotenv
load_dotenv()

from src.workflow.graph.graph import app_fluxo
from langchain_core.messages import HumanMessage
from time import sleep

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