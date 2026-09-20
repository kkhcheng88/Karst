# 部署:Karst 資料服務(Zeabur + 遠端 MCP)

> 這一頁只講「怎樣把服務放上去、兩個客戶端怎樣接上」。**本頁不含任何憑證值,只列環境變數名稱。**
> 服務只開公開市場方法與研究讀寫;倉內沒有帳戶、持倉或下單入口。

## 一、服務起法

| 項 | 值 |
|---|---|
| 建置 | 倉根 `Dockerfile`(python:3.12-slim,裝 `requirements.txt`) |
| 啟動 | `python -m karst.mcp_server --http --host 0.0.0.0 --port 8080 --data-dir /data` |
| 對外埠 | 8080 |
| MCP 位址 | `https://<你的域名>/mcp` |
| 健康檢查 | `GET /healthz`(免驗證,回 `{status, version, data_dir}`) |
| 持久盤 | 掛一個 volume 到 **`/data`**。不掛的話,重啟即失去研究與證據 |

**驗證未設定時服務拒絕以 HTTP 起動**(不會靜靜開一個無驗證的埠)。本機開發用 stdio,不需要驗證。

驗證有兩個模式,由 `KARST_AUTH_MODE` 決定:

- **`github`(部署用)**:GitHub OAuth 授權碼 + PKCE,由 fastmcp 代理;客戶端自己完成授權、自己拿 token。ChatGPT 的自訂 MCP 連接器只支援 OAuth,沒有固定 token 欄位,所以遠端部署走這個模式。授權成功只證明身分,**能不能用還要看 `KARST_ALLOWED_GITHUB_USERS` 這張允許清單**;清單外的 GitHub 帳戶即使登入成功,每個請求一律 401。
- **`token`(本機或過渡用)**:一個固定 Bearer token,客戶端自己帶 header。

## 二、環境變數(只列名稱與用途,值在 Zeabur 的 Variables 裡填)

| 名稱 | 用途 | 沒有會怎樣 |
|---|---|---|
| `KARST_AUTH_MODE` | `github` 或 `token`;不填時有 GitHub client id 及 secret 就當 `github`,否則當 `token` | 見上 |
| `KARST_GITHUB_CLIENT_ID` | GitHub OAuth App 的 Client ID(`github` 模式) | 拒絕起動 |
| `KARST_GITHUB_CLIENT_SECRET` | 同一個 OAuth App 的 Client secret(`github` 模式) | 拒絕起動 |
| `KARST_BASE_URL` | 服務的公開網址,例 `https://karst.zeabur.app`;OAuth 回呼位址 = 這個值加 `/auth/callback` | 拒絕起動 |
| `KARST_ALLOWED_GITHUB_USERS` | 准入的 GitHub 登入名,逗號分隔(大小寫不計) | 拒絕起動——不容許任何 GitHub 帳戶都寫得到研究 |
| `KARST_MCP_TOKEN` | **`token` 模式才用**:遠端 MCP 的 Bearer token | `token` 模式拒絕起動 |
| `KARST_DATA_DIR` | 持久根目錄,部署時設 `/data`(映像已預設) | 落在容器內,重啟即失 |
| `LONGPORT_APP_KEY` | Longbridge 公開行情 | 取價的每個輸出寫 `status: error`,不捏造 |
| `LONGPORT_APP_SECRET` | 同上 | 同上 |
| `LONGPORT_ACCESS_TOKEN` | 同上(會過期,要定期換) | 同上 |
| `KARST_EDGAR_USER_AGENT` | EDGAR 要求的 `<名字 email>` | EDGAR 拒絕回應 |
| `ANTHROPIC_API_KEY` | **可選。** 只供 `request_review` 的自動模式(服務自己呼叫模型 API 做覆核,無人值守)。第一版是手動互評——覆核由 ChatGPT 或 Claude Code 客戶端的模型做、經 MCP 寫回——服務端不呼叫任何 LLM,不填即可 | 自動模式明確拒絕,不假裝已接通;手動互評不受影響 |
| `OPENAI_API_KEY` | 同上(OpenAI adapter) | 同上 |

換 token 或換 OAuth App = 改這幾個變數再重啟,不用改程式;`github` 模式換了 client secret,兩端要重新授權一次。

## 三、資料目錄結構(`/data`)

```
/data
├── karst.sqlite                     研究版本、來源索引、任務、全文索引
├── companies/<證券ID 安全化>/
│   ├── bundle/                      該公司唯一證據倉(evidence/objects、manifest.jsonl、evidence.json、packet.json)
│   └── releases/                    發布的可讀頁面
├── oauth-proxy/                     `github` 模式的授權狀態(客戶端註冊、交易中的授權、加密後的上游 token)
└── tmp/                             取數暫存與任務目錄;可以隨時清
```

`oauth-proxy/` 放在持久盤,是為了重啟之後 ChatGPT 與 Claude Code 不用重新註冊、已發出的 token 仍然有效;加密鑰匙由 client secret 推導,所以換 secret 等於作廢舊 token。

同一家公司做幾多次研究都共用同一個 `bundle/`:重覆取到同樣內容只算「無變」,新內容才算「新增／變更」。

## 四、備份

```bash
python -m karst.store backup --data-dir /data --out /data/../karst-backup-<日期>.zip
```

打包 SQLite 的一致快照(用 SQLite 線上備份 API,不是複製檔案)加上 `companies/` 全部檔案;`tmp/` 是暫存,不備份。
**DB 與證據檔要一齊備份**——研究版本在 DB,原文在檔案,分開還原會對不上。

## 五、兩端連接(`github` 模式)

兩端都是同一個 endpoint、同一份研究方法與資料;**兩端都不用手抄 token**——各自用 GitHub 登入,服務自己發 token 給那個客戶端。

### (a) 先建一個 GitHub OAuth App(一次過)

1. GitHub → 右上頭像 → **Settings** → 左欄最底 **Developer settings** → **OAuth Apps** → **New OAuth App**。
2. 三格:
   - **Application name**:自己認得就可以,例 `Karst 研究服務`。
   - **Homepage URL**:`https://karst.zeabur.app`
   - **Authorization callback URL**:`https://karst.zeabur.app/auth/callback` ← **必須一字不差**,這是 fastmcp 的預設回呼路徑;填錯 GitHub 會在授權最後一步拒絕。
3. 建好之後記下 **Client ID**,再按 **Generate a new client secret** 取得 secret(只顯示一次)。

### (b) 在 Zeabur 加變數,然後重啟

```
KARST_AUTH_MODE=github
KARST_GITHUB_CLIENT_ID=<上一步的 Client ID>
KARST_GITHUB_CLIENT_SECRET=<上一步的 client secret>
KARST_BASE_URL=https://karst.zeabur.app
KARST_ALLOWED_GITHUB_USERS=<你的 GitHub 登入名>
```

`KARST_MCP_TOKEN` 在這個模式不用;留着也不生效。

### (c) ChatGPT(自訂 MCP 連接器)

1. Settings → **Security and login** → 開 **Developer mode**。
2. **Plugins** 一欄按「**＋**」新增自訂 MCP:URL 填 `https://karst.zeabur.app/mcp`。
3. 驗證方式選 **OAuth**(這個連接器沒有固定 token 欄位,所以服務才要行 OAuth)。
4. 按連接後會跳去 GitHub 登入、再回到服務的授權確認頁,按允許。
5. 見到 `get_research_protocol`、`refresh_sources`、`search_evidence` 等工具即為接通。

### (d) Claude Code

```bash
claude mcp remove karst      # 舊的帶 header 設定要先清掉
claude mcp add --transport http karst https://karst.zeabur.app/mcp
```

**不要帶 `--header`。** 之後在 Claude Code 打 `/mcp`,揀 `karst` → **Authenticate**,瀏覽器完成 GitHub 登入即接通。

### (e) 接通前先自己核一次

```bash
curl https://karst.zeabur.app/healthz                                      # 應回 {"status":"ok",...}
curl https://karst.zeabur.app/.well-known/oauth-protected-resource/mcp     # 應回 JSON,resource 指向本服務的 /mcp
curl https://karst.zeabur.app/.well-known/oauth-authorization-server       # 應回 JSON,authorization_endpoint 指向本服務
curl -i https://karst.zeabur.app/mcp                                       # 無 token 應回 401,並在 WWW-Authenticate 指回上面那個 resource_metadata
```

探索位址按 RFC 9728 帶住 MCP 路徑(`/.well-known/oauth-protected-resource/mcp`);**光溜溜的 `/.well-known/oauth-protected-resource` 會 404,這是正常的**,客戶端是照 401 回應裡的 `resource_metadata` 去取。

## 六、界線

- 遠端服務可寫研究版本,所以 token 等同寫入權;不要貼進聊天內容、票或 commit。GitHub client secret 同樣。
- 允許清單是唯一那道人手閘:清單上多一個名,等於多一個人可以寫研究版本。
- `/healthz` 只證明程序活着,不證明來源憑證有效或某家公司已有資料。
- 接通一端不代表另一端已驗;哪一端未實測就照實列明。**本頁的 OAuth 流程是按本機測試與 fastmcp 2.14.7 的實際行為寫的,兩端未在真域名上實測。**

## Versioned research input seed (0.2.5)

The Docker command explicitly passes `--knowledge-seed /app/strategy/data/research-inputs-v1.json`. This is reviewed research configuration, not hardcoded symbols in the engine. Startup validates the manifest and inserts only absent objects into the mounted SQLite store; it assigns acquisition time at import, never the source publication date. Restart/redeploy does not overwrite live revisions. To revise an existing object, read `get_knowledge`, then `save_knowledge` with expected_version. The manifest is not a substitute for cloud backup.

Four MCP methods expose knowledge read/write, bounded value-chain lookup and an independent EPS×P/E matrix. Existing get_research_context also returns the subject's knowledge, so older client tool catalogs can read the deployed inputs. Frozen research context only includes knowledge known at that version's creation time. No auth change; all data tools still require the existing OAuth/token access.

Comparison snapshots distinguish reported/guidance/estimate/missing/not_applicable and carry explicit period, unit, basis and source. They do not make unavailable consensus data appear. Relationship and assumption revisions route only through explicit thesis dependencies; they never auto-change a rating.
