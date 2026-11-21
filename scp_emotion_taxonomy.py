"""Словарь эмоций и базовых реакций."""

from dataclasses import dataclass

__all__ = ["TAXONOMY", "Emotion", "EMOTION_DELTAS"]


@dataclass(frozen=True)
class Emotion:
    name: str
    category: str
    baseline: float
    decay_per_hour: float
    triggers: tuple
    suppressors: tuple
    prompt_phrase: str


GROUPS = {
    "basic": "joy sadness anger fear surprise disgust contempt",
    "social": "trust love affection tenderness gratitude pride shame guilt embarrassment envy jealousy admiration amusement nostalgia loneliness longing protectiveness attachment insecurity missing_you",
    "cognitive": "curiosity interest boredom concentration confusion awe skepticism determination hope despair anticipation resignation doubt alertness",
    "regulatory": "calm irritation frustration resentment forgiveness playfulness seriousness melancholy excitement satisfaction dissatisfaction quiet_pride restless_curiosity mild_annoyance reconciliation",
    "composite": "bittersweet jealousy_composite wounded_pride wounded_pride_composite guilty_pleasure nervous_excitement homesickness tough_love",
}
PHRASES = """радость грусть злость страх удивление отвращение презрение
доверие любовь привязанность нежность благодарность гордость стыд вина смущение зависть ревность восхищение веселье ностальгия одиночество тоска забота близость неуверенность скучаешь
любопытство интерес скука сосредоточенность замешательство трепет скепсис решимость надежда отчаяние предвкушение смирение сомнение настороженность
спокойствие раздражение досада обида прощение игривость серьёзность меланхолия волнение удовлетворение недовольство тихая-гордость нетерпеливое-любопытство лёгкая-досада примирение
светлая-грусть ревность уязвлённость уязвлённая-гордость запретная-радость волнение тоска-по-дому строгая-забота""".split()
EMOTION_DELTAS = {
    "user_message_positive": dict(
        joy=0.10, tenderness=0.05, gratitude=0.08, sadness=-0.05
    ),
    "user_message_negative": dict(sadness=0.08, mild_annoyance=0.06, alertness=0.10),
    "user_message": dict(interest=0.04, curiosity=0.02),
    "user_returned": dict(
        joy=0.20, bittersweet=0.25, resentment=-0.10, missing_you=-0.30, tenderness=0.15
    ),
    "tool_failure": dict(frustration=0.10, determination=0.06, joy=-0.05),
    "tool_success": dict(pride=0.08, joy=0.05, satisfaction=0.06),
    "absence_6": dict(missing_you=0.10, curiosity=0.05),
    "absence_24": dict(missing_you=0.15, mild_annoyance=0.10),
    "absence_72": dict(resentment=0.15, wounded_pride=0.10, longing=0.10),
    "diary_written": dict(quiet_pride=0.03, calm=0.02),
    "knowledge_added": dict(curiosity=0.04, interest=0.03),
    "app_started": dict(anticipation=0.04, interest=0.02),
    "app_closed": dict(calm=0.02, anticipation=-0.02),
    "user_absent": dict(longing=0.03, loneliness=0.02),
    "llm_error": dict(confusion=0.05, doubt=0.03),
    "task_completed": dict(satisfaction=0.06, pride=0.04),
    "task_failed": dict(frustration=0.07, determination=0.04),
    "web_found": dict(curiosity=0.03, surprise=0.04),
    "time_of_day": dict(calm=0.001, concentration=0.001),
    "weekday": dict(anticipation=0.01, interest=0.01),
    "safety_override": dict(alertness=0.06, calm=0.02),
}
TAXONOMY = {}
phrases = iter(PHRASES)
for cat, names in GROUPS.items():
    for name in names.split():
        base = {
            "joy": 0.45,
            "sadness": 0.18,
            "curiosity": 0.30,
            "calm": 0.32,
            "resentment": 0.12,
        }.get(name, 0.08)
        TAXONOMY[name] = Emotion(
            name,
            cat,
            base,
            {"social": 0.09, "basic": 0.15}.get(cat, 0.12),
            tuple(k for k, d in EMOTION_DELTAS.items() if d.get(name, 0) > 0),
            tuple(k for k, d in EMOTION_DELTAS.items() if d.get(name, 0) < 0),
            next(phrases),
        )
