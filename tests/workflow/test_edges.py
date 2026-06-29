from src.workflow.edges.decidir_agente import decidir_pos_entrada, decidir_pos_roteador


def test_decidir_pos_entrada_retorna_fim_quando_rota_e_fim():
    assert decidir_pos_entrada({"rota": "fim"}) == "fim"


def test_decidir_pos_entrada_retorna_prosseguir_para_outras_rotas():
    assert decidir_pos_entrada({"rota": "solar_panel_specialist"}) == "prosseguir"


def test_decidir_pos_roteador_retorna_fim_quando_rota_e_fim():
    assert decidir_pos_roteador({"rota": "fim"}) == "fim"


def test_decidir_pos_roteador_retorna_prosseguir_para_outras_rotas():
    assert decidir_pos_roteador({"rota": "orquestrador"}) == "prosseguir"
