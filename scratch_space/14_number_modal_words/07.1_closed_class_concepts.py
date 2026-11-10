"""Write the closed-class concepts and their links (phase 7).

Appends the curated concept rows to ``data/curated/concept_additions.jsonl``
(a row whose ``source_key`` is already there is skipped), and writes two label
files for ``02.1_apply_labels.py``:

- ``14_closed_class.labels.txt``: one ``add`` per (word, concept), the word's
  main meaning first, so a lemma the addition creates takes its part of speech
  from it; applied after a build that has the concepts;
- ``14_closed_class_pins.labels.txt``: a ``pin`` of the main meaning for every
  word with more than one link, since each ``add`` pins its own; applied after
  the next build.

Every word of the pt top 1,000 on the closed-class list must have a link.

Usage: ``07.1_closed_class_concepts.py [--write]``
"""

from pathlib import Path
import sys

from wordfreq import top_n_list

from lang_tools.lexicon.ingestion.closed_class import CLOSED_CLASS
from lang_tools.lexicon.ingestion.concept_additions import CONCEPT_ADDITIONS_FILE
from lang_tools.lexicon.ingestion.concept_additions import ConceptAddition
from lang_tools.lexicon.ingestion.concept_additions import load_concept_additions
from lang_tools.lexicon.ingestion.review_batches import append_rows
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.params.lang_tools_params import get_lang_tools_params

BATCH = "14_number_modal_words"
REASON = "closed-class word: WordNet has no concept for it"
WORK = Path("data/work/sense_review")

# slug: (lexfile, English definition, English members)
CONCEPTS: dict[str, tuple[str, str, list[str]]] = {
    # personal pronouns
    "pronoun-i": ("pron.personal", "the speaker or writer, as the subject", ["I"]),
    "pronoun-me": (
        "pron.personal",
        "the speaker or writer, as the object of a verb or after a preposition",
        ["me"],
    ),
    "pronoun-you": ("pron.personal", "the person or people spoken to", ["you"]),
    "pronoun-he": (
        "pron.personal",
        "a man, boy or male animal already mentioned; also a thing (it)",
        ["he", "him"],
    ),
    "pronoun-she": (
        "pron.personal",
        "a woman, girl or female animal already mentioned; also a thing (it)",
        ["she", "her"],
    ),
    "pronoun-we": (
        "pron.personal",
        "the speaker or writer together with others",
        ["we", "us"],
    ),
    "pronoun-they": (
        "pron.personal",
        "the people or things already mentioned",
        ["they", "them"],
    ),
    "pronoun-oneself": (
        "pron.reflexive",
        "the subject of the verb, as its own object",
        ["oneself", "himself", "herself", "itself", "themselves"],
    ),
    "pronoun-to-him-her": (
        "pron.personal",
        "to or for him, her or you: the person something is given, said or done to",
        ["to him", "to her", "to you"],
    ),
    # possessives
    "possessive-my": ("det.possessive", "belonging to the speaker", ["my", "mine"]),
    "possessive-your": (
        "det.possessive",
        "belonging to the person spoken to",
        ["your", "yours"],
    ),
    "possessive-his-her-their": (
        "det.possessive",
        "belonging to him, her, it or them, or to you (formal)",
        ["his", "her", "its", "their", "your"],
    ),
    "possessive-our": (
        "det.possessive",
        "belonging to the speaker and others",
        ["our", "ours"],
    ),
    # demonstratives
    "demonstrative-this": (
        "det.demonstrative",
        "the one here, near the speaker",
        ["this", "these"],
    ),
    "demonstrative-that": (
        "det.demonstrative",
        "the one there, near the person spoken to, or just mentioned",
        ["that", "those"],
    ),
    "demonstrative-that-yonder": (
        "det.demonstrative",
        "the one over there, away from both speaker and listener",
        ["that", "those"],
    ),
    # indefinites and quantifiers
    "indefinite-everything": (
        "pron.indefinite",
        "all things; the whole of something",
        ["everything", "all"],
    ),
    "indefinite-something": (
        "pron.indefinite",
        "a thing that is not named or not known",
        ["something"],
    ),
    "indefinite-nobody": ("pron.indefinite", "no person", ["nobody", "no one"]),
    "quantifier-each": (
        "det.quantifier",
        "every one of a group, taken one by one",
        ["each", "every"],
    ),
    "quantifier-any": (
        "det.quantifier",
        "one or some, no matter which",
        ["any", "whichever"],
    ),
    "quantifier-some": (
        "det.quantifier",
        "a certain one or a few, not named",
        ["some", "a certain"],
    ),
    "quantifier-both": ("det.quantifier", "the two together", ["both"]),
    "quantifier-such": ("det.quantifier", "of that kind; like that", ["such"]),
    # interrogatives and relatives
    "interrogative-who": (
        "pron.interrogative",
        "what person or people; the person that",
        ["who", "whom"],
    ),
    "interrogative-what": ("pron.interrogative", "what thing; which thing", ["what"]),
    "interrogative-which": (
        "pron.interrogative",
        "what one or ones out of a group",
        ["which", "what"],
    ),
    "interrogative-how-much": (
        "pron.interrogative",
        "what amount or number",
        ["how much", "how many"],
    ),
    "interrogative-where": (
        "adv.interrogative",
        "in or to what place; the place in which",
        ["where"],
    ),
    "interrogative-how": ("adv.interrogative", "in what way or manner", ["how"]),
    "adverb-even": (
        "adv.focus",
        "used to stress something surprising or extreme",
        ["even"],
    ),
    # articles
    "article-the": (
        "det.article",
        "the definite article: a particular one, already known",
        ["the"],
    ),
    "article-a": (
        "det.article",
        "the indefinite article: one, any one, not a particular one",
        ["a", "an"],
    ),
    # prepositions
    "preposition-of-from": (
        "prep",
        "belonging to, made of, or coming from",
        ["of", "from"],
    ),
    "preposition-in-on": (
        "prep",
        "inside, on top of, or at a place or a time",
        ["in", "on", "at"],
    ),
    "preposition-to-at": (
        "prep",
        "towards a place or a person, or at a point in time",
        ["to", "at"],
    ),
    "preposition-for": (
        "prep",
        "meant for, towards, or in order to",
        ["for", "to", "in order to"],
    ),
    "preposition-with": ("prep", "together with, or using", ["with"]),
    "preposition-by": (
        "prep",
        "the doer, the way or the cause; through a place",
        ["by", "through", "for", "per"],
    ),
    "preposition-about": (
        "prep",
        "concerning; or on top of, over",
        ["about", "on", "over"],
    ),
    "preposition-until": ("prep", "up to a time or a place", ["until", "up to"]),
    "preposition-without": ("prep", "not having; not with", ["without"]),
    "preposition-between": (
        "prep",
        "in the space or the group of",
        ["between", "among"],
    ),
    "preposition-under": ("prep", "beneath; lower than", ["under", "beneath"]),
    "preposition-after": ("prep", "later than; following", ["after"]),
    "preposition-since": ("prep", "starting at a time", ["since", "from"]),
    "preposition-against": (
        "prep",
        "in opposition to, or touching",
        ["against"],
    ),
    "preposition-during": (
        "prep",
        "throughout, or at a point in, a period",
        ["during"],
    ),
    "preposition-through": (
        "prep",
        "from one side to the other; by means of",
        ["through", "across"],
    ),
    "preposition-behind": ("prep", "at or to the back", ["behind", "back"]),
    "preposition-despite": ("prep", "without being stopped by", ["despite"]),
    # conjunctions
    "conjunction-and": ("conj", "joins words or clauses: also, in addition", ["and"]),
    "conjunction-but": ("conj", "introduces a contrast", ["but"]),
    "conjunction-or": ("conj", "introduces an alternative", ["or"]),
    "conjunction-because": ("conj", "for the reason that", ["because", "since"]),
    "conjunction-if": ("conj", "on condition that; whether", ["if", "whether"]),
    "conjunction-nor": ("conj", "and not; not even", ["nor", "not even"]),
    "conjunction-when": ("conj", "at what time; at the time that", ["when"]),
    "conjunction-while": ("conj", "during the time that; whereas", ["while"]),
    "conjunction-although": (
        "conj",
        "despite the fact that",
        ["although", "even though"],
    ),
    "conjunction-however": (
        "conj",
        "but still; nevertheless",
        ["however", "nevertheless"],
    ),
    "conjunction-that": (
        "conj",
        "introduces a clause: I know that it is late",
        ["that"],
    ),
    "conjunction-than": (
        "conj",
        "introduces the second part of a comparison",
        ["than"],
    ),
    "conjunction-as-like": ("conj", "in the way that; in the role of", ["as", "like"]),
}

# word: [(concept slug or a WordNet concept key, form note)], the main meaning first
LINKS: dict[str, list[tuple[str, str]]] = {
    # articles and their contractions
    "o": [
        ("article-the", ""),
        ("pronoun-he", 'object form of "ele": him, it'),
    ],
    "a": [
        ("article-the", 'feminine of "o": the'),
        ("preposition-to-at", ""),
        ("pronoun-she", 'object form of "ela": her, it'),
    ],
    "os": [
        ("article-the", 'masculine plural of "o": the'),
        ("pronoun-they", 'object form of "eles": them'),
    ],
    "as": [
        ("article-the", 'feminine plural of "o": the'),
        ("pronoun-they", 'object form of "elas": them'),
    ],
    "um": [("article-a", "")],
    "uma": [("article-a", 'feminine of "um": a, an')],
    "uns": [("quantifier-some", 'masculine plural of "um": some')],
    "umas": [("quantifier-some", 'feminine plural of "um": some')],
    "do": [("preposition-of-from", 'contraction of "de" + "o": of the')],
    "da": [("preposition-of-from", 'contraction of "de" + "a": of the')],
    "dos": [("preposition-of-from", 'contraction of "de" + "os": of the')],
    "das": [("preposition-of-from", 'contraction of "de" + "as": of the')],
    "no": [("preposition-in-on", 'contraction of "em" + "o": in the, on the')],
    "na": [("preposition-in-on", 'contraction of "em" + "a": in the, on the')],
    "nos": [
        ("preposition-in-on", 'contraction of "em" + "os": in the, on the'),
        ("pronoun-we", 'object form of "nós": us'),
    ],
    "nas": [("preposition-in-on", 'contraction of "em" + "as": in the, on the')],
    "num": [("preposition-in-on", 'contraction of "em" + "um": in a, on a')],
    "numa": [("preposition-in-on", 'contraction of "em" + "uma": in a, on a')],
    "ao": [("preposition-to-at", 'contraction of "a" + "o": to the')],
    "à": [("preposition-to-at", 'contraction of "a" + "a": to the')],
    "aos": [("preposition-to-at", 'contraction of "a" + "os": to the')],
    "às": [("preposition-to-at", 'contraction of "a" + "as": to the')],
    "pelo": [("preposition-by", 'contraction of "por" + "o": by the, through the')],
    "pela": [("preposition-by", 'contraction of "por" + "a": by the, through the')],
    "pelos": [("preposition-by", 'contraction of "por" + "os": by the, through the')],
    "pelas": [("preposition-by", 'contraction of "por" + "as": by the, through the')],
    # prepositions
    "de": [("preposition-of-from", "")],
    "em": [("preposition-in-on", "")],
    "para": [("preposition-for", "")],
    "pra": [("preposition-for", 'spoken short form of "para": for, to')],
    "com": [("preposition-with", "")],
    "por": [("preposition-by", "")],
    "sobre": [("preposition-about", "")],
    "até": [("preposition-until", ""), ("adverb-even", "")],
    "sem": [("preposition-without", "")],
    "entre": [("preposition-between", "")],
    "sob": [("preposition-under", "")],
    "após": [("preposition-after", "")],
    "desde": [("preposition-since", "")],
    "contra": [("preposition-against", "")],
    "durante": [("preposition-during", "")],
    "através": [("preposition-through", 'in "através de": through, across')],
    "trás": [("preposition-behind", 'in "para trás": back; "por trás de": behind')],
    "apesar": [("preposition-despite", 'in "apesar de": despite')],
    # conjunctions
    "e": [("conjunction-and", "")],
    "mas": [("conjunction-but", "")],
    "ou": [("conjunction-or", "")],
    "porque": [("conjunction-because", "")],
    "pois": [("conjunction-because", "")],
    "se": [
        ("conjunction-if", ""),
        ("pronoun-oneself", "reflexive pronoun: himself, herself, itself, themselves"),
    ],
    "nem": [("conjunction-nor", "")],
    "quando": [("conjunction-when", "")],
    "enquanto": [("conjunction-while", "")],
    "embora": [("conjunction-although", "")],
    "porém": [("conjunction-however", "")],
    "entanto": [("conjunction-however", 'in "no entanto": however')],
    "que": [
        ("conjunction-that", ""),
        ("interrogative-what", ""),
        ("conjunction-than", ""),
    ],
    "como": [("interrogative-how", ""), ("conjunction-as-like", "")],
    # personal pronouns
    "eu": [("pronoun-i", "")],
    "me": [("pronoun-me", "")],
    "mim": [("pronoun-me", 'form of "eu" after a preposition: me')],
    "comigo": [("pronoun-me", '"com" + "mim": with me')],
    "você": [("pronoun-you", "")],
    "vocês": [("pronoun-you", 'plural of "você": you')],
    "tu": [("pronoun-you", 'informal "you", mostly in Portugal and southern Brazil')],
    "te": [("pronoun-you", 'object form of "tu": you')],
    "ti": [("pronoun-you", 'form of "tu" after a preposition: you')],
    "ele": [("pronoun-he", "")],
    "ela": [("pronoun-she", "")],
    "nós": [("pronoun-we", "")],
    "eles": [("pronoun-they", "")],
    "elas": [("pronoun-they", 'feminine of "eles": they')],
    "lhe": [("pronoun-to-him-her", "")],
    "si": [("pronoun-oneself", 'form of "se" after a preposition: himself, herself')],
    "consigo": [
        # conjugated "conseguir": attain success or reach a desired goal
        ("a8353a975f63", '1st person singular present of "conseguir": I manage, I can'),
        ("pronoun-oneself", '"com" + "si": with himself, with herself, with you'),
    ],
    # possessives
    "meu": [("possessive-my", "")],
    "minha": [("possessive-my", 'feminine of "meu": my')],
    "meus": [("possessive-my", 'masculine plural of "meu": my')],
    "minhas": [("possessive-my", 'feminine plural of "meu": my')],
    "teu": [("possessive-your", "")],
    "tua": [("possessive-your", 'feminine of "teu": your')],
    "seu": [("possessive-his-her-their", "")],
    "sua": [("possessive-his-her-their", 'feminine of "seu"')],
    "seus": [("possessive-his-her-their", 'masculine plural of "seu"')],
    "suas": [("possessive-his-her-their", 'feminine plural of "seu"')],
    "nosso": [("possessive-our", "")],
    "nossa": [("possessive-our", 'feminine of "nosso": our')],
    "nossos": [("possessive-our", 'masculine plural of "nosso": our')],
    "nossas": [("possessive-our", 'feminine plural of "nosso": our')],
    "dele": [("possessive-his-her-their", 'contraction of "de" + "ele": his')],
    "dela": [("possessive-his-her-their", 'contraction of "de" + "ela": her, hers')],
    "deles": [("possessive-his-her-their", 'contraction of "de" + "eles": their')],
    # demonstratives
    "este": [("demonstrative-this", "")],
    "esta": [("demonstrative-this", 'feminine of "este": this')],
    "estes": [("demonstrative-this", 'masculine plural of "este": these')],
    "estas": [("demonstrative-this", 'feminine plural of "este": these')],
    "isto": [("demonstrative-this", 'neuter form of "este": this, this thing')],
    "neste": [("demonstrative-this", 'contraction of "em" + "este": in this')],
    "nesta": [("demonstrative-this", 'contraction of "em" + "esta": in this')],
    "deste": [("demonstrative-this", 'contraction of "de" + "este": of this')],
    "desta": [("demonstrative-this", 'contraction of "de" + "esta": of this')],
    "esse": [("demonstrative-that", "")],
    "essa": [("demonstrative-that", 'feminine of "esse": that')],
    "esses": [("demonstrative-that", 'masculine plural of "esse": those')],
    "essas": [("demonstrative-that", 'feminine plural of "esse": those')],
    "isso": [("demonstrative-that", 'neuter form of "esse": that, that thing')],
    "nesse": [("demonstrative-that", 'contraction of "em" + "esse": in that')],
    "nessa": [("demonstrative-that", 'contraction of "em" + "essa": in that')],
    "desse": [("demonstrative-that", 'contraction of "de" + "esse": of that')],
    "dessa": [("demonstrative-that", 'contraction of "de" + "essa": of that')],
    "desses": [("demonstrative-that", 'contraction of "de" + "esses": of those')],
    "dessas": [("demonstrative-that", 'contraction of "de" + "essas": of those')],
    "disso": [("demonstrative-that", 'contraction of "de" + "isso": of that')],
    "aquele": [("demonstrative-that-yonder", "")],
    "aquela": [("demonstrative-that-yonder", 'feminine of "aquele": that')],
    "aqueles": [("demonstrative-that-yonder", 'masculine plural of "aquele": those')],
    "aquilo": [("demonstrative-that-yonder", 'neuter form of "aquele": that thing')],
    # indefinites, quantifiers, interrogatives
    "tudo": [("indefinite-everything", "")],
    "algo": [("indefinite-something", "")],
    "ninguém": [("indefinite-nobody", "")],
    "cada": [("quantifier-each", "")],
    "qualquer": [("quantifier-any", "")],
    "algum": [("quantifier-some", "")],
    "ambos": [("quantifier-both", "")],
    "tais": [("quantifier-such", 'plural of "tal": such')],
    "quem": [("interrogative-who", "")],
    "qual": [("interrogative-which", "")],
    "quais": [("interrogative-which", 'plural of "qual": which')],
    "quanto": [("interrogative-how-much", "")],
    "onde": [("interrogative-where", "")],
}


def concept_rows() -> list[ConceptAddition]:
    """Return one accepted row per concept."""
    return [
        ConceptAddition(
            source_key=f"manual:{slug}",
            slug=slug,
            lexfile=lexfile,
            definition=definition,
            members=members,
            reason=REASON,
            status="accepted",
            model="manual",
            batch=BATCH,
        )
        for slug, (lexfile, definition, members) in CONCEPTS.items()
    ]


def main() -> None:
    """Check the inventory, then write the rows and labels with ``--write``."""
    keys = {row.slug: row.concept_key for row in concept_rows()}
    top = set(top_n_list("pt", 1000))
    unlinked = sorted(w for w in CLOSED_CLASS["pt"] & top if w not in LINKS)
    unused = sorted(set(CONCEPTS) - {s for links in LINKS.values() for s, _ in links})
    print(
        len(CONCEPTS), "concepts;", len(LINKS), "words;", sum(map(len, LINKS.values()))
    )
    print("closed-class top 1,000 words with no link:", unlinked)
    print("concepts no word links:", unused)
    if unlinked or unused or "--write" not in sys.argv:
        return

    data_fol = get_lang_tools_params().paths.data_fol
    have = {row.source_key for row in load_concept_additions(data_fol)}
    new = [row for row in concept_rows() if row.source_key not in have]
    append_rows(curated_path(data_fol, CONCEPT_ADDITIONS_FILE), new)
    adds, pins = [], []
    for word, links in LINKS.items():
        for slug, note in links:
            adds.append(f"add\t{word}\t{keys.get(slug, slug)}\t{note}\t{REASON}")
        if len(links) > 1:
            pins.append(f"pin\t{word}\t{keys.get(links[0][0], links[0][0])}")
    (WORK / "14_closed_class.labels.txt").write_text("\n".join(adds) + "\n")
    (WORK / "14_closed_class_pins.labels.txt").write_text("\n".join(pins) + "\n")
    print(len(new), "concept rows appended;", len(adds), "adds;", len(pins), "pins")


main()
