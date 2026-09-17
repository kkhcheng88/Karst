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

**缺 `KARST_MCP_TOKEN` 時服務拒絕以 HTTP 起動**(不會靜靜開一個無驗證的埠)。本機開發用 stdio,不需要 token。

## 二、環境變數(只列名稱與用途,值在 Zeabur 的 Variables 裡填)

| 名稱 | 用途 | 沒有會怎樣 |
|---|---|---|
| `KARST_MCP_TOKEN` | 遠端 MCP 的 Bearer token;兩個客戶端各自帶同一個值 | HTTP 模式拒絕起動 |
| `KARST_DATA_DIR` | 持久根目錄,部署時設 `/data`(映像已預設) | 落在容器內,重啟即失 |
| `LONGPORT_APP_KEY` | Longbridge 公開行情 | 取價的每個輸出寫 `status: error`,不捏造 |
| `LONGPORT_APP_SECRET` | 同上 | 同上 |
| `LONGPORT_ACCESS_TOKEN` | 同上(會過期,要定期換) | 同上 |
| `KARST_EDGAR_USER_AGENT` | EDGAR 要求的 `<名字 email>` | EDGAR 拒絕回應 |
| `ANTHROPIC_API_KEY` | **可選。** 只供 `request_review` 的自動模式(服務自己呼叫模型 API 做覆核,無人值守)。第一版是手動互評——覆核由 ChatGPT 或 Claude Code 客戶端的模型做、經 MCP 寫回——服務端不呼叫任何 LLM,不填即可 | 自動模式明確拒絕,不假裝已接通;手動互評不受影響 |
| `OPENAI_API_KEY` | 同上(OpenAI adapter) | 同上 |

Token 換值 = 改這個變數再重啟,不用改程式;兩端的連接器要同步更新。

## 三、資料目錄結構(`/data`)

```
/data
├── karst.sqlite                     研究版本、來源索引、任務、全文索引
├── companies/<證券ID 安全化>/
│   ├── bundle/                      該公司唯一證據倉(evidence/objects、manifest.jsonl、evidence.json、packet.json)
│   └── releases/                    發布的可讀頁面
└── tmp/                             取數暫存與任務目錄;可以隨時清
```

同一家公司做幾多次研究都共用同一個 `bundle/`:重覆取到同樣內容只算「無變」,新內容才算「新增／變更」。

## 四、備份

```bash
python -m karst.store backup --data-dir /data --out /data/../karst-backup-<日期>.zip
```

打包 SQLite 的一致快照(用 SQLite 線上備份 API,不是複製檔案)加上 `companies/` 全部檔案;`tmp/` 是暫存,不備份。
**DB 與證據檔要一齊備份**——研究版本在 DB,原文在檔案,分開還原會對不上。

## 五、兩端連接

兩端都是同一個 endpoint、同一份研究方法與資料;各自帶同一個 Bearer token。

### ChatGPT(自訂 MCP 連接器)

1. Settings → Connectors → Create / Add custom connector。
2. MCP server URL 填 `https://<你的域名>/mcp`,傳輸選 Streamable HTTP。
3. 驗證選 Bearer / Access token,值填 `KARST_MCP_TOKEN` 的那個值。
4. 儲存後在工具清單見到 `get_research_protocol`、`refresh_sources`、`search_evidence` 等即為接通。

### Claude Code

```bash
claude mcp add --transport http karst https://<你的域名>/mcp \
  --header "Authorization: Bearer <KARST_MCP_TOKEN 的值>"
```

之後 `/mcp` 可見 `karst` 已連接。要移除:`claude mcp remove karst`。

### 接通前先自己核一次

```bash
curl https://<你的域名>/healthz                         # 應回 {"status":"ok",...}
curl -i https://<你的域名>/mcp                          # 無 token 應回 401
```

## 六、界線

- 遠端服務可寫研究版本,所以 token 等同寫入權;不要貼進聊天內容、票或 commit。
- `/healthz` 只證明程序活着,不證明來源憑證有效或某家公司已有資料。
- 接通一端不代表另一端已驗;哪一端未實測就照實列明。
