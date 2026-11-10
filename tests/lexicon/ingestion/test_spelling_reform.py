"""Tests for the pre-reform pt respelling (`ingestion.spelling_reform`)."""

import pytest

from lang_tools.lexicon.ingestion.spelling_reform import respell_pt


@pytest.mark.parametrize(
    ("old", "new"),
    [
        # the trema on gue / gui / que / qui
        ("freqüência", "frequência"),
        ("agüentar", "aguentar"),
        ("lingüiça", "linguiça"),
        ("qüestão", "questão"),
        # the open diphthong of a paroxytone no other rule accents
        ("idéia", "ideia"),
        ("jóia", "joia"),
        ("heróico", "heroico"),
        ("asteróides", "asteroides"),
        # ôo and êem
        ("vôo", "voo"),
        ("lêem", "leem"),
        # the table
        ("juíz", "juiz"),
        ("feiúra", "feiura"),
        ("pólo", "polo"),
        # word by word
        ("União Européia", "União Europeia"),
        ("Lontra-européia", "Lontra-europeia"),
        ("cinturão de asteróides", "cinturão de asteroides"),
    ],
)
def test_a_pre_reform_spelling_is_respelt(old: str, new: str) -> None:
    assert respell_pt(old) == new


@pytest.mark.parametrize(
    "text",
    [
        # oxytones keep the accent, alone or inside a phrase
        "papéis",
        "herói",
        "lençóis freáticos",
        "Dia dos Fiéis Defuntos",
        # a proparoxytone, and a paroxytone in -r
        "géiseres",
        "destróier",
        # a foreign ü
        "Albrecht Dürer",
        "Lübeck",
        # pêlo would become the closed-class pelo
        "pêlo",
        # already modern
        "ideia",
        "têm",
    ],
)
def test_a_modern_or_protected_spelling_is_kept(text: str) -> None:
    assert respell_pt(text) == text
