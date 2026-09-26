# 三支腳本共用：資料夾位置、帳號設定讀取、UTF-8 輸出、選用的 DNS 備援。
#
# 資料（帳號、中獎號碼、撈到的發票）一律放在 repo／plugin 資料夾以外，
# plugin 更新時整個資料夾會被換掉，放裡面會跟著消失。
#   預設：~/.gmail-invoice-lottery/
#   自訂：環境變數 INVOICE_DATA_DIR
import json
import os
import pathlib
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except AttributeError:
    pass

# 本機 DNS 偶爾解不出網域時，改問 8.8.8.8。預設關閉，設 INVOICE_DNS_FALLBACK=1 才啟用。
if os.environ.get("INVOICE_DNS_FALLBACK") == "1":
    import dnsfix  # noqa: F401


def data_dir():
    d = pathlib.Path(os.environ.get("INVOICE_DATA_DIR") or pathlib.Path.home() / ".gmail-invoice-lottery")
    d.mkdir(parents=True, exist_ok=True)
    return d


def accounts_file():
    return data_dir() / "accounts.json"


def load_accounts():
    f = accounts_file()
    if not f.exists():
        return []
    return json.loads(f.read_text(encoding="utf-8")).get("accounts", [])


def save_accounts(accounts):
    f = accounts_file()
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps({"accounts": accounts}, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, f)
    try:
        os.chmod(f, 0o600)
    except OSError:
        pass


def pick_account(target=None):
    """target 可以是標籤或信箱；沒給就用第一個帳號。"""
    accounts = load_accounts()
    if not accounts:
        sys.exit(f"還沒設定帳號。請在自己的終端機執行：python {pathlib.Path(__file__).with_name('account.py')} add <標籤> <Gmail 信箱>")
    if not target:
        return accounts[0]
    acc = next((a for a in accounts if target in (a["label"], a["email"])), None)
    if not acc:
        labels = "、".join(a["label"] for a in accounts)
        sys.exit(f"找不到帳號：{target}（已設定：{labels}）")
    return acc


def invoices_file(label):
    return data_dir() / f"invoices_{label}.json"


def winning_file():
    return data_dir() / "winning_numbers.json"
