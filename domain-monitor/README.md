# Domain monitor

Checks a list of domains with Lookproof's domain health check and alerts you when SPF, DKIM, DMARC or MTA-STS changes or gets weaker. Made for a daily cron job: each run checks every domain once, compares the result with the previous run and keeps the latest result per domain in a small state file.

Alerts go to stdout, Discord, Telegram or email (any combination).

Cost: $0.08 per domain per run (`/v1/domain/health`), so 3 domains checked daily cost $0.24 a day, $7.20 per 30 days.

## What it compares

| Check | Compared | Counted as weaker |
|---|---|---|
| SPF | the record and its `all` qualifier | `-all` becomes `~all`, `?all`, no `all` or `+all`; the record disappears; the record becomes invalid (too many DNS lookups, syntax error, multiple records, include loop) |
| DKIM | keys found on common selectors (type, size, revoked, testing, a hash of the key) | a selector disappears, is revoked, its key gets shorter, or switches to testing |
| DMARC | the record, the policy that applies, `pct`, test mode, subdomain policy | `reject` becomes `quarantine` or `none`; `pct` drops; test mode switches on; the record disappears |
| MTA-STS | the record, policy id, mode, `max_age`, policy MX patterns | `enforce` becomes `testing` or `none`; the policy can no longer be fetched; an MX host is no longer covered; the record disappears |

Any other difference (a new SPF include, a rotated DKIM key, a new DMARC report address) is reported as `CHANGED`. Set `ALERT_ON=weaker` to alert only on `WEAKER`.

If one section of a check fails (for example a DNS timeout), it is reported as `UNKNOWN` and the previous value is kept, so a temporary failure never shows up as "record removed". DKIM is found by trying common selector names; a domain whose selector is not on that list shows "no DKIM key found" on every run, which is not a change.

The first run for a domain records a baseline and sends no alert.

## Setup

Use a dedicated wallet with a few dollars of USDC on Base mainnet. Never your main wallet.

```bash
cd domain-monitor
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# The wallet key in a file only you can read:
install -m 600 /dev/null ~/.lookproof-wallet.key
nano ~/.lookproof-wallet.key        # paste the private key, save

cp domains.example.txt domains.txt  # one domain per line
```

Copy [`../.env.example`](../.env.example) to `../.env` and fill in the monitor settings:

| Variable | Default | Effect |
|---|---|---|
| `DOMAINS` or `DOMAINS_FILE` | | Comma-separated domains, or a file with one per line. Arguments on the command line win. At most 50. |
| `X402_PAY` | off | Without `X402_PAY=1` (or `--pay`), the monitor shows the cost per run and stops. |
| `PRIVATE_KEY_FILE` / `PRIVATE_KEY` | | The wallet key: a file only you can read (recommended), or the key itself. |
| `MAX_SPEND_USD` | `0.10` | Spending cap per run. A run that would cost more is refused before anything is paid. Set it to at least $0.08 times the number of domains. |
| `STATE_FILE` | `.monitor-state.json` here | Latest result per domain (public DNS data only, mode 600). |
| `ALERT_ON` | `change` | `change` alerts on any difference; `weaker` only on weaker or unknown. |
| `DELIVERY` | `stdout` | Comma-separated: `stdout`, `discord`, `telegram`, `email`. |
| `DISCORD_WEBHOOK_URL` | | Discord channel webhook (Channel settings, Integrations, Webhooks). |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | | A bot from @BotFather and the chat it should write to. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM`, `MAIL_TO` | port `587` | Email via SMTP with STARTTLS (port 465: implicit TLS). |

Test the alert channels first. This is free: it calls no API and sends one test message.

```bash
set -a; . ../.env; set +a
.venv/bin/python monitor.py --test-alert
```

## Run

```bash
set -a; . ../.env; set +a
.venv/bin/python monitor.py                 # dry run: domains, price, cost per run
.venv/bin/python monitor.py --pay           # checks every domain once and pays
```

Dry run:

```
3 domains x $0.080 = $0.240 per run ($7.20 per 30 days if run daily). USDC on eip155:8453, payTo 0x<lookproof-address>
Dry run: nothing paid. Re-run with --pay (or X402_PAY=1) to check the domains.
```

First paid run (shape only, not yet verified against the live API; values depend on the domain):

```
3 domains x $0.080 = $0.240 per run ($7.20 per 30 days if run daily). USDC on eip155:8453, payTo 0x<lookproof-address>
example.com: baseline recorded
  SPF      -all (fail)
  DKIM     selector1 (rsa 2048 bit)
  DMARC    p=reject
  MTA-STS  mode=enforce max_age=604800
...
This run cost $0.240 (3 payments, last tx https://basescan.org/tx/0x<transaction-hash>)
```

A later run with changes (the alert text, sent to every channel in `DELIVERY`):

```
Lookproof monitor: 2 weaker, 1 changed, 0 not checked
[WEAKER] example.com DMARC: p=reject -> p=none
[WEAKER] example.com SPF: -all (fail) -> ~all (softfail)
[CHANGED] example.org DKIM: selector1 (rsa 2048 bit) -> selector1 (rsa 2048 bit), selector2 (rsa 2048 bit)
```

The exit code is 0 when every domain was checked and every alert was delivered, otherwise 1 (so cron can mail you about failures).

## Cron

Once a day at 06:17:

```cron
17 6 * * * cd /path/to/x402-examples/domain-monitor && set -a && . ../.env && set +a && X402_PAY=1 .venv/bin/python monitor.py >> monitor.log 2>&1
```

## Safety

- Every payment is locked to the amount, asset (USDC), network (Base) and `payTo` of the 402 response for that domain, and a quote above the documented $0.08 is refused.
- The whole run is checked against `MAX_SPEND_USD` before the first payment. A domain whose check fails after the payment was signed still counts toward the cap.
- Lookproof settles only when it returns a result, so a failed check (`503`) is not charged.
- DNS records are written by the owner of each domain. Alerts quote them as plain text (control characters removed, `@` mentions and backticks neutralized, length capped) and nothing in them is ever followed. Discord alerts are sent with mentions disabled; Telegram alerts without formatting.
- Error messages never include the Discord webhook URL or the Telegram bot token.
