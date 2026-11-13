# 崩壞：星穹鐵道躍遷一覽表 - 跨對話協同與即時交接看板 (Live Handoff Board)

> 🚩 **【當前接力棒 (Active Baton)】**：`待命 (Standby)`

本文件為所有對話視窗共享的即時工作黑板。每次切換角色視窗時，輸入 `@[docs/HANDOFF.md]` 即可觸發對應角色自動接手待辦任務。

> 🔒 **【對話身分註冊表】**：參見 [`docs/agent_sessions.json`](agent_sessions.json)
> - 👑 **技術主管**：`tech_lead`
> - ⚙️ **後端 / 爬蟲與資料專家**：`backend_specialist`
> - 🎨 **前端 / 介面設計師**：`frontend_designer`
> - 🧪 **品質驗證專家**：`qa_engineer`
> - 🔄 **發布工程師**：`release_engineer`

---

## 📌 當前各角色任務交接指引 (Active Handoffs)

### 1. ⚙️ 致【後端 / 爬蟲與資料專家】
* **核心邊界**：負責 `update_gist.py`（Fandom Wiki 爬蟲、MediaWiki 解析、StarRailRes 繁中對齊、五道防護門檻與動態審計），不修改前端 UI，不私自 `git push`。
* **待執行任務**：
  - 目前無待執行工單，待命中 (Standby)。

---

### 2. 🎨 致【前端 / 介面設計師】
* **核心邊界**：負責 `index.html`、`editor.html`、`css/style.css`、`js/app.js`、`js/paths.js`、`js/buffs.js`、`js/types.js`（深空琉璃樣式、圖示降級、篩選面板、表格渲染與 Popover），不修改爬蟲核心邏輯，不私自 `git push`。
* **待執行任務**：
  - 目前無待執行工單，待命中 (Standby)。

---

### 3. 🧪 致【品質驗證專家】
* **核心邊界**：負責 `test_update_gist.py`（Python 79+ 測試）、`app.test.js`（Jest 113+ 測試）與回歸把關，發現 Bug 請開單回傳對應專家修復。
* **待執行任務**：
  - 目前無待執行工單，待命中 (Standby)。

---

### 4. 👑 致【技術主管】
* **核心邊界**：技術會診、架構審核、任務分診、五道門檻把關與最終測試驗收；領域任務優先派發工單施工。
* **待執行任務**：
  - 目前無待執行工單，待命接收需求或審核專家交付。

---

### 5. 🔄 致【發布工程師】
* **核心邊界**：專注分支同步、排除每日 `github-actions[bot]` 自動更新衝突、Commit 與 `git push`；未經技術主管驗收禁止推送。
* **待執行任務**：
  - 目前無待執行工單，待命中 (Standby)。
