"""
通用多 Agent 協同體系 - 看板與交接狀態秒級診斷工具 (Handoff Checker)
職責：
1. 實體讀取 docs/HANDOFF.md 頂部的『🚩 【當前接力棒 (Active Baton)】』
2. 檢查工作區 Git 狀態（確認是否有未提交變更）
3. 自動推導下一棒負責角色，杜絕憑對話記憶誤判交接進度
"""

import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HANDOFF_FILE = PROJECT_ROOT / "docs" / "HANDOFF.md"
SESSIONS_FILE = PROJECT_ROOT / "docs" / "agent_sessions.json"

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 通用接力棒關鍵字 -> 角色映射表（可依專案角色擴充）
DEFAULT_ROLE_KEYWORDS = [
    ("發布", "🔄 發布工程師"),
    ("release", "🔄 發布工程師"),
    ("技術主管", "👑 技術主管"),
    ("主管", "👑 技術主管"),
    ("tech_lead", "👑 技術主管"),
    ("後端", "⚙️ 後端 / 核心邏輯專家"),
    ("backend", "⚙️ 後端 / 核心邏輯專家"),
    ("前端", "🎨 前端 / 介面設計師"),
    ("frontend", "🎨 前端 / 介面設計師"),
    ("測試", "🧪 品質驗證專家"),
    ("qa", "🧪 品質驗證專家"),
]


def get_active_baton() -> str:
    """從 docs/HANDOFF.md 讀取最新接力棒內容。"""
    if not HANDOFF_FILE.exists():
        return "UNKNOWN (HANDOFF.md 不存在)"
    try:
        content = HANDOFF_FILE.read_text(encoding="utf-8")
        match = re.search(r"【當前接力棒[^】]*】[*]*\s*[：:]\s*[`*]*([^`*\r\n]+)[`*]*", content)
        if match:
            return match.group(1).strip()
    except Exception as exc:
        return f"ERROR ({exc})"
    return "UNKNOWN"


def get_git_changes() -> list[str]:
    """取得目前 Git 工作區的變更檔案清單。"""
    try:
        res = subprocess.run(
            ["git", "status", "-s"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return [line.strip() for line in res.stdout.strip().splitlines() if line.strip()]
    except Exception:
        return []


def resolve_next_role(baton: str) -> str:
    """根據接力棒字串與專案角色表推導下一棒負責人。"""
    lowered = baton.lower()
    for keyword, role_label in DEFAULT_ROLE_KEYWORDS:
        if keyword in baton or keyword in lowered:
            return role_label

    # 若專案於 agent_sessions.json 擴充了自訂 role_key / title，動態補充比對
    if SESSIONS_FILE.exists():
        try:
            data = json.loads(SESSIONS_FILE.read_text(encoding="utf-8"))
            for rkey, info in data.get("available_roles", {}).items():
                title = info.get("title", "")
                if rkey.lower() in lowered or (title and title in baton):
                    return title or rkey
        except Exception:
            pass

    return "待命 (Standby)"


def main() -> None:
    project_name = PROJECT_ROOT.name
    print("=" * 60)
    print(f"  {project_name} - 看板與交接即時檢測 (Handoff Checker)")
    print("=" * 60)

    baton = get_active_baton()
    print(f"[BATON] 磁碟最新接力棒 : {baton}")

    changes = get_git_changes()
    print(f"[GIT]   工作區變更檔案數 : {len(changes)}")
    for ch in changes[:8]:
        print(f"        -> {ch}")
    if len(changes) > 8:
        print(f"        -> ... (其餘 {len(changes) - 8} 個省略)")

    target_role = resolve_next_role(baton)
    print("-" * 60)
    print(f"[ACTION] 下一個該動手的角色: {target_role}")
    if changes and ("審核" in baton or "驗收" in baton):
        print("💡 提示: 偵測到已有工作區程式碼變更，請技術主管進行審核與測試把關。")
    print("=" * 60)


if __name__ == "__main__":
    main()
