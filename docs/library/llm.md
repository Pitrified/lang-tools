# LLM chains

The `lang_tools.llm` package wraps `llm-core`'s `StructuredLLMChain` for the
seven recurring tasks of the language-learning stack. Every chain ships with
a versioned Jinja prompt under `src/lang_tools/prompts/<name>/v1.jinja` and a
`build_*_chain(chat_config, ...)` factory.

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
| [`build_tutor_chain`](../reference/lang_tools/llm/tutor/) | `TutorInput` | `TutorOutput` | Tutor reply with `correction` + `conversation` blocks |
| [`build_topic_suggestion_chain`](../reference/lang_tools/llm/topics/) | `TopicSuggestionInput` | `TopicSuggestionOutput` | Suggest topics for practice |
| [`build_paragraph_splitter_chain`](../reference/lang_tools/llm/splitter/) | `SplitterInput` | `SplitterOutput` | Split text into reconstruction-friendly portions |
| [`build_greeting_chain`](../reference/lang_tools/llm/greeting/) | `GreetingInput` | `GreetingOutput` | Open a tutor conversation |
| [`build_word_generator_chain`](../reference/lang_tools/llm/word_generator/) | `WordGeneratorInput` | `WordGeneratorOutput` | Generate themed vocabulary on demand |

`StructuredLLMChain` validates that every Jinja variable in the prompt
matches a field of the input model at construction time, so a prompt edit
that drops or renames a variable surfaces immediately.
