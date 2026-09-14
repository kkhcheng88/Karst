# karst/tests/fixtures/ —— 公開市場真實回傳樣本(D-183 步一;KARST-241)

給 GPT 定契約與寫通用核心用的參數化測試用例;也給本地接口整合作對照。**目前為空,樣本抓取待用戶講「開始」。**

## 規矩

1. 只放公開市場資料:申報文本、逐字稿、報表、共識與評級、機構與內部人持股、淡倉、日線、業績日曆。**券商帳戶、持倉、成本、盈虧、現金、下單類回傳一律不入**(與研究不讀持倉同一條線,D-181)。
2. 保留真實的缺漏與口徑:空值、缺逐字稿、不同財務期間、幣別與單位差異、分頁游標,照原樣留;不為整齊先清掉問題。
3. 一隻首批股票足以開始接線;之後用另一種生意(例如成熟軟件對商業化前虧損)再取一套驗通用性。這些是參數化案例,不是每股一支程式(D-180)。
4. 每份樣本旁附同名 `.meta.json`:`source`(edgar / defeatbeta / futu / longbridge / local-prices)、`tool`(MCP 工具名或函式名)、`params`、`fetched_at`(UTC)、`published_at` 與 `published_at_basis`、`period`、`truncated`(有否截短及截到哪)、`known_gaps`。
5. 體積:逐字稿與長申報可截到測試夠用(標 `truncated`);券商回傳原樣但只取一家。

## 目錄

```
fixtures/
  README.md
  edgar/        <accession>.<form>.txt(+.meta.json)、submissions 索引切片
  defeatbeta/   transcript、quarterly statements、revenue breakdown、shares、calendar
  futu/         consensus、rating summary、valuation detail、insider、institutional、short interest、earnings price history、market snapshot
  longbridge/   consensus、forecast_eps、institution_rating(_history)、shareholder、fund_holder、short_positions、filings、finance_calendar、valuation、business_segments
  prices/       daily slice(local + defeatbeta 續抓,含 source 欄)
```
