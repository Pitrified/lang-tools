# show words starting

## overview

when filtering for words in the webapp, the whole webpage is shown inside the filter output

1. add a log when we load words so that we can confirm that the bootstrap CSVs are being loaded correctly
1. make it so that the word list is shown automatically when we click on the "Words" link in the navbar, without needing to submit an empty filter form
1. fix the filter form so that it actually filters the word list instead of showing the whole page again

## plan

Root cause: the HTMX filter uses `hx-get="/words"` which returns the full page (extends base.html). HTMX then injects the full HTML (including head/body) into `#word-table-container`.

Fixes:

1. **Add log on word store load** - add a `loguru` log in `word_store._load_all()` reporting how many words were loaded per file.

2. **Show words on page load** - the template already receives `words` from the router (we wired it in the last session). The table renders if `words` is truthy. Since `get_words_filtered(None, None)` returns all words, the table should already display on initial load. If it doesn't, something is off with the data path. Verify and fix.

3. **Fix HTMX filter** - create a separate partial template `pages/words/_word_table.html` that renders only the table (no base.html extend). Add a dedicated endpoint `GET /words/partial` that returns just the table partial. Update the HTMX attributes to point to `/words/partial` instead of `/words`.
