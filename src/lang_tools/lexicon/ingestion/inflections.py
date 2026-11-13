"""Inflected forms: give a frequent pt form its base word's meaning, by rule.

The sources list base words only, so a frequent form such as pt *anos*, *foi* or
*boa* has no lemma unless a reviewed `sense_additions` row creates it. This
module generates the forms instead, from rules of our own (no third-party
morphology table, so the corpus licence stays as it is):

- `inflect` gives the forms of a base word in one class: a noun's plural; an
  adjective's feminine and plurals; a verb's finite forms, personal infinitive,
  gerund and past participles, from the regular -ar, -er and -ir paradigms with
  their spelling changes (*ficar*, *fiquei*; *conhecer*, *conheço*), the stem
  changes of some -ir verbs (*sentir*, *sinto*), and `IRREGULAR_VERBS`, a table
  of the irregular verbs and their compounds;
- `pick_readings` chooses one base for a form that several bases generate
  (*partes*: the plural of *parte*, not "you leave" of *partir*);
- `form_note` writes the label a card shows (``3rd person singular preterite of
  "ser"``);
- `apply_inflections` is the build stage: a frequent form the build lacks gets a
  lemma whose senses are its base's senses of the form's class, each with the
  note, so its card is its base's card; `propagate_base_pins` then gives it its
  base's pinned sense. A word the build already has, as a noun or adjective
  form of a class it has no sense of (*nova*, otherwise only the star), gets
  that class's base senses; its verb forms are left out, since a common word
  that spells a verb form (*casa*, *fala*) would gain a sense it rarely has. A
  word with a reviewed row is left alone, so a `sense_additions` row always wins
  over the rules.

Generating from the base, rather than guessing the base of a form, keeps a wrong
guess to a form that is mostly not a word at all, and `analyse` keeps only the
forms `wordfreq` knows well. Imperatives, diminutives (*cantinho*), superlatives
and clitic forms (*fazê-lo*) are not generated.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from loguru import logger as lg

from lang_tools.lexicon.ingestion.closed_class import CLOSED_CLASS
from lang_tools.lexicon.ingestion.sense_additions import LEXFILE_POS
from lang_tools.lexicon.ingestion.transform import SOURCE_INFLECTION
from lang_tools.lexicon.ingestion.transform import SOURCE_MANUAL
from lang_tools.lexicon.lemma import Lemma
from lang_tools.lexicon.sense import Sense

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterable
    from collections.abc import Mapping

    from lang_tools.lexicon.ingestion.transform import TaggedTables


def _words(text: str) -> frozenset[str]:
    """Return the whitespace-separated words of a table string."""
    return frozenset(text.split())


#: The (person, number) slots of a finite tense, in paradigm order.
PERSONS: tuple[tuple[int, str], ...] = (
    (1, "singular"),
    (2, "singular"),
    (3, "singular"),
    (1, "plural"),
    (2, "plural"),
    (3, "plural"),
)

#: Tense and mood labels, in the order a form note lists them.
TENSES: dict[str, str] = {
    "present": "present",
    "preterite": "preterite",
    "imperfect": "imperfect",
    "pluperfect": "pluperfect",
    "future": "future",
    "conditional": "conditional",
    "present_subjunctive": "present subjunctive",
    "imperfect_subjunctive": "imperfect subjunctive",
    "future_subjunctive": "future subjunctive",
    "personal_infinitive": "personal infinitive",
}

#: Tenses whose readings lose to any other reading of the same form, as a
#: second-person reading does (`Reading.is_weak`: *formas* "you form" against the
#: plural of *forma*): the simple pluperfect is mostly written, and spelled like
#: a commoner form (*vira*).
WEAK_TENSES = frozenset({"pluperfect"})

_REGULAR: dict[str, dict[str, str]] = {
    "ar": {
        "present": "o as a amos ais am",
        "preterite": "ei aste ou amos astes aram",
        "imperfect": "ava avas ava ávamos áveis avam",
        "subjunctive": "e es e emos eis em",
    },
    "er": {
        "present": "o es e emos eis em",
        "preterite": "i este eu emos estes eram",
        "imperfect": "ia ias ia íamos íeis iam",
        "subjunctive": "a as a amos ais am",
    },
    "ir": {
        "present": "o es e imos is em",
        "preterite": "i iste iu imos istes iram",
        "imperfect": "ia ias ia íamos íeis iam",
        "subjunctive": "a as a amos ais am",
    },
}

#: Endings of the -uir and -air verbs, whose stem ends in a vowel, so the *i* of
#: the ending is written with an accent where it is stressed (*incluí*, *saía*).
_HIATUS: dict[str, str] = {
    "present": "o is i ímos ís em",
    "preterite": "í íste iu ímos ístes íram",
    "imperfect": "ía ías ía íamos íeis íam",
    "future_subjunctive": "ir íres ir irmos irdes írem",
}

_FUTURE = "ei ás á emos eis ão"
_CONDITIONAL = "ia ias ia íamos íeis iam"
_INFINITIVE = ("", "es", "", "mos", "des", "em")

#: -ir verbs whose last stem *e* is *i* in the 1st person singular present and
#: the whole present subjunctive (*sentir*: *sinto*, *sinta*).
_E_TO_I = _words("""
    sentir consentir ressentir pressentir mentir desmentir seguir conseguir
    perseguir prosseguir vestir investir revestir servir preferir referir
    transferir conferir inferir interferir sugerir digerir ferir repetir competir
    divertir advertir inserir aderir refletir despir convergir divergir
    """)
#: -ir verbs whose last stem *o* is *u* in the same forms (*dormir*: *durmo*).
_O_TO_U = _words("dormir cobrir descobrir encobrir recobrir tossir engolir")
#: -ir verbs whose last stem *u* is *o* in the 2nd and 3rd persons singular and
#: the 3rd plural present (*subir*: *sobe*).
_U_TO_O = _words("subir fugir sacudir consumir cuspir acudir sumir")
#: -ir verbs whose last stem *e* is *i* in every stressed-stem form
#: (*agredir*: *agrido*, *agride*).
_E_TO_I_STRESSED = _words("agredir progredir regredir transgredir prevenir denegrir")
#: Verbs whose stressed stem vowel is written with an accent, as a hiatus
#: (*reunir*: *reúne*), in the stressed forms of the present.
_STRESSED_STEMS = {
    "reunir": "reún",
    "proibir": "proíb",
    "coibir": "coíb",
    "saudar": "saúd",
}
#: -iar verbs conjugated like the -ear ones (*odiar*: *odeio*).
_IAR_LIKE_EAR = _words("mediar intermediar remediar ansiar incendiar odiar")

#: Irregular past participles; a verb listed with two keeps both (*ganhar*:
#: *ganho* and *ganhado*).
_PARTICIPLES: dict[str, tuple[str, ...]] = {
    "fazer": ("feito",),
    "dizer": ("dito",),
    "ver": ("visto",),
    "vir": ("vindo",),
    "pôr": ("posto",),
    "escrever": ("escrito",),
    "abrir": ("aberto",),
    "cobrir": ("coberto",),
    "descobrir": ("descoberto",),
    "morrer": ("morto", "morrido"),
    "ganhar": ("ganho", "ganhado"),
    "gastar": ("gasto", "gastado"),
    "pagar": ("pago", "pagado"),
    "aceitar": ("aceito", "aceitado"),
    "eleger": ("eleito", "elegido"),
    "entregar": ("entregue", "entregado"),
    "prender": ("preso", "prendido"),
    "imprimir": ("impresso", "imprimido"),
    "acender": ("aceso", "acendido"),
    "expulsar": ("expulso", "expulsado"),
    "limpar": ("limpo", "limpado"),
    "salvar": ("salvo", "salvado"),
    "soltar": ("solto", "soltado"),
    "suspender": ("suspenso", "suspendido"),
    "extinguir": ("extinto", "extinguido"),
    "envolver": ("envolto", "envolvido"),
    "reabrir": ("reaberto",),
    "reeleger": ("reeleito", "reelegido"),
    "descrever": ("descrito",),
    "inscrever": ("inscrito",),
    "prescrever": ("prescrito",),
    "subscrever": ("subscrito",),
    "transcrever": ("transcrito",),
    "reescrever": ("reescrito",),
}


@dataclass(frozen=True)
class IrregularVerb:
    """The tenses of an irregular verb that the regular engine gets wrong.

    Each tense is six forms in `PERSONS` order, space-separated; a tense left
    empty is generated by the regular engine. The pluperfect and the imperfect
    and future subjunctives are always built on the preterite (``fize-``ram ->
    *fizera*, *fizesse*, *fizer*), so they need no entry.

    Attributes:
        present: Present indicative.
        preterite: Preterite.
        imperfect: Imperfect indicative.
        subjunctive: Present subjunctive, when it does not follow from the 1st
            person singular present (*sou* -> *seja*).
        future_stem: Stem of the future and the conditional (*far-*).
        strong: The preterite stem's vowel takes an acute in the 1st and 2nd
            persons plural (*fizéramos*), not the circumflex of the regular -er
            verbs (*comêramos*); ``ô`` for *ser* and *ir* (*fôramos*).
    """

    present: str = ""
    preterite: str = ""
    imperfect: str = ""
    subjunctive: str = ""
    future_stem: str = ""
    strong: str = ""


#: The irregular verbs, by infinitive. Compounds are in `_COMPOUNDS`.
IRREGULAR_VERBS: dict[str, IrregularVerb] = {
    "ser": IrregularVerb(
        present="sou és é somos sois são",
        preterite="fui foste foi fomos fostes foram",
        imperfect="era eras era éramos éreis eram",
        subjunctive="seja sejas seja sejamos sejais sejam",
        strong="ô",
    ),
    "ir": IrregularVerb(
        present="vou vais vai vamos ides vão",
        preterite="fui foste foi fomos fostes foram",
        subjunctive="vá vás vá vamos vades vão",
        strong="ô",
    ),
    "estar": IrregularVerb(
        present="estou estás está estamos estais estão",
        preterite="estive estiveste esteve estivemos estivestes estiveram",
        subjunctive="esteja estejas esteja estejamos estejais estejam",
        strong="é",
    ),
    "ter": IrregularVerb(
        present="tenho tens tem temos tendes têm",
        preterite="tive tiveste teve tivemos tivestes tiveram",
        imperfect="tinha tinhas tinha tínhamos tínheis tinham",
        strong="é",
    ),
    "haver": IrregularVerb(
        present="hei hás há havemos haveis hão",
        preterite="houve houveste houve houvemos houvestes houveram",
        subjunctive="haja hajas haja hajamos hajais hajam",
        strong="é",
    ),
    "vir": IrregularVerb(
        present="venho vens vem vimos vindes vêm",
        preterite="vim vieste veio viemos viestes vieram",
        imperfect="vinha vinhas vinha vínhamos vínheis vinham",
        strong="é",
    ),
    "fazer": IrregularVerb(
        present="faço fazes faz fazemos fazeis fazem",
        preterite="fiz fizeste fez fizemos fizestes fizeram",
        future_stem="far",
        strong="é",
    ),
    "dizer": IrregularVerb(
        present="digo dizes diz dizemos dizeis dizem",
        preterite="disse disseste disse dissemos dissestes disseram",
        future_stem="dir",
        strong="é",
    ),
    "trazer": IrregularVerb(
        present="trago trazes traz trazemos trazeis trazem",
        preterite="trouxe trouxeste trouxe trouxemos trouxestes trouxeram",
        future_stem="trar",
        strong="é",
    ),
    "poder": IrregularVerb(
        present="posso podes pode podemos podeis podem",
        preterite="pude pudeste pôde pudemos pudestes puderam",
        strong="é",
    ),
    "querer": IrregularVerb(
        present="quero queres quer queremos quereis querem",
        preterite="quis quiseste quis quisemos quisestes quiseram",
        subjunctive="queira queiras queira queiramos queirais queiram",
        strong="é",
    ),
    "requerer": IrregularVerb(
        present="requeiro requeres requer requeremos requereis requerem"
    ),
    "saber": IrregularVerb(
        present="sei sabes sabe sabemos sabeis sabem",
        preterite="soube soubeste soube soubemos soubestes souberam",
        subjunctive="saiba saibas saiba saibamos saibais saibam",
        strong="é",
    ),
    "caber": IrregularVerb(
        present="caibo cabes cabe cabemos cabeis cabem",
        preterite="coube coubeste coube coubemos coubestes couberam",
        strong="é",
    ),
    "ver": IrregularVerb(
        present="vejo vês vê vemos vedes veem",
        preterite="vi viste viu vimos vistes viram",
    ),
    "ler": IrregularVerb(present="leio lês lê lemos ledes leem"),
    "crer": IrregularVerb(present="creio crês crê cremos credes creem"),
    "dar": IrregularVerb(
        present="dou dás dá damos dais dão",
        preterite="dei deste deu demos destes deram",
        subjunctive="dê dês dê demos deis deem",
        strong="é",
    ),
    "pôr": IrregularVerb(
        present="ponho pões põe pomos pondes põem",
        preterite="pus puseste pôs pusemos pusestes puseram",
        imperfect="punha punhas punha púnhamos púnheis punham",
        future_stem="por",
        strong="é",
    ),
    "rir": IrregularVerb(present="rio ris ri rimos rides riem"),
    "ouvir": IrregularVerb(present="ouço ouves ouve ouvimos ouvis ouvem"),
    "pedir": IrregularVerb(present="peço pedes pede pedimos pedis pedem"),
    "medir": IrregularVerb(present="meço medes mede medimos medis medem"),
    "perder": IrregularVerb(present="perco perdes perde perdemos perdeis perdem"),
    "valer": IrregularVerb(present="valho vales vale valemos valeis valem"),
    "doer": IrregularVerb(
        present="doo dóis dói doemos doeis doem",
        preterite="doí doeste doeu doemos doestes doeram",
        imperfect="doía doías doía doíamos doíeis doíam",
    ),
    "construir": IrregularVerb(
        present="construo constróis constrói construímos construís constroem"
    ),
    "destruir": IrregularVerb(
        present="destruo destróis destrói destruímos destruís destroem"
    ),
}

#: Prefixed compounds of an irregular verb, conjugated as that verb.
_COMPOUNDS: dict[str, str] = {
    "ter": "manter conter obter deter reter entreter ater abster suster",
    "vir": "convir intervir provir advir sobrevir",
    "pôr": """compor propor supor dispor expor impor opor repor depor transpor
        pressupor decompor recompor contrapor justapor sobrepor""",
    "fazer": "desfazer satisfazer refazer perfazer",
    "dizer": "contradizer predizer bendizer maldizer",
    "ver": "prever rever antever",
    "ler": "reler",
    "crer": "descrer",
    "rir": "sorrir",
    "pedir": "despedir impedir expedir",
    "valer": "equivaler",
}

#: Monosyllables of *ter* and *vir* that take an accent in a compound
#: (*tem* -> *mantém*).
_COMPOUND_ACCENTS = {"tem": "tém", "tens": "téns", "vem": "vém", "vens": "véns"}

_STRIP = str.maketrans("áâãàéêíóôõú", "aaaaeeiooou")


@dataclass(frozen=True)
class Reading:
    """One analysis of a form: which form of which base word it is.

    Attributes:
        base: The base word (the infinitive, the masculine singular).
        part_of_speech: ``noun``, ``adjective`` or ``verb``: the class of the
            base senses the form shares.
        kind: The tense key of `TENSES`, or ``plural``, ``feminine``,
            ``participle``, ``gerund``.
        person: 1, 2 or 3 for a finite form or a personal infinitive.
        number: ``singular`` or ``plural`` where the form has one.
        feminine: True for a feminine adjective or participle.
    """

    base: str
    part_of_speech: str
    kind: str
    person: int | None = None
    number: str | None = None
    feminine: bool = False

    @property
    def is_weak(self) -> bool:
        """True for a second-person or pluperfect reading (`WEAK_TENSES`)."""
        return self.person == 2 or self.kind in WEAK_TENSES  # noqa: PLR2004 - the second person


def _attach(stem: str, ending: str, conjugation: str) -> str:
    """Join a verb stem and an ending, with the spelling changes of the stem.

    A stem keeps its sound before the ending's vowel: -ar *fic-* + *-ei* ->
    *fiquei*, *cheg-* -> *cheguei*, *começ-* -> *comecei*; -er and -ir *conhec-*
    + *-o* -> *conheço*, *proteg-* -> *protejo*, *ergu-* -> *ergo*.
    """
    if not ending:
        return stem
    first = ending[0]
    if conjugation == "ar" and first in "eéê":
        for old, new in (("c", "qu"), ("g", "gu"), ("ç", "c")):
            if stem.endswith(old):
                return stem[: -len(old)] + new + ending
    if conjugation in {"er", "ir"} and first in "aoáó":
        for old, new in (("gu", "g"), ("c", "ç"), ("g", "j")):
            if stem.endswith(old):
                return stem[: -len(old)] + new + ending
    return stem + ending


def _replace_last(stem: str, old: str, new: str) -> str:
    """Replace the last ``old`` vowel of a stem (*sent-* -> *sint-*)."""
    at = stem.rfind(old)
    return stem if at < 0 else stem[:at] + new + stem[at + 1 :]


def _accent_last_vowel(root: str, strong: str) -> str:
    """Accent the last vowel of a preterite root (*fala-* -> *falá-ramos*).

    The regular -er root takes a circumflex (*comê-ramos*), a strong preterite an
    acute (*fizé-ramos*), *ser* and *ir* a circumflex on the *o* (*fô-ramos*). A
    root already accented (*incluí-*) is returned as it is.
    """
    last = root[-1]
    accents = {"a": "á", "i": "í", "e": "é" if strong else "ê", "o": strong or "ô"}
    return root[:-1] + accents[last] if last in accents else root


def _conjugation(infinitive: str) -> str | None:
    """Return ``ar``, ``er`` or ``ir`` (``er`` for *pôr*), or None for no verb."""
    if infinitive == "pôr":
        return "er"
    ending = infinitive[-2:]
    if ending not in _REGULAR:
        return None
    return ending if len(infinitive) > len(ending) or infinitive == "ir" else None


def _is_hiatus(infinitive: str) -> bool:
    """Return whether the verb is -uir or -air (*incluir*, *sair*), not -guir."""
    return infinitive.endswith(("uir", "air")) and not infinitive.endswith(
        ("guir", "quir")
    )


def _compound_of(infinitive: str) -> tuple[str, str] | None:
    """Return ``(prefix, verb)`` when the infinitive is a listed compound."""
    for verb, compounds in _COMPOUNDS.items():
        if infinitive in compounds.split():
            return infinitive[: -len(verb.translate(_STRIP))], verb
    return None


def _six(forms: str) -> list[str]:
    """Return the six forms of a space-separated tense."""
    return forms.split()


def _is_ear_like(infinitive: str) -> bool:
    """Return whether the verb is -ear or an -iar verb like one (*odiar*)."""
    return infinitive.endswith("ear") or infinitive in _IAR_LIKE_EAR


def _regular_present(stem: str, infinitive: str, conjugation: str) -> list[str]:
    """Return the present indicative of a regular verb, stem changes included."""
    if _is_hiatus(infinitive):
        forms = [stem + ending for ending in _six(_HIATUS["present"])]
        if infinitive.endswith("air"):
            forms[0] = stem + "io"
        return forms
    stems = [stem] * 6
    stressed = (0, 1, 2, 5)
    if _is_ear_like(infinitive):
        changed = stem + "i" if infinitive.endswith("ear") else stem[:-1] + "ei"
        stems = [changed if i in stressed else stem for i in range(6)]
    elif infinitive in _STRESSED_STEMS:
        changed = _STRESSED_STEMS[infinitive]
        stems = [changed if i in stressed else stem for i in range(6)]
    elif infinitive in _E_TO_I_STRESSED:
        changed = _replace_last(stem, "e", "i")
        stems = [changed if i in stressed else stem for i in range(6)]
    elif infinitive in _E_TO_I:
        stems[0] = _replace_last(stem, "e", "i")
    elif infinitive in _O_TO_U:
        stems[0] = _replace_last(stem, "o", "u")
    elif infinitive in _U_TO_O:
        changed = _replace_last(stem, "u", "o")
        stems = [changed if i in (1, 2, 5) else stem for i in range(6)]
    endings = _six(_REGULAR[conjugation]["present"])
    forms = [
        _attach(s, ending, conjugation)
        for s, ending in zip(stems, endings, strict=True)
    ]
    if infinitive.endswith("uzir") or infinitive in {"jazer", "aprazer"}:
        forms[2] = stem  # the 3rd singular drops its *e*: *produz*, *jaz*
    return forms


def _present_subjunctive(
    stem: str, first_singular: str, infinitive: str, conjugation: str
) -> list[str]:
    """Return the present subjunctive, built on the 1st person singular present."""
    # The root keeps the spelling of the 1st person singular (*sig-o*, *sig-a*),
    # except that -ar *fic-o* writes *fiqu-e* before the subjunctive's *e*.
    root = first_singular.removesuffix("o")
    endings = _six(_REGULAR[conjugation]["subjunctive"])
    if conjugation == "ar":
        forms = [_attach(root, ending, conjugation) for ending in endings]
    else:
        forms = [root + ending for ending in endings]
    if _is_ear_like(infinitive) or infinitive in _STRESSED_STEMS:
        # The 1st and 2nd plural are not stressed on the stem: *passeemos*.
        forms[3] = _attach(stem, endings[3], conjugation)
        forms[4] = _attach(stem, endings[4], conjugation)
    return forms


def _personal_infinitive(infinitive: str) -> list[str]:
    """Return the personal infinitive (*fazer*, *fazeres*, ... *fazerem*)."""
    plain = infinitive.translate(_STRIP)
    if _is_hiatus(infinitive):
        return [plain[:-2] + e for e in _six(_HIATUS["future_subjunctive"])]
    forms = [plain + ending for ending in _INFINITIVE]
    forms[0] = forms[2] = infinitive
    return forms


def verb_tenses(infinitive: str) -> dict[str, list[str]]:
    """Return the finite tenses and the personal infinitive of a verb.

    Args:
        infinitive: The verb (*falar*, *fazer*, *pôr*, *manter*).

    Returns:
        `TENSES` key -> the six forms in `PERSONS` order; empty when the word is
        not an infinitive.
    """
    compound = _compound_of(infinitive)
    if compound is not None:
        prefix, verb = compound
        tenses = {
            tense: [prefix + _COMPOUND_ACCENTS.get(form, form) for form in forms]
            for tense, forms in verb_tenses(verb).items()
        }
        tenses["personal_infinitive"] = _personal_infinitive(infinitive)
        return tenses
    conjugation = _conjugation(infinitive)
    if conjugation is None:
        return {}
    plain = infinitive.translate(_STRIP)
    stem = plain[:-2]
    irregular = IRREGULAR_VERBS.get(infinitive, IrregularVerb())
    regular = _REGULAR[conjugation]
    hiatus = _is_hiatus(infinitive)
    present = _six(irregular.present) or _regular_present(stem, plain, conjugation)
    if irregular.preterite:
        preterite = _six(irregular.preterite)
    elif hiatus:
        preterite = [stem + ending for ending in _six(_HIATUS["preterite"])]
    else:
        preterite = [
            _attach(stem, ending, conjugation) for ending in _six(regular["preterite"])
        ]
    imperfect = _six(irregular.imperfect) or [
        stem + ending
        for ending in _six(_HIATUS["imperfect"] if hiatus else regular["imperfect"])
    ]
    future = irregular.future_stem or plain
    # The pluperfect and the imperfect and future subjunctives share the root of
    # the 3rd person plural preterite: *fize-ram*, *fize-ra*, *fize-sse*, *fize-r*.
    root = preterite[5].removesuffix("ram")
    stressed = _accent_last_vowel(root, irregular.strong)
    tenses = {
        "present": present,
        "preterite": preterite,
        "imperfect": imperfect,
        "pluperfect": [
            *(root + ending for ending in ("ra", "ras", "ra")),
            *(stressed + ending for ending in ("ramos", "reis")),
            root + "ram",
        ],
        "future": [future + ending for ending in _six(_FUTURE)],
        "conditional": [future + ending for ending in _six(_CONDITIONAL)],
        "present_subjunctive": _six(irregular.subjunctive)
        or _present_subjunctive(stem, present[0], plain, conjugation),
        "imperfect_subjunctive": [
            *(root + ending for ending in ("sse", "sses", "sse")),
            *(stressed + ending for ending in ("ssemos", "sseis")),
            root + "ssem",
        ],
        "future_subjunctive": (
            [stem + ending for ending in _six(_HIATUS["future_subjunctive"])]
            if hiatus
            else [root + "r" + ending for ending in _INFINITIVE]
        ),
        "personal_infinitive": _personal_infinitive(infinitive),
    }
    return tenses


def participles(infinitive: str) -> tuple[str, ...]:
    """Return the masculine singular past participles of a verb (*feito*)."""
    compound = _compound_of(infinitive)
    if compound is not None:
        prefix, verb = compound
        return tuple(prefix + form for form in participles(verb))
    if infinitive in _PARTICIPLES:
        return _PARTICIPLES[infinitive]
    conjugation = _conjugation(infinitive)
    if conjugation is None:
        return ()
    stem = infinitive.translate(_STRIP)[:-2]
    if _is_hiatus(infinitive):
        return (stem + "ído",)
    return (stem + ("ado" if conjugation == "ar" else "ido"),)


#: -ão words with the -ães plural, and those with -ãos; the rest take -ões.
_AO_AES = _words(
    "pão cão alemão capitão charlatão escrivão sacristão tabelião catalão capelão"
)
_AO_AOS = _words(
    """
    mão irmão cidadão cristão órgão órfão bênção grão chão vão são cortesão
    pagão sótão acórdão desvão afegão
    """
)
_PLURALS = {"mal": "males", "cônsul": "cônsules"}
_ACCENTS = "áéíóúâêôãõ"


def plural(word: str) -> str | None:
    """Return the plural of a noun or of a masculine adjective.

    Args:
        word: The singular.

    Returns:
        The plural, or None for a word written the same in the plural (*lápis*,
        *ônibus*, *tórax*).
    """
    if word in _PLURALS:
        return _PLURALS[word]
    if word.endswith("ão"):
        if word in _AO_AES:
            return word[:-2] + "ães"
        return word + "s" if word in _AO_AOS else word[:-2] + "ões"
    by_last = {
        "m": lambda w: w[:-1] + "ns",
        "s": _plural_of_s,
        "l": _plural_of_l,
        "z": _plural_of_z,
        "r": lambda w: w + "es",
    }
    last = word[-1]
    if last in by_last:
        return by_last[last](word)
    return None if last == "x" else word + "s"


def _plural_of_z(word: str) -> str:
    """Return the plural of a word in -z, with the hiatus of *raiz*, *raízes*."""
    if word.endswith(("aiz", "uiz")):
        return word[:-2] + "ízes"
    return word + "es"


def _plural_of_s(word: str) -> str | None:
    """Return the plural of a word in -s: stressed on the last syllable only."""
    for old, new in (("ês", "eses"), ("ás", "ases"), ("ós", "oses"), ("ís", "íses")):
        if word.endswith(old):
            return word[: -len(old)] + new
    if any(c in _ACCENTS for c in word):
        return None  # stressed before the last syllable: *lápis*, *ônibus*
    vowels = "aeiou"
    syllables = sum(
        1
        for i, c in enumerate(word)
        if c in vowels and (i == 0 or word[i - 1] not in vowels)
    )
    return word + "es" if syllables == 1 else None


def _plural_of_l(word: str) -> str:
    """Return the plural of a word in -l (*animal*, *papel*, *fácil*, *sol*)."""
    unstressed = any(c in _ACCENTS for c in word[:-2])
    endings = {
        "al": "ais",
        "el": "eis" if unstressed else "éis",
        "il": "eis" if unstressed else "is",
        "ol": "ois" if unstressed else "óis",
        "ul": "uis",
    }
    ending = endings.get(word[-2:])
    return word[:-2] + ending if ending else word + "es"


_FEMININES = {
    "bom": "boa",
    "mau": "má",
    "judeu": "judia",
    "réu": "ré",
    "são": "sã",
    "vão": "vã",
    "nu": "nua",
    "cru": "crua",
}
#: Adjectives in -or with one form for both genders.
_INVARIANT_OR = _words(
    """
    melhor pior maior menor superior inferior anterior posterior exterior
    interior ulterior
    """
)


def feminine(word: str) -> str | None:
    """Return the feminine singular of an adjective, or None when invariant.

    Args:
        word: The masculine singular (*novo*, *português*, *trabalhador*).

    Returns:
        The feminine, or None for an adjective with one form (*grande*, *feliz*).
    """
    if word in _FEMININES:
        return _FEMININES[word]
    rules = (("ão", "ã"), ("o", "a"), ("ês", "esa"), ("eu", "eia"))
    for old, new in rules:
        if word.endswith(old):
            return word[: -len(old)] + new
    if word.endswith("or") and word not in _INVARIANT_OR:
        return word + "a"
    return None


def _nominal_forms(base: str, part_of_speech: str) -> list[tuple[str, Reading]]:
    """Return the gender and number forms of a noun or an adjective.

    A noun has a plural; an adjective, and a noun naming a person (``person``,
    *professor*, *biólogo*), also a feminine. Any other noun in -o is left
    alone, since its -a twin is mostly another word (*olho*, *olha*).
    """
    out: list[tuple[str, Reading]] = []
    if part_of_speech != "person":
        many = plural(base)
        if many is not None:
            reading = Reading(base, part_of_speech, "plural", number="plural")
            out.append((many, reading))
    if part_of_speech == "noun":
        return out
    female = feminine(base)
    part_of_speech = "noun" if part_of_speech == "person" else part_of_speech
    if female is not None:
        for form, number in ((female, "singular"), (female + "s", "plural")):
            reading = Reading(
                base, part_of_speech, "feminine", number=number, feminine=True
            )
            out.append((form, reading))
    return out


def _verb_forms(base: str) -> list[tuple[str, Reading]]:
    """Return every form of a verb with its reading."""
    tenses = verb_tenses(base)
    if not tenses:
        return []
    out = [
        (form, Reading(base, "verb", tense, person, number))
        for tense, forms in tenses.items()
        for form, (person, number) in zip(forms, PERSONS, strict=True)
    ]
    first_plural = tenses["preterite"][3]
    if base.endswith("ar") and first_plural.endswith("amos"):
        # pt-PT writes the 1st plural preterite with an accent: *falámos*.
        pt_pt = first_plural.removesuffix("amos") + "ámos"
        out.append((pt_pt, Reading(base, "verb", "preterite", 1, "plural")))
    gerund = base.translate(_STRIP)[:-1] + "ndo"
    out.append((gerund, Reading(base, "verb", "gerund")))
    for participle in participles(base):
        female = participle[:-1] + "a" if participle.endswith("o") else None
        for form, number, is_female in (
            (participle, "singular", False),
            (plural(participle), "plural", False),
            (female, "singular", True),
            (female and female + "s", "plural", True),
        ):
            if form:
                reading = Reading(
                    base, "verb", "participle", number=number, feminine=is_female
                )
                out.append((form, reading))
    return out


def inflect(base: str, part_of_speech: str) -> list[tuple[str, Reading]]:
    """Return the inflected forms of a base word in one class, with their readings.

    Args:
        base: The base word: a noun or adjective in the (masculine) singular, a
            verb in the infinitive.
        part_of_speech: ``noun``, ``adjective`` or ``verb``, or ``person`` for
            the feminine of a noun naming a person (*bióloga*); any other class
            has no forms.

    Returns:
        ``(form, reading)`` pairs; a form can appear more than once (*falamos*
        is the present and the preterite), and the base itself can be one of
        them (*fazer* is a personal infinitive).
    """
    if part_of_speech == "verb":
        return _verb_forms(base)
    if part_of_speech in {"noun", "adjective", "person"}:
        return _nominal_forms(base, part_of_speech)
    return []


def pick_readings(
    readings: Iterable[Reading], zipf: Callable[[str], float]
) -> list[Reading]:
    """Return the readings of the one base a form is given.

    In order: a base that is a gender form of another adjective base gives way
    to it (*novas* is of *novo*, not of *nova*); a verb gives way to its own
    participle used as a word (*estados* is of *estado*, not of *estar*;
    *comidas* of *comida*, not of *comer*); weak
    readings give way to any other (`Reading.is_weak`: *partes* is of *parte*,
    not "you leave" of *partir*); then the most frequent base wins (*foi* is of
    *ser*, not of *ir*), ties to the first in alphabetical order.

    Args:
        readings: Every reading of one form.
        zipf: The ``wordfreq`` zipf of a base word.

    Returns:
        The readings of the chosen base, in their input order.
    """
    readings = list(dict.fromkeys(readings))
    adjectives = {r.base for r in readings if r.part_of_speech == "adjective"}
    verbs = {r.base for r in readings if r.part_of_speech == "verb"}
    nominal = {r.base for r in readings if r.part_of_speech != "verb"}
    drop = {
        base
        for base in adjectives
        for adjective in adjectives
        if base != adjective and base == feminine(adjective)
    }
    for verb in verbs:
        words = set(participles(verb))
        words |= {word[:-1] + "a" for word in words if word.endswith("o")}
        if nominal & words:
            drop.add(verb)
    readings = [r for r in readings if r.base not in drop] or readings
    readings = [r for r in readings if not r.is_weak] or readings
    best = max(sorted({r.base for r in readings}), key=zipf)
    return [r for r in readings if r.base == best]


_ORDINALS = {1: "1st", 2: "2nd", 3: "3rd"}


def _persons(readings: Iterable[Reading]) -> str:
    """Return the person phrase of the readings of one tense."""
    by_number: dict[str, set[int]] = {}
    for reading in readings:
        if reading.number is not None and reading.person is not None:
            by_number.setdefault(reading.number, set()).add(reading.person)
    phrases = [
        " and ".join(_ORDINALS[p] for p in sorted(by_number[number]))
        + f" person {number}"
        for number in ("singular", "plural")
        if number in by_number
    ]
    return " and ".join(phrases)


def _nominal_label(reading: Reading) -> str:
    """Return the label of a non-finite or nominal reading."""
    if reading.kind == "gerund":
        return "gerund"
    words = ["feminine"] if reading.feminine else []
    if reading.number == "plural":
        words.append("plural")
    if reading.kind == "participle":
        words.append("past participle")
    return " ".join(words) or "form"


def form_note(readings: Iterable[Reading]) -> str:
    """Return the form note of a form's readings of one base.

    Tenses that share a person phrase are joined (``1st person plural present
    or preterite of "falar"``); other labels follow, joined by ``or``.

    Args:
        readings: The readings of one base, typically from `pick_readings`.

    Returns:
        The note, ``<label> of "<base>"``.
    """
    readings = list(readings)
    by_tense: dict[str, list[Reading]] = {}
    labels: list[str] = []
    for reading in readings:
        if reading.kind in TENSES:
            by_tense.setdefault(reading.kind, []).append(reading)
        else:
            labels.append(_nominal_label(reading))
    by_phrase: dict[str, list[str]] = {}
    for tense, name in TENSES.items():
        if tense in by_tense:
            by_phrase.setdefault(_persons(by_tense[tense]), []).append(name)
    finite = [f"{phrase} {' or '.join(tenses)}" for phrase, tenses in by_phrase.items()]
    label = " or ".join(dict.fromkeys(finite + labels))
    return f'{label} of "{readings[0].base}"'


def analyse(
    bases: Mapping[str, Iterable[str]],
    *,
    known: Iterable[str],
    zipf: Callable[[str], float],
    floor: float,
) -> dict[str, list[Reading]]:
    """Return the frequent forms the corpus lacks, each with its picked readings.

    Args:
        bases: Base word -> the classes of its senses (``noun``, ``adjective``,
            ``verb``, ``person`` for a noun naming a person; others are
            ignored).
        known: Words that are left out as forms: the language's lemmas and its
            closed-class words.
        zipf: The ``wordfreq`` zipf of a word.
        floor: The lowest zipf a form needs.

    Returns:
        Form -> the readings of its one base (`pick_readings`).
    """
    known = set(known)
    candidates: dict[str, list[Reading]] = {}
    for base, classes in bases.items():
        if len(base) < 2:  # noqa: PLR2004 - a one-letter lemma is a letter name
            continue
        for part_of_speech in classes:
            for form, reading in inflect(base, part_of_speech):
                if form in known or not (form.isalpha() and form.islower()):
                    continue
                candidates.setdefault(form, []).append(reading)
    return {
        form: pick_readings(readings, zipf)
        for form, readings in candidates.items()
        if len(form) > 1 and zipf(form) >= floor
    }


#: The language the rules cover.
INFLECTION_LANGUAGE = "pt"

#: The lowest ``wordfreq`` zipf a generated form needs for a lemma: about once
#: per million words.
INFLECTION_ZIPF_FLOOR = 3.0

#: Lexfile of the senses a person-noun feminine shares (*bióloga*).
_PERSON_LEXFILE = "noun.person"


@dataclass(frozen=True)
class InflectionCounts:
    """What `apply_inflections` did.

    Attributes:
        forms: Lemmas created.
        extended: Existing words that took base senses they lacked.
        senses: Senses created, on both.
        links: Each created or extended form's lemma id -> its base's lemma id,
            for `propagate_base_pins`.
    """

    forms: int
    extended: int
    senses: int
    links: dict[str, str]


def _sense_classes(lexfile: str) -> set[str]:
    """Return the `inflect` classes a sense of this lexfile supports."""
    pos = LEXFILE_POS.get(lexfile.split(".", maxsplit=1)[0])
    if pos is None:
        return set()
    return {pos, "person"} if lexfile == _PERSON_LEXFILE else {pos}


def _shares(reading: Reading, lexfile: str) -> bool:
    """Return whether a base sense of this lexfile is a sense of the reading."""
    if reading.part_of_speech == "noun" and reading.kind == "feminine":
        return lexfile == _PERSON_LEXFILE  # *bióloga* is a person, not a field
    return LEXFILE_POS.get(lexfile.split(".", maxsplit=1)[0]) == reading.part_of_speech


def _add_form_lemma(
    tables: TaggedTables,
    form: str,
    shared: list[Sense],
    lexfiles: Mapping[str, str],
) -> str:
    """Add a generated form's lemma, its class the commonest of its senses'."""
    classes = Counter(LEXFILE_POS[lexfiles[s.concept_id].split(".")[0]] for s in shared)
    lemma = Lemma(
        text=form,
        language=INFLECTION_LANGUAGE,
        part_of_speech=classes.most_common(1)[0][0],
        sources=[SOURCE_INFLECTION],
    )
    tables.lemmas.append(lemma)
    tables.lemma_sources.append(SOURCE_INFLECTION)
    return lemma.id


def apply_inflections(
    tables: TaggedTables,
    *,
    zipf: Callable[[str], float],
    floor: float = INFLECTION_ZIPF_FLOOR,
) -> InflectionCounts:
    """Give each frequent form its base's senses: a new lemma, or the ones it lacks.

    Runs after the sense additions, so every reviewed form is a lemma already
    and is left alone, and before enrichment, so the new senses get their
    frequency and band like any other. A sense that is itself a form note
    (a reviewed form's) is never a base sense.

    A form the build already has (*nova*, which own-pt lists only as the star)
    takes the base senses of a noun or adjective reading whose class it has no
    sense of: *nova* gains "feminine of *novo*", while *irmã* and *leis*, nouns
    already, are left alone. A verb reading of an existing word, and a word with
    a reviewed sense (a manual source or a form note), are left alone too.

    Args:
        tables: The transformed tables, edited in place.
        zipf: The ``wordfreq`` zipf of a pt word.
        floor: The lowest zipf a form needs (`INFLECTION_ZIPF_FLOOR`).

    Returns:
        The counts, and the form -> base links.
    """
    language = INFLECTION_LANGUAGE
    lexfiles = {concept.id: concept.lexfile or "" for concept in tables.concepts}
    texts = {
        lemma.id: lemma.text for lemma in tables.lemmas if lemma.language == language
    }
    base_senses: dict[str, list[Sense]] = {}
    for sense in tables.senses:
        text = texts.get(sense.lemma_id)
        if text is not None and sense.form_note is None:
            base_senses.setdefault(text, []).append(sense)
    bases = {
        text: set().union(*(_sense_classes(lexfiles[s.concept_id]) for s in senses))
        for text, senses in base_senses.items()
        if text.isalpha() and text.islower()
    }
    reviewed = {
        texts[sense.lemma_id]
        for sense, source in zip(tables.senses, tables.sense_sources, strict=True)
        if sense.lemma_id in texts
        and (source == SOURCE_MANUAL or sense.form_note is not None)
    }
    existing = {text: lemma_id_ for lemma_id_, text in texts.items()}
    has = {
        (sense.lemma_id, sense.concept_id)
        for sense in tables.senses
        if sense.lemma_id in texts
    }
    classes_of: dict[str | None, set[str]] = {}
    for sense in tables.senses:
        if sense.lemma_id in texts:
            pos = LEXFILE_POS.get(lexfiles[sense.concept_id].split(".", maxsplit=1)[0])
            classes_of.setdefault(sense.lemma_id, set()).add(pos or "")
    known = reviewed | CLOSED_CLASS[language]
    found = analyse(bases, known=known, zipf=zipf, floor=floor)
    links: dict[str, str] = {}
    added = 0
    extended = 0
    for form, readings in sorted(found.items()):
        base = readings[0].base
        form_id = existing.get(form)
        picked = (
            readings
            if form_id is None
            else [
                r
                for r in readings
                if r.part_of_speech != "verb"
                and r.part_of_speech not in classes_of.get(form_id, set())
            ]
        )
        shared = [
            sense
            for sense in base_senses[base]
            if any(_shares(r, lexfiles[sense.concept_id]) for r in picked)
            and (form_id, sense.concept_id) not in has
        ]
        if not shared or form == base:
            continue
        if form_id is None:
            form_id = _add_form_lemma(tables, form, shared, lexfiles)
        else:
            extended += 1
        note = form_note(picked)
        for sense in shared:
            tables.senses.append(
                Sense(lemma_id=form_id, concept_id=sense.concept_id, form_note=note)
            )
            tables.sense_sources.append(SOURCE_INFLECTION)
        added += len(shared)
        links[form_id] = shared[0].lemma_id
    lg.info(
        "Inflections: {} new form(s), {} existing word(s) extended, {} sense(s)",
        len(links) - extended,
        extended,
        added,
    )
    return InflectionCounts(
        forms=len(links) - extended, extended=extended, senses=added, links=links
    )


def propagate_base_pins(senses: Iterable[Sense], links: Mapping[str, str]) -> int:
    """Pin each generated form's sense on its base's pinned concept, in place.

    Runs after `best_senses.apply_best_senses`: a base whose card a review
    pinned (pt *rede* "network") gives its forms the same card (*redes*).

    Args:
        senses: Every sense of the build.
        links: Form lemma id -> base lemma id (`InflectionCounts.links`).

    Returns:
        The number of form senses pinned.
    """
    senses = list(senses)
    bases = set(links.values())
    pinned = {
        s.lemma_id: s.concept_id for s in senses if s.is_best and s.lemma_id in bases
    }
    own_pin = {s.lemma_id for s in senses if s.is_best and s.lemma_id in links}
    count = 0
    for sense in senses:
        base = links.get(sense.lemma_id)
        if sense.lemma_id in own_pin:
            continue  # a form with its own reviewed pin keeps it
        if base is not None and pinned.get(base) == sense.concept_id:
            sense.is_best = True
            count += 1
    lg.info("Inflections: {} form pin(s) from their base", count)
    return count
