# 不連網、不碰真實信箱的自測：對獎規則、開獎日與領獎期、RSS 解析、信件抽號碼、整段對獎輸出。
# 用法：python selftest.py
import datetime
import email
import json
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
SCRIPTS = HERE / "skills" / "invoice" / "scripts"
sys.path.insert(0, str(SCRIPTS))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

import gmail_invoice  # noqa: E402
import invoice_check  # noqa: E402
import update_winning_numbers as uwn  # noqa: E402

results = []


def check(name, cond, detail=""):
    results.append(cond)
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  → {detail}"))


# ---------- 對獎規則 ----------
P = {"special": "12345678", "grand": "87654321", "first": ["11112222", "33334444", "55556666"],
     "increased_sixth": ["777"]}
cases = [
    ("12345678", "特別獎", 10000000),
    ("87654321", "特獎", 2000000),
    ("33334444", "頭獎", 200000),
    ("93334444", "二獎", 40000),
    ("99334444", "三獎", 10000),
    ("99934444", "四獎", 4000),
    ("99994444", "五獎", 1000),
    ("99999444", "六獎", 200),
    ("99999777", "增開六獎", 200),
    ("02345678", None, 0),   # 特別獎只認 8 位全同，末 7 碼相同不算
    ("07654321", None, 0),   # 特獎同理
    ("99999999", None, 0),
]
for digits, want, prize in cases:
    got = invoice_check.match(digits, P)
    check(f"match {digits} → {want}", got == (want, prize), got)

# ---------- 開獎日 ----------
for ym, want in [("2026/07", "2026-09-25"), ("2026/08", "2026-09-25"), ("2026/09", "2026-11-25"),
                 ("2026/11", "2027-01-25"), ("2026/12", "2027-01-25")]:
    check(f"next_draw {ym}", invoice_check.next_draw(ym) == want, invoice_check.next_draw(ym))

# ---------- 領獎期間 ----------
for draw, want in [(datetime.date(2026, 9, 25), ("2026-10-06", "2027-01-05")),
                   (datetime.date(2026, 11, 25), ("2026-12-06", "2027-03-05")),
                   (datetime.date(2027, 1, 25), ("2027-02-06", "2027-05-05"))]:
    check(f"claim_window {draw}", uwn.claim_window(draw) == want, uwn.claim_window(draw))

# ---------- RSS 解析 ----------
RSS = """<rss><channel>
<item><title><![CDATA[115年 07~08月]]></title>
<link><![CDATA[https://www.etax.nat.gov.tw/etw-main/ETW183W2_11507/]]></link>
<description><![CDATA[<p>特別獎：12345678</p><p>特獎：87654321</p><p>頭獎：11112222、33334444、55556666</p>]]></description>
<pubDate>Fri, 25 Sep 2026 12:00:00 +0800</pubDate></item>
<item><title><![CDATA[115年 11~12月]]></title>
<description><![CDATA[<p>特別獎：11111111</p><p>特獎：22222222</p><p>頭獎：33333333、44444444、55555555</p>]]></description>
<pubDate>not a date</pubDate></item>
<item><title><![CDATA[115年 05~06月]]></title>
<description><![CDATA[<p>特別獎：11111111</p><p>頭獎：33333333</p>]]></description></item>
</channel></rss>"""
periods, skipped = uwn.parse_rss(RSS, fetch_sixth=lambda url: [])
by = {p["period"]: p for p in periods}
check("RSS 抓到兩期完整資料", set(by) == {"115年07-08月", "115年11-12月"}, list(by))
check("RSS 欄位不完整的期別被略過", skipped == ["115年05-06月"], skipped)
p78 = by.get("115年07-08月", {})
check("RSS 號碼正確", p78.get("special") == "12345678" and p78.get("first") == ["11112222", "33334444", "55556666"], p78)
check("RSS 領獎期由 pubDate 算", (p78.get("claim_start"), p78.get("claim_end")) == ("2026-10-06", "2027-01-05"), p78)
p1112 = by.get("115年11-12月", {})
check("pubDate 壞掉時 11-12 月期別跨年推開獎日", p1112.get("draw_date") == "2027-01-25", p1112.get("draw_date"))


# ---------- 信件抽號碼 ----------
def mail(body, subtype="plain", subject="電子發票開立通知", sender="某商店 <noreply@example.com>"):
    raw = (f"From: {sender}\nSubject: {subject}\nDate: Mon, 03 Aug 2026 10:00:00 +0800\n"
           f"MIME-Version: 1.0\nContent-Type: text/{subtype}; charset=utf-8\n\n{body}")
    return email.message_from_bytes(raw.encode("utf-8"))


rows = gmail_invoice.parse_invoice_mail(mail("訂單編號 AB12345678\n發票號碼：CD-87654321\n開立時間 2026/08/02\n總計 NT$1,280\n載具：手機條碼"))
check("只認發票號碼旁的號碼，不抓訂單編號", [r["number"] for r in rows] == ["CD87654321"], rows)
check("開立日期、金額、載具", rows and (rows[0]["issued_date"], rows[0]["amount"], rows[0]["carrier"]) == ("2026/08/02", "1,280", "手機條碼"), rows)
check("賣方取寄件者名稱", rows and rows[0]["seller"] == "某商店", rows)
rows = gmail_invoice.parse_invoice_mail(mail("發票號碼 EF11223344\n已捐贈"))
check("捐贈註記", rows and rows[0]["donated"] is True, rows)
rows = gmail_invoice.parse_invoice_mail(mail("<table><tr><td>發票號碼</td><td>GH55667788</td></tr></table>", subtype="html"))
check("只有 HTML 的信也抽得到", [r["number"] for r in rows] == ["GH55667788"], rows)
rows = gmail_invoice.parse_invoice_mail(mail("您的驗證碼 XY12345678，請於 10 分鐘內輸入", subject="登入驗證"))
check("不是發票的信回空", rows == [], rows)

# ---------- 整段對獎（隔離的資料夾）----------
with tempfile.TemporaryDirectory() as tmp:
    d = pathlib.Path(tmp)
    today = datetime.date.today()
    fresh = {"period": "新期", "covers": ["2026/07", "2026/08"], **P,
             "claim_start": (today - datetime.timedelta(days=1)).isoformat(),
             "claim_end": (today + datetime.timedelta(days=30)).isoformat()}
    old = {"period": "舊期", "covers": ["2026/03", "2026/04"], **P,
           "claim_start": "2026-06-06", "claim_end": (today - datetime.timedelta(days=1)).isoformat()}
    (d / "winning_numbers.json").write_text(json.dumps({"periods": [fresh, old]}, ensure_ascii=False), encoding="utf-8")
    (d / "accounts.json").write_text(json.dumps({"accounts": [{"label": "test", "email": "test@example.com", "app_password": ""}]}), encoding="utf-8")

    def inv(number, date, donated=False):
        return {"number": number, "digits": number[2:], "issued_date": date, "seller": "測試商店", "donated": donated}

    (d / "invoices_test.json").write_text(json.dumps({"account": "test@example.com", "invoices": [
        inv("AA99999444", "2026/08/01"),                 # 新期六獎，可領
        inv("BB33334444", "2026/03/15"),                 # 舊期頭獎，但已過領獎期
        inv("CC12345678", "2026/07/10", donated=True),   # 特別獎號碼但已捐贈
        inv("DD00000001", "2026/09/05"),                 # 還沒開獎
        inv("EE00000002", "2026/08/20"),                 # 沒中
    ]}, ensure_ascii=False), encoding="utf-8")
    env = dict(os.environ, INVOICE_DATA_DIR=tmp, PYTHONUTF8="1")
    out = subprocess.run([sys.executable, str(SCRIPTS / "invoice_check.py")], capture_output=True,
                         text=True, encoding="utf-8", env=env).stdout
    check("統計列正確", "共 5 張；實際對獎 3 張（捐贈 1 張不參加、尚未開獎 1 張" in out, out)
    check("可領金額只算沒過期的", "還能領的 1 張、合計 NT$200" in out, out)
    check("過期的中獎有標出來", "BB33334444｜頭獎 NT$200,000" in out and "領不到了" in out, out)
    check("捐贈的特別獎號碼不算中", "CC12345678" not in out, out)
    check("未開獎的附開獎日", "DD00000001" in out and "2026-11-25 開獎" in out, out)

    out = subprocess.run([sys.executable, str(SCRIPTS / "account.py"), "list"], capture_output=True,
                         text=True, encoding="utf-8", env=env).stdout
    check("account.py list 不印密碼", "test@example.com" in out and "缺密碼" in out, out)

with tempfile.TemporaryDirectory() as tmp:
    env = dict(os.environ, INVOICE_DATA_DIR=tmp, PYTHONUTF8="1")
    r = subprocess.run([sys.executable, str(SCRIPTS / "gmail_invoice.py")], capture_output=True,
                       text=True, encoding="utf-8", env=env)
    check("沒設帳號時提示去跑 account.py", r.returncode != 0 and "account.py" in r.stderr, r.stderr)

print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
