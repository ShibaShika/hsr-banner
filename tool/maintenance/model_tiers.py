"""
跨專案共用的模型算力階級讀取與自動同步工具 (Model Tiers)。

設計目標：
1. 消除規則與維護腳本對特定 AI 型號名稱的硬編碼依賴。
2. 支援直接解析 Antigravity 2 `swarm(action="models", all=True)` 的即時回應，
   依算力階級與即時剩餘額度自動排序並寫入共用的 `model_tiers.json`。
3. 讀取優先序：專案 `docs/model_tiers.json` > 全域 `~/.gemini/config/model_tiers.json` > 內建抽象回退描述。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# 防止 Windows CP950 控制台輸出 UTF-8 字元失敗
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

TZ_TAIPEI = timezone(timedelta(hours=8))
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GLOBAL_MODEL_TIERS_PATH = Path.home() / ".gemini" / "config" / "model_tiers.json"

THINKING_ORDER = ("Low", "Medium", "High", "XHigh")
THINKING_RANK = {name: idx for idx, name in enumerate(THINKING_ORDER)}

TIER_META = {
    "light": {
        "label": "輕量極速級",
        "preferred_thinking": ("Low", "Medium", "High"),
        "fallback_display": "輕量極速模型 (Low)",
    },
    "standard": {
        "label": "常規主力級",
        "preferred_thinking": ("High", "Medium", "Low"),
        "fallback_display": "常規主力模型 (High)",
    },
    "heavy": {
        "label": "高階推理級",
        "preferred_thinking": ("High", "XHigh", "Medium"),
        "fallback_display": "高階旗艦模型 (High)",
    },
}


def resolve_tiers_read_path(
    project_root: Path | None = None,
    global_path: Path | None = None,
) -> Path | None:
    """按『專案覆蓋 > 全域共用』順序回傳存在的設定檔路徑。"""
    root = project_root or PROJECT_ROOT
    project_file = root / "docs" / "model_tiers.json"
    if project_file.is_file():
        return project_file

    shared_file = global_path or GLOBAL_MODEL_TIERS_PATH
    if shared_file.is_file():
        return shared_file
    return None


def load_model_tiers(
    project_root: Path | None = None,
    global_path: Path | None = None,
) -> dict[str, Any]:
    """載入目前生效的模型階級設定；若尚無檔案或解析異常則回傳空階級結構。"""
    target = resolve_tiers_read_path(project_root=project_root, global_path=global_path)
    if target is None:
        return {"tiers": {}, "thinking_levels": list(THINKING_ORDER)}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("tiers"), dict):
            return data
    except Exception:
        pass
    return {"tiers": {}, "thinking_levels": list(THINKING_ORDER)}


def format_tier_recommendation(
    tier_key: str,
    project_root: Path | None = None,
    global_path: Path | None = None,
    with_quota: bool = False,
) -> str:
    """取得指定算力階級的可讀模型建議字串（例如 'Gemini 4 Hydrogen (High)'）。"""
    data = load_model_tiers(project_root=project_root, global_path=global_path)
    tier = data.get("tiers", {}).get(tier_key, {})
    model = tier.get("model")
    if not model:
        return TIER_META.get(tier_key, {}).get("fallback_display", "高階推理模型 (High)")

    thinking = tier.get("thinking")
    base = f"{model} ({thinking})" if thinking else model
    if with_quota and tier.get("quota_remaining"):
        return f"{base} [剩餘額度 {tier['quota_remaining']}]"
    return base


def get_tier_info(
    tier_key: str,
    project_root: Path | None = None,
    global_path: Path | None = None,
) -> dict[str, Any]:
    """取得指定階級完整資訊字典（不存在時回傳含預設說明的字典）。"""
    data = load_model_tiers(project_root=project_root, global_path=global_path)
    tier = data.get("tiers", {}).get(tier_key)
    if isinstance(tier, dict) and tier.get("model"):
        return tier
    return {
        "label": TIER_META.get(tier_key, {}).get("label", tier_key),
        "model": "",
        "thinking": "",
        "candidates": [],
    }


def _parse_version_tuple(family_name: str) -> tuple[int, ...]:
    match = re.search(r"gemini\s+(\d+(?:\.\d+)*)", family_name, re.IGNORECASE)
    if not match:
        return (0,)
    return tuple(int(part) for part in match.group(1).split("."))


def _parse_quota_percent(quota_str: str | None) -> int:
    if not quota_str:
        return -1
    match = re.search(r"(\d+)", str(quota_str))
    return int(match.group(1)) if match else -1


def _pick_thinking(available: list[str], preferred: tuple[str, ...]) -> str:
    for candidate in preferred:
        if candidate in available:
            return candidate
    return available[0] if available else ""


def _pick_max_thinking(available: list[str]) -> str:
    if not available:
        return ""
    return max(available, key=lambda lvl: THINKING_RANK.get(lvl, -1))


def build_tiers_from_swarm_payload(
    payload: dict[str, Any],
    allowed_prefix: str = "gemini-",
    excluded_keywords: tuple[str, ...] = ("claude", "gpt", "orchestrator"),
) -> dict[str, Any]:
    """將 `swarm(action="models", all=True)` 回應轉換為跨專案標準模型階級表。

    僅納入受授權的 Google Gemini 對話/編碼模型，並依即時配額可用性、
    代次版本號與最高思考能力自動排序歸入 light / standard / heavy。
    """
    display_names = payload.get("display_names") or {}
    quotas = payload.get("quotas") or {}
    model_ids = payload.get("models") or list(display_names.keys())

    families: dict[str, dict[str, Any]] = {}
    observed_thinking: set[str] = set()

    for model_id in model_ids:
        lowered_id = str(model_id).lower()
        if not lowered_id.startswith(allowed_prefix):
            continue
        if any(bad in lowered_id for bad in excluded_keywords):
            continue

        display = str(display_names.get(model_id, "")).strip()
        match = re.match(r"^(Gemini\s+.+?)\s*\(([^)]+)\)$", display)
        if not match:
            continue

        family_name = match.group(1).strip()
        thinking_level = match.group(2).strip()
        observed_thinking.add(thinking_level)

        q_info = quotas.get(model_id) or {}
        q_rem = str(q_info.get("quota_remaining", "")).strip()
        q_reset = str(q_info.get("quota_resets", "")).strip()

        entry = families.setdefault(
            family_name,
            {
                "model": family_name,
                "is_flash": "flash" in family_name.lower(),
                "version": _parse_version_tuple(family_name),
                "thinking_levels": [],
                "quota_remaining": q_rem,
                "quota_pct": _parse_quota_percent(q_rem),
                "quota_resets": q_reset,
            },
        )
        if thinking_level not in entry["thinking_levels"]:
            entry["thinking_levels"].append(thinking_level)

        # 若同家族不同檔位配額有差異，保留最高可用百分比供排序参考
        pct = _parse_quota_percent(q_rem)
        if pct > entry["quota_pct"]:
            entry["quota_pct"] = pct
            entry["quota_remaining"] = q_rem
            entry["quota_resets"] = q_reset

    # 依標準順序整理每個家族支援的思考程度
    for entry in families.values():
        entry["thinking_levels"].sort(key=lambda lvl: THINKING_RANK.get(lvl, 99))

    general_reset_times = {
        f["quota_resets"]
        for f in families.values()
        if f["is_flash"] and f["quota_resets"]
    }
    for f in families.values():
        f["is_general_pool"] = f["is_flash"] or (
            bool(f["quota_resets"]) and f["quota_resets"] in general_reset_times
        )

    def rank_key(item: dict[str, Any]) -> tuple[int, tuple[int, ...], int, int, str]:
        has_quota = 1 if item["quota_pct"] > 0 else 0
        max_think = max((THINKING_RANK.get(t, -1) for t in item["thinking_levels"]), default=-1)
        return (has_quota, item["version"], item["quota_pct"], max_think, item["model"])

    flash_candidates = sorted((f for f in families.values() if f["is_flash"]), key=rank_key, reverse=True)
    general_candidates = sorted((f for f in families.values() if f["is_general_pool"]), key=rank_key, reverse=True)
    flagship_candidates = sorted((f for f in families.values() if not f["is_flash"]), key=rank_key, reverse=True)

    # 若平台沒有區分 Flash（例如未來全部整合），回退互補
    if not flash_candidates:
        flash_candidates = flagship_candidates
    if not general_candidates:
        general_candidates = flagship_candidates
    if not flagship_candidates:
        flagship_candidates = flash_candidates

    def serialize_tier(tier_key: str, ranked: list[dict[str, Any]]) -> dict[str, Any]:
        meta = TIER_META[tier_key]
        if not ranked:
            return {
                "label": meta["label"],
                "model": "",
                "thinking": "",
                "candidates": [],
            }
        primary = ranked[0]
        levels = primary["thinking_levels"]
        thinking = _pick_thinking(levels, meta["preferred_thinking"])
        max_thinking = _pick_max_thinking(levels)
        return {
            "label": meta["label"],
            "model": primary["model"],
            "thinking": thinking,
            "max_thinking": max_thinking,
            "quota_remaining": primary["quota_remaining"],
            "quota_resets": primary["quota_resets"],
            "candidates": [
                {
                    "model": c["model"],
                    "thinking_levels": c["thinking_levels"],
                    "quota_remaining": c["quota_remaining"],
                    "quota_resets": c["quota_resets"],
                }
                for c in ranked
            ],
        }

    all_thinking = sorted(
        observed_thinking or set(THINKING_ORDER),
        key=lambda lvl: THINKING_RANK.get(lvl, 99),
    )

    return {
        "_schema_version": "1.0",
        "synced_at": datetime.now(TZ_TAIPEI).isoformat(timespec="seconds"),
        "source": "swarm.models",
        "excluded_families": ["Claude", "GPT"],
        "thinking_levels": all_thinking,
        "tiers": {
            "light": serialize_tier("light", flash_candidates),
            "standard": serialize_tier("standard", general_candidates),
            "heavy": serialize_tier("heavy", flagship_candidates),
        },
    }


def sync_from_swarm_payload(
    payload: dict[str, Any],
    output_path: Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    """依 `swarm(action="models")` 回應生成並寫入模型階級設定檔。"""
    target = output_path or GLOBAL_MODEL_TIERS_PATH
    tiers_data = build_tiers_from_swarm_payload(payload)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(tiers_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target, tiers_data


def format_reset_time_taipei(iso_utc: str) -> str:
    """將雲端 ISO UTC 時間轉為台北時區 (UTC+8) 友善字串。"""
    if not iso_utc:
        return ""
    try:
        dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
        return dt.astimezone(TZ_TAIPEI).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return iso_utc


def main() -> None:
    parser = argparse.ArgumentParser(description="Antigravity 跨專案模型算力階級設定與自動同步工具")
    parser.add_argument("--show", action="store_true", help="顯示目前生效之模型算力階級與路徑")
    parser.add_argument("--sync-file", type=str, help="從指定 JSON 檔案讀取 swarm(models) 回應並同步寫入")
    parser.add_argument("--stdin", action="store_true", help="從標準輸入讀取 swarm(models) JSON 並同步寫入")
    parser.add_argument("--to-project", action="store_true", help="將同步結果寫入當前專案 docs/model_tiers.json（預設寫入全域）")
    args = parser.parse_args()

    if args.sync_file or args.stdin:
        raw = sys.stdin.read() if args.stdin else Path(args.sync_file).read_text(encoding="utf-8")
        payload = json.loads(raw)
        dest = (PROJECT_ROOT / "docs" / "model_tiers.json") if args.to_project else GLOBAL_MODEL_TIERS_PATH
        written_path, synced = sync_from_swarm_payload(payload, output_path=dest)
        print(f"[SYNCED] 模型等級配置已更新: {written_path}")
        for key in ("light", "standard", "heavy"):
            t = synced["tiers"][key]
            print(f"  - {t['label']} ({key}): {t['model']} ({t['thinking']}) | 剩餘額度: {t.get('quota_remaining') or 'N/A'}")
        return

    # 預設 --show
    active_path = resolve_tiers_read_path()
    data = load_model_tiers()
    print(f"生效設定來源: {active_path or '(尚未建立設定檔，使用內建抽象回退)'}")
    print(f"上次同步時間: {data.get('synced_at', '未同步')}")
    print(f"可用思考層級: {', '.join(data.get('thinking_levels', []))}")
    for key in ("light", "standard", "heavy"):
        t = data.get("tiers", {}).get(key, {})
        label = TIER_META[key]["label"]
        print(f"  - {label} ({key}): {format_tier_recommendation(key, with_quota=True)}")
        if key == "heavy" and t.get("max_thinking"):
            print(f"    極限攻堅最高思考檔位: {t['max_thinking']}")


if __name__ == "__main__":
    main()
