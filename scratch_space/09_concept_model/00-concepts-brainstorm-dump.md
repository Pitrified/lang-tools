

Extracting false friends from the `Word` model into a dedicated relationship model (an "edge table") is an excellent design choice for a Concept-Centric architecture.

Because false friends are relatively rare, keeping them in a separate structure keeps the core `Word` model clean, lightweight, and completely decoupled from cross-lingual edge management. It also eliminates data integrity bugs where an engineer might update a false friend on Word A but forget to add the symmetrical link back on Word B.

Here is a comprehensive design for extracting false friends into a separate table, along with its integration into the in-memory `word_store.py`.

---

### 1. The Decoupled Schema Design

We introduce a standalone `FalseFriendRelation` model. To handle serialization (like JSON or CSV) cleanly, we define two explicit word fields. We can guarantee uniqueness by ensuring `word_id_a` is always lexicographically smaller than `word_id_b` (`word_id_a < word_id_b`).

#### `src/lang_tools/words/word.py`

```python
from __future__ import annotations
from pydantic import BaseModel, Field, computed_field
from lang_tools.words.word_id import word_id

class Word(BaseModel):
    """Represents a purely lexical token in a specific language."""
    text: str
    language: str
    normalized: str = ""
    part_of_speech: str | None = None
    
    # Links this word to its semantic meanings (handles polysemy)
    concept_ids: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def id(self) -> str:
        """Deterministic ID derived from (text, language)."""
        return word_id(self.text, self.language)


class Concept(BaseModel):
    """A language-independent semantic meaning (Synset)."""
    id: str  # e.g., "c_library_place"
    definitions: dict[str, str] = Field(default_factory=dict)  # {"en": "...", "pt": "..."}
    lemmas: dict[str, list[str]] = Field(default_factory=dict)       # {"en": ["w_library_en"], "pt": [...]}


class FalseFriendRelation(BaseModel):
    """A standalone edge table documenting a symmetrical false friend illusion."""
    word_id_a: str
    word_id_b: str
    similarity_score: float | None = None
    
    # Language-specific explanation notes for learners
    # e.g., {"en": "Don't confuse with 'livraria' (bookstore)", "pt": "Não confunda com 'library' (biblioteca)"}
    explanation_notes: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _enforce_deterministic_order(self) -> FalseFriendRelation:
        """Ensures a single canonical orientation for the symmetric pair."""
        if self.word_id_a > self.word_id_b:
            self.word_id_a, self.word_id_b = self.word_id_b, self.word_id_a
        return self

```

---

### 2. Symmetrical Indexing in the Word Store

Since the word store loads data into memory at import time, we can build a fast, bidirectional lookup registry for these relations. This gives us $O(1)$ query performance for any given word ID without polluting the `Word` instances.

#### `src/lang_tools/words/word_store.py`

```python
# ... (existing imports)
from collections import defaultdict
from lang_tools.words.word import Word, Concept, FalseFriendRelation

_ALL_WORDS: list[Word] = _load_all()
_BY_ID: dict[str, Word] = {w.id: w for w in _ALL_WORDS}

# --- New False Friend "Edge Table" Storage ---
_ALL_FALSE_FRIENDS: list[FalseFriendRelation] = _load_false_friends() 

# Symmetrical look-aside index: maps a single word ID to all its false friend relations
_FALSE_FRIENDS_BY_WORD_ID: dict[str, list[FalseFriendRelation]] = defaultdict(list)

def _initialize_false_friend_index():
    for rel in _ALL_FALSE_FRIENDS:
        _FALSE_FRIENDS_BY_WORD_ID[rel.word_id_a].append(rel)
        _FALSE_FRIENDS_BY_WORD_ID[rel.word_id_b].append(rel)

_initialize_false_friend_index()

# --- Public API Functions ---

def get_false_friends_for_word(word_id: str) -> list[tuple[Word, FalseFriendRelation]]:
    """Finds all false friends for a given word, returning the related Word and Edge metadata."""
    relations = _FALSE_FRIENDS_BY_WORD_ID.get(word_id, [])
    results = []
    for rel in relations:
        # Determine which side of the symmetric relation is the "other" word
        other_id = rel.word_id_b if rel.word_id_a == word_id else rel.word_id_a
        other_word = _BY_ID.get(other_id)
        if other_word:
            results.append((other_word, rel))
    return results

```

---

### 3. Concrete Data Example

With this separate table approach, your bootstrap data or JSON configurations layout cleanly with zero duplication of the relationship details:

```python
# The Table/List of Relations
false_friend_registry = [
    FalseFriendRelation(
        word_id_a="w_library_en",
        word_id_b="w_livraria_pt",
        similarity_score=0.85,
        explanation_notes={
            "en": "Livraria looks like library, but it actually means bookstore!",
            "pt": "Library parece livraria, mas na verdade significa biblioteca!"
        }
    )
]

```

### Why this shines at scale

1. **Easy Ingestion:** When writing a CSV loader or populating data via an LLM execution chain, you don't have to fetch, modify, and resave two separate language rows. You simply append a single row to a `false_friends.csv` file.
2. **Lean Word Payloads:** When a user-facing tutor application requests a common word via the API route `/api/v1/words/{id}`, it receives a clean, streamlined payload. The heavy relationship graphs are only fetched out-of-band when generating specific vocabulary trap exercises.
3. **Perfect for Cognates Too:** This exact same pattern can be used if you eventually decide to explicitly map tricky or irregular Real Friends (Cognates) that don't perfectly share a single concept node but are phonetically linked.

------------

Here is a comprehensive data example using real-world linguistic data mapped directly to our proposed **Concept-Centric Architecture**.

These examples show how this structure handles **Polysemy** (one word, multiple meanings), **Synonymy/Dialects** (one concept, multiple words in the same language), **Cognates** (shared cross-lingual concepts), and **False Friends** (lexical collisions across separate concepts).

---

### 1. Polysemy (Words with Multiple Concepts)

A classic example is the word **"banco"** in Portuguese or Spanish, which can mean a financial institution or a physical seat (a bench).

In this architecture, the word exists exactly once per language to prevent lexical token duplication, but points out to multiple distinct conceptual IDs:

```python
# --- THE WORD ---
word_banco_pt = Word(
    text="banco",
    language="pt",
    concept_ids=["c_financial_bank", "c_seating_bench"] # Maps to both meanings
)

# --- THE CORRESPONDING CONCEPTS ---
concept_financial_bank = Concept(
    id="c_financial_bank",
    definitions={
        "pt": "Instituição que aceita depósitos e realiza empréstimos.",
        "en": "A financial institution licensed to receive deposits and make loans."
    },
    lemmas={
        "pt": ["w_banco_pt"],
        "en": ["w_bank_en"]
    }
)

concept_seating_bench = Concept(
    id="c_seating_bench",
    definitions={
        "pt": "Assento longo para duas ou mais pessoas, comum em parques.",
        "en": "A long seat for several people, typically found in parks or gardens."
    },
    lemmas={
        "pt": ["w_banco_pt"],
        "en": ["w_bench_en"]
    }
)

```

---

### 2. Synonymy & Regional Dialects (Concepts with More Lemmas)

Sometimes, a single, precise concept can be expressed by multiple words within the same language. For example, a railway train is called **"trem"** in Brazilian Portuguese and **"comboio"** in European Portuguese. In English, **"couch"** and **"sofa"** share the same core meaning.

The `Concept` node groups these lemmas together natively inside its language keys:

```python
# --- THE CONCEPT ---
concept_railway_train = Concept(
    id="c_railway_train",
    definitions={
        "en": "A connected series of railway carriages moved by a locomotive.",
        "pt": "Um meio de transporte que se desloca sobre carris ou trilhos."
    },
    lemmas={
        "en": ["w_train_en"],
        "pt": ["w_trem_pt", "w_comboio_pt"] # Multiple lemmas for Portuguese!
    }
)

# --- THE WORDS ---
word_trem_pt = Word(text="trem", language="pt", concept_ids=["c_railway_train"])
word_comboio_pt = Word(text="comboio", language="pt", concept_ids=["c_railway_train"])

```

---

### 3. Cognates / Real Friends (Implicit Cross-Lingual Links)

Cognates are words that look/sound similar across different languages because they share historical roots and have the exact same meaning. Examples include **"hospital"** (EN/ES/PT) or **"universidad"** (ES) / **"universidade"** (PT) / **"university"** (EN).

Instead of drawing explicit relationship arrows between these words, they are implicitly grouped by the fact that they inhabit the exact same `Concept` node:

```python
# --- THE CENTRALIZED COGNATE CONCEPT ---
concept_university = Concept(
    id="c_university_institution",
    definitions={
        "en": "An institution of high-level learning that awards degrees.",
        "pt": "Instituição de ensino superior que concede graus acadêmicos.",
        "es": "Institución de enseñanza superior que otorga títulos académicos."
    },
    lemmas={
        "en": ["w_university_en"],
        "pt": ["w_universidade_pt"],
        "es": ["w_universidad_es"]
    }
)

# --- THE WORDS ---
word_university_en = Word(text="university", language="en", concept_ids=["c_university_institution"])
word_universidade_pt = Word(text="universidade", language="pt", concept_ids=["c_university_institution"])
word_universidad_es = Word(text="universidad", language="es", concept_ids=["c_university_institution"])

```

*Your application layer can run a simple text-similarity function (like Levenshtein distance) on all word strings found under the same concept to automatically discover and flag them as "Real Friends" for the user.*

---

### 4. False Friends (Decoupled Edge Table Entry)

A dangerous trap for English speakers learning Spanish is the word **"embarazada"** (which means *pregnant*, not *embarrassed*).

Because their meanings completely conflict, they belong to completely separate concepts. We map this dangerous intersection using a standalone **Edge Table** (`FalseFriendRelation`), which ensures our core models stay completely clean:

```python
# --- THE CONCEPTS (Entirely Separate) ---
concept_pregnant = Concept(
    id="c_pregnant_state",
    definitions={
        "es": "Que lleva un feto en el útero.",
        "en": "Having a developing embryo or fetus in the uterus."
    },
    lemmas={"es": ["w_embarazada_es"], "en": ["w_pregnant_en"]}
)

concept_embarrassed = Concept(
    id="c_feeling_embarrassed",
    definitions={
        "en": "Feeling ashamed, self-conscious, or uncomfortable.",
        "es": "Sentirse avergonzado o incómodo por una acción."
    },
    lemmas={"en": ["w_embarrassed_en"], "es": ["w_avergonzado_es"]}
)

# --- THE WORDS ---
word_embarazada_es = Word(text="embarazada", language="es", concept_ids=["c_pregnant_state"])
word_embarrassed_en = Word(text="embarrased", language="en", concept_ids=["c_feeling_embarrassed"])

# --- THE GLOBAL FALSE FRIEND REGISTRY ---
# Stored out-of-band in an independent file/table (e.g., false_friends.json)
false_friends_db = [
    FalseFriendRelation(
        word_id_a="w_embarrassed_en",
        word_id_b="w_embarazada_es",
        similarity_score=0.88, # Highly deceptive visual similarity
        explanation_notes={
            "en": "The Spanish word 'embarazada' means 'pregnant'. If you mean humiliated, use 'avergonzado'.",
            "es": "La palabra inglesa 'embarrassed' significa 'avergonzado'. Si te refieres a gestación, usa 'pregnant'."
        }
    )
]

```

### Summary of Data Flows

* To build a **Synonym Matching Quiz**: Find a `Concept` where any language key list length is $> 1$.
* To build a **Cognate Flashcard Deck**: Find a `Concept` where multiple language keys contain strings with high visual similarities.
* To build a **False Friend Warning**: When a user selects a word, check the bidirectional `_FALSE_FRIENDS_BY_WORD_ID` lookup index in the `word_store` to see if an edge exists.

------------

Here is a comprehensive data example using real-world linguistic data mapped directly to our proposed **Concept-Centric Architecture**.

These examples show how this structure handles **Polysemy** (one word, multiple meanings), **Synonymy/Dialects** (one concept, multiple words in the same language), **Cognates** (shared cross-lingual concepts), and **False Friends** (lexical collisions across separate concepts).

---

### 1. Polysemy (Words with Multiple Concepts)

A classic example is the word **"banco"** in Portuguese or Spanish, which can mean a financial institution or a physical seat (a bench).

In this architecture, the word exists exactly once per language to prevent lexical token duplication, but points out to multiple distinct conceptual IDs:

```python
# --- THE WORD ---
word_banco_pt = Word(
    text="banco",
    language="pt",
    concept_ids=["c_financial_bank", "c_seating_bench"] # Maps to both meanings
)

# --- THE CORRESPONDING CONCEPTS ---
concept_financial_bank = Concept(
    id="c_financial_bank",
    definitions={
        "pt": "Instituição que aceita depósitos e realiza empréstimos.",
        "en": "A financial institution licensed to receive deposits and make loans."
    },
    lemmas={
        "pt": ["w_banco_pt"],
        "en": ["w_bank_en"]
    }
)

concept_seating_bench = Concept(
    id="c_seating_bench",
    definitions={
        "pt": "Assento longo para duas ou mais pessoas, comum em parques.",
        "en": "A long seat for several people, typically found in parks or gardens."
    },
    lemmas={
        "pt": ["w_banco_pt"],
        "en": ["w_bench_en"]
    }
)

```

---

### 2. Synonymy & Regional Dialects (Concepts with More Lemmas)

Sometimes, a single, precise concept can be expressed by multiple words within the same language. For example, a railway train is called **"trem"** in Brazilian Portuguese and **"comboio"** in European Portuguese. In English, **"couch"** and **"sofa"** share the same core meaning.

The `Concept` node groups these lemmas together natively inside its language keys:

```python
# --- THE CONCEPT ---
concept_railway_train = Concept(
    id="c_railway_train",
    definitions={
        "en": "A connected series of railway carriages moved by a locomotive.",
        "pt": "Um meio de transporte que se desloca sobre carris ou trilhos."
    },
    lemmas={
        "en": ["w_train_en"],
        "pt": ["w_trem_pt", "w_comboio_pt"] # Multiple lemmas for Portuguese!
    }
)

# --- THE WORDS ---
word_trem_pt = Word(text="trem", language="pt", concept_ids=["c_railway_train"])
word_comboio_pt = Word(text="comboio", language="pt", concept_ids=["c_railway_train"])

```

---

### 3. Cognates / Real Friends (Implicit Cross-Lingual Links)

Cognates are words that look/sound similar across different languages because they share historical roots and have the exact same meaning. Examples include **"hospital"** (EN/ES/PT) or **"universidad"** (ES) / **"universidade"** (PT) / **"university"** (EN).

Instead of drawing explicit relationship arrows between these words, they are implicitly grouped by the fact that they inhabit the exact same `Concept` node:

```python
# --- THE CENTRALIZED COGNATE CONCEPT ---
concept_university = Concept(
    id="c_university_institution",
    definitions={
        "en": "An institution of high-level learning that awards degrees.",
        "pt": "Instituição de ensino superior que concede graus acadêmicos.",
        "es": "Institución de enseñanza superior que otorga títulos académicos."
    },
    lemmas={
        "en": ["w_university_en"],
        "pt": ["w_universidade_pt"],
        "es": ["w_universidad_es"]
    }
)

# --- THE WORDS ---
word_university_en = Word(text="university", language="en", concept_ids=["c_university_institution"])
word_universidade_pt = Word(text="universidade", language="pt", concept_ids=["c_university_institution"])
word_universidad_es = Word(text="universidad", language="es", concept_ids=["c_university_institution"])

```

*Your application layer can run a simple text-similarity function (like Levenshtein distance) on all word strings found under the same concept to automatically discover and flag them as "Real Friends" for the user.*

---

### 4. False Friends (Decoupled Edge Table Entry)

A dangerous trap for English speakers learning Spanish is the word **"embarazada"** (which means *pregnant*, not *embarrassed*).

Because their meanings completely conflict, they belong to completely separate concepts. We map this dangerous intersection using a standalone **Edge Table** (`FalseFriendRelation`), which ensures our core models stay completely clean:

```python
# --- THE CONCEPTS (Entirely Separate) ---
concept_pregnant = Concept(
    id="c_pregnant_state",
    definitions={
        "es": "Que lleva un feto en el útero.",
        "en": "Having a developing embryo or fetus in the uterus."
    },
    lemmas={"es": ["w_embarazada_es"], "en": ["w_pregnant_en"]}
)

concept_embarrassed = Concept(
    id="c_feeling_embarrassed",
    definitions={
        "en": "Feeling ashamed, self-conscious, or uncomfortable.",
        "es": "Sentirse avergonzado o incómodo por una acción."
    },
    lemmas={"en": ["w_embarrassed_en"], "es": ["w_avergonzado_es"]}
)

# --- THE WORDS ---
word_embarazada_es = Word(text="embarazada", language="es", concept_ids=["c_pregnant_state"])
word_embarrassed_en = Word(text="embarrased", language="en", concept_ids=["c_feeling_embarrassed"])

# --- THE GLOBAL FALSE FRIEND REGISTRY ---
# Stored out-of-band in an independent file/table (e.g., false_friends.json)
false_friends_db = [
    FalseFriendRelation(
        word_id_a="w_embarrassed_en",
        word_id_b="w_embarazada_es",
        similarity_score=0.88, # Highly deceptive visual similarity
        explanation_notes={
            "en": "The Spanish word 'embarazada' means 'pregnant'. If you mean humiliated, use 'avergonzado'.",
            "es": "La palabra inglesa 'embarrassed' significa 'avergonzado'. Si te refieres a gestación, usa 'pregnant'."
        }
    )
]

```

### Summary of Data Flows

* To build a **Synonym Matching Quiz**: Find a `Concept` where any language key list length is $> 1$.
* To build a **Cognate Flashcard Deck**: Find a `Concept` where multiple language keys contain strings with high visual similarities.
* To build a **False Friend Warning**: When a user selects a word, check the bidirectional `_FALSE_FRIENDS_BY_WORD_ID` lookup index in the `word_store` to see if an edge exists.
