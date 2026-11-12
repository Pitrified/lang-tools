# Open points

Known problems with no plan folder yet, one section each.
To work on one, open a numbered folder for it, start its `00_start.md` from the section,
and remove the section here.
A new point gets a section: what is wrong, how big, and where it was found.

## pt *pêlo* / *pelo* homograph

The corpus keeps the old spelling *pêlo* "hair", since respelt it would be the closed-class
*pelo* "by the".
Two reviewed look-alike rows on *pelos* (it *pelo* "hair", *peloso*) were reviewed for "hairs",
which this corpus spells *pêlos*, so they now sit on the contraction "by the".
Found in `14_number_modal_words/07_closed_class_concepts.md` and `06_spelling.md`;
the spelling rule is in `docs/library/lexicon.md`.

## lang-tutor drops an empty `exclude_part_of_speech`

lang-tutor sends only the `CardQuery` fields that differ from their defaults
(`content/http.py` `_card_params`), and an empty list encodes to no pair at all.
So a query with `exclude_part_of_speech=[]` reaches 8010 as the default and still gets no
function word (0 against 123 when 8010 is sent `?exclude_part_of_speech=` directly).
No lang-tutor query sets it today.
The fix is in lang-tutor: send the bare key for an empty list.
Found in `16_card_pos_filter/03_release.md`.

## Doubtful base picks for three pt forms

From a read of 100 of a 500 sample of the inflected forms the build adds:
*virei* (the future of *vir*; in speech mostly *virar* "I turned"),
*obvio* (a misspelling of *óbvio*, read as *obviar*),
*rebelo* (mostly a name).
Found in `15_inflection_model/02_build_stage.md`.

## Wrong glosses inherited from the base's card

A form shows its base's card by design, so a wrong card on the base shows on its forms too.
Three seen in the same read: *gorduras* "soil, dirt", *troncos* "belly", *pintadas* "paved".
A card review of the bases fixes both.
Found in `15_inflection_model/02_build_stage.md`.

## pt forms that are also English words or names

Kept on purpose, with no filter, since forms are out of drills by default:
183 forms as frequent in English as in Portuguese (*to*, *for*, *some*, *times*, *classes*),
most of them real pt forms, with *to* and *does* noise;
140 forms that kaikki also lists as names (*gomes*, *castro*, *domingos*, *irão*), most of them
real forms too.
Worth a look only if forms come back into drills or word lists.
Found in `15_inflection_model/01_form_table.md`.
