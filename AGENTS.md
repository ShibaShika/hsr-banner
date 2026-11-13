# AGENTS.md — 專案架構、開發規範與多 Agent 協同體系

本文件供 AI Agent 快速掌握 `hsr-banner`（崩壞：星穹鐵道｜限定躍遷一覽表）的核心架構、檔案職責、修改鐵則與多 Agent 協同規範，無需重新掃描全專案即可安全開發。

---

## 1. 專案核心架構

1. **純靜態前端（Zero-Build Vanilla Stack）**：
   - 無打包器，直接由 `index.html` 依序載入 `js/patches.js`、`js/paths.js`、`js/elements.js`、`js/buffs.js`、`js/types.js`、`js/characters.js` 與 `js/app.js`。
   - 首屏優先讀取 `js/characters.js` 內建的 `LAST_UPDATED` 常數與本地資料同步渲染表格，再非同步從 StarRailRes CDN 補齊高清頭像，若載入失敗則自動退回 SVG 姓氏首字頭像或深空琉璃文字標章。
2. **零字典全自動爬蟲與五道防護門檻**：
   - `update_gist.py` 每日透過 GitHub Actions（`auto_update.yml`）抓取 Fandom Wiki（`Warp/List`、`Store`、各 Change History 與前瞻分類）及 StarRailRes 中英資料，透過批次 MediaWiki API 自動解析繁中譯名、命途、屬性、取得方式與排程（支援上／中／下三階段版本與預覽角色動態覆蓋）。
   - 寫入前強制執行 **五道安全防護檢驗門檻**（正式角色與版本數不減、版本格式 `^\d+\.\d+[上下中]$` 與日期 `YY/MM/DD` 合規、排程版本存在、正式角色歷史紀錄不縮水）與 **第 6 道動態標籤審計（僅記錄、絕不熔斷）**。
3. **命途、強化模式與取得方法全自動動態適配**：
   - **爬蟲端**：遇到未預設的新命途、新強化模式或新取得途徑標記時，一律保留並寫入角色資料（`buffs` 維持版本字串陣列以向下相容，非預設強化模式記錄於 `buffTypes`；取得方式記錄於 `term` 與多階段 `terms`）。
   - **前端與視覺端**：篩選器、強化模式切換鈕與取得方式皆從 `RAW_CHARACTERS` 動態聚合生成，並雙向同步至網址列參數（`?path=...&buff=...&type=...&up=1`）；未定義專屬色彩或 CDN 尚無圖示時，自動套用 `css/style.css` 的 **深空琉璃通用降級風格（Deep-Space Glass Fallback Style）** 與純文字琉璃標章。
4. **統一台灣時區（UTC+8）**：
   - 後端爬蟲（`TZ_TW = timezone(timedelta(hours=8))`）與前端當前版本判定（`Date.now() + 8 * 3600 * 1000`）一律以 **台灣時間（UTC+8）** 為唯一基準，禁止混用執行環境本地時區或純 UTC 日期。

---

## 2. 關鍵檔案職責

| 檔案路徑 | 核心職責與結構說明 |
| :--- | :--- |
| `update_gist.py` | 全自動爬蟲、MediaWiki 批次解析、三階段預覽版本推算、動態命途/強化/取得整合、五道防護門檻 + 審計 6，並直寫 `js/characters.js` 與 `js/patches.js`。 |
| `js/app.js` | 前端核心邏輯：表格與熱力色階渲染、動態篩選器與強化/取得按鈕生成、多維度角色排序、當前大版本一鍵篩選、URL Query Params 雙向同步、角色統計琉璃浮動卡、圖示 `onerror` 降級、以及 `html2canvas` 截圖匯出。底部透過 `module.exports` 匯出純函式供 Jest 測試。 |
| `js/characters.js` | 儲存 `LAST_UPDATED`（`YYYY/MM/DD`）與 `RAW_CHARACTERS` 陣列（欄位含 `cid`、`name`、`path`、`elem`、`runs`、`buffs`、選填 `buffTypes`、`term`、選填 `terms`、`isCollab`、選填 `collabDate`、`isPreview`）。 |
| `js/patches.js` | 儲存 `PATCH_DATA` 陣列（欄位含 `patch`、`date`（`YY/MM/DD`）、選填 `isPreview`）。 |
| `js/paths.js` | 命途顯示優先順序（`PATH_ORDER`）與已知命途圖示映射（`PATH_ICONS`）註冊表；非白名單，未註冊的新命途會自動排在已知命途之後、「未知」之前。 |
| `js/buffs.js` | 強化模式預設值（`DEFAULT_BUFF_TYPE = '礪爍新輝'`）、顯示順序（`BUFF_ORDER`）與角標設定（`BUFF_META`）註冊表。 |
| `js/types.js` | 取得方式預設值（`DEFAULT_ACQUISITION_TYPE = 'normal'`）、顯示順序（`TYPE_ORDER`）與元數據（`TYPE_META`）註冊表；非白名單，未註冊的新途徑自動套用深空琉璃降級樣式。 |
| `editor.html` | 獨立視覺化資料編輯器，支援搜尋過濾、`isPreview` 切換、取得途徑/強化設定、排序調整、異動高亮與匯出前防呆檢查。 |

---

## 3. 開發與修改鐵則

1. **嚴禁破壞既有 DOM ID 與匯出介面**：
   - 必須保留 `#tracker`、`#version-items-container`、`#path-items-container`、`#elem-items-container`、`#type-items-container`、`#buff-mode-container`、`#buff-toggle-btn`、`#buff-mode-btn`、`#preview-toggle-btn`、`#current-ver-up-btn`、`#char-search-input`、`#char-stats-popover`、`#char-sort-popover` 等核心 DOM ID，以及 `js/app.js` 的 `module.exports` 匯出符號。
2. **新命途、新強化模式與新取得途徑一律走動態聚合與琉璃降級**：
   - 禁止在前端或爬蟲寫死固定數量的白名單而阻擋未知資料。
   - 新增圖示渲染邏輯時，必須綁定 `onerror="handleIconError(this)"` 或使用 `createFallbackBadgeElement` / `buildFallbackBadgeHtml`，並搭配 `.icon-fallback-badge`、`.path-fallback-cell`、`.buff-mode-fallback`、`.buff-badge-fallback`、`.term-fallback`、`.type-fallback-badge` 等深空琉璃降級樣式。
3. **維持 `getFilterState()` 與資料結構向下相容**：
   - 預設強化模式（`礪爍新輝`）在 URL 參數中保持輸出 `buff=1`；僅在啟用非預設強化模式或多模式篩選時輸出 `buff=<模式名>`。
   - 單一取得方式維持 `term: { type, patch }` 物件；多階段演進時在 `terms` 維護歷次清單，`term` 指向最新階段。
4. **提交前強制執行雙測試套件（192+ 項測試 100% 通過）**：
   - 任何程式碼或資料修改完成後，**必須**於專案根目錄執行以下兩項測試指令並確認全數通過：
     ```powershell
     $env:PYTHONIOENCODING="utf-8"; python -m unittest test_update_gist
     npx jest --env=jsdom
     ```
5. **開工與提交前先確認遠端 Bot 同步狀態**：
   - `.github/workflows/auto_update.yml` 每日會由 `github-actions[bot]` 自動提交 `js/characters.js` 與 `js/patches.js` 至 `main`。開始修改或準備推送前，請先檢查 `git status` 與遠端差異（必要時執行 `git pull --ff-only`），避免與每日自動更新衝突。

---

## 4. 角色職責邊界 (Role Boundaries)

本專案採用多角色職能分工機制，並以 [`docs/HANDOFF.md`](docs/HANDOFF.md) 作為所有對話視窗的共享即時交接看板：

| 角色 | `role_key` | 核心職責與負責目錄 | 嚴禁事項（邊界鐵則） |
| :--- | :--- | :--- | :--- |
| 👑 **技術主管** | `tech_lead` | 架構設計、病因診斷、任務拆解分診、Code Review、五道門檻把關與全域測試驗收 | **Triage & Dispatch First**：凡屬明確領域開發或獨立功能，優先轉化工單派發給對應專家，不輕易越俎代庖。 |
| ⚙️ **後端 / 爬蟲與資料專家** | `backend_specialist` | `update_gist.py`（Fandom Wiki 爬蟲、MediaWiki 解析、StarRailRes 繁中對齊、五道防護門檻與動態審計） | 不碰前端 UI 樣式，不執行 `git push`；改動須附帶對應單元測試。 |
| 🎨 **前端 / 介面設計師** | `frontend_designer` | `index.html`、`editor.html`、`css/style.css`、`js/app.js`、`js/paths.js`、`js/buffs.js`、`js/types.js`（深空琉璃樣式、圖示降級、篩選面板、表格渲染與 Popover） | 不碰爬蟲核心邏輯與五道防護門檻，不執行 `git push`。 |
| 🧪 **品質驗證專家** | `qa_engineer` | `test_update_gist.py`（Python 79+ 測試）、`app.test.js`（Jest 113+ 測試）與回歸把關 | 不直接魔改生產業務代碼以迎合測試；發現缺陷回報工單交由對應專家修復。 |
| 🔄 **發布工程師** | `release_engineer` | GitOps、分支整合、排除每日 `github-actions[bot]` 自動更新衝突、版本標籤與遠端倉庫推送 | **唯一推送權**：未經技術主管驗收通過嚴禁 `git push`；非發布工程師嚴禁私自推送遠端。 |

---

## 5. 跨對話協同與交接看板協議 (Multi-Agent Handoff & Baton Protocol)

1. **頂部接力棒強制指針**：[`docs/HANDOFF.md`](docs/HANDOFF.md) 頂部永遠維護單一明確的 `🚩 【當前接力棒 (Active Baton)】`。每次更新看板時，最後動手的角色必須將接力棒指向下一個執行者（例如：`⚙️ 爬蟲專家施工中` → `👑 技術主管待審核` → `🔄 發布工程師待推送` → `待命 (Standby)`）。
2. **雙向工單流轉**：
   - 專家完工交付時：在自己章節打勾 `[x]` 並填寫完工摘要，於【👑 技術主管】章節登記 `- [ ] 【待審核驗收】工單 TASK-XXX`。
   - 技術主管驗收通過時：在自己章節結案，於【🔄 發布工程師】章節登記 `- [ ] 【待發布推送】工單 TASK-XXX`。
3. **無縫觸發**：當收到使用者輸入 `@[docs/HANDOFF.md]` 時，應立即閱讀頂部接力棒並自主執行對應工單，使用者無需額外說明前情提要。
4. **🚨 看板即時磁碟強制讀取鐵律**：
   - 凡輸入提及 `HANDOFF.md`、交接或完工回報，**第一個工具呼叫必須強制讀取磁碟上的 `docs/HANDOFF.md`**，嚴禁依賴對話記憶判斷接力棒歸屬。
   - 技術主管驗收時必須同步確認 `git status -s`，以實體檔案變更為客觀真理。

---

## 6. 對話身分自鎖定協議 (Session Role Auto-Binding Protocol)

- 每個對話視窗透過本機全域 Hook（`role_injector.py`）自動比對環境 `Conversation ID` 與 [`docs/agent_sessions.json`](docs/agent_sessions.json)。
- **首次開啟視窗**：當使用者指定角色時，Agent 應取得自身 `Conversation ID` 並登記至 `docs/agent_sessions.json`，確保 `/compact` 或重啟後身分永久不遺失。

---

## 7. 任務前置模組適配度審查與動態模型建議協議 (Adaptive Model Tier Protocol)

本協議採用**「抽象算力階級 + 平台即時感知」**設計，嚴禁在規範或腳本中寫死特定模型名稱，以確保隨 Antigravity 平台迭代自動跟上最新模型（並恪守**僅使用 Google Gemini 原生系列、排除 Claude 與 GPT** 之鐵則）：

### A. 抽象算力階級標準
- **`light`（輕量極速級）**：輕量高速模型（低思考 `Low / Medium`）— 適用純查詢、文字記錄、看板勾選、常規 GitOps。
- **`standard`（常規主力級）**：輕量/中階模型高思考（`High`）或進階主力低思考 — 適用單一明確功能開發、局部單元測試、UI 微調、局部審查。
- **`heavy`（高階推理級）**：高階旗艦模型（優先挑選即時額度 > 0% 之最新高階 Gemini 模型，開 `High` 至極限 `XHigh`）— 適用複雜病因除錯、長日誌診斷、動態架構重構、防護門檻擴充。

### B. 動態查詢與全域同步 (Auto-Sync)
- 專案維護共用工具 [`tool/maintenance/model_tiers.py`](tool/maintenance/model_tiers.py)，優先讀取專案覆蓋檔（`docs/model_tiers.json`）或全域共用配置（`~/.gemini/config/model_tiers.json`）：
  ```powershell
  # 查詢目前生效之模型階級與剩餘配額
  uv run python tool/maintenance/model_tiers.py --show
  ```
- 當環境出現新模型或某高階模型額度耗盡時，Agent 應唯讀調用 `swarm(action="models", all=True)` 取得最新模型清單與剩餘配額，並透過 `tool/maintenance/model_tiers.py --stdin` 寫入更新。

### C. 算力適配自我提醒
1. **配置過低（高風險做錯）**：若任務屬 `heavy` 級別而當前運行在 `light` 配置，**必須在開頭給出強烈風險提示**，建議依即時可用額度切換至 `heavy` 階級再執行。
2. **配置過高（額度浪費提醒）**：若任務僅屬 `light` 級別而當前開著高階推理階級（`heavy`），**需在回覆中溫馨提醒**改用 `light` 階級即可高效完成。
3. **配置契合**：直接高效施工並給出精準交付。

### D. 回覆結尾標準建議格式
每次回覆結尾建議附上動態計算後的可複製建議區塊（優先從 `~/.gemini/config/model_tiers.json` 或 `tool/maintenance/model_tiers.py` 查詢結果填入真實型號名稱與尚有配額之選項）：
```markdown
> 🎯 **下一輪對話建議配置**：
> - **建議模組**：`<依即時 model_tiers 選定的可用 Google Gemini 模型>`
> - **思考程度**：`<依平台支援的實際檔位：Low / Medium / High / XHigh>`
> - **建議理由**：<簡要說明任務複雜度、對應算力階級與即時配額考量>
> - **建議內容**：`<此處提供可直接複製貼到下一次對話的精確文字指令>`
```

---

## 8. 常用互動口令約定

- **「開工」**：檢查 `git status -s`、`docs/HANDOFF.md` 與專案雙測試健康狀態；若有待辦工單則立即安排施工。
- **「檢討」**：針對最新執行/測試結果或錯誤日誌做根因診斷，產出可交接的精確修復工單。
- **「結案」**：確認雙測試全綠且遠端已同步後，清理暫存檔並將 `docs/HANDOFF.md` 重置為輕量待命模式。
