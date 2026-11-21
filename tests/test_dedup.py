from scp_autonomy import ThoughtDeduplicator


def test_ten_thoughts(tmp_path):
    d = ThoughtDeduplicator(tmp_path)
    for i in range(10):
        text = f"Тема {i}: музыка звучит иначе {i}"
        assert not d.is_duplicate(text)
        d.remember(text)
        assert d.is_duplicate(text.upper() + "!")
    assert ThoughtDeduplicator(tmp_path).is_duplicate(text)
