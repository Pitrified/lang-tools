"""Classify the absent pt top-N wordfreq words (phase 1 of 14_number_modal_words)."""

from collections import Counter
import json
from pathlib import Path
import random
import sys

from wordfreq import top_n_list
from wordfreq import zipf_frequency

from lang_tools.lexicon.ingestion.closed_class import CLOSED_CLASS
from lang_tools.lexicon.lemma_store import get_store

OUT = sys.argv[1]
store = get_store()
lemmas = store.get_lemmas_by_language("pt")
pt = {lemma.text for lemma in lemmas}
verbs = {lemma.text for lemma in lemmas if lemma.part_of_speech == "verb"}
closed = CLOSED_CLASS["pt"]

# Irregular forms -> infinitive, for the verbs whose forms no ending rule reaches.
IRREGULAR = {
    "ser": "é são foi era eram será sou somos seja sejam fosse fossem sido sendo fui foram "
    "seria seriam serão serem és fomos éramos sejamos",
    "ir": "vai vou vamos vão ia iam irá irão indo vá vás",
    "ter": "tem têm tinha tinham teve tive tenho tenha tenham tivesse tivessem terá terão "
    "teria tiveram temos tendo tido tivemos tens",
    "estar": "está estão estava estavam estou esteve estive estamos esteja estivesse estado "
    "estando estiveram",
    "fazer": "faz fez fiz fazem faço feito feita fizeram faça fazendo fará faria fazia "
    "fizesse feitos feitas fazemos",
    "dizer": "diz disse dizem digo dito dizendo diga dizia disseram dirá diria",
    "poder": "pode podem posso pude pôde possa possam podia podiam poderia poderá poderão "
    "pudesse pudessem puder podemos podendo",
    "haver": "há houve havia haja haverá houver haviam",
    "ver": "vê viu vi vejo veja vendo visto vista vimos viram via verá vêem veem",
    "vir": "vem vêm veio vinha vindo venha vieram virá",
    "dar": "dá deu dei dão dava dado dada desse dê dando dera",
    "saber": "sabe sei sabia sabem soube saiba sabendo sabemos",
    "querer": "quer quero queria querem quis queira quiser quisesse queremos",
    "pôr": "põe pus pôs posto posta pondo",
    "trazer": "traz trouxe trazem",
    "ler": "lê leu li",
    "crer": "crê creio",
    "ouvir": "ouço ouvi ouviu",
    "pedir": "peço pede",
    "sair": "sai saiu saí saio",
    "cair": "cai caiu",
    "seguir": "sigo segue",
    "sentir": "sinto sente",
    "dever": "deve devem devia deviam deveria deveriam deverá devemos devo deves",
    "conseguir": "consigo consegue conseguem conseguiu",
}
IRR = {form: inf for inf, forms in IRREGULAR.items() for form in forms.split()}

VERB_ENDINGS = sorted(
    [
        "o",
        "as",
        "a",
        "amos",
        "ais",
        "am",
        "es",
        "e",
        "emos",
        "eis",
        "em",
        "imos",
        "is",
        "ei",
        "aste",
        "ou",
        "aram",
        "i",
        "este",
        "eu",
        "eram",
        "iste",
        "iu",
        "iram",
        "ámos",
        "ava",
        "avas",
        "ávamos",
        "avam",
        "ia",
        "ias",
        "íamos",
        "iam",
        "arei",
        "arás",
        "ará",
        "aremos",
        "arão",
        "erei",
        "erás",
        "erá",
        "eremos",
        "erão",
        "irei",
        "irás",
        "irá",
        "iremos",
        "irão",
        "aria",
        "arias",
        "aríamos",
        "ariam",
        "eria",
        "erias",
        "eríamos",
        "eriam",
        "iria",
        "irias",
        "iríamos",
        "iriam",
        "asse",
        "asses",
        "ássemos",
        "assem",
        "esse",
        "esses",
        "êssemos",
        "essem",
        "isse",
        "isses",
        "íssemos",
        "issem",
        "ar",
        "ares",
        "armos",
        "arem",
        "er",
        "eres",
        "ermos",
        "erem",
        "ir",
        "ires",
        "irmos",
        "irem",
        "ando",
        "endo",
        "indo",
        "ado",
        "ada",
        "ados",
        "adas",
        "ido",
        "ida",
        "idos",
        "idas",
    ],
    key=len,
    reverse=True,
)

NOMINAL = [
    ("ões", "ão"),
    ("ães", "ão"),
    ("ãos", "ão"),
    ("ais", "al"),
    ("éis", "el"),
    ("eis", "il"),
    ("óis", "ol"),
    ("is", "il"),
    ("ns", "m"),
    ("res", "r"),
    ("zes", "z"),
    ("ses", "s"),
    ("s", ""),
    ("as", "o"),
    ("a", "o"),
    ("ora", "or"),
    ("oras", "or"),
    ("esa", "ês"),
    ("esas", "ês"),
    ("ona", "ão"),
    ("onas", "ão"),
]


def base_of(word: str) -> tuple[str, str] | None:
    """Return (base, kind) when the word is a form of a lemma the corpus has."""
    if word in IRR:
        return IRR[word], "verb form (irregular table)"
    for end, repl in NOMINAL:
        if word.endswith(end) and len(word) > len(end) + 1:
            cand = word[: -len(end)] + repl
            if cand in pt and cand != word:
                return cand, "plural or feminine"
    for end in VERB_ENDINGS:
        if word.endswith(end) and len(word) > len(end) + 1:
            stem = word[: -len(end)]
            for inf in (stem + "ar", stem + "er", stem + "ir"):
                if inf in verbs and inf != word:
                    return inf, "verb form"
    return None


def classify(word: str) -> dict:
    """Return the word's row with its rule group (the rest is sorted by hand)."""
    row = {"word": word, "zipf": round(zipf_frequency(word, "pt"), 2)}
    if word in closed:
        row["group"] = "closed-class"
        return row
    found = base_of(word)
    if found:
        row["group"], row["base"], row["rule"] = "form of a lemma", found[0], found[1]
        return row
    if zipf_frequency(word, "en") > zipf_frequency(word, "pt"):
        row["group"] = "english"
        return row
    row["group"] = "unclassified"
    return row


rows = []
for n_from, n_to in ((0, 1000), (1000, 2000)):
    rows.extend(
        {**classify(w), "band": f"{n_from + 1}-{n_to}"}
        for w in top_n_list("pt", n_to)[n_from:]
        if w.isalpha() and w not in pt
    )
random.seed(14)
band3 = [w for w in top_n_list("pt", 5000)[2000:] if w.isalpha() and w not in pt]
rows.extend(
    {**classify(w), "band": "2001-5000 sample"} for w in random.sample(band3, 300)
)
with Path(OUT).open("w") as f:
    f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
print("band3 absent", len(band3))
for band in ("1-1000", "1001-2000", "2001-5000 sample"):
    print(band, Counter(r["group"] for r in rows if r["band"] == band).most_common())
