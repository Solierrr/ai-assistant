from types import SimpleNamespace

from src.agents.specialist.solar_calculator.tools import client


def test_get_solar_calculator_tools_loads_and_caches_tools(monkeypatch):
    tools = [SimpleNamespace(name="calcular_sistema_solar")]
    fake_module = SimpleNamespace(SOLAR_CALCULATOR_TOOLS=tuple(tools))
    client.get_solar_calculator_tools.cache_clear()

    monkeypatch.setitem(
        __import__("sys").modules,
        "src.agents.specialist.solar_calculator.tools.langchain_tools",
        fake_module,
    )

    assert client.get_solar_calculator_tools() == tools
    assert client.get_solar_calculator_tools() is client.get_solar_calculator_tools()
