# 設定要掃的 Gmail 帳號。應用程式密碼只在你自己的終端機輸入（不顯示在畫面上），
# 不要貼進 AI 對話。
#
# 用法：
#   python account.py add main you@gmail.com     # 會提示輸入應用程式密碼
#   python account.py list
#   python account.py remove main
import getpass
import re
import sys

import common


def main():
    args = sys.argv[1:]
    if not args or args[0] not in ("add", "list", "remove"):
        sys.exit("用法: python account.py add <標籤> <Gmail 信箱> | list | remove <標籤>")
    cmd = args[0]
    accounts = common.load_accounts()

    if cmd == "list":
        if not accounts:
            print(f"還沒設定帳號（{common.accounts_file()}）")
        for a in accounts:
            state = "已設定密碼" if a.get("app_password") else "缺密碼"
            print(f"{a['label']}\t{a['email']}\t{state}")
        return

    if cmd == "remove":
        if len(args) < 2:
            sys.exit("用法: python account.py remove <標籤>")
        rest = [a for a in accounts if a["label"] != args[1]]
        if len(rest) == len(accounts):
            sys.exit(f"找不到帳號：{args[1]}")
        common.save_accounts(rest)
        print(f"已移除 {args[1]}。記得到 https://myaccount.google.com/apppasswords 撤銷那組應用程式密碼。")
        return

    if len(args) < 3:
        sys.exit("用法: python account.py add <標籤> <Gmail 信箱>")
    label, email = args[1], args[2]
    if not re.fullmatch(r"[\w.-]+", label):
        sys.exit("標籤只能用英數字、底線、點、減號（會拿來當檔名）")
    print("到 https://myaccount.google.com/apppasswords 產生一組應用程式密碼（需要先開兩步驟驗證）。")
    pw = getpass.getpass("貼上應用程式密碼（輸入時不會顯示）：").replace(" ", "")
    if not re.fullmatch(r"[a-zA-Z]{16}", pw):
        sys.exit("格式不對：應用程式密碼是 16 個英文字母（空格可有可無）。這不是你的 Google 登入密碼。")
    accounts = [a for a in accounts if a["label"] != label]
    accounts.append({"label": label, "email": email, "app_password": pw})
    common.save_accounts(accounts)
    print(f"已儲存 {label} <{email}> 到 {common.accounts_file()}")


if __name__ == "__main__":
    main()
