# 拿 gmail_invoice.py 撈到的發票，對 winning_numbers.json 的中獎號碼。
#
# 用法：
#   python invoice_check.py          # 第一個帳號
#   python invoice_check.py main
#
# 對獎規則（統一發票）：
#   特別獎 1000萬：8 位全同
#   特  獎  200萬：8 位全同
#   頭  獎   20萬：與任一組頭獎 8 位全同
#   二  獎    4萬：末 7 位同頭獎
#   三  獎    1萬：末 6 位同頭獎
#   四  獎   4000：末 5 位同頭獎
#   五  獎   1000：末 4 位同頭獎
#   六  獎    200：末 3 位同頭獎
#   增開六獎  200：末 3 位同增開號碼（該期有開才算）
# 捐贈的發票不參加對獎。特別獎、特獎只認 8 位全同，末幾碼相同不算。
import datetime
import json
import sys

import common

TIERS = [
    (7, "二獎", 40000),
    (6, "三獎", 10000),
    (5, "四獎", 4000),
    (4, "五獎", 1000),
    (3, "六獎", 200),
]


def match(digits, period):
    if digits == period["special"]:
        return "特別獎", 10000000
    if digits == period["grand"]:
        return "特獎", 2000000
    for f in period["first"]:
        if digits == f:
            return "頭獎", 200000
    for n, name, prize in TIERS:
        for f in period["first"]:
            if digits[-n:] == f[-n:]:
                return name, prize
    for x in period.get("increased_sixth", []):
        if digits[-3:] == x[-3:]:
            return "增開六獎", 200
    return None, 0


def next_draw(ym):
    """ym 像 2026/09 → 那期的開獎日（雙月的下個月 25 日）。"""
    y, m = int(ym[:4]), int(ym[5:7])
    m = m + (m % 2) + 1
    if m > 12:
        y, m = y + 1, m - 12
    return datetime.date(y, m, 25).isoformat()


def main():
    acc = common.pick_account(sys.argv[1] if len(sys.argv) > 1 else None)
    inv_file = common.invoices_file(acc["label"])
    if not inv_file.exists():
        sys.exit(f"找不到 {inv_file}，請先跑 gmail_invoice.py")
    wn_file = common.winning_file()
    if not wn_file.exists():
        sys.exit(f"找不到 {wn_file}，請先跑 update_winning_numbers.py")
    data = json.loads(inv_file.read_text(encoding="utf-8"))
    wn = json.loads(wn_file.read_text(encoding="utf-8"))
    today = datetime.date.today().isoformat()

    by_month = {}
    for p in wn["periods"]:
        for m in p["covers"]:
            by_month[m] = p

    wins, checked, skipped, pending, donated, seen = [], 0, [], [], 0, {}
    for inv in data["invoices"]:
        ym = inv["issued_date"][:7].replace("-", "/")
        if inv["donated"]:
            donated += 1
            continue
        p = by_month.get(ym)
        if not p:
            (pending if ym >= max(by_month) else skipped).append(inv)
            continue
        checked += 1
        seen[p["period"]] = p
        name, prize = match(inv["digits"], p)
        if name:
            wins.append((inv, p, name, prize))

    print(f"# 對獎結果（{data['account']}）")
    print(f"共 {len(data['invoices'])} 張；實際對獎 {checked} 張"
          f"（捐贈 {donated} 張不參加、尚未開獎 {len(pending)} 張、期別過期或無資料 {len(skipped)} 張）\n")

    if wins:
        claimable = [w for w in wins if w[1]["claim_end"] >= today]
        expired = [w for w in wins if w[1]["claim_end"] < today]
        total = sum(w[3] for w in claimable)
        print(f"## 中獎 {len(wins)} 張，其中還能領的 {len(claimable)} 張、合計 NT${total:,}\n")
        for inv, p, name, prize in wins:
            start, end = p["claim_start"], p["claim_end"]
            if end < today:
                status = f"已過領獎期（{end} 截止），領不到了"
            elif start > today:
                status = f"{start} 起可領，{end} 截止"
            else:
                days_left = (datetime.date.fromisoformat(end) - datetime.date.fromisoformat(today)).days
                status = f"可領獎，{end} 截止（剩 {days_left} 天）"
            print(f"- {inv['number']}｜{name} NT${prize:,}｜{inv['issued_date']} {inv['seller'][:20]}")
            print(f"  期別 {p['period']}｜{status}")
        if expired:
            print(f"\n（上面有 {len(expired)} 張已過領獎期，金額未計入合計）")
    else:
        print("## 沒有中獎\n對過的發票沒有任何一張對中，含末三碼。")

    # 對過的期別都列出領獎期限：已過期的要讓人知道，就算中了也領不到
    if seen:
        print("\n## 各期領獎期限")
        for p in sorted(seen.values(), key=lambda p: p["covers"][0], reverse=True):
            state = "可領獎" if p["claim_start"] <= today <= p["claim_end"] else (
                "尚未開放領獎" if today < p["claim_start"] else "已過領獎期")
            print(f"- {p['period']}：{p['claim_start']} ~ {p['claim_end']}（{state}）")

    if pending:
        print(f"\n## 尚未開獎（{len(pending)} 張）")
        for inv in pending:
            ym = inv["issued_date"][:7].replace("-", "/")
            print(f"- {inv['issued_date']} {inv['number']} {inv['seller'][:20]}（{next_draw(ym)} 開獎）")
    if skipped:
        print(f"\n## 未對（期別不在 winning_numbers.json，多半已過領獎期）（{len(skipped)} 張）")
        for inv in skipped:
            print(f"- {inv['issued_date']} {inv['number']} {inv['seller'][:20]}")


if __name__ == "__main__":
    main()
