# 從財政部稅務入口網抓統一發票中獎號碼，更新 winning_numbers.json。
# 每期單月 25 日開獎，開獎後跑一次即可；重跑不會弄壞既有資料（同期別覆蓋、其餘保留）。
#
# 用法：
#   python update_winning_numbers.py            # 抓 RSS 全部期別（通常最近 6 期）
#   python update_winning_numbers.py --keep 8   # 只保留最近 8 期
#
# 資料來源：
#   https://invoice.etax.nat.gov.tw/invoice.xml  （特別獎/特獎/頭獎；官方 RSS）
#   https://www.etax.nat.gov.tw/etw-main/ETW183W2_<民國年期別>/  （補「增開六獎」，多數期沒有）
import argparse
import datetime
import json
import os
import re
import urllib.request

import common

RSS = "https://invoice.etax.nat.gov.tw/invoice.xml"
UA = {"User-Agent": "Mozilla/5.0"}

NOTE = ("統一發票中獎號碼。每期單月 25 日開獎，開獎後跑 update_winning_numbers.py 自動更新。"
        "increased_sixth 為「增開六獎」號碼陣列，該期沒有就留空陣列。")


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode("utf-8", "replace")


def add_months(d, n):
    m = d.month - 1 + n
    return datetime.date(d.year + m // 12, m % 12 + 1, min(d.day, 28))


def claim_window(draw_date):
    """領獎期間＝開獎次月 6 日起 3 個月（至 3 個月後的 5 日止；遇例假日官方會順延）。"""
    start = add_months(draw_date.replace(day=6), 1)
    end = add_months(start, 3) - datetime.timedelta(days=1)
    return start.isoformat(), end.isoformat()


def fetch_increased_sixth(link):
    """增開六獎多數期沒有；抓不到就當沒有，不讓它擋住整份更新。"""
    try:
        html = get(link if link.endswith("/") else link + "/")
    except Exception:
        return []
    m = re.search(r"增開六獎[^0-9]{0,40}((?:\d{3}[^0-9]{0,6})+)", html)
    if not m:
        return []
    return re.findall(r"\d{3}", m.group(1))


def parse_rss(xml, fetch_sixth=fetch_increased_sixth):
    """把官方 RSS 拆成期別資料；欄位不完整的期別略過並回報名稱。"""
    periods, skipped = [], []
    for it in re.findall(r"<item>(.*?)</item>", xml, re.S):
        title = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>", it, re.S)
        desc = re.search(r"<description><!\[CDATA\[(.*?)\]\]></description>", it, re.S)
        link = re.search(r"<link><!\[CDATA\[(.*?)\]\]></link>", it, re.S)
        pub = re.search(r"<pubDate>(.*?)</pubDate>", it, re.S)
        if not (title and desc):
            continue
        # 標題像「115年 05~06月」
        tm = re.search(r"(\d{3})年\s*(\d{2})[~-](\d{2})月", title.group(1))
        if not tm:
            continue
        roc, m1, m2 = int(tm.group(1)), tm.group(2), tm.group(3)
        year = roc + 1911
        name = f"{roc}年{m1}-{m2}月"

        body = desc.group(1)
        special = re.search(r"特別獎[^0-9]{0,6}(\d{8})", body)
        grand = re.search(r"特獎[^0-9]{0,6}(\d{8})", body)
        first = re.findall(r"\d{8}", re.search(r"頭獎[^<]*", body).group(0)) if "頭獎" in body else []
        if not (special and grand and len(first) == 3):
            skipped.append(name)
            continue

        try:
            draw = datetime.datetime.strptime(pub.group(1)[:16].strip(), "%a, %d %b %Y").date()
        except Exception:
            # pubDate 壞掉就用「雙月的下個月 25 日」；11–12 月期要跨到隔年 1 月，不然會算出 13 月
            draw = datetime.date(year + (int(m2) == 12), int(m2) % 12 + 1, 25)
        cs, ce = claim_window(draw)

        url = link.group(1) if link else ""
        periods.append({
            "period": name,
            "covers": [f"{year}/{m1}", f"{year}/{m2}"],
            "special": special.group(1),
            "grand": grand.group(1),
            "first": first,
            "increased_sixth": fetch_sixth(url) if url else [],
            "draw_date": draw.isoformat(),
            "claim_start": cs,
            "claim_end": ce,
            "source": url,
        })
    return periods, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", type=int, default=8, help="保留最近幾期（預設 8）")
    args = ap.parse_args()

    out = common.winning_file()
    periods = {}
    if out.exists():
        for p in json.loads(out.read_text(encoding="utf-8")).get("periods", []):
            periods[p["period"]] = p

    fresh, skipped = parse_rss(get(RSS))
    for name in skipped:
        print(f"[SKIP] {name}：RSS 欄位不完整，未更新")
    for p in fresh:
        periods[p["period"]] = p

    ordered = sorted(periods.values(), key=lambda p: p["covers"][0], reverse=True)[:args.keep]
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(json.dumps({"_note": NOTE, "updated": datetime.date.today().isoformat(),
                               "periods": ordered}, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, out)

    print(f"已更新 {out.name}：共 {len(ordered)} 期（本次自 RSS 取得 {len(fresh)} 期）\n")
    today = datetime.date.today().isoformat()
    for p in ordered:
        state = "可領獎" if p["claim_start"] <= today <= p["claim_end"] else (
            "尚未開放領獎" if today < p["claim_start"] else "已過領獎期")
        six = "、".join(p["increased_sixth"]) if p["increased_sixth"] else "無"
        print(f"{p['period']}  特別獎 {p['special']}  特獎 {p['grand']}")
        print(f"    頭獎 {'、'.join(p['first'])}  增開六獎 {six}")
        print(f"    領獎 {p['claim_start']} ~ {p['claim_end']}（{state}；遇例假日官方順延）")


if __name__ == "__main__":
    main()
