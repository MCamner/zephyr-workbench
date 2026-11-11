# Zephyr: genomförd tillförlitlighetsgranskning

Datum: 2026-11-11. Ändringarna är lokala och ännu inte releasade.

## Genomförda ändringar

- Python- och webbdiff täcker arkitekturens namn, beskrivning, domäner/regler, komponentfält, riskernas mitigation/referenser, kontroller, stakeholders och trust boundaries. JSON och historik tar med de nya ändringskategorierna.
- Risker kan ange `components`, `flows` och `controls`. Referenser valideras och följer med i laddning, sammanfattning, sökresultat och riskförklaringar. Äldre modeller fungerar utan referenser; förklaringen gissar inte berörda system.
- Borttagen mitigation identifieras som potentiellt omitigierad risk och ger hög konsekvensnivå.
- CLI och runtime delar importflöde. Import validerar innan output skrivs och returnerar strukturerade fel. Befintlig output lämnas orörd vid valideringsfel.
- Lokal bildimport identifierar rektanglar, OCR-läser etiketter och tolkar raka centrerade pilar. Otydlig riktning utelämnas med varning. Tesseract krävs separat; Pillow finns som `image`-extra.
- Minnesindex har innehållshash och källstatus. `memory refresh` uppdaterar ändrade/äldre poster och rapporterar saknade/ogiltiga källor utan att radera dem. Indexskrivning använder atomisk ersättning; det innebär inte samtidighetslåsning.
- Modelljämförelse använder typade riktade graffingeravtryck, antal komponenter/relationer och två grannskapssteg. Namnbyte ensamt ändrar inte likheten.
- Verktygskontrakten täcker analys, import, reviews, governance, konsekvensanalys, snapshots, historik och minne, med faktiska skriveffekter.
- Webbutkast och aktiv fil sparas lokalt och återställs efter omladdning. Ogiltig YAML bevaras. Korrupt lagring skrivs inte över automatiskt; lagringsfel och konflikter mellan flikar visas.
- README, roadmap, changelog, schema, kontraktsdokumentation och tre repo-skills har uppdaterats. CI kör också browser-core-kontroller med Node.

## Verifiering

- Före implementation: 13 nya regressionstester fallerade på granskningsfynden. Ytterligare felvägar testades före respektive korrigering.
- Slutlig testkörning: `python3 -m pytest -q` → **580 passed in 2.83s**.
- `node tests/browser_core.cjs` → diff, riskreferenser, utkaståterställning, korrupt/dubbel lagring och kvotfel godkända.
- `python3 scripts/generate_js_core.py` → redan i synk; generatorns idempotens testas också i pytest.
- Alla åtta arkitekturexempel validerar. Governance-policyfilen är en separat policy och räknas inte som arkitekturmodell.
- Riktig webbläsare: redigerat YAML-utkast överlevde omladdning; därefter skapades en andra fil och även aktiv fil återställdes. Inga JavaScript-fel vid dessa omladdningar. Babel visar sin befintliga utvecklingsvarning.
- Riktig lokal OCR/CLI: genererad testbild gav Client, Server och en riktad relation. Enhetstester täcker också omvänd/vertikal pil, linje utan pil och tom bild.
- CLI-minne i temporär katalog: add → ändrad källa → refresh → aktuell källa, med uppdaterat modellnamn.
- Tre ändrade skills har godkänd frontmatter-/namnvalidering med skill-creators validator. Ett realistiskt användningsfall är ändring av riskfält med diff/runtime-regressioner; ren README-korrektur behöver inte modell-/OCR-flödet.
- `git diff --check` passerar. Minnestesterna använder isolerat index; det spårade `.zephyr/memory/index.json` har inte ändrats.

## Kvarvarande produktgränser

Sökning är nyckelordsmatchning utan embeddings eller synonymförståelse. Graffingeravtrycket är en begränsad likhetsmetrik, inte bevis på grafekvivalens. Rasterimport är experimentell och begränsad till mörka rektanglar/raka centrerade pilar på ljus bakgrund, högst 2500 pixlar per sida. Alla importer kräver manuell kontroll av etiketter, typer och relationer. CLI/Python har fler funktioner än webbgränssnittet.

En bred Ruff-kontroll visar även sedan tidigare oanvända importer/variabler i flera moduler; dessa har inte gjorts till en separat städrefaktorering. Nya regressionstestfiler har kontrollerats med Ruff.

## Lärdomar

1. En grön testsuite bevisar bara de kontrakt som faktiskt testas. Säkerhetsrelevanta diff-fält behöver egna regressioner genom diff, JSON och historik.
2. Riskpåverkan ska komma från explicita referenser, inte från generell kritikalitet.
3. OCR-text och visuell diagramrekonstruktion är olika kapabiliteter. Ange stödda former, pilar och osäkerhet, och verifiera med riktig OCR.
4. Genererade JS-sektioner garanterar inte att handskriven browserlogik följer Python. Kör separata diff-/referens-/lagringstester.
5. Runtime-tester med standardlagring måste isolera indexet så att tester inte ändrar användardata.
6. Beskriv kapabiliteter efter implementationen: ordöverlapp är inte embeddings och ett tvåstegsfingeravtryck är inte grafisomorfism.
