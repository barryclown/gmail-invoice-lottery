---
name: invoice
description: Check Taiwan uniform-invoice (統一發票) lottery results by scanning the e-invoice notification emails in the user's Gmail and matching them against the Ministry of Finance winning numbers. Use when the user asks to 對發票, 對獎, 查發票中獎, 統一發票有沒有中, check invoices, or invokes /invoice. Runs locally over read-only IMAP; winning numbers come from the official MOF RSS feed, never from model memory.
---

# Uniform invoice lottery check

Taiwan draws the uniform-invoice lottery on the 25th of every odd month, covering the two preceding months. Many shops email an e-invoice notification, so the check can be automated: refresh the winning numbers, extract invoice numbers from mail, compare.

Run the steps below and report. Don't ask clarifying questions first; the defaults fit almost every request.

## Where things are

- Scripts: the `scripts/` folder next to this file. Use this skill's base directory as the working directory.
- Data (accounts, winning numbers, extracted invoices): `~/.gmail-invoice-lottery/`, or `$INVOICE_DATA_DIR` if set. It lives outside the skill folder so a plugin update doesn't wipe it.

## First run: no account yet

If `python scripts/account.py list` says no account is set up, stop and tell the user to run this **in their own terminal**:

```
python <this skill's base directory>/scripts/account.py add <label> <their Gmail address>
```

It prompts for a Gmail app password (created at https://myaccount.google.com/apppasswords, which requires 2-Step Verification) without echoing it. Never ask the user to paste the app password into the chat, and never write one to disk yourself. If they paste one anyway, don't repeat it; point them to `account.py add`.

## Capability gate

Required: run local Python 3.8+, write to the data folder, and reach `imap.gmail.com` and `invoice.etax.nat.gov.tw` over the network. If one of these fails after one safe attempt, stop, say this client can't run the check, and report no result. **Never guess or reconstruct winning numbers from memory.** Model memory is stale by definition, and a wrong "you won" or "you lost" is the one failure that matters here.

## Parameters

- Account: a label from `account.py list`. No label means the first account. Pass the label through unchanged.
- Lookback: `--days 200` (the default) covers the current period plus every period still inside its claim window. Go larger only if the user asks to dig through older mail.

## Run

From this skill's base directory, in order, stopping at the first hard failure:

```
python scripts/update_winning_numbers.py
python scripts/gmail_invoice.py [label] --days 200
python scripts/invoice_check.py [label]
```

- Claude Code (Bash tool): prefix each with `cd "<base directory>" && `.
- Windows PowerShell 5.1 (Codex, others): `Set-Location` once, then run them one at a time (no `&&` in 5.1).

Step 1 failing on the network alone is recoverable: if `winning_numbers.json` already has the period the invoices fall into, continue and say the numbers weren't refreshed this run. Step 2 failing with "Gmail 拒絕登入" means the app password is wrong or revoked; relay the script's instructions, don't retry.

## Report

Answer in the user's language (Traditional Chinese by default). Lead with the verdict: did anything win, and how much can actually be claimed. Then the breakdown, kept to what the user needs to act on.

Always state these, because each one silently changes the answer:

- Donated invoices (`已捐贈`) don't enter the draw and are excluded.
- Invoices from a period not drawn yet are pending; give the draw date (the script prints it).
- An invoice whose claim window has closed can't be redeemed even if it won. Say so instead of counting it.
- This only covers invoices that arrived as email. Purchases stored on a 手機條碼載具 without a notification email are outside this check; the MOF 統一發票兌獎 app covers those. Mention this whenever reporting "nothing won", so the result isn't mistaken for a full sweep.

For a win, give the invoice number, prize tier, amount, seller and claim deadline. Never round or embellish an amount.

## Pitfalls

- The scripts open Gmail read-only (`readonly=True`, `BODY.PEEK`) and never mark mail as read, delete, move or send. Keep it that way.
- Invoice numbers are two uppercase letters plus eight digits. Extraction anchors on the literal 發票號碼 label; loosening that regex starts matching order numbers and verification codes.
- Prize tiers match the three 頭獎 numbers by trailing digits (7 → 二獎 down to 3 → 六獎). 特別獎 and 特獎 only pay on a full eight-digit match, never on a tail. 增開六獎 only exists in periods that opened one.
- Only the Inbox is searched. Mail that was archived or filtered out of the Inbox is not found.
- An invoice whose buyer is a business, government agency, state-owned enterprise, public school or the military (typically one printed with that buyer's 統一編號) can't be redeemed under Article 11 of the 統一發票給獎辦法. The scripts don't detect these; if the user bought something on a company tax ID, remind them.
- All files are UTF-8. The scripts reconfigure stdout themselves on Windows.
- If IMAP fails on DNS resolution, set `INVOICE_DNS_FALLBACK=1` to retry resolution through 8.8.8.8. A failure after that is a real network or credential problem.
