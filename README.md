# 崩壞：星穹鐵道｜限定躍遷一覽表

[![CI](https://github.com/ShibaShika/hsr-banner/actions/workflows/ci.yml/badge.svg)](https://github.com/ShibaShika/hsr-banner/actions/workflows/ci.yml)

🔗 **線上一覽表：** <https://shibashika.github.io/hsr-banner/>

⚙️ **視覺化資料編輯器：** <https://shibashika.github.io/hsr-banner/editor.html>

## 專案簡介

本專案以表格整理《崩壞：星穹鐵道》角色的限定躍遷登場紀錄，方便查閱角色初次登場、復刻間隔與特殊取得方式。資料由網站讀取專案內的 JavaScript 資料檔，並透過自動化流程定期檢查及更新。

## 網站功能

- **登場紀錄與復刻間隔：** 以時間軸呈現角色各版本的登場情況，並依等待版本數與顏色層級顯示間隔。
- **多維度排序與欄位對照：** 左上角表頭提供微型琉璃排序選單，支援依「登場順序（最新／最舊）」、「上次復刻（最久未復刻／最近復刻）」及「UP 次數（最多／最少）」排序，並可切換版本時間軸方向；滑鼠移至表格儲存格時會高亮對應欄位。
- **搜尋、篩選與網址狀態同步：** 可依實裝版本、命途、屬性、取得方式及角色名稱篩選，也能依強化模式（如「礪爍新輝」或未來新增的強化標籤）篩選；篩選與排序狀態會自動雙向同步至網址列參數（Query Params），方便直接複製連結分享特定篩選結果。
- **命途與強化模式全自動動態適配架構：** 前端篩選器與強化模式切換鈕皆由角色資料動態聚合生成，不寫死固定清單；當未來推出未預設的新命途、新強化模式或 CDN 圖示尚未就緒時，會自動套用「深空琉璃通用降級風格（Fallback Style）」與純文字琉璃金色標章，確保版面完整且不破圖。
- **預覽版本：** 可切換是否顯示資料中的預覽版本與預覽角色。預覽資訊可能隨來源更新而變動。
- **角色統計琉璃浮動資訊卡：** 電腦端懸浮或手機端點擊左側角色欄時，會顯示深空琉璃風格的浮動資訊卡，呈現實裝版本、目前等待版本數、歷史最長等待、總 UP 次數與超期警報。
- **匯出圖片：** 依目前顯示的角色與紀錄匯出全尺寸 PNG 表格圖片。
- **偏好設定：** 介面縮放與工具列摺疊狀態會保存在瀏覽器中。

## 編輯器

編輯器位於 [`editor.html`](editor.html)，提供角色與版本資料的視覺化檢視及編輯工具，支援角色名稱快速過濾、`isPreview` 預覽狀態切換、上下移動排序、唯一識別異動高亮，以及匯出前的資料完整性防呆檢查。編輯完成後，可使用頁面提供的匯出功能複製資料程式碼，再依專案維護流程更新資料檔。

編輯器適合用於人工校對或小幅資料調整；它與每日自動抓取流程是不同的功能。自動更新由 GitHub Actions 執行，詳細流程見下方「資料更新與品質檢查」。

## 資料更新與品質檢查

GitHub Actions 工作流程 [`auto_update.yml`](.github/workflows/auto_update.yml) 每日 **UTC 01:00（台灣時間 09:00）** 執行，也可由有權限的維護者在 GitHub Actions 頁面手動啟動。手動執行可選擇 `dry_run`，只抓取及檢查資料，不提交更新。

自動更新程式 [`update_gist.py`](update_gist.py) 會讀取既有角色與版本資料，從 Fandom Wiki 擷取卡池歷史與前瞻排程，並補充角色資料後合併結果（遇到未預設的新命途或新強化模式標記時會自動保留並整合，不會因未知命途而熔斷）。若通過資料完整性檢查且內容確實有變更，工作流程會更新 `js/characters.js`（含 `LAST_UPDATED` 更新日期常數）與 `js/patches.js`，並提交至 `main`。

更新程式會在寫入前執行五道安全防護檢查與動態標籤審計，包括正式角色與正式版本數量不可減少、版本名稱及日期格式、角色排程對應的版本，以及既有正式角色歷史紀錄是否完整保留（預覽角色與預覽版本則允許隨最新前瞻資訊動態覆蓋與調整）。若無法取得有效排程或檢查未通過，更新會停止，避免將不完整結果寫入資料檔；自動更新工作流程會在程式失敗時建立 GitHub Issue 警報。

CI 工作流程 [`ci.yml`](.github/workflows/ci.yml) 會在推送至 `main` 或建立 Pull Request 時執行 JavaScript 與 Python 單元測試，並直接針對專案實際的 `js/characters.js` 與 `js/patches.js` 進行靜態完整性驗證。

## 本機執行

網站是靜態頁面。可使用 Python 內建 HTTP 伺服器在專案根目錄啟動本機預覽：

```powershell
python -m http.server 8000
```

接著以瀏覽器開啟 <http://localhost:8000/>。按 `Ctrl+C` 可停止伺服器。也可以直接開啟 `index.html`，但使用本機伺服器較能貼近網站實際載入資源的方式。

## 開發與測試

專案的 CI 使用 **Node.js 20** 與 **Python 3.11**。在專案根目錄安裝依賴：

```powershell
npm ci
python -m pip install -r requirements.txt
```

執行完整測試（目前共 **176 項測試** 100% 通過：69 項 Python + 107 項 Jest）：

```powershell
npm test -- --runInBand
python -m unittest
```

若要在本機執行資料更新程式：

```powershell
python update_gist.py
```

此程式會連線至外部資料來源，並在資料有更新且檢查通過時寫入 `js/characters.js` 和 `js/patches.js`。執行前請先確認工作目錄，並在提交前檢查產生的差異。

## 專案結構

```text
hsr-banner/
├── .github/
│   └── workflows/
│       ├── auto_update.yml  # 定期資料更新與失敗警報
│       └── ci.yml           # Pull Request／main 測試
├── css/
│   └── style.css            # 網站樣式（含深空琉璃通用降級風格）
├── js/
│   ├── app.js               # 表格渲染、動態篩選聚合、統計與圖片匯出
│   ├── buffs.js             # 強化模式優先序與視覺設定註冊表
│   ├── characters.js        # 角色及登場歷史資料
│   ├── elements.js          # 屬性設定與圖示
│   ├── patches.js           # 版本名稱與日期資料
│   └── paths.js             # 命途優先序與圖示註冊表
├── app.test.js              # 前端 JavaScript 測試（107 項）
├── editor.html              # 視覺化資料編輯器
├── index.html               # 網站首頁
├── test_update_gist.py      # 資料更新程式測試（69 項）
└── update_gist.py           # 資料抓取、合併與完整性檢查
```

## 免責聲明

本專案為玩家製作的非官方工具，供社群交流與個人查閱使用，與遊戲發行商及營運商無關。遊戲名稱、角色名稱、美術圖像及其他相關素材的權利均屬其各自權利人所有。本專案程式碼與資料可能因來源變動而修正；如發現錯誤，請透過 GitHub Issues 回報。
