# MCP-kataloger: status og indsendelse (2026-11-21)

Research for `lookproof-mcp` og `swaphunt-mcp` (PyPI) og de hostede servere. Intet er indsendt. Alle tekster nedenfor er forslag til ejerens godkendelse.

Metode: sider hentet 2026-11-21 (Glama, mcp.so, MCP Market, officielle MCP Registry, PyPI, Claude-dokumentation, awesome-listernes CONTRIBUTING). Det, der ikke kunne læses, er markeret **Uverificeret**.

## Kort overblik

| Katalog | Lookproof | SwapHunt | Handling |
|---|---|---|---|
| Officielt MCP Registry | Listet (`io.github.lookproof/lookproof-mcp` 0.2.1, med remote `https://api.lookproof.dev/mcp`) | Listet (`io.github.swaphunt/swaphunt-mcp` 0.8.1, kun stdio) | SwapHunt: tilføj `remotes` når ejeren siger til (hostet er nu live) |
| Glama | Listet som server (`lookproof/x402-examples`) og connector, tekst delvist forældet | Ikke fundet | Claim connector; opdatér README-snapshot; indsend SwapHunt |
| mcp.so | Ikke fundet (0 resultater) | Ikke fundet | Indsend gratis (repo-URL) eller betalt ($39) |
| MCP Market | Ikke fundet i søgning | Ikke fundet | Indsend GitHub-repo (gratis) eller $29 |
| Smithery | **Uverificeret** (host blokeret af netværkspolitik) | **Uverificeret** | Tjek manuelt |
| PulseMCP | **Uverificeret** (403 fra sitet) | **Uverificeret** | Tjek manuelt |
| awesome-mcp-servers (punkpeye) | PR [#20345](https://github.com/punkpeye/awesome-mcp-servers/pull/20345) åben (2026-11-22) | Ikke indsendt | Afvent review |
| awesome-mcp-servers (appcypher) | Repoet er arkiveret (maj 2026), PR'er slået fra | Samme | Ingen; kan ikke indsendes |
| Claudes connector-katalog | Ikke indsendt | Ikke indsendt | Lookproof kan indsendes; SwapHunt har ikke egnet profil endnu |

Vigtigt fund: `https://api.swaphunt.dev/mcp` svarer 200 på `initialize` (serverInfo `swaphunt` 0.1.0, titel "SwapHunt (free trial)") og har 6 tools. `docs/hosted-mcp.md` i swaphunt/x402-examples siger, at den endnu er 404 bag `SWAPHUNT_MCP_ENABLED=false`. Dokumentet er altså forældet, eller flaget er slået til uden dokumentation. Afklar med ejeren, før noget indsendes med den URL.

Live tool-lister (via `tools/list`, 2026-11-21):

- `api.lookproof.dev/mcp`: 22 tools uden nøgle, alle `readOnlyHint: true`. Pakken `lookproof-mcp` har 23 tools (`get_usage` kræver nøgle).
- `api.swaphunt.dev/mcp`: `pm_fees`, `get_supported_assets`, `get_halving`, `get_alt_season`, `get_market_silence`, `get_quota`; alle `readOnlyHint: true`.

## Officielt MCP Registry (kilde for flere kataloger)

- Lookproof: 3 versioner (0.1.0, 0.2.0, 0.2.1). Titel "Lookproof DNS and mail security checks", beskrivelse "SPF, DKIM, DMARC, MTA-STS, DNSSEC, TLS and DNS checks. Free API key or pay-per-call (x402).", streamable-http-remote `https://api.lookproof.dev/mcp`. Korrekt.
- SwapHunt: 7 versioner (0.4.0 til 0.8.1). Titel "SwapHunt crypto market context", beskrivelse "Hyperliquid prices, regime, vol, funding, FOMO checks (x402, USDC); free Kalshi/Polymarket fees". Kun PyPI/stdio, ingen remote. Teksten er korrekt for pakken, men nævner ikke den hostede gratis prøve.
- Rettelse: ny version af `server.json` publiceres med `mcp-publisher` (GitHub-login til `io.github.<org>/...`). Metadata er uforanderlig pr. version, så en rettelse kræver en ny version.

## Glama

Lookproof:
- Serversiden: https://glama.ai/mcp/servers/lookproof/x402-examples, navn "lookproof-mcp", mærket Official, kategorier Security og Networking & Infrastructure, Python, Remote, licens A, maintenance B.
- Katalogtekst: "DNS and email security checks for AI agents: SPF, DKIM, DMARC, MTA-STS, DNSSEC, TLS and more, with a fix for every finding. Pay per call in USDC on Base via x402, with dry run by default and a per-session spending cap." (opdateret 2026-11-20).
- **Teksten er ufuldstændig:** den nævner ikke den gratis API-nøgle (250 credits/md), som siden 0.2.0 er Option 1.
- Serversidens README-visning er et ældre snapshot af repoets rod-README: "No account, no API key: the payment is the credential", "47 paid endpoints", tabellen med 23 tools. Repoets nuværende README (master) har nøglen først. Ret: Glama genindlæser fra GitHub; hvis snapshotet ikke opdateres, brug "Admin" på serversiden.
- Connector: https://glama.ai/mcp/connectors/io.github.lookproof/lookproof-mcp, "Lookproof DNS, mail and TLS security checks", Healthy, 100 % uptime, Streamable HTTP, MCP 2025-11-25, TDQS 4/5 over 22 tools. Siden siger "If you are the author of this connector, you can claim ownership": **connectoren er ikke claimet.**
- Krav og proces: `glama.json` findes i repoets rod med `maintainers: ["realninjadaddy"]`; Glama indekserer offentlige GitHub-repos, og connectors kommer fra det officielle registry. Claim kræver Glama-konto (Sign In) og at kontoen er maintainer. Pakkens PyPI-beskrivelse nævner, at Dockerfilen bruges af Glamas automatiske tjek. Detaljer om claim-flowet er **ikke læst i Glamas dokumentation** (kun fra selve siden).
- `glama.json` har kun GitHub-brugeren `realninjadaddy`. Hvis organisationens listing skal administreres af Lookproof-identiteten, skal maintainer-listen afklares af ejeren.

SwapHunt: ingen server- eller connector-listing (søgning på `swaphunt`, `swaphunt-mcp` og `hyperliquid x402` gav ingen). Repoet `swaphunt/x402-examples` har ingen `glama.json` i checkout. Næste skridt: tilføj `glama.json` (med maintainer) og brug "Add Server" på https://glama.ai/mcp/servers med repo-URL'en. Connectoren kommer med, når `remotes` står i registryet.

## mcp.so

- Søgning på `lookproof` og `swaphunt`: 0 resultater.
- Indsendelse: https://mcp.so/submit. Kategorierne MCP Server (GitHub-repo-URL) og Remote Server (endpoint-URL), felter Repository URL og Name. Betalt listing $39 engangs (publiceres straks uden review, verified-badge, dofollow-link). Hvorvidt der findes en gratis sti med review fremgår ikke tydeligt af siden; **uverificeret** (kræver login for at se).
- Krav: konto (Sign In) formentlig; ikke verificeret.

## MCP Market

- Søgning på `lookproof` og `swaphunt`: ingen egne listings (kun sponsorerede og uafhængige resultater).
- Indsendelse: https://mcpmarket.com/submit, vælg MCP Server, indsæt fuld GitHub-repo-URL (eller "Remote MCP"), e-mail meddeles ved publicering. Gratis indsendelse reviewes; $29 giver listing inden 24 timer, "Official"-badge og "Try Now"-link.

## Smithery og PulseMCP (uverificeret)

- smithery.ai: proxyen svarede 403 ("no rule or network setting allows this host") selv efter værten blev tilføjet; `registry.smithery.ai` gav 500. Ingen listing-status.
- pulsemcp.com: 403 fra sitet selv.
- Fra hukommelse, ikke verificeret mod dokumentation: Smithery bruger `smithery.yaml` til stdio-servere og kan hoste remote servere via konto; PulseMCP henter fra det officielle registry og har en indsendelses-/rettelsesformular. Begge påstande skal tjekkes manuelt på sitet, før nogen handler på dem.

## awesome-mcp-servers

Status 2026-11-22: kun punkpeye-listen er aktiv. appcypher/awesome-mcp-servers er arkiveret (sidste push 2026-05-06) med PR'er slået fra, så der kan ikke indsendes dertil. Lookproof er indsendt til punkpeye som PR [#20345](https://github.com/punkpeye/awesome-mcp-servers/pull/20345) (fork `realninjadaddy/awesome-mcp-servers`, branch `add-lookproof`, commits som Lookproof <github@lookproof.dev>). Hele README og oversættelserne blev tjekket først: Lookproof stod der ikke. Linjen står under 🔒 Security mellem `LaurieWired/GhidraMCP` og `luiacuaniello/perspectivegraph` (sektionen er ikke sorteret i praksis) med Glama-badge og `🎖️ 🐍 ☁️ 🏠 🍎 🪟 🐧`. SwapHunt er ikke indsendt.

Fundet (punkpeye/awesome-mcp-servers og appcypher/awesome-mcp-servers, CONTRIBUTING og README):

- punkpeye: fork, branch, ret `README.md`, åbn PR; commit "Add new XYZ server". Navn linket til repo plus kort beskrivelse; alfabetisk orden i hver kategori. Tilføj `🤖🤖🤖` til slutningen af PR-titlen for at tilvælge fast-track (agent-PR). Kun remote servere uden pakke hører hjemme i `awesome-remote-mcp-servers`; vores to har installerbare PyPI-pakker og hører i hovedlisten. Kategorier: 🔒 Security (Lookproof), 💰 Finance & Fintech (SwapHunt); der er ingen "Cryptocurrency"-overskrift. README er meget stor (1,75 M tegn); kun begyndelsen blev læst, så "ikke listet" er **ikke verificeret**. Glama-badge kræves ikke i CONTRIBUTING, men de fleste poster har et.
- appcypher (arkiveret maj 2026, gælder ikke længere): én PR pr. forslag, tilføj nederst i kategorien, alfabetisk orden, brugbar titel. Kategorier 🔒 Security og 💹 Finance. Ikke listet i den læste del (resten er modelresumé).
- modelcontextprotocol/servers har ingen community-liste; den henviser til MCP Registry.

### PR-tekst 1: punkpeye, Lookproof (indsendt som #20345)

Den indsendte linje har 🎖️ (official implementation) foran 🐍, Glama-badge og en beskrivelse med 23 read-only tools; teksten herunder er det oprindelige forslag.

Titel: `Add Lookproof (DNS and email security checks) 🤖🤖🤖`

Linje under 🔒 Security (indsættes alfabetisk; præcis emoji-legende og Glama-badge skal kontrolleres mod listens nuværende poster):

```
- [lookproof/x402-examples](https://github.com/lookproof/x402-examples/tree/master/mcp-server) 🐍 ☁️ - DNS and email security checks for AI agents: SPF, DKIM, DMARC, MTA-STS, DNSSEC, TLS and HTTP security headers, with a fix for every finding. Free API key (250 credits a month) or pay per call in USDC on Base via x402. Local (`uvx lookproof-mcp`) or hosted at https://api.lookproof.dev/mcp.
```

Beskrivelse:

```
Adds lookproof-mcp (PyPI, MIT), 23 read-only tools for DNS, mail-authentication, TLS and HTTP checks of public domains. Every tool carries readOnlyHint. Also listed in the official MCP Registry as io.github.lookproof/lookproof-mcp.
Placed under Security in alphabetical order.
```

### PR-tekst 2: punkpeye, SwapHunt

Titel: `Add SwapHunt (Hyperliquid market context, prediction-market fees) 🤖🤖🤖`

Linje under 💰 Finance & Fintech:

```
- [swaphunt/x402-examples](https://github.com/swaphunt/x402-examples/tree/main/mcp-server) 🐍 🏠 - 30 crypto market tools computed from Hyperliquid perpetuals (prices, BTC regime, chop, volatility, funding, anti-FOMO checks), paid per call in USDC on Base via x402 with a spending cap and dry run by default. One free local tool, `pm_fees`, computes exact Kalshi and Polymarket trading fees.
```

Beskrivelse:

```
Adds swaphunt-mcp (PyPI, MIT, `uvx swaphunt-mcp`). Dry run by default: no payment without X402_PAY=1 and a wallet key. Also in the official MCP Registry as io.github.swaphunt/swaphunt-mcp.
```

Hvis ejeren vil nævne den hostede prøve (`https://api.swaphunt.dev/mcp`, 6 gratis tools), skal URL-status først afklares (se afsnittet om uoverensstemmelse ovenfor), og linjen skifter 🏠 til 🏠 ☁️.

### PR-tekst 3 og 4: appcypher (udgået: repoet er arkiveret)

En PR pr. forslag. Titler: `Add Lookproof` (Security, nederst i kategorien) og `Add SwapHunt` (Finance, nederst). Samme beskrivelser som ovenfor, uden emoji-legende udover det, listen bruger. Kontrollér format mod kategoriens nuværende poster.

## Claudes connector-katalog

- Indsendelse: https://claude.ai/directory/manage → "Submit new" → "MCP connector" (kilder: claude.com/docs/connectors/building/submission.md og claude.com/docs/directory/publish.md).
- Krav: betalt plan (Pro, Max, Ultra, Team, Enterprise); på Team/Enterprise indsender en Owner. Serveren skal være remote over HTTPS. Auth: OAuth 2.0, eller ingen auth for offentlige data. Hvert tool skal have titel og `readOnlyHint` eller `destructiveHint`; ingen catch-all-tool; navne højst 64 tegn; beskrivelser må ikke ligne prompt-injection; hvert tool skal lykkes med gyldigt input. Privatlivspolitik-URL, offentlig dokumentation og supportkontakt kræves. Testes med MCP Inspector eller som custom connector.
- Review: automatisk scan, listes som "Community"; Anthropic kan eskalere til "Verified". Tidsplan er ikke fast; eskalering til `mcp-review@anthropic.com`. Rettelser sendes fra indsendelsens detaljeside og vises som afventende; slug er permanent; nyt visningsnavn kræver re-review.
- Regel: "No money transfer or crypto". Det gør SwapHunt (x402-betalinger, kryptomarkedsdata) til en tvivlsom kandidat og peger på, at kun den gratis hostede prøve kunne indsendes, og kun hvis reglen ikke rammer markedsdata. **Afklar med review-kriterierne, før der indsendes.**
- Lookproof: den hostede server har kun API-nøgle og en authless prøve; OAuth er "næste trin" (CLAUDE.md). Authless er tilladt for offentlige data, men en nøglebaseret fuld funktion kræver OAuth for at kunne bruges som login-connector. Mulig første indsendelse: den authless prøve (22 read-only tools med annotations). `lookproof.dev/agents` viser stadig "Hosted connector coming soon", så siden skal opdateres samtidig.
- Dokumentet siger intet om, at registry-listing er krævet; den er ikke en forudsætning.

### Indsendelsestekst: Lookproof (udkast til portalen)

- Navn: Lookproof
- Kort beskrivelse: "DNS, email-authentication and TLS checks for public domains: SPF, DKIM, DMARC, MTA-STS, BIMI, DNSSEC, HTTP security headers. Read-only; results are data, not instructions."
- Eksempler: "Why does mail from example.com fail DMARC?", "Check example.com's SPF record and lookup count", "Can someone spoof example.com?"
- Auth: ingen (gratis prøve, få kald om dagen pr. netværk); API-nøgle via Bearer til fuld brug.
- Data: kun offentlige DNS-/web-data om det domæne, brugeren spørger om; ingen persondata om brugeren gemmes i prøven.
- Support: support@lookproof.dev. Dokumentation: https://lookproof.dev/agents.

## Rettelser og åbne spørgsmål til ejeren

1. SwapHunt: er `api.swaphunt.dev/mcp` bevidst tændt? Opdatér `docs/hosted-mcp.md` (status "stadig 404" er forkert pr. 2026-11-21) og beslut `remotes` i `server.json`.
2. Lookproof på Glama: claim connectoren; sørg for at serverens README-snapshot og beskrivelse nævner den gratis nøgle.
3. `glama.json` i lookproof/x402-examples har kun `realninjadaddy` som maintainer.
4. Smithery og PulseMCP kunne ikke tjekkes herfra; tjek manuelt.
5. Claude-katalog: kryptoreglen og OAuth-kravet afgør, hvad der kan indsendes.
6. Betalte placeringer (mcp.so $39, MCP Market $29) er ejerens beslutning; de gratis veje er listet først.

## Kilder

- Glama: https://glama.ai/mcp/servers/lookproof/x402-examples og https://glama.ai/mcp/connectors/io.github.lookproof/lookproof-mcp
- mcp.so: https://mcp.so/submit; MCP Market: https://mcpmarket.com/submit
- Officielt registry: https://registry.modelcontextprotocol.io/v0/servers?search=lookproof og `?search=swaphunt`
- Claude: https://claude.com/docs/connectors/building/submission.md, https://claude.com/docs/directory/publish.md, https://claude.com/docs/connectors/building/review-criteria.md, https://claude.com/docs/connectors/building/managing-your-listing.md
- Awesome: https://github.com/punkpeye/awesome-mcp-servers (CONTRIBUTING.md), https://github.com/appcypher/awesome-mcp-servers (CONTRIBUTING.md)
- PyPI: https://pypi.org/project/lookproof-mcp/ (0.2.1), https://pypi.org/project/swaphunt-mcp/ (0.8.1)

---

# Udvidelse (2026-11-23): flere gratis steder at blive listet

Kun rapport. Intet er indsendt, ingen konti oprettet. Tjekket 2026-11-23: `gh pr list`/PR-listen (ingen åbne PR'er rører dette dokument; #11 og #8 er andre emner) og `git log origin/master` (HEAD `773e4b5`, PR #13 merget). Allerede dækket og derfor ikke gentaget: officielt MCP Registry, Glama, mcp.so, MCP Market, Smithery, PulseMCP, mcptry, mcprush, punkpeye/appcypher awesome-mcp-servers, Claudes connector-katalog.

## Metode og begrænsninger

- **Læst direkte:** README/CONTRIBUTING via `raw.githubusercontent.com` (hele filen er søgt efter `lookproof` og `swaphunt`: 0 hits i alle nedenfor, med forbehold for at README'er kan være indeks over undersider), GitHub-søgning for stjerner, seneste push og arkivering, samt mcp.so, mcpmarket.com, glama.ai (200 OK).
- **Kun fra websøgning (sekundær kilde, ikke læst på kildesiden):** markeret *søgning*. Skal bekræftes, før nogen handler.
- **Netværket blokerede** (403/DNS): cursor.directory, mcpservers.org, lobehub.com, x402.org, agentic.market, x402scan.com, docs.cline.bot, zed.dev, docs.continue.dev, librechat.ai, goose-docs.ai, apify.com, huggingface.co, composio.dev, docs.docker.com, github.com (web), samt alle sammenligningsguider (apideck, geekflare, tallyfy, manufact, dynomapper, saascity). Disse er **ikke tjekket**; hvor tabellen alligevel har oplysninger, stammer de fra søgeresultater eller fra README'er på GitHub, og det står i kolonnen.
- Værdi (høj/mellem/lav) er et skøn ud fra stjerner og kendt rækkevidde, ikke målt trafik. Stjerner og push-datoer er fra GitHub-søgning 2026-11-23.
- Hverken Lookproof eller SwapHunt blev fundet i nogen af stederne nedenfor (for GitHub-lister: 0 hits i README). For sites uden læsning: ukendt.

## A. Henter automatisk eller kræver ingen ekstra indsendelse

Lookproof står i det officielle registry (0.2.1, med remote). SwapHunt står der kun med PyPI/stdio.

| Navn | URL | Type | Pris | Hvordan | Står vi der? | Aktivitet | Værdi |
|---|---|---|---|---|---|---|---|
| GitHub MCP Registry | github.com/mcp | Katalog (GitHub) | Gratis | Automatisk fra officielt MCP Registry (*søgning*: GitHub-blog, sept. 2025; nuværende adfærd ikke bekræftet). Intet at gøre. | Ukendt (siden blokeret) | Aktiv (GitHub-produkt) | Høj |
| VS Code MCP-galleri (`@mcp`) | code.visualstudio.com | Klientkatalog | Gratis | Via GitHub MCP Registry, dvs. indirekte fra officielt registry (*søgning*). Intet at gøre. | Ukendt | Aktiv | Høj |
| Zed (MCP via registry) | zed.dev/docs/extensions/mcp-extensions | Klientkatalog | Gratis | *Søgning*: Zed udfaser MCP-udvidelser til fordel for det officielle registry. Derfor ingen egen indsendelse nødvendig. Gammel vej: PR med submodule til `zed-industries/extensions` (1.981 stjerner, push 2026-11-21). | Nej (ingen Zed-udvidelse); registry-vejen ukendt | Aktiv | Mellem |
| Agentic.Market og CDP x402 Bazaar | agentic.market | x402-katalog | Gratis | *Søgning* (Coinbase-dokumentation): automatisk indeksering, når CDP-facilitatoren afvikler en betaling på et endpoint med Bazaar-discovery-extension slået til og metadata deklareret pr. route. Kræver kode (extension), ikke en formular. | Ukendt (blokeret) | Lanceret 2026-04-20; Bazaar siden sept. 2025 | Høj for x402-fokus |
| rdmgator12/awesome-claude-connectors | github.com/rdmgator12/awesome-claude-connectors | Awesome-liste | Gratis | Sporer Claudes katalog ugentligt; kommer med efter en indsendelse dér. Vi står der ikke (0 hits). | Nej | 170 stjerner, push 2026-11-23 | Lav |

## B. Sorteret efter værdi og indsatslethed

Indsats: **1** = én PR/formular uden konto ud over GitHub; **2** = kræver ekstra krav (badge, test, stjerne); **3** = kræver kode eller konto med afklaring.

| # | Navn | URL | Type | Pris | Hvordan, GitHub-rettigheder | Står vi der? | Aktivitet | Værdi | Indsats |
|---|---|---|---|---|---|---|---|---|---|
| 1 | punkpeye/awesome-remote-mcp-servers | github.com/punkpeye/awesome-remote-mcp-servers | Awesome-liste (kun hostede servere) | Gratis | PR (fork). Kræver: endpoint svarer på `initialize` (CI tjekker), brugbar af alle, Streamable HTTP/SSE, **og Glama-connector-badge på hver post**. Prioriterer PR'er med backlink til Glama-connector. Lookproof-connectoren findes men er ikke claimet (se hovedrapporten). Hostede `api.lookproof.dev/mcp` passer; SwapHunts først når afklaret. | Nej (0 hits i 783 KB README) | 3.841 stjerner, push 2026-11-22 | Høj | 2 |
| 2 | docker/mcp-registry (Docker MCP Catalog) | github.com/docker/mcp-registry | Registry/katalog (Docker Desktop, Docker Hub `mcp/`) | Gratis | PR med `server.yaml` under `servers/` (lokal server kræver Dockerfile, og Lookproof har en til Glama; remote servere er tilladt uden Dockerfile). Teamet reviewer hver PR; testnøgler deles via formular. Licens skal være MIT/Apache (vores er MIT). Docker-kataloget bygger og hoster billedet. | Nej (ikke søgt i `servers/`, kun repoet set via søgning) | 589 stjerner, push 2026-11-23 | Høj | 2 |
| 3 | mcpservers.org (wong2) | mcpservers.org/submit | Katalog + awesome-liste | Gratis; *søgning* nævner $39 som betalt hurtigspor | Formular (README: "We do not accept PRs"). Ingen GitHub-rettighed nødvendig. Siden blokeret. | Nej (0 hits i README; hjemmesiden ikke tjekket) | wong2/awesome-mcp-servers: 4.417 stjerner, push 2026-07-13 | Høj | 1 |
| 4 | TensorBlock MCP Index | github.com/TensorBlock/awesome-mcp-servers | Awesome-liste + hostet søgbart index/API | Gratis | PR eller GitHub-issue-kø ("new server submissions", "profile claims" ifølge README). Ingen særlige rettigheder ud over GitHub. | Nej | 1.125 stjerner, push 2026-11-23 | Mellem | 1 |
| 5 | toolsdk-ai/toolsdk-mcp-registry (MCPSDK.dev) | github.com/toolsdk-ai/toolsdk-mcp-registry | Registry (Node-pakker) | Gratis | PR med én JSON-fil under `packages/<kategori>/`; **kræver stjerne på repoet fra indsenderkontoen**. README nævner, at agent-assisterede PR'er er velkomne. Pakker er npm-orienterede; en Python/PyPI-server passer måske ikke, afklar formatet først. | Nej | 305 stjerner, push 2026-11-23 | Mellem | 2 |
| 6 | cline/mcp-marketplace | github.com/cline/mcp-marketplace | Klientkatalog (Cline, ét-klik-installation) | Gratis | GitHub-issue med skabelonen `mcp-server-submission`: repo-URL, 400×400 PNG-logo og begrundelse; indsender skal have testet, at Cline kan installere ud fra README/`llms-install.md`. Kræver kun GitHub-konto. | Nej | 800 stjerner; repoets sidste push 2025-06-24, men nye indsendelses-issues 2026-11-23 (intake kører, behandlingstid ukendt) | Høj (Cline-brugere) | 2 |
| 7 | x402 Ecosystem (x402.org/ecosystem) | github.com/x402eco/website; github.com/x402-foundation/x402 | x402-katalog | Gratis | *Søgning*: PR med en JSON-fil `data/ecosystem/<kategori>/<projekt>.json` (navn, beskrivelse, URL, kategori, logo) plus logo i `public/logos/`. Om x402.org/ecosystem henter fra `x402eco/website` er **ikke bekræftet**; `coinbase/x402`s README henviser til demo-sidens README i `x402-foundation/x402` (6.822 stjerner, push 2026-11-20). Læs den før PR. | Nej (0 hits i x402-foundation README) | Aktiv | Høj for x402 | 2 |
| 8 | xpaysh/awesome-x402 | github.com/xpaysh/awesome-x402 | Awesome-liste (x402) | Gratis | PR, én ændring pr. PR, format `[Navn](link) - Beskrivelse.`; kun GitHub. | Nej (0 hits i 379 KB README) | 307 stjerner, push 2026-07-28 | Mellem | 1 |
| 9 | Recall-Kitchen/awesome-x402-mcp-services | github.com/Recall-Kitchen/awesome-x402-mcp-services | Awesome-liste (hostede MCP med x402) | Gratis | PR med én linje under rigtig sektion (alfabetisk). Krav: offentlig streamable-HTTP-MCP uden nøgle til `initialize`/`tools/list`, en betalt tool/route der giver HTTP 402 uden konto, "real product". **Udelukker** crypto/trading/DeFi/token-screens og x402-routere: **SwapHunt er sandsynligvis uden for**. Lookproofs betalingssti (402) skal kunne vises i PR-teksten; afklar om den hostede prøve returnerer 402 eller kvotefejl. Åbne PR'er behandles løbende. | Nej | 1 stjerne, push 2026-11-18, flere PR'er 2026-11-19 til 2026-11-23 | Lav (ny liste) men målrettet | 2 |
| 10 | Merit-Systems/awesome-agentic-commerce | github.com/Merit-Systems/awesome-agentic-commerce | Awesome-liste (x402, agentbetalinger) | Gratis | PR ("Contributions welcome via pull requests"); linker x402.org/ecosystem, x402scan m.fl. | Nej (0 hits) | Stjerner ikke tjekket (kom ikke frem i søgning) | Mellem | 1 |
| 11 | xpaysh/awesome-agentic-commerce | github.com/xpaysh/awesome-agentic-commerce | Awesome-liste | Gratis | PR; regler ikke læst. | Nej | 85 stjerner, push 2026-06-24 | Lav | 1 |
| 12 | payapi-market/awesome-x402-apis | github.com/payapi-market/awesome-x402-apis | Awesome-liste + API-katalog (PayAPI Market) | Gratis | Enten gratis formular på payapi.market/providers (kræver testbetaling der afvikles) eller PR mod `data/external.md` for x402-API'er, der ikke skal ligge på markedet (regler i CONTRIBUTING.md, ikke læst). | Nej | 1 stjerne, push 2026-11-22; 208 KB liste | Lav | 2 |
| 13 | michielpost/x402-dev (x402dev.com) | github.com/michielpost/x402-dev | Awesome-liste + udviklerportal | Gratis | PR til `Projects.md`; udgives på x402dev.com. | Nej | 5 stjerner, push 2026-11-20 | Lav | 1 |
| 14 | nohumans.directory | nohumans.directory | x402-opdagelseslag (REST + MCP) | Gratis (*README-tekst fra xpaysh*) | Indsendelse over HTTP/MCP ifølge listens tekst, ingen dashboard; kontakten genprøves hvert 15. minut. Siden blokeret, **ikke tjekket**. | Ukendt | Ukendt | Lav | 2 |
| 15 | soxoj/awesome-osint-mcp-servers | github.com/soxoj/awesome-osint-mcp-servers | Awesome-liste (OSINT; mange DNS/WHOIS-poster) | Gratis | PR (regler ikke læst). Lookproof er en ren DNS/mail/TLS-server, så det passer under domæne-/DNS-poster. | Nej (0 hits) | 554 stjerner, push 2026-11-22 | Mellem (målrettet) | 1 |
| 16 | Puliczek/awesome-mcp-security | github.com/Puliczek/awesome-mcp-security | Awesome-liste (MCP-sikkerhed) | Gratis | PR (regler ikke læst). Handler mest om sikkerhed *af* MCP, så fit er svagt. | Nej | 750 stjerner, push 2026-03-03 | Lav | 1 |
| 17 | MorDavid/awesome-cyber-security-mcp | github.com/MorDavid/awesome-cyber-security-mcp | Awesome-liste (cybersikkerhed) | Gratis | PR (regler ikke læst). | Nej | 107 stjerner, push 2026-02-28 | Lav | 1 |
| 18 | jaw9c/awesome-remote-mcp-servers | github.com/jaw9c/awesome-remote-mcp-servers | Awesome-liste (remote) | Gratis | PR efter README-retningslinjer. | Nej | 1.198 stjerner, push 2026-11-09 | Mellem | 1 |
| 19 | yzfly/Awesome-MCP-ZH | github.com/yzfly/Awesome-MCP-ZH | Awesome-liste (kinesisk, servere og klienter) | Gratis | PR; regler ikke læst. | Nej (0 hits i 443 KB) | 7.861 stjerner, push 2026-11-14 | Mellem (kinesisk publikum) | 1 |
| 20 | YuzeHao2023/Awesome-MCP-Servers | github.com/YuzeHao2023/Awesome-MCP-Servers | Awesome-liste | Gratis | PR; regler ikke læst. | Nej | 1.093 stjerner, push 2026-11-13 | Lav | 1 |
| 21 | apappascs/mcp-servers-hub | github.com/apappascs/mcp-servers-hub | Awesome-liste (tabel) | Gratis | PR; regler ikke læst. | Nej | 331 stjerner, push 2026-11-21 | Lav | 1 |
| 22 | demcp/awesome-web3-mcp-servers | github.com/demcp/awesome-web3-mcp-servers | Awesome-liste (web3) | Gratis | PR. Relevant for SwapHunt, men **stillestående**. | Nej | 616 stjerner, push 2025-05-22 | Lav | 1 |
| 23 | VoltAgent/official-mcp-servers | github.com/VoltAgent/official-mcp-servers | Awesome-liste ("officielle" servere fra selskaber) | Gratis | PR; kræver sandsynligvis, at serveren udgives af selskabet bag produktet (ikke læst). | Nej | 425 stjerner, push 2026-11-19 | Lav | 2 |
| 24 | mcp.directory | mcp.directory/submit | Katalog | *Ukendt* | *Søgning*: har en "Submit Server"-side. Siden blokeret, **ikke tjekket**. | Ukendt | Ukendt | Ukendt | ? |
| 25 | cursor.directory | cursor.directory/mcp/new | Klientkatalog (Cursor) | *Ukendt* | *Søgning*, to kilder der er uenige: formular med GitHub-login, eller PR mod katalogets repo. Siden blokeret, **ikke tjekket**. | Ukendt | Ukendt | Høj (formentlig) | ? |
| 26 | LobeHub MCP-marked | lobehub.com/mcp | Klientkatalog (LobeChat) | *Ukendt* | Søgning fandt ingen indsendelsesregler; siden blokeret. **Ikke tjekket.** | Ukendt | Ukendt | Mellem | ? |
| 27 | Goose-udvidelser | goose-docs.ai/extensions | Klientkatalog (Goose) | *Ukendt* | *Søgning*: Goose kan tilføje enhver MCP-server uden katalogplads; ingen indsendelsessti fundet. **Ikke tjekket.** | Ukendt | Ukendt | Lav | ? |
| 28 | LibreChat | librechat.ai/docs/features/mcp | Klient (konfig) | Gratis | *Søgning*: ingen egen liste; servere tilføjes i `librechat.yaml`. Der er intet at indsende. | n/a | n/a | n/a | n/a |
| 29 | Windsurf (Cascade) | docs.windsurf.com | Klient | Gratis | *Søgning*: ingen indsendelsessti fundet, kun konfigurationsfil. **Ikke tjekket** på kildesiden. | Ukendt | Ukendt | Ukendt | ? |
| 30 | Continue Hub | continue.dev | Klientkatalog (Continue) | *Ukendt* | Søgning gav ingen regler for at udgive en MCP-blok; repoet `continuedev/continue` har 36.541 stjerner (push 2026-11-23). **Ikke tjekket.** | Ukendt | Aktiv | Mellem | ? |
| 31 | JetBrains AI Assistant | jetbrains.com | Klient | *Ukendt* | Intet fundet; **ikke tjekket**. | Ukendt | Ukendt | Ukendt | ? |
| 32 | Composio (egen MCP-toolkit) | docs.composio.dev/docs/extending-sessions/custom-mcp | Agentplatform | Konto kræves (pris ikke tjekket) | *Søgning*: registrér MCP-URL som "custom toolkit"; synlig kun i eget projekt, **ingen offentlig listing**. Ikke en katalogplads. | Nej | Eksperimentel | Lav | 3 |
| 33 | Hugging Face Spaces med MCP | huggingface.co/docs/hub/spaces-mcp-servers | Agentregister | Gratis | *Søgning*: Gradio-Space med `launch(mcp_server=True)` får MCP-badge og er filtrérbar. Kræver en egen Space (en tynd wrapper om vores API); kræver HF-konto. | Nej | Aktiv | Mellem, men passer dårligt | 3 |
| 34 | LiteLLM MCP server submissions | docs.litellm.ai/docs/mcp_server_submissions | Gateway-katalog | *Ukendt* | Kun set som søgetræf; **ikke læst**. | Ukendt | Ukendt | Lav | ? |
| 35 | Apify Store, LlamaHub, LangChain-integrationer | apify.com, llamahub.ai, docs.langchain.com | Agent-/værktøjsregistre | *Ukendt* | **Ikke tjekket** (blokeret eller ingen resultater). Kræver formentlig en pakke/Actor/integrationskode, ikke en MCP-URL. | Ukendt | Ukendt | Ukendt | ? |

Ikke medtaget: **appcypher** (arkiveret, dækket), **punkpeye/awesome-mcp-clients** (6.643 stjerner, men kun klienter), **agentic-community/mcp-gateway-registry** og **docker/mcp-gateway** (selvhostede gateways, ikke offentlige kataloger), små x402-lister med få stjerner (fffilimonov/awesome-x402-servers 1, X402blockchains/awesome-x402 3, Rail402/awesome-rail402 12; stillestående eller uden tydelig vej), generelle AI-agent-lister (dipakkr/awesome-ai-engineering 22.620, caramaschiHG/awesome-ai-agents-2026 2.091, jim-schwoebel/awesome_ai_agents 2.031; handler om rammeværker, regler ikke læst), `buddies2705/awesome-blockchain-crypto-api` (1 stjerne). Betalte placeringer er heller ikke gentaget her (mcp.so $39, MCP Market $29 står i hovedrapporten; mcpservers.org $39 er kun *søgning*).

## Anbefalet rækkefølge (til ejerens beslutning)

1. **Claim Lookproof-connectoren på Glama først.** Det åbner `awesome-remote-mcp-servers` (#1), som kræver connector-badge, og giver backlink, de prioriterer.
2. **Gratis og hurtigt, kun GitHub:** #3 (formular), #4, #8, #10, #13, #15. Én PR eller formular hver.
3. **Med lidt arbejde:** #6 Cline (test, logo), #2 Docker (`server.yaml`), #5 toolsdk (stjerne, npm-format), #7 x402-økosystemet (læs foundation-README først).
4. **Intet at gøre:** sektion A følger det officielle registry. Her giver det værdi at tilføje `remotes` til SwapHunt (hovedrapportens punkt 1), så SwapHunt også dukker op i de registry-baserede kataloger.
5. **Bazaar/Agentic.Market** kræver kode (discovery-extension på x402-ruter) og en afviklet betaling; det er en udviklingsopgave, ikke en indsendelse.
6. **Tjek manuelt, når netværket tillader det:** #24 til #31 og #35.

## Kilder (denne udvidelse)

- GitHub-søgning (stjerner, push, arkiveret) og README/CONTRIBUTING via raw.githubusercontent.com for: punkpeye/awesome-remote-mcp-servers, wong2/awesome-mcp-servers, TensorBlock/awesome-mcp-servers, toolsdk-ai/toolsdk-mcp-registry, docker/mcp-registry, cline/mcp-marketplace, xpaysh/awesome-x402, Recall-Kitchen/awesome-x402-mcp-services, payapi-market/awesome-x402-apis, michielpost/x402-dev, Merit-Systems/awesome-agentic-commerce, soxoj/awesome-osint-mcp-servers m.fl.
- Websøgning (sekundær): https://docs.cdp.coinbase.com/x402/seller/get-discovered.md, https://www.coinbase.com/developer-platform/discover/launches/agentic-market, https://github.blog/ai-and-ml/github-copilot/meet-the-github-mcp-registry-the-fastest-way-to-discover-mcp-servers/, https://zed.dev/docs/extensions/mcp-extensions, https://huggingface.co/docs/hub/spaces-mcp-servers, https://docs.composio.dev/docs/extending-sessions/custom-mcp, https://github.com/x402eco/website.
