"""Tests for the pt inflection rules (`ingestion.inflections`)."""

import pytest

from lang_tools.lexicon.ingestion.inflections import Reading
from lang_tools.lexicon.ingestion.inflections import analyse
from lang_tools.lexicon.ingestion.inflections import feminine
from lang_tools.lexicon.ingestion.inflections import form_note
from lang_tools.lexicon.ingestion.inflections import inflect
from lang_tools.lexicon.ingestion.inflections import participles
from lang_tools.lexicon.ingestion.inflections import pick_readings
from lang_tools.lexicon.ingestion.inflections import plural
from lang_tools.lexicon.ingestion.inflections import verb_tenses


@pytest.mark.parametrize(
    ("verb", "tense", "forms"),
    [
        ("falar", "present", "falo falas fala falamos falais falam"),
        ("comer", "preterite", "comi comeste comeu comemos comestes comeram"),
        ("partir", "imperfect", "partia partias partia partíamos partíeis partiam"),
        # spelling changes before the ending's vowel
        ("ficar", "preterite", "fiquei ficaste ficou ficamos ficastes ficaram"),
        (
            "começar",
            "present_subjunctive",
            "comece comeces comece comecemos comeceis comecem",
        ),
        (
            "conhecer",
            "present",
            "conheço conheces conhece conhecemos conheceis conhecem",
        ),
        (
            "dirigir",
            "present_subjunctive",
            "dirija dirijas dirija dirijamos dirijais dirijam",
        ),
        ("seguir", "present_subjunctive", "siga sigas siga sigamos sigais sigam"),
        # stem changes
        ("sentir", "present", "sinto sentes sente sentimos sentis sentem"),
        ("dormir", "present", "durmo dormes dorme dormimos dormis dormem"),
        ("subir", "present", "subo sobes sobe subimos subis sobem"),
        (
            "passear",
            "present_subjunctive",
            "passeie passeies passeie passeemos passeeis passeiem",
        ),
        ("odiar", "present", "odeio odeias odeia odiamos odiais odeiam"),
        ("reunir", "present", "reúno reúnes reúne reunimos reunis reúnem"),
        ("produzir", "present", "produzo produzes produz produzimos produzis produzem"),
        # a vowel stem
        (
            "incluir",
            "preterite",
            "incluí incluíste incluiu incluímos incluístes incluíram",
        ),
        ("sair", "present", "saio sais sai saímos saís saem"),
        # irregular verbs and their compounds
        ("ser", "imperfect_subjunctive", "fosse fosses fosse fôssemos fôsseis fossem"),
        ("ter", "pluperfect", "tivera tiveras tivera tivéramos tivéreis tiveram"),
        ("fazer", "future", "farei farás fará faremos fareis farão"),
        ("dar", "present_subjunctive", "dê dês dê demos deis deem"),
        ("ver", "future_subjunctive", "vir vires vir virmos virdes virem"),
        ("manter", "present", "mantenho manténs mantém mantemos mantendes mantêm"),
        (
            "compor",
            "preterite",
            "compus compuseste compôs compusemos compusestes compuseram",
        ),
        ("pôr", "personal_infinitive", "pôr pores pôr pormos pordes porem"),
    ],
)
def test_a_tense_is_conjugated(verb: str, tense: str, forms: str) -> None:
    assert verb_tenses(verb)[tense] == forms.split()


def test_a_word_that_is_not_an_infinitive_has_no_tenses() -> None:
    assert verb_tenses("casa") == {}


@pytest.mark.parametrize(
    ("verb", "expected"),
    [
        ("falar", ("falado",)),
        ("incluir", ("incluído",)),
        ("fazer", ("feito",)),
        ("ganhar", ("ganho", "ganhado")),
        ("propor", ("proposto",)),
        ("inscrever", ("inscrito",)),
    ],
)
def test_participles(verb: str, expected: tuple[str, ...]) -> None:
    assert participles(verb) == expected


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("ano", "anos"),
        ("homem", "homens"),
        ("mulher", "mulheres"),
        ("luz", "luzes"),
        ("raiz", "raízes"),
        ("mês", "meses"),
        ("país", "países"),
        ("deus", "deuses"),
        ("lápis", None),
        ("animal", "animais"),
        ("papel", "papéis"),
        ("nível", "níveis"),
        ("fácil", "fáceis"),
        ("barril", "barris"),
        ("sol", "sóis"),
        ("azul", "azuis"),
        ("nação", "nações"),
        ("pão", "pães"),
        ("mão", "mãos"),
        ("mal", "males"),
    ],
)
def test_plural(word: str, expected: str | None) -> None:
    assert plural(word) == expected


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("novo", "nova"),
        ("alemão", "alemã"),
        ("português", "portuguesa"),
        ("europeu", "europeia"),
        ("trabalhador", "trabalhadora"),
        ("bom", "boa"),
        ("melhor", None),
        ("grande", None),
    ],
)
def test_feminine(word: str, expected: str | None) -> None:
    assert feminine(word) == expected


def test_a_noun_has_a_plural_only_unless_it_names_a_person() -> None:
    assert [form for form, _ in inflect("olho", "noun")] == ["olhos"]
    assert [form for form, _ in inflect("biólogo", "person")] == ["bióloga", "biólogas"]


def _zipf(word: str) -> float:
    return {
        "ser": 6.0,
        "ir": 5.5,
        "parte": 5.0,
        "partir": 4.6,
        "novo": 5.0,
        "nova": 5.2,
    }.get(word, 3.0)


def _readings(form: str, bases: dict[str, set[str]]) -> list[Reading]:
    return [
        reading
        for base, classes in bases.items()
        for pos in classes
        for generated, reading in inflect(base, pos)
        if generated == form
    ]


def test_the_most_frequent_base_wins() -> None:
    picked = pick_readings(_readings("foi", {"ser": {"verb"}, "ir": {"verb"}}), _zipf)
    assert {r.base for r in picked} == {"ser"}


def test_a_weak_reading_loses() -> None:
    picked = pick_readings(
        _readings("partes", {"parte": {"noun"}, "partir": {"verb"}}), _zipf
    )
    assert {r.base for r in picked} == {"parte"}


def test_a_feminine_base_gives_way_to_its_masculine() -> None:
    bases = {"novo": {"adjective"}, "nova": {"adjective"}}
    assert {r.base for r in pick_readings(_readings("novas", bases), _zipf)} == {"novo"}


def test_a_verb_gives_way_to_its_participle_used_as_a_word() -> None:
    bases = {"estado": {"noun"}, "estar": {"verb"}}
    assert {r.base for r in pick_readings(_readings("estados", bases), _zipf)} == {
        "estado"
    }
    bases = {"comida": {"noun"}, "comer": {"verb"}}
    assert {r.base for r in pick_readings(_readings("comidas", bases), _zipf)} == {
        "comida"
    }


@pytest.mark.parametrize(
    ("form", "base", "note"),
    [
        ("foi", "ser", '3rd person singular preterite of "ser"'),
        ("falamos", "falar", '1st person plural present or preterite of "falar"'),
        (
            "falasse",
            "falar",
            '1st and 3rd person singular imperfect subjunctive of "falar"',
        ),
        ("falaram", "falar", '3rd person plural preterite of "falar"'),
        ("falara", "falar", '1st and 3rd person singular pluperfect of "falar"'),
        ("feitas", "fazer", 'feminine plural past participle of "fazer"'),
        ("sendo", "ser", 'gerund of "ser"'),
    ],
)
def test_form_note(form: str, base: str, note: str) -> None:
    readings = pick_readings(_readings(form, {base: {"verb"}}), _zipf)
    assert form_note(readings) == note


def test_a_nominal_note() -> None:
    assert form_note(_readings("anos", {"ano": {"noun"}})) == 'plural of "ano"'
    assert (
        form_note(_readings("boas", {"bom": {"adjective"}}))
        == 'feminine plural of "bom"'
    )


def test_analyse_keeps_frequent_forms_the_corpus_lacks() -> None:
    zipf = {"anos": 5.0, "anes": 0.0, "casas": 4.0}.get
    found = analyse(
        {"ano": {"noun"}, "casa": {"noun"}, "x": {"noun"}},
        known={"casas"},
        zipf=lambda word: zipf(word, 0.0),
        floor=3.0,
    )
    assert set(found) == {"anos"}
    assert found["anos"][0].base == "ano"


def test_the_pt_pt_first_plural_preterite_is_a_form_too() -> None:
    forms = {form for form, _ in inflect("falar", "verb")}
    assert {"falamos", "falámos"} <= forms
    assert not any(form.endswith("ámos") for form, _ in inflect("dar", "verb"))
