# Estimize 的 point-in-time 聲明(原文照錄)

- 取自:https://www.estimize.com/data_access_faq
- 取數日期:2026-08-31
- 取法:`curl` 帶瀏覽器 User-Agent(該站對無標頭的請求回 403)
- 為何要記低:這是全次勘察唯一一個**經本票親自核實、而且個人拿得到**的
  前瞻預測 point-in-time 來源。它不是轉述,是官方問答的原文。

---

## 一、是不是 point-in-time

> **Is Estimize data point-in-time?**
> Yes, we keep point-in-time data for all estimates contributed to the platform.
> **We never delete estimates or change estimates.** The sanctity of this data is
> extremely important to us because our clients need to be able to trust that the
> historical data they are backtesting is what they would have seen at the time in
> production.

## 二、試用檔案本身就是 point-in-time 全貌

> What's data is available in the testing files?
> Our testing files for each data set provide a **full point-in-time look at all of the
> data that would have been available to you at that time.** The US Equity EPS/Revenue,
> US Equity KPIs, and Global Economic Indicator data sets each have consensus time series
> files and detailed individual estimate files.

## 三、逐條預測都帶時點,可自行重砌共識

> In both each of the API, FTP, and data testing files you will see that **all individual
> estimates are available on a point-in-time basis as they are created**, whether or not
> they were flagged. This allows firms that wish to judge all of the individual estimates
> for reliability themselves in order to create a consensus the ability to do so.

## 四、日期格式

> All datetime formats are given is ISO-8601. Time zones are included in the datetime
> format as a UTC offset.

## 五、學術用途:可免費下載,公開研究才要買授權

> **Do you license data for academic research?**
> We have a long history of licensing data to academics… **Our full historical data set is
> available to academics to download and conduct research. If and when you choose to make
> your research public, in any way, we require you to purchase an academic license.**

## 六、覆蓋面

> Estimize is an open financial estimates platform designed to collect forward looking
> financial estimates from independent, buy-side, and sell-side analysts, along with those
> of private investors and academics. Currently, **over 130,000 analysts contribute to
> Estimize, resulting in coverage on over 3,000 stocks and 85 economic indicators each
> quarter.** The Estimize consensus has proven more accurate than comparable sell side
> data sets over…

---

## 本票的判讀(不是原文)

- **可信度高**:「從不刪改」是一句寫死的承諾,而且它的商業模式(賣回測數據畀基金)
  正正建基於這句話,說謊的代價很大。
- **但要記住它不是賣方共識。** 分母階梯第一級講「前瞻市盈率」,市場實際錨定的是
  賣方分析員共識(I/B/E/S 那類);Estimize 是群眾來源(獨立、買方、賣方、私人投資者混合)。
  文獻普遍認為它更準、更快,但**更準不等於更接近市場當時所錨定的那個數**——
  倍數情緒儀量的是「市場肯畀幾多」,用一個比市場更準的分母,量到的可能是另一樣東西。
  這一點屬策略設計判斷,不在本勘察票範圍,只記低供後續票考慮。
- **未核實**:起始年份(第三方稱 2012 年 1 月)、確實欄位名、試用檔案的實際取得流程。
  本票依鐵律沒有註冊帳戶、沒有提交任何表格,故此止於官方文字。
