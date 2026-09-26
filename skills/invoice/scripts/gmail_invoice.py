# 從 Gmail 撈電子發票開立通知，解析出發票號碼／開立日期／賣方／捐贈註記，寫成 JSON 供對獎用。
# 全程唯讀：以 readonly 開收件匣、用 BODY.PEEK 讀信，不會把信標成已讀，也不刪、不寄、不改。
#
# 用法：
#   python gmail_invoice.py                 # 第一個帳號，近 200 天
#   python gmail_invoice.py main --days 400
#
# 產物：
#   - stdout：發票清單
#   - invoices_<標籤>.json（在資料夾裡）：結構化，給 invoice_check.py 對獎
import email
import html
import imaplib
import json
import os
import re
import sys
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime

import common

IMAP_HOST = "imap.gmail.com"
SEARCH_KEYWORDS = ("發票", "invoice", "電子發票")

# 台灣電子發票號碼：2 個大寫英文字軌 + 8 位數字（有些信會寫成 AB-12345678）
INV_RE = re.compile(r"\b([A-Z]{2})-?(\d{8})\b")


def dec(s):
    if not s:
        return ""
    out = []
    for part, enc in decode_header(s):
        if isinstance(part, bytes):
            try:
                out.append(part.decode(enc or "utf-8", "replace"))
            except LookupError:
                out.append(part.decode("utf-8", "replace"))
        else:
            out.append(part)
    return "".join(out)


def to_text(msg):
    plain, rich = "", ""
    parts = msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        ctype = part.get_content_type()
        if ctype not in ("text/plain", "text/html"):
            continue
        if "attachment" in str(part.get("Content-Disposition")):
            continue
        try:
            body = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
        except Exception:
            continue
        if ctype == "text/plain" and not plain:
            plain = body
        elif ctype == "text/html" and not rich:
            rich = body
    text = plain or rich
    if not plain and rich:
        text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
        text = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</td>", "\n", text)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
    return "\n".join(ln.strip() for ln in text.splitlines() if ln.strip())


def parse_invoice_mail(msg, uid=""):
    """從一封信抽出發票資料；不是發票通知就回空清單。"""
    subject = dec(msg.get("Subject"))
    name, addr = parseaddr(dec(msg.get("From")))
    text = to_text(msg)
    # 只認「發票號碼」附近的號碼，避免把訂單編號、驗證碼誤當發票
    anchored = re.findall(r"發票號碼[^A-Z0-9]{0,12}([A-Z]{2})-?(\d{8})", text)
    hits = anchored or (INV_RE.findall(text) if "發票" in text else [])
    if not hits:
        return []
    try:
        when = parsedate_to_datetime(msg.get("Date")).strftime("%Y-%m-%d")
    except Exception:
        when = ""
    issued = re.search(r"開立時間[^0-9]{0,6}(\d{4}[/-]\d{1,2}[/-]\d{1,2})", text)
    amount = re.search(r"(?:總計|金額|合計)[^0-9]{0,6}([0-9,]+)", text)
    donated = "已捐贈" in text or "捐贈碼" in text
    carrier = re.search(r"(手機條碼|會員載具|自然人憑證)", text)
    rows = []
    for pre, num in hits:
        rows.append({
            "uid": uid,
            "number": pre + num,
            "prefix": pre,
            "digits": num,
            "mail_date": when,
            "issued_date": (issued.group(1).replace("-", "/") if issued else when.replace("-", "/")),
            "seller": name or addr,
            "subject": subject,
            "donated": donated,
            "carrier": carrier.group(1) if carrier else "",
            "amount": amount.group(1) if amount else "",
        })
    return rows


def gm_search(M, raw):
    """X-GM-RAW 搜尋；中文關鍵字要走 literal + CHARSET UTF-8，否則 imaplib 會 ascii 編碼失敗。"""
    M.literal = raw.encode("utf-8")
    typ, data = M.uid("SEARCH", "CHARSET", "UTF-8", "X-GM-RAW")
    return data[0].split() if data and data[0] else []


def main():
    args = sys.argv[1:]
    days = 200
    if "--days" in args:
        i = args.index("--days")
        days = int(args[i + 1])
        del args[i:i + 2]
    acc = common.pick_account(args[0] if args else None)
    pw = acc.get("app_password", "").replace(" ", "")
    if not pw:
        sys.exit(f"{acc['label']} 還沒設定應用程式密碼，請在自己的終端機執行 account.py add")

    M = imaplib.IMAP4_SSL(IMAP_HOST)
    try:
        M.login(acc["email"], pw)
    except imaplib.IMAP4.error as e:
        sys.exit(f"Gmail 拒絕登入 {acc['email']}（{e}）。\n"
                 "通常是應用程式密碼錯了或已失效：改過 Google 密碼、重設兩步驟驗證都會讓舊的應用程式密碼作廢。\n"
                 "到 https://myaccount.google.com/apppasswords 重新產生一組，再執行 account.py add 覆蓋。")
    M.select("INBOX", readonly=True)

    uids = set()
    for kw in SEARCH_KEYWORDS:
        for u in gm_search(M, f"{kw} newer_than:{days}d"):
            uids.add(u)

    rows, seen_numbers = [], set()
    for uid in sorted(uids, key=lambda x: int(x)):
        typ, md = M.uid("fetch", uid, "(BODY.PEEK[])")
        if not md or not md[0]:
            continue
        for r in parse_invoice_mail(email.message_from_bytes(md[0][1]), uid.decode()):
            if r["number"] in seen_numbers:
                continue
            seen_numbers.add(r["number"])
            rows.append(r)
    M.logout()

    rows.sort(key=lambda r: r["issued_date"])
    out = common.invoices_file(acc["label"])
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(json.dumps({"account": acc["email"], "days": days, "invoices": rows},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, out)
    print(f"# {acc['label']} <{acc['email']}>：近 {days} 天找到 {len(rows)} 張電子發票\n")
    for r in rows:
        flag = "（已捐贈，不參加對獎）" if r["donated"] else ""
        print(f"{r['issued_date']}  {r['number']}  {r['seller'][:22]}{flag}")
    print(f"\n（結構化資料已寫入 {out}）")


if __name__ == "__main__":
    main()
