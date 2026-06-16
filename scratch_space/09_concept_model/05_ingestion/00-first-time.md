# First time downloading

## dowload

we have run the
`/home/pmn/ephem/lang-tools/notebooks/lexicon_ingest/01_download.ipynb`
for en pt

### omw

when downloading omw some lang filer clearly were not passed down to the downloader

```log
2026-06-17 12:58:40.166 | INFO     | lang_tools.lexicon.ingestion.acquire:download_omw:110 - Downloading OMW omw:1.4 for ['en', 'pt']
Download [##############################] (49414200/49414200 bytes) 
Added omw-da:1.4 (DanNet)############] (23898/23898) 
Added omw-es:1.4 (Multilingual Central Repository (Spanish))
Added omw-iwn:1.4 (ItalWordNet)######] (112094/112094) 
Added omw-nn:1.4 (Norwegian Wordnet (Nynorsk))18741) 
Added omw-he:1.4 (Hebrew Wordnet)####] (35066/35066) 
Added omw-arb:1.4 (Arabic WordNet (AWN v2))267/101267) 
Added omw-ja:1.4 (Japanese Wordnet)##] (593565/593565) 
Added omw-gl:1.4 (Multilingual Central Repository (Galician))
Added omw-ro:1.4 (Romanian Wordnet)##] (354490/354490) 
Added omw-fi:1.4 (FinnWordNet)#######] (698216/698216) 
Added omw-hr:1.4 (Croatian Wordnet)##] (158287/158287) 
Added omw-is:1.4 (IceWordNet)########] (55920/55920) 
Added omw-sl:1.4 (sloWNet)###########] (241879/241879) 
Added omw-cmn:1.4 (Chinese Open Wordnet)312162/312162) 
Added omw-en:1.4 (OMW English Wordnet based on WordNet 3.0)
Added omw-sv:1.4 (WordNet-SALDO)#####] (31316/31316) 
Added omw-th:1.4 (Thai Wordnet)######] (419310/419310) 
Added omw-zsm:1.4 (Wordnet Bahasa (Malaysian))/258204) 
Added omw-nl:1.4 (Open Dutch WordNet)] (221437/221437) 
Added omw-el:1.4 (Greek Wordnet)#####] (115019/115019) 
Added omw-pt:1.4 (OpenWN-PT)#########] (282703/282703) 
Added omw-eu:1.4 (Multilingual Central Repository (Basque))
Added omw-id:1.4 (Wordnet Bahasa (Indonesian))/273346) 
Added omw-ca:1.4 (Multilingual Central Repository (Catalan))
Added omw-nb:1.4 (Norwegian Wordnet (Bokmål))/22773) 
Added omw-it:1.4 (MultiWordNet (Italian))31291/231291) 
Added omw-bg:1.4 (BulTreeBank Wordnet (BTB-WN))3548) 
Added omw-lt:1.4 (Lithuanian  WordNet) (59778/59778) 
Added omw-sk:1.4 (Slovak WordNet)####] (150220/150220) 
Added omw-fr:1.4 (WOLF (Wordnet Libre du Français))90) 
Added omw-pl:1.4 (plWordNet)#########] (222570/222570) 
Added omw-sq:1.4 (Albanet)###########] (41743/41743) 
```

```json
{"wn_version": "1.1.0",
 "omw_version": "omw:1.4",
 "languages": ["en", "pt"],
 "lexicons": ["omw-arb:1.4",
  "omw-bg:1.4",
  "omw-ca:1.4",
  "omw-cmn:1.4",
  "omw-da:1.4",
  "omw-el:1.4",
  "omw-en:1.4",
  "omw-es:1.4",
  "omw-eu:1.4",
  "omw-fi:1.4",
  "omw-fr:1.4",
  "omw-gl:1.4",
  "omw-he:1.4",
  "omw-hr:1.4",
  "omw-id:1.4",
  "omw-is:1.4",
  "omw-it:1.4",
  "omw-iwn:1.4",
  "omw-ja:1.4",
  "omw-lt:1.4",
  "omw-nb:1.4",
  "omw-nl:1.4",
  "omw-nn:1.4",
  "omw-pl:1.4",
  "omw-pt:1.4",
  "omw-ro:1.4",
  "omw-sk:1.4",
  "omw-sl:1.4",
  "omw-sq:1.4",
  "omw-sv:1.4",
  "omw-th:1.4",
  "omw-zsm:1.4"],
 "wn_data_dir": "/home/pmn/ephem/lang-tools/data/_raw/lexicon/wn_data"}
```

### kaikki

seems ok

## run transform

we did run
`/home/pmn/ephem/lang-tools/notebooks/lexicon_ingest/02_transform.ipynb`
on en and pt

got an error (captured by re-running `build_initial(['en','pt'], ...)`):

```text
  File ".../lexicon/ingestion/sources/omw.py", line 206, in wn_synset_entries
    ili=ili.id if ili is not None else None,
        ^^^^^^
AttributeError: 'str' object has no attribute 'id'
```

Analysis and the fix plan for this (and two related OMW-acquisition issues
surfaced by the log above) are in
[`../05.1_ingestion_fixes.md`](../05.1_ingestion_fixes.md).
