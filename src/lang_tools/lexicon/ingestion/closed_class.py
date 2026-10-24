"""Closed-class words: drop the senses WordNet cannot give them (phase 11).

WordNet covers nouns, verbs, adjectives and adverbs only, so a preposition,
article, conjunction, pronoun or contraction has no concept of its own. The
non-English wordnets still attach some of them to content concepts, mostly as
fragments of a longer phrase: pt *com* is "with success", *para* is "toward the
east", *como* is "as an example", fr *pour* is a Laotian coin. A drill card then
teaches the wrong meaning of the most frequent words of the language.

The rule is deterministic, so it lives here rather than in the reviewed
``member_form_drops.jsonl``: every sense of a lemma whose text is on its
language's closed-class list is dropped, and the lemma with it when no sense is
left (`apply_form_drops`). A word that is also a common content word keeps its
senses and is left off the list (es *bajo* "low", fr *son* "sound", *ton*,
*or*, *vers*, it *verso*, *sopra*, *sotto*, pt *caso*). English is exempt:
Princeton WordNet's senses for *a*, *in* or *can* are real homographs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lang_tools.lexicon.concept_id import concept_key
from lang_tools.lexicon.ingestion.form_review import FormDrop

if TYPE_CHECKING:
    from lang_tools.lexicon.ingestion.transform import TaggedTables

#: The `FormDrop.model` tag of a rule-made drop.
CLOSED_CLASS_MODEL = "closed-class-rule"

_LISTS = {
    "pt": """
        a o as os uma uns umas de do da dos das em no na nos nas num numa nuns numas
        ao à aos às pelo pela pelos pelas por para pra pro com sem sob sobre entre até
        desde contra perante após ante trás dum duma deste desta destes destas neste
        nesta nestes nestas desse dessa desses dessas nesse nessa nesses nessas daquele
        daquela naquele naquela dele dela deles delas nele nela neles nelas
        e ou mas nem que se porque pois porém contudo todavia embora quando como
        enquanto
        eu tu ele ela nós vós eles elas você vocês me te lhe vos lhes mim ti si comigo
        contigo consigo conosco convosco meu minha meus minhas teu tua teus tuas seu sua
        seus suas nosso nossa nossos nossas vosso vossa vossos vossas
        este esta estes estas esse essa esses essas aquele aquela aqueles aquelas isto
        isso aquilo qual quais quem cujo cuja cujos cujas onde durante cada
    """,
    "es": """
        el la los las lo un una unos unas de del a al en por para con sin sobre entre
        hasta desde contra hacia según tras ante durante mediante
        y e o u ni pero sino que si porque aunque como cuando mientras pues
        yo tú él ella nosotros nosotras vosotros vosotras ellos ellas usted ustedes me
        te se nos os le les mí ti sí conmigo contigo consigo
        mi mis tu tus su sus nuestro nuestra nuestros nuestras vuestro vuestra vuestros
        vuestras este esta estos estas ese esa esos esas aquel aquella aquellos aquellas
        esto eso aquello qué quién quiénes cuál cuáles cuyo cuya cuyos cuyas donde dónde
        cada
    """,
    "fr": """
        le la les l une des du de d au aux à en dans par pour avec sans sous sur entre
        chez contre depuis pendant avant après malgré selon parmi envers
        et ou mais ni donc car que qu si comme quand lorsque puisque
        je j tu il elle on nous vous ils elles me m te t se s lui leur leurs toi soi eux
        y mon ma mes ta tes sa ses notre nos votre vos
        ce c cet cette ces ceci cela ça celui celle ceux celles
        qui quoi dont où lequel laquelle lesquels lesquelles chaque
    """,
    "it": """
        il lo la i gli le l una di del dello della dei degli delle a al allo alla ai
        agli alle da dal dallo dalla dai dagli dalle in nel nello nella nei negli nelle
        su sul sullo sulla sui sugli sulle con per tra fra senza contro
        e ed o od ma né che se perché poiché però quando come mentre
        io tu lui lei noi voi loro egli ella esso essa essi esse mi ti si ci vi ne me te
        sé mio mia miei mie tuo tua tuoi tue suo sua suoi sue nostro nostra nostri
        nostre vostro vostra vostri vostre questo questa questi queste quello quella
        quelli quelle chi cui quale quali dove durante ogni
    """,
}

#: Closed-class word forms per language (lowercase, exact match on `Lemma.text`).
CLOSED_CLASS: dict[str, frozenset[str]] = {
    language: frozenset(words.split()) for language, words in _LISTS.items()
}


def closed_class_drops(tables: TaggedTables) -> list[FormDrop]:
    """Return a drop for every sense of a closed-class lemma in ``tables``.

    Args:
        tables: The freshly transformed tables.

    Returns:
        Accepted `FormDrop` rows, ready for `apply_form_drops`.
    """
    closed = {
        lemma.id: lemma
        for lemma in tables.lemmas
        if lemma.text in CLOSED_CLASS.get(lemma.language, frozenset())
    }
    return [
        FormDrop(
            lemma_id=sense.lemma_id,
            concept_key=concept_key(sense.concept_id),
            language=closed[sense.lemma_id].language,
            form=closed[sense.lemma_id].text,
            kind="closed-class",
            drop=True,
            status="accepted",
            model=CLOSED_CLASS_MODEL,
        )
        for sense in tables.senses
        if sense.lemma_id in closed
    ]
