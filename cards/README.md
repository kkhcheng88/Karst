# cards/ —— 研究發布與最新視圖

研究以 thesis_id 管論點,以 entity_id／security_id 管公司與證券。目錄不是關係資料庫,一份產業研究可由多家公司引用。

## 計劃路徑與正本

- releases/<publication_id>/manifest.json:發布身份、來源／假設／方法版本、截止時間、目標日、上一版與待更新項。
- releases/<publication_id>/card.md:同一發布的可讀分析;計算結果與必要輸入清單一併保存。這整個不可變 bundle 是研究正本。
- companies/<entity_id>.md:公司的最新已發布研究視圖,可含多個論點／證券,指向 publication_id。
- industries/<entity_id>.md:產業與鏈位假設的最新視圖,成員與關係有方向、期間、來源及版本。
- market/<entity_id>.md:需求、政策、利率等主題最新視圖。
- plans/ 如使用,只作對發布包內 plan_id 的索引,不另維護第二份計劃正本。

卡片含研究評級、今日公允價值與範圍、指定日期目標價、條件計劃、TA、來源定位及變化。MD 正文與 manifest 分管內容／元資料,從同一次已驗證結果生成;畫面不能手改成另一個真相。

每次修訂新建發布,原評級、期限、目標與證據清單保留。人工修正也走同一路徑。最新卡不含用戶成本、持倉或模型帳本;模型配置引用不可變發布,不引用可覆寫最新卡來計分。

Git 保存可讀研究版本;完整發布包及其所引不入 git 的原文仍需備份。發布一致性與 schema 依[設計計劃](../strategy/specs/獨立投研工作台設計與交付計劃-v1.md),目前尚未實作 runner。
