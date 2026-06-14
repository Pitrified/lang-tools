"""Content read API webapp for lang-tools.

A thin HTTP layer over the frozen word query helpers
(`lang_tools.words.word_store`). The service reads content from the cloned
working tree (git LFS) and serves it as JSON so `lang-tutor` can consume it
over HTTP instead of importing the store in-process.

The content is public; no authentication is required to read it.
"""
