from src.workflow.state import Estado

def decidir_pos_roteador(estado: Estado) -> str:
    if estado["rota"] == "fim":
        return "fim"
    return "prosseguir"

def decidir_pos_entrada(estado: Estado) -> str:
    if estado["rota"] == "fim":
        return "fim"
    return "prosseguir"