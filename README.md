# gmail-invoice-lottery — 用 Gmail 裡的電子發票自動對統一發票

[English](README.en.md) | **繁體中文**

網購、外送、Steam 這類店家開電子發票時，會寄一封開立通知信到你的信箱。這個 Claude Code skill
會把那些信裡的發票號碼撈出來，對財政部公告的中獎號碼，告訴你有沒有中、還能不能領。
在對話裡說一句「對發票」就好。

## 效果

（以下號碼是示意用的）

```
你：對發票

Claude：7–8 月那期中了 1 張六獎，NT$200，10/6 起可以領，2027/1/5 截止。
        另外 3 張是捐贈發票不參加對獎，9 月那張要等 11/25 開獎。
        這次只對得到有寄通知信的發票，手機條碼載具裡的要用財政部「統一發票兌獎」App 查。
```

背後腳本實際印出來的是這樣，Claude 再把它整理成上面那段：

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

## 你只需要知道四件事

- **信箱只讀不改**：用唯讀模式開收件匣，讀信不會變成已讀，也不刪、不移動、不寄信。
- **密碼不會進 AI 對話**：Gmail 應用程式密碼是你自己在終端機輸入的，輸入時不顯示，AI 看不到也碰不到。
- **中獎號碼抓官方的，不靠 AI 記憶**：每次都從財政部的官方 RSS 抓最新號碼。抓不到就停下來講清楚，不會讓 AI 憑印象回答「有中」或「沒中」。
- **會把影響答案的事講出來**：哪些是捐贈發票不參加對獎、哪些還沒開獎（附開獎日）、哪些已經過了領獎期、哪些發票根本不在信箱裡。

## 它怎麼運作

它是一支 skill（一份給 AI 看的操作說明）加上幾支 Python 小程式。你說「對發票」，Claude 會照說明依序跑：

| 步驟 | 程式 | 做什麼 |
| --- | --- | --- |
| 1 | `update_winning_numbers.py` | 從財政部官方 RSS 抓最近幾期的中獎號碼，順便算出每期的領獎期間 |
| 2 | `gmail_invoice.py` | 用 IMAP 唯讀連上 Gmail，找近 200 天含「發票」的信，抽出發票號碼、日期、賣方、有沒有捐贈 |
| 3 | `invoice_check.py` | 把發票依月份對到該期號碼，算出中了什麼、還能不能領 |

對獎本身是程式算的，不是 AI 算的。AI 負責跑程式和把結果講成人話。

## 安裝與使用

### 1. 先準備好

- Python 3.8 以上。只用到標準函式庫，不用 `pip install` 任何東西。
- Claude Code（桌面版或終端機版都可以）。Codex 這類支援 Agent Skills 的工具也能用，見方法 B。
- 要掃的 Gmail 帳號已經開好兩步驟驗證（沒開就不能產生應用程式密碼）。

### 2. 安裝（兩種方法選一種）

**方法 A：當成 Claude Code plugin 裝（建議）**，在 Claude Code 的對話框輸入：

```
/plugin marketplace add barryclown/gmail-invoice-lottery
/plugin install gmail-invoice-lottery@gmail-invoice-lottery
```

裝好後重開 Claude Code。

如果第一行出現 `Host key verification failed` 或 `SSH host key is not in your known_hosts`，
代表 `owner/repo` 這種簡寫在你的電腦上會走 SSH、但你沒設定 GitHub 的 SSH。改用完整網址就好：
`/plugin marketplace add https://github.com/barryclown/gmail-invoice-lottery.git`

**方法 B：直接放進 skills 資料夾**

```bash
git clone https://github.com/barryclown/gmail-invoice-lottery.git   # 或在 GitHub 頁面按 Code → Download ZIP
```

把裡面的 `skills/invoice` 整個資料夾複製到 `~/.claude/skills/invoice`（Windows 是 `C:\Users\<你>\.claude\skills\invoice`）。
Codex 就複製到 `~/.codex/skills/invoice`。

### 3. 設定 Gmail 帳號（這一步要你自己在終端機做）

1. 到 <https://myaccount.google.com/apppasswords> 產生一組應用程式密碼，名稱隨便取，例如 `invoice`。它是 16 個英文字母，**不是你的 Google 登入密碼**。
2. 在終端機執行下面這行，照提示貼上那組密碼：

```bash
python <skill 資料夾>/scripts/account.py add main you@gmail.com
```

`main` 是帳號的標籤，之後可以用它指定要對哪個帳號。有好幾個信箱就各加一次，換個標籤。

skill 資料夾在哪：方法 A 是 `~/.claude/plugins/cache/gmail-invoice-lottery/gmail-invoice-lottery/<版本>/skills/invoice`，
方法 B 就是你複製過去的位置。找不到的話，直接跟 Claude 說「對發票」，它會把完整指令印給你。

### 4. 確認裝好了

- 在 Claude Code 說「對發票」，應該會看到它依序跑三支程式並回報結果。
- 用方法 B 的話，也可以在 clone 下來的資料夾跑 `python selftest.py`，不連網、不碰信箱，38 項全過就對了。

### 5. 平常怎麼用

- 每逢單月 25 日開獎後，說「對發票」。
- 有好幾個帳號：「對發票，用 work 那個帳號」。沒指定就用第一個加進去的帳號。
- 想翻更久以前的信：「對發票，往前翻 400 天」。
- 不想經過 AI 的話，三支程式也可以自己在終端機依序跑，見〈它怎麼運作〉的表。

### 6. 更新與移除

- 方法 A：更新 `/plugin marketplace update gmail-invoice-lottery`；移除 `/plugin uninstall gmail-invoice-lottery@gmail-invoice-lottery`
- 方法 B：更新就 `git pull` 後重新複製；移除就刪掉 `~/.claude/skills/invoice`
- 兩種方法移除後，資料夾 `~/.gmail-invoice-lottery/` 都要自己刪，也記得到 <https://myaccount.google.com/apppasswords> 撤銷那組應用程式密碼。

### 7. 常見問題

- **「Gmail 拒絕登入」／`AUTHENTICATIONFAILED Invalid credentials`**：應用程式密碼打錯了，或已經作廢。
  改過 Google 密碼、重設過兩步驟驗證，舊的應用程式密碼都會失效。重新產生一組，再跑一次 `account.py add` 覆蓋。
- **某家店的發票一直對不到**：那家的通知信裡沒有「發票號碼」這幾個字，或信不在收件匣裡（被封存、被篩選器移走）。見〈限制〉。
- **plugin 裝不起來**：見第 2 步，改用完整的 HTTPS 網址。

## 隱私與安全

**存在哪裡**：全部在你自己的電腦，預設是 `~/.gmail-invoice-lottery/`（可用環境變數 `INVOICE_DATA_DIR` 改）。
放在 skill 資料夾以外，plugin 更新時才不會被清掉。

| 檔案 | 內容 |
| --- | --- |
| `accounts.json` | 帳號標籤、信箱、應用程式密碼（明文） |
| `invoices_<標籤>.json` | 撈到的發票：號碼、日期、賣方、信件主旨、金額、載具、是否捐贈 |
| `winning_numbers.json` | 最近幾期的中獎號碼與領獎期間 |

應用程式密碼是明文存的，能讀你使用者資料夾的程式都讀得到。這也是為什麼要用應用程式密碼而不是 Google
登入密碼：它只能收信，而且隨時可以單獨撤銷，不影響你的帳號。

**連到哪裡**：程式本身只連三個地方——`imap.gmail.com`（讀信）、`invoice.etax.nat.gov.tw` 和 `www.etax.nat.gov.tw`
（財政部中獎號碼）。沒有其他伺服器，也沒有任何使用統計回傳。只有你自己設了 `INVOICE_DNS_FALLBACK=1`，
本機 DNS 解析失敗時才會改問 Google 公共 DNS（8.8.8.8）。
另外，透過 Claude 這類 AI 使用時，程式印出來的東西（你的信箱地址、發票號碼、賣方、日期）會進到對話裡，
也就是會傳到你用的 AI 服務；密碼不會出現在任何輸出。介意的話，三支程式可以自己在終端機跑，不經過 AI。

**讀了哪些信**：只搜收件匣裡近 N 天（預設 200）含「發票」「invoice」「電子發票」的信。信件內容只在記憶體裡解析，
存檔的只有上表列的發票欄位，不會把信件本文存下來。

**不做的事**：不把信標成已讀、不刪信、不移動、不寄信、不改 Gmail 設定。

## 對獎規則

| 獎別 | 獎金 | 條件 |
| --- | --- | --- |
| 特別獎 | 1,000 萬 | 8 位數全部相同 |
| 特獎 | 200 萬 | 8 位數全部相同 |
| 頭獎 | 20 萬 | 與任一組頭獎 8 位數全部相同 |
| 二獎～六獎 | 4 萬／1 萬／4,000／1,000／200 | 末 7／6／5／4／3 位與任一組頭獎相同 |
| 增開六獎 | 200 | 末 3 位與增開號碼相同（該期有開才算） |

特別獎和特獎只認 8 位全同，末幾碼一樣不算。捐贈的發票不參加對獎。

## 限制

- **只看得到有寄通知信的發票。** 存在手機條碼載具、但店家沒寄信的發票不在這裡，要用財政部「統一發票兌獎」App 查。
- 只搜收件匣。被封存或被篩選器移出收件匣的信找不到。
- 號碼是靠信裡的「發票號碼」字樣抓的。格式特殊的店家可能會漏抓。
- 買受人是營業人、政府機關、公營事業、公立學校或部隊的發票（通常就是打了這些單位統編的發票），依
  [統一發票給獎辦法](https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=G0340083) 第 11 條不能領獎，程式不會辨識。
- 領獎期間是照「開獎次月 6 日起三個月」推算的，遇到例假日官方會順延，以財政部公告為準。
- 只在 Windows 上測過。只用 Python 標準函式庫，macOS／Linux 理論上也能跑，但沒驗證過。
- 程式輸出和程式碼註解是中文。
- **中獎號碼一律以財政部公告為準**，本工具只供對照，兌獎前請核對實體或雲端發票。

## 授權

MIT，見 [LICENSE](LICENSE)。
