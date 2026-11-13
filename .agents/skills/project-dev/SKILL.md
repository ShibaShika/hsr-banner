---
name: project-dev
description: >-
  hsr-banner 專屬的開發、建置與驗證快捷工具包。
  提供雙測試套件（Python 爬蟲防護門檻單元測試 + 前端 Jest DOM 測試）
  與動態模型算力階級查詢。
---

# hsr-banner 專案開發與測試規範

## 常用指令

### 1. 單項測試
```powershell
# 後端爬蟲與防護門檻測試 (79+ 項測試)
$env:PYTHONIOENCODING="utf-8"; python -m unittest test_update_gist

# 前端 Jest 測試 (113+ 項測試)
npx jest --env=jsdom
```

### 2. 雙測試套件全量驗收（提交 / 推送前強制通過）
```powershell
$env:PYTHONIOENCODING="utf-8"; python -m unittest test_update_gist; npx jest --env=jsdom
```

### 3. 抽象模型算力階級查詢（讀取全域 ~/.gemini/config/model_tiers.json）
```powershell
uv run python tool/maintenance/model_tiers.py --show
```
