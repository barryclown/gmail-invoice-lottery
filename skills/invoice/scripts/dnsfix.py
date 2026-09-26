# 本機 DNS 偶爾解不出網域名時 → getaddrinfo 失敗才改用 8.8.8.8（Google 公共 DNS）解析。
# 只在原生解析失敗時才 fallback，DNS 正常時完全不影響；保留原 hostname 給 TLS SNI/憑證驗證。
# 預設不啟用；設環境變數 INVOICE_DNS_FALLBACK=1 時由 common.py 載入。
import re
import socket
import subprocess

_orig = socket.getaddrinfo
_cache = {}


def _public_resolve(host):
    if host in _cache:
        return _cache[host]
    try:
        out = subprocess.run(["nslookup", host, "8.8.8.8"],
                             capture_output=True, text=True, timeout=15).stdout
    except Exception:
        out = ""
    ips = re.findall(r"((?:\d{1,3}\.){3}\d{1,3})", out)
    ips = [ip for ip in ips if ip != "8.8.8.8"]
    _cache[host] = ips
    return ips


def _patched(host, port, family=0, type=0, proto=0, flags=0):
    try:
        return _orig(host, port, family, type, proto, flags)
    except socket.gaierror:
        for ip in _public_resolve(host):
            try:
                return _orig(ip, port, socket.AF_INET, type, proto, flags)
            except socket.gaierror:
                continue
        raise


socket.getaddrinfo = _patched
