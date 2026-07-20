# 崩壞：星穹鐵道 - 限定躍遷一覽表 (HSR Banner Tracker)

這是一個用來追蹤《崩壞：星穹鐵道》角色限定躍遷（卡池）歷史與復刻間隔的互動式表格網頁[cite: 7]。

🔗 **線上即時預覽**：https://shibashika.github.io/hsr-banner/

---

## 📂 專案資料夾結構

本專案採用模組化結構與視覺化後台，方便日後維護與更新[cite: 7]：
* `index.html`：網頁主架構與核心渲染邏輯[cite: 7]。
* `admin.html`：專屬視覺化資料管理後台（支援新增/修改角色與版本）。
* `css/style.css`：網頁專屬樣式與配色定義[cite: 7]。
* `js/characters.js`：角色資料庫（包含角色名稱、命途、屬性、復刻紀錄）[cite: 7]。
* `js/patches.js`：遊戲版本與對應日期資料[cite: 7]。
* `js/paths.js`：命途圖標連結與順序配置[cite: 7]。
* `js/elements.js`：屬性分類配置[cite: 7]。

---

## 💡 如何進行日常維護與更新？

本專案內建了網頁版管理後台，讓您無需手動刻寫程式碼即可輕鬆維護資料：

### 1. 開啟管理後台
在瀏覽器中打開您的管理後台網址：
> `https://shibashika.github.io/hsr-banner/admin.html`
*(或直接在本地電腦雙擊開啟專案中的 `admin.html`)*

### 2. 新增或修改資料
* **角色管理**：可在此頁籤中直接修改角色名稱、切換命途、屬性，或維護卡池歷史紀錄。
* **版本管理**：可在此新增或修改遊戲版本與對應日期。

### 3. 套用更新至專案
1. 在管理後台完成編輯後，點擊下方的 **「複製 Characters」** 或 **「複製 Patches」** 按鈕[cite: 6]。
2. 至 GitHub 專案的 `js/` 資料夾中，開啟對應的檔案 (`characters.js` 或 `patches.js`) 進行編輯[cite: 7]。
3. 貼上新產生的程式碼並儲存 (`Commit changes`)，等待幾十秒後即可在主頁面看到最新內容。
