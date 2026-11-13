# Data license

The code in this repository is under the MIT license (`LICENSE`).
This file covers the lexical data:
the reviewed inputs under `data/curated/`, the sample seed under `data/bootstrap/`,
the corpus the build writes to `data/lexicon/`, and any copy or export of them.

## License

The data is licensed under the
[Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/)
(CC BY 4.0), with the French exception below.
Copyright (c) 2026 Pietro Maria Nobili.

You may share and adapt it for any purpose, commercial ones included, as long as you give the
attribution below.
It is built on the sources listed further down: their data stays available under their own
terms, and this license covers the selection and arrangement of it, the values derived from it,
and the text written for this project.

## How to credit it

Copy this, or an equivalent, where your users can see it (an about or licenses screen, a README):

> Lexical data from lang-tools by Pietro Maria Nobili, licensed under CC BY 4.0
> (https://github.com/Pitrified/lang-tools/blob/main/DATA_LICENSE.md).
> Built on Princeton WordNet 3.0, OpenWordnet-PT, the Multilingual Central Repository,
> MultiWordNet, the Collaborative Interlingual Index and wordfreq.

and keep the WordNet 3.0 notice at the end of this file with any copy of the data.

## Sources

| Source | Used for | License |
| --- | --- | --- |
| Princeton WordNet 3.0, as packaged in the Open Multilingual Wordnet 1.4 (`omw-en`) | en words, concepts, glosses, examples, relations | WordNet 3.0 license (below) |
| OpenWordnet-PT 1.0.0 (`own-pt`) | pt words, their links to concepts, pt antonyms | CC BY 4.0 |
| Multilingual Central Repository 3.0, Spanish (`omw-es`) | es words and their links to concepts | CC BY 3.0 |
| MultiWordNet, Italian (`omw-it`) | it words, their links to concepts, it glosses | CC BY 3.0 |
| Collaborative Interlingual Index (`cili`) | the shared concept ids; en glosses where WordNet has none | CC BY 4.0 |
| wordfreq 3.1.1 | word frequencies, from which the sense frequencies and CEFR bands are derived | data CC BY-SA 4.0, code Apache-2.0 |
| WOLF, French (`omw-fr`) | fr words and their links to concepts | CeCILL-C, see below |

From OpenWordnet-PT only the words, their links to concepts and the antonyms are used:
its definitions and examples, partly taken from Wikipedia, are not.
The frequencies are numbers computed from wordfreq's word lists, not the lists themselves;
wordfreq's data sources are credited below.

Text written for this project is under this license too:
the glosses written for es, fr, it and pt, the look-alike notes, the reviewed sense choices,
the example sentences, and the inflected forms and their notes, which the build generates from
rules of its own.

### French

The French wordnet, WOLF, is under the CeCILL-C license
(http://www.cecill.info/licenses/Licence_CeCILL-C_V1-en.html), a weak copyleft license, and
is not covered by the CC BY 4.0 grant above.
French is part of the local build and of the sample seed, and is left out of the data this
project ships.
If you use the French data, its CeCILL-C terms apply to it.

## Citations

- Christiane Fellbaum (ed.). 1998. *WordNet: An Electronic Lexical Database*. MIT Press.
- Valeria de Paiva, Alexandre Rademaker and Gerard de Melo. 2012. OpenWordNet-PT: An Open
  Brazilian Wordnet for Reasoning. In *Proceedings of COLING 2012: Demonstration Papers*,
  pages 353-360. Mumbai, India.
- Aitor Gonzalez-Agirre, Egoitz Laparra and German Rigau. 2012. Multilingual Central Repository
  version 3.0: upgrading a very large lexical knowledge base. In *Proceedings of the 6th Global
  WordNet Conference (GWC 2012)*. Matsue, Japan.
- Emanuele Pianta, Luisa Bentivogli and Christian Girardi. 2002. MultiWordNet: Developing an
  Aligned Multilingual Database. In *Proceedings of the First International Conference on Global
  WordNet*, pages 293-302. Mysore, India.
- Francis Bond, Piek Vossen, John McCrae and Christiane Fellbaum. 2016. CILI: the Collaborative
  Interlingual Index. In *Proceedings of the 8th Global WordNet Conference (GWC 2016)*,
  pages 50-57. Bucharest, Romania.
- Benoit Sagot and Darja Fišer. 2008. Building a free French wordnet from multilingual
  resources. In *Proceedings of the Sixth International Language Resources and Evaluation
  Conference (LREC 2008)*. Marrakech, Morocco.
- Robyn Speer. 2022. rspeer/wordfreq: v3.0. Zenodo. https://doi.org/10.5281/zenodo.7199437

wordfreq's frequencies come from, among others: Wikipedia; the OPUS OpenSubtitles 2018 corpus,
with attribution to OpenSubtitles; the SUBTLEX lists by Marc Brysbaert et al., which are freely
available data; Google Books Ngrams (https://books.google.com/ngrams); the Leeds Internet Corpus
(University of Leeds Centre for Translation Studies); and ParaCrawl.

## WordNet 3.0 license

```text
WordNet Release 3.0

This software and database is being provided to you, the LICENSEE, by
Princeton University under the following license.  By obtaining, using
and/or copying this software and database, you agree that you have
read, understood, and will comply with these terms and conditions.:

Permission to use, copy, modify and distribute this software and
database and its documentation for any purpose and without fee or
royalty is hereby granted, provided that you agree to comply with
the following copyright notice and statements, including the disclaimer,
and that the same appear on ALL copies of the software, database and
documentation, including modifications that you make for internal
use or for distribution.

WordNet 3.0 Copyright 2006 by Princeton University.  All rights reserved.

THIS SOFTWARE AND DATABASE IS PROVIDED "AS IS" AND PRINCETON
UNIVERSITY MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR
IMPLIED.  BY WAY OF EXAMPLE, BUT NOT LIMITATION, PRINCETON
UNIVERSITY MAKES NO REPRESENTATIONS OR WARRANTIES OF MERCHANT-
ABILITY OR FITNESS FOR ANY PARTICULAR PURPOSE OR THAT THE USE
OF THE LICENSED SOFTWARE, DATABASE OR DOCUMENTATION WILL NOT
INFRINGE ANY THIRD PARTY PATENTS, COPYRIGHTS, TRADEMARKS OR
OTHER RIGHTS.

The name of Princeton University or Princeton may not be used in
advertising or publicity pertaining to distribution of the software
and/or database.  Title to copyright in this software, database and
any associated documentation shall at all times remain with
Princeton University and LICENSEE agrees to preserve same.
```
