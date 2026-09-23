from types import SimpleNamespace

from src.infra.billscanner import client


def test_get_billscanner_tools_loads_and_caches_tools(monkeypatch):
    tools = [SimpleNamespace(name="calcular_sistema_solar")]
    fake_module = SimpleNamespace(BILLSCANNER_TOOLS=tuple(tools))
    client.get_billscanner_tools.cache_clear()

    monkeypatch.setitem(__import__("sys").modules, "app.langchain_tools", fake_module)

    assert client.get_billscanner_tools() == tools
    assert client.get_billscanner_tools() is client.get_billscanner_tools()
