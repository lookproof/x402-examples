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
