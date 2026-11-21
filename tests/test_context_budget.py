import pytest

from scp_context_manager import ContextManager


def test_budget(tmp_path):
    c = ContextManager(3072, tmp_path)
    turns = [
        (f"Вопрос {i}: " + "а" * 350, f"Ответ {i}: " + "б" * 300) for i in range(40)
    ]
    prompt = c.build_prompt(
        "СИСТЕМА",
        "ЭМОЦИИ",
        "ПРОФИЛЬ",
        turns,
        ["саммари" * 2000],
        ["факт" * 2000],
        512,
        "почему?",
    )
    assert (len(prompt) + 2) // 3 <= 3072 - 512 - 32
    assert all(
        x in prompt
        for x in ["СИСТЕМА", "ЭМОЦИИ", "ПРОФИЛЬ", "почему?", *turns[-1], *turns[-2]]
    )
    with pytest.raises(ValueError):
        c.build_prompt("x" * 10000, "", "", [], [], [], 512)


def test_summary_reused(tmp_path):
    msgs = [
        {"role": r, "content": f"{i}{r}"}
        for i in range(20)
        for r in ("user", "assistant")
    ] + [{"role": "user", "content": "сейчас"}]
    calls = []
    for _ in range(2):
        out = ContextManager(3072, tmp_path).prepare(
            msgs, 160, lambda p: calls.append(p) or "краткий итог"
        )
        assert "краткий итог" in out
    assert len(calls) == 1


def test_cold_keeps_fact_not_transcript():
    messages = []
    for i in range(30):
        messages.extend(
            [
                {
                    "role": "user",
                    "content": "запомни: любимый цвет синий." if not i else f"Тема {i}",
                },
                {"role": "assistant", "content": f"старая-реплика-{i}!"},
            ]
        )
    messages.append({"role": "user", "content": "что помнишь?"})
    prompt = ContextManager().prepare(messages, 96)
    assert "любимый цвет синий" in prompt and "старая-реплика-0!" not in prompt
