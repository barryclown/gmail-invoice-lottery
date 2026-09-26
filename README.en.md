# gmail-invoice-lottery — check Taiwan's invoice lottery from your Gmail

**English** | [繁體中文](README.md)

Every receipt in Taiwan (a uniform invoice, 統一發票) doubles as a lottery ticket, drawn every two months.
Online shops, delivery apps and stores like Steam email you an e-invoice notice when they issue one.
This Claude Code skill pulls the invoice numbers out of those emails, matches them against the winning
numbers published by the Ministry of Finance, and tells you whether anything won and whether it can
still be claimed. Just say "check my invoices" (or 對發票).

## What it looks like

(The numbers below are made up.)

```
You:    check my invoices

Claude: One invoice from the Jul–Aug period won the sixth prize, NT$200. You can claim it from
        Oct 6; the deadline is Jan 5, 2027. Three others were donated, so they don't enter the
        draw, and the September one is drawn on Nov 25. This only covers invoices that came by
        email; ones on a mobile barcode carrier need the MOF invoice app.
```

What the scripts actually print, which Claude then summarises as above (output is in Chinese):

```
# 對獎結果（you@gmail.com）
共 12 張；實際對獎 8 張（捐贈 3 張不參加、尚未開獎 1 張、期別過期或無資料 0 張）

## 中獎 1 張，其中還能領的 1 張、合計 NT$200

- AB12345835｜六獎 NT$200｜2026/08/03 某電商
  期別 115年07-08月｜2026-10-06 起可領，2027-01-05 截止

## 各期領獎期限
- 115年07-08月：2026-10-06 ~ 2027-01-05（尚未開放領獎）
- 115年05-06月：2026-08-06 ~ 2026-11-05（可領獎）

## 尚未開獎（1 張）
- 2026/09/22 CD13572468 某外送平台（2026-11-25 開獎）
```

## Four things worth knowing

- **Your mailbox is read-only to it.** The Inbox is opened read-only, reading a message doesn't mark it as
  read, and nothing is deleted, moved or sent.
- **The password never enters the chat.** You type the Gmail app password into your own terminal, where it
  isn't echoed. The AI never sees it.
- **Winning numbers come from the official feed, not from AI memory.** Every run fetches the latest numbers
  from the Ministry of Finance RSS feed. If that fails, it stops and says so, instead of letting the model
  guess "you won" or "you didn't".
- **It tells you what changes the answer**: which invoices were donated and don't enter the draw, which
  periods haven't been drawn yet (with the draw date), which wins are past their claim window, and which
  invoices were never in your mailbox to begin with.

## How it works

It is a skill (a set of instructions the AI follows) plus a few small Python scripts. When you ask, Claude
runs them in order:

| Step | Script | What it does |
| --- | --- | --- |
| 1 | `update_winning_numbers.py` | Fetches recent winning numbers from the official MOF RSS feed and works out each period's claim window |
| 2 | `gmail_invoice.py` | Connects to Gmail over read-only IMAP, finds mail from the last 200 days mentioning an invoice, and extracts the number, date, seller and donation flag |
| 3 | `invoice_check.py` | Matches each invoice against its period's numbers and works out what won and whether it can still be claimed |

The matching is done by the script, not the AI. The AI runs the scripts and explains the result.

## Install and use

### 1. What you need

- Python 3.8+. Standard library only; nothing to `pip install`.
- Claude Code (desktop app or CLI). Codex and other tools that read Agent Skills work too; see Method B.
- 2-Step Verification turned on for the Gmail account (app passwords require it).

### 2. Install (pick one)

**Method A: as a Claude Code plugin (recommended).** In Claude Code, type:

```
/plugin marketplace add barryclown/gmail-invoice-lottery
/plugin install gmail-invoice-lottery@gmail-invoice-lottery
```

Then restart Claude Code.

If the first line fails with `Host key verification failed` or `SSH host key is not in your known_hosts`,
the `owner/repo` shorthand is cloning over SSH and your machine has no GitHub SSH setup. Use the full URL instead:
`/plugin marketplace add https://github.com/barryclown/gmail-invoice-lottery.git`

**Method B: drop it into your skills folder**

```bash
git clone https://github.com/barryclown/gmail-invoice-lottery.git   # or Code → Download ZIP on GitHub
```

Copy the `skills/invoice` folder to `~/.claude/skills/invoice` (on Windows, `C:\Users\<you>\.claude\skills\invoice`).
For Codex, copy it to `~/.codex/skills/invoice`.

### 3. Add your Gmail account (you do this in your own terminal)

1. Create an app password at <https://myaccount.google.com/apppasswords>; any name will do, e.g. `invoice`.
   It is 16 letters and **not your Google sign-in password**.
2. Run this and paste the app password when asked:

```bash
python <skill folder>/scripts/account.py add main you@gmail.com
```

`main` is a label you can use later to pick an account. Add each mailbox once with its own label.

Where the skill folder is: with Method A, `~/.claude/plugins/cache/gmail-invoice-lottery/gmail-invoice-lottery/<version>/skills/invoice`;
with Method B, wherever you copied it. If in doubt, ask Claude to check your invoices and it will print
the full command for you.

### 4. Check it works

- Ask Claude Code to check your invoices; it should run the three scripts in order and report.
- With Method B you can also run `python selftest.py` in the cloned folder. It needs no network and no
  mailbox; all 38 checks should pass.

### 5. Everyday use

- After each draw (the 25th of every odd month), ask it to check your invoices.
- Several accounts: "check my invoices on the work account". Without a label it uses the first account you added.
- Older mail: "check my invoices, go back 400 days".
- You can also run the three scripts yourself in a terminal, without the AI; see the table in How it works.

### 6. Update and remove

- Method A: update with `/plugin marketplace update gmail-invoice-lottery`; remove with `/plugin uninstall gmail-invoice-lottery@gmail-invoice-lottery`
- Method B: update with `git pull` and copy again; remove by deleting `~/.claude/skills/invoice`
- Either way, delete `~/.gmail-invoice-lottery/` yourself afterwards and revoke the app password at
  <https://myaccount.google.com/apppasswords>.

### 7. Common problems

- **"Gmail 拒絕登入" / `AUTHENTICATIONFAILED Invalid credentials`**: the app password is mistyped or has been
  revoked. Changing your Google password or resetting 2-Step Verification revokes existing app passwords.
  Create a new one and run `account.py add` again.
- **One shop's invoices never show up**: its emails don't contain the 發票號碼 label, or they aren't in the
  Inbox (archived or moved by a filter). See Limitations.
- **The plugin won't install**: see step 2 and use the full HTTPS URL.

## Privacy and security

**Where data lives**: on your machine only, in `~/.gmail-invoice-lottery/` by default (override with the
`INVOICE_DATA_DIR` environment variable). It sits outside the skill folder so a plugin update doesn't wipe it.

| File | Contents |
| --- | --- |
| `accounts.json` | account labels, addresses and app passwords (plain text) |
| `invoices_<label>.json` | extracted invoices: number, date, seller, email subject, amount, carrier, donated or not |
| `winning_numbers.json` | recent winning numbers and claim windows |

The app password is stored in plain text, so any program that can read your user folder can read it. That
is why this uses an app password rather than your Google password: it can only fetch mail, and you can
revoke it on its own at any time without touching your account.

**What it connects to**: the scripts themselves only reach `imap.gmail.com` (mail), `invoice.etax.nat.gov.tw`
and `www.etax.nat.gov.tw` (winning numbers). No other servers, no telemetry. Only if you set
`INVOICE_DNS_FALLBACK=1` does it ask Google Public DNS (8.8.8.8) when your local DNS fails to resolve a host.
Beyond that, when you use it through an AI such as Claude, whatever the scripts print (your address, invoice
numbers, sellers, dates) enters the conversation, which means it goes to the AI service you use; the password
never appears in any output. If that bothers you, run the three scripts yourself in a terminal instead.

**Which mail it reads**: Inbox messages from the last N days (200 by default) that mention 發票, invoice or
電子發票. Messages are parsed in memory; only the invoice fields in the table above are saved, never the
message body.

**What it never does**: mark mail as read, delete, move, send, or change Gmail settings.

## Prize rules

| Prize | Amount (NT$) | Condition |
| --- | --- | --- |
| Special prize (特別獎) | 10,000,000 | all 8 digits match |
| Grand prize (特獎) | 2,000,000 | all 8 digits match |
| First prize (頭獎) | 200,000 | all 8 digits match one of the three first-prize numbers |
| Second to sixth | 40,000 / 10,000 / 4,000 / 1,000 / 200 | last 7 / 6 / 5 / 4 / 3 digits match a first-prize number |
| Extra sixth (增開六獎) | 200 | last 3 digits match an extra number (only in periods that open one) |

The special and grand prizes only pay on a full eight-digit match, never on the last few digits. Donated
invoices don't enter the draw.

## Limitations

- **It only sees invoices that were emailed.** Invoices stored on a mobile barcode carrier without a
  notification email aren't here; use the Ministry of Finance invoice app for those.
- Only the Inbox is searched. Archived mail, or mail a filter moved out of the Inbox, isn't found.
- Numbers are found by the 發票號碼 ("invoice number") label in the email. Shops with unusual formats may be missed.
- Invoices whose buyer is a business, government agency, state-owned enterprise, public school or the military
  (usually ones printed with that buyer's tax ID) can't be redeemed under Article 11 of the
  [Uniform Invoice Prize Regulations](https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=G0340083). The scripts don't detect them.
- Claim windows are computed as three months from the 6th of the month after the draw. The ministry extends
  deadlines that fall on holidays; its announcement is authoritative.
- Tested on Windows only. It uses only the Python standard library, so macOS and Linux should work, but that
  is unverified.
- Script output and code comments are in Traditional Chinese.
- **The Ministry of Finance announcement is authoritative.** This is a cross-checking aid; verify against the
  invoice itself before claiming.

## Licence

MIT. See [LICENSE](LICENSE).
