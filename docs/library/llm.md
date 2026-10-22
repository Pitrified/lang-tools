# LLM chains

The `lang_tools.llm` package wraps `llm-core`'s `StructuredLLMChain` for the
content-producing tasks of the language-learning stack. Every chain ships with
a versioned Jinja prompt under `src/lang_tools/prompts/<name>/v1.jinja` and a
`build_*_chain(chat_config, ...)` factory. The interactive tutor chain
(`build_tutor_chain`) was extracted to `lang-tutor` in the phase 2 split.

Each factory accepts:

- `chat_config`: any `llm-core` `ChatConfig` (e.g.
  `ChatOpenAIConfig(api_key=...)`).
- `base_prompt_fol`: optional prompts root override.
- `version`: prompt version (default `"auto"`, picks the highest `vN`).

```python
from llm_core.chat.config.openai import ChatOpenAIConfig
from lang_tools.llm import build_translation_chain, TranslationInput

chain = build_translation_chain(ChatOpenAIConfig())
result = chain.invoke(TranslationInput(text="Bom dia",
                                       source_language="pt",
                                       target_language="en"))
print(result.translated_text)
```

## Available chains

| Factory | Input | Output | Purpose |
| --- | --- | --- | --- |
| [`build_translation_chain`](../reference/lang_tools/llm/translation/) | `TranslationInput` | `TranslationOutput` | Translate a single string |
| [`build_conversation_chain`](../reference/lang_tools/llm/conversation/) | `ConversationInput` | `ConversationOutput` | Generate a multi-turn bilingual dialogue |
| [`build_topic_suggestion_chain`](../reference/lang_tools/llm/topics/) | `TopicSuggestionInput` | `TopicSuggestionOutput` | Suggest topics for practice |
| [`build_paragraph_splitter_chain`](../reference/lang_tools/llm/splitter/) | `SplitterInput` | `SplitterOutput` | Split text into reconstruction-friendly portions |
| [`build_greeting_chain`](../reference/lang_tools/llm/greeting/) | `GreetingInput` | `GreetingOutput` | Open a tutor conversation |
| [`build_lemma_generator_chain`](../reference/lang_tools/llm/lemma_generator/) | `LemmaGeneratorInput` | `LemmaGeneratorOutput` | Generate themed vocabulary on demand |
| [`build_gloss_repair_chain`](../reference/lang_tools/llm/gloss_repair/) | `GlossRepairInput` | `GlossRepairOutput` | Rewrite a thin `definition == lemma` gloss, grounded in synset context (feeds the [maintenance loop](lexicon.md#maintenance-loop-phase-0555)) |
| [`build_slug_qualifier_chain`](../reference/lang_tools/llm/slug_qualifier/) | `SlugQualifierInput` | `SlugQualifierOutput` | Pick gloss-derived qualifiers for a group of concepts sharing a slug (phase 8) |
| [`build_form_review_chain`](../reference/lang_tools/llm/form_review/) | `FormReviewInput` | `FormReviewOutput` | Classify a suspicious member form (term, name, definition, wrong language, garbled) (phase 8) |
| [`build_gloss_translate_chain`](../reference/lang_tools/llm/gloss_translate/) | `GlossTranslateInput` | `GlossTranslateOutput` | Render ~25 English glosses into one language in a single call (the phase-8 gloss backfill) |

`StructuredLLMChain` validates that every Jinja variable in the prompt
matches a field of the input model at construction time, so a prompt edit
that drops or renames a variable surfaces immediately.

## Running a chain over a corpus worklist

`lang_tools.llm.runner` runs any chain over a keyed worklist, for the phase-8
maintenance jobs (see [Maintenance jobs](lexicon.md#maintenance-jobs-phase-8)):

- `run_chain(chain, items, checkpoint=..., limit=...)` runs live with a few worker
  threads. Every result is appended to a JSONL checkpoint as a `RunRecord` (key,
  output or error, model, prompt hash, path). A re-run skips finished keys, so an
  interrupted job resumes without paying twice; `limit` runs a sample.
- `submit_batch` / `collect_batch` take the same items through the OpenAI Batch
  API at half price. The request body is the chain's own rendered prompt with a
  strict JSON schema of its output model. `submit_batch` refuses to pay twice: while
  the batch it last submitted is alive or completed, it returns that id. `metadata`
  tags the batch so `find_batches` can find it again from another checkout.
- Every record carries the provider's measured token `Usage` (input, cached,
  output, reasoning). `summarize_usage` totals a checkpoint and `UsageTotals.cost`
  prices it, so a cost estimate comes from a measured sample, not a price list.

Hidden reasoning can dominate the bill: on the first phase-8 job it was 74% of the
output tokens for a task that did not need it. For these mechanical jobs, turn
reasoning off (`reasoning_effort="none"` on the batch body, or a `ChatOpenAIConfig`
subclass with that field for live runs).
