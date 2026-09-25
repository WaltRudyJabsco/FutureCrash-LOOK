# LOOK Information Edges

LOOK prefers a small number of named, public, text-friendly information sources over an unbounded API collection.

| Edge | Current provider | Intended use |
|---|---|---|
| WEATHER | Open-Meteo | live weather and forecast |
| PLACE | Open-Meteo geocoding | geographic resolution |
| WIKI | Wikipedia | stable readable background |
| DATA | Wikidata | structured entities and identifiers |
| PAPERS | Crossref | DOI/bibliographic metadata |
| ARCHIVE | Internet Archive | historical/archive objects |
| WEB | Ollama web search | general current information |

Canonical edge results use a common receipt:

```text
EDGE        WEATHER
SOURCE      Open-Meteo
CONFIDENCE  DIRECT
AS-OF       <source time when supplied>
RETRIEVED   <local retrieval time>
SOURCE-URL  <canonical provider>
```

`DIRECT`, `DERIVED`, `SEARCHED`, and `MODEL` describe provenance, not probability. LOOK does not manufacture confidence percentages.

The list is deliberately short. New edges should be added only when a canonical source materially improves reliability, provenance, or structured access over WIKI/WEB.
