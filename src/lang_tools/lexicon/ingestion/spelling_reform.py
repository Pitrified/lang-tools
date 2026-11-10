"""Pre-reform pt spelling: respell a lemma as the 2009 orthography writes it.

The pt wordnet (OpenWN-PT) is Brazilian and predates the 2009 orthography
reform, so it writes *idéia*, *seqüência*, *jóia* and *vôo* where today's pt
writes *ideia*, *sequência*, *joia* and *voo*. Today's text, and so `wordfreq`,
mostly uses the new spelling: the old lemma ranks low or not at all, its card is
rare, and the frequent modern word looks absent from the corpus. A few lemmas
are plain misspellings (*juíz*, *raíz*).

The reform's changes are mechanical, so `respell_pt` applies them as rules
rather than as reviewed rows:

- the trema goes: it only ever sat on the *u* of *gue*, *gui*, *que*, *qui*
  (*freqüente* -> *frequente*); a foreign *ü* (*Dürer*, *Lübeck*) stays;
- the open diphthongs *éi* and *ói* lose the accent in a paroxytone that no
  other rule accents, that is when consonants and a final *a(s)*, *e(s)*,
  *o(s)*, *am* or *em* follow (*idéia*, *heróico*, *asteróide*); an oxytone
  (*papéis*, *lençóis*), a proparoxytone (*géiseres*) and a paroxytone in *-r*
  (*destróier*) keep it;
- *ôo* and *êem* lose the circumflex (*vôo*, *enjôo*, *lêem*);
- `PT_RESPELLINGS` holds the words no rule reaches: misspellings, the hiatus of
  *feiúra*, and the differential accents the reform removed (*pólo*, *pêra*).
  *pêlo* "hair" is left out on purpose: respelt it is *pelo*, the closed-class
  contraction "by the", whose senses the build drops.

Each rule reads its word alone, so a multi-word lemma is respelt word by word
(*União Européia* -> *União Europeia*). The build applies it while it folds
spelling noise, before lemma ids are minted, so a respelt lemma merges with the
modern lemma when the wordnet has both and nothing downstream sees the old
spelling. Frequency is not consulted: `wordfreq` still counts the old spelling
higher for many words (*paranóia*, *heróico*, *bóia*).
"""

from __future__ import annotations

import re

#: pt words no rule respells, mapped to today's spelling.
PT_RESPELLINGS: dict[str, str] = {
    "juíz": "juiz",
    "raíz": "raiz",
    "síliqüa": "síliqua",
    "feiúra": "feiura",
    "pólo": "polo",
    "pêra": "pera",
}

_TREMA = re.compile(r"([gqGQ])ü(?=[eiéíêEI])")
_OPEN_DIPHTHONG = re.compile(
    r"([éó])i(?=[^aeiouáéíóúâêôãõ\s-]*(?:[aeo]s?|am|em)\b)",
)
_UNACCENTED = {"é": "e", "ó": "o"}
_WORD = re.compile(r"[^\s-]+")


def _respell_word(word: str) -> str:
    """Return one word in today's spelling."""
    if word in PT_RESPELLINGS:
        return PT_RESPELLINGS[word]
    word = _TREMA.sub(r"\1u", word)
    word = _OPEN_DIPHTHONG.sub(lambda m: _UNACCENTED[m[1]] + "i", word)
    return word.replace("ôo", "oo").replace("êem", "eem")


def respell_pt(text: str) -> str:
    """Return a pt lemma text in post-2009 spelling, word by word.

    Args:
        text: A pt lemma text, one word or several.

    Returns:
        The text with every pre-reform word respelt; unchanged when none is.

    Example:
        ::

            respell_pt("União Européia")  # "União Europeia"
    """
    return _WORD.sub(lambda m: _respell_word(m[0]), text)
