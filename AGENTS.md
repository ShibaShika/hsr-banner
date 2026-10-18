# AGENTS.md — 專案架構與 AI 開發規範

本文件供 AI Agent 快速掌握 `hsr-banner`（崩壞：星穹鐵道｜限定躍遷一覽表）的核心架構、檔案職責與修改鐵則，無需重新掃描全專案即可安全開發。

---

## 1. 專案核心架構

1. **純靜態前端（Zero-Build Vanilla Stack）**：
   - 無打包器，直接由 `index.html` 依序載入 `js/patches.js`、`js/paths.js`、`js/elements.js`、`js/buffs.js`、`js/characters.js` 與 `js/app.js`。
   - 首屏優先讀取 `js/characters.js` 內建的 `LAST_UPDATED` 常數與本地資料同步渲染表格，再非同步從 StarRailRes CDN 補齊高清頭像，若載入失敗則自動退回 SVG 姓氏首字頭像或深空琉璃文字標章。
2. **零字典全自動爬蟲與五道防護門檻**：
   - `update_gist.py` 每日透過 GitHub Actions（`auto_update.yml`）抓取 Fandom Wiki（`Warp/List` 與前瞻分類）及 StarRailRes 中英資料，透過批次 MediaWiki API 自動解析繁中譯名、命途、屬性與排程（支援上／中／下三階段版本與預覽角色動態覆蓋）。
   - 寫入前強制執行 **五道安全防護檢驗門檻**（正式角色與版本數不減、版本格式 `^\d+\.\d+[上下中]$` 與日期 `YY/MM/DD` 合規、排程版本存在、正式角色歷史紀錄不縮水）與 **第 6 道動態標籤審計（僅記錄、絕不熔斷）**。
3. **命途與強化模式全自動動態適配**：
   - **爬蟲端**：遇到未預設的新命途或新強化模式標記時，一律保留並寫入角色資料（`buffs` 維持版本字串陣列以向下相容，非預設強化模式則額外記錄於 `buffTypes: { "<版本>": "<模式名稱>" }`）。
   - **前端與視覺端**：篩選器與強化模式切換鈕皆從 `RAW_CHARACTERS` 動態聚合生成，並雙向同步至網址列參數（`?path=...&buff=...`）；未定義專屬色彩或 CDN 尚無圖示時，自動套用 `css/style.css` 的 **深空琉璃通用降級風格（Deep-Space Glass Fallback Style）** 與 `onerror="handleIconError(this)"` 純文字琉璃標章。
4. **統一台灣時區（UTC+8）**：
   - 後端爬蟲（`TZ_TW = timezone(timedelta(hours=8))`）與前端當前版本判定（`Date.now() + 8 * 3600 * 1000`）一律以 **台灣時間（UTC+8）** 為唯一基準，禁止混用執行環境本地時區或純 UTC 日期。

---

## 2. 關鍵檔案職責

| 檔案路徑 | 核心職責與結構說明 |
| :--- | :--- |
| `update_gist.py` | 全自動爬蟲、MediaWiki 批次解析、三階段預覽版本推算、動態命途/強化整合、五道防護門檻 + 審計 6，並直寫 `js/characters.js` 與 `js/patches.js`。 |
| `js/app.js` | 前端核心邏輯：表格與熱力色階渲染、動態篩選器與強化按鈕生成、多維度角色排序、URL Query Params 雙向同步、角色統計琉璃浮動卡、圖示 `onerror` 降級、以及 `html2canvas` 截圖匯出。底部透過 `module.exports` 匯出純函式供 Jest 測試。 |
| `js/characters.js` | 儲存 `LAST_UPDATED`（`YYYY/MM/DD`）與 `RAW_CHARACTERS` 陣列（欄位含 `cid`、`name`、`path`、`elem`、`runs`、`buffs`、選填 `buffTypes`、`term`、`isCollab`、`isPreview`）。 |
| `js/patches.js` | 儲存 `PATCH_DATA` 陣列（欄位含 `patch`、`date`（`YY/MM/DD`）、選填 `isPreview`）。 |
| `js/paths.js` | 命途顯示優先順序（`PATH_ORDER`）與已知命途圖示映射（`PATH_ICONS`）註冊表；非白名單，未註冊的新命途會自動排在已知命途之後、「未知」之前。 |
| `js/buffs.js` | 強化模式預設值（`DEFAULT_BUFF_TYPE = '礪爍新輝'`）、顯示順序（`BUFF_ORDER`）與角標設定（`BUFF_META`）註冊表。 |
| `editor.html` | 獨立視覺化資料編輯器，支援搜尋過濾、`isPreview` 切換、排序調整、異動高亮與匯出前防呆檢查。 |

---

## 3. 開發與修改鐵則

1. **嚴禁破壞既有 DOM ID 與匯出介面**：
   - 必須保留 `#tracker`、`#version-items-container`、`#path-items-container`、`#elem-items-container`、`#type-items-container`、`#buff-mode-container`、`#buff-toggle-btn`、`#preview-toggle-btn`、`#char-search-input`、`#char-stats-popover`、`#char-sort-popover` 等核心 DOM ID，以及 `js/app.js` 的 `module.exports` 匯出符號。
2. **新命途與新強化模式一律走動態聚合與琉璃降級**：
   - 禁止在前端或爬蟲寫死固定數量的命途白名單而阻擋未知資料。
   - 新增圖示渲染邏輯時，必須綁定 `onerror="handleIconError(this)"` 或使用 `createFallbackBadgeElement` / `buildFallbackBadgeHtml`，並搭配 `.icon-fallback-badge`、`.path-fallback-cell`、`.buff-mode-fallback`、`.buff-badge-fallback` 等深空琉璃降級樣式。
3. **維持 `getFilterState()` 與資料結構向下相容**：
   - 預設強化模式（`礪爍新輝`）在 URL 參數中保持輸出 `buff=1`；僅在啟用非預設強化模式或多模式篩選時將 `selectedBuffs` 設為可枚舉屬性並輸出 `buff=<模式名>`。
4. **提交前強制執行雙測試套件（176+ 項測試 100% 通過）**：
   - 任何程式碼或資料修改完成後，**必須**於專案根目錄執行以下兩項測試指令並確認全數通過：
     ```powershell
     $env:PYTHONIOENCODING="utf-8"; python -m unittest test_update_gist
     npx jest --env=jsdom
     ```
