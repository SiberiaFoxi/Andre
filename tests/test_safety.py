import pytest

from scp_safety import SafetyLayer
from scp_tools_extra import python_exec


def test_reconciliation():
    assert (
        SafetyLayer.filter("Ты должен. Я уйду, удалю себя.", {"resentment": 0.9})
        == "Я расстроена, но хочу поговорить."
    )


def test_arithmetic_only():
    assert python_exec(None, "x=12\nx/2") == "6.0"
    with pytest.raises(ValueError):
        python_exec(None, "import pathlib")
