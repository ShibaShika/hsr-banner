import json
import os
import re
import requests
from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

GIST_ID = "53c5bb324cd140fb8751c9812bd5df68"
GITHUB_TOKEN = os.environ.get("GIST_TOKEN")

PATH_MAP = {
    "Destruction": "毀滅",
    "Warrior": "毀滅",
    "Hunt": "巡獵",
    "Rogue": "巡獵",
    "Erudition": "智識",
    "Mage": "智識",
    "Harmony": "同諧",
    "Shaman": "同諧",
    "Nihility": "虛無",
    "Warlock": "虛無",
    "Preservation": "存護",
    "Knight": "存護",
    "Abundance": "豐饒",
    "Priest": "豐饒",
    "Remembrance": "記憶",
    "Memory": "記憶",
    "Elation": "歡愉",
}

ELEM_MAP = {
    "Physical": "物理",
    "Fire": "火",
    "Ice": "冰",
    "Lightning": "雷",
    "Thunder": "雷",
    "Wind": "風",
    "Quantum": "量子",
    "Imaginary": "虛數",
}


def sanitize_name(name):
    """去除空格與所有非英數字元（包含 • 等符號），並轉為小寫"""
    if not name:
        return ""
    return re.sub(r"[^a-zA-Z0-9]", "", name).lower()


def fetch_upcoming_wiki_char_map():
    """自動連線 Fandom Wiki 的 Category:Upcoming_Characters API，
    提取所有新角色的 Wikitext 繁體中文譯名 (|zh_tw = 或 |zh =)
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    wiki_map = {}
    try:
        api_url = "https://honkai-star-rail.fandom.com/api.php"

        # 1. 取得 Category:Upcoming_Characters 的所有頁面清單
        cat_params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": "Category:Upcoming_Characters",
            "cmlimit": "500",
            "format": "json",
        }
        res = requests.get(
            api_url, params=cat_params, headers=headers, timeout=5
        ).json()
        members = res.get("query", {}).get("categorymembers", [])

        page_titles = [m["title"] for m in members if "title" in m]
        if not page_titles:
            return wiki_map

        # 2. 批次查詢這些頁面的內容，提取中文譯名
        pages_params = {
            "action": "query",
            "prop": "revisions",
            "titles": "|".join(page_titles),
            "rvprop": "content",
            "format": "json",
        }
        pages_res = requests.get(
            api_url, params=pages_params, headers=headers, timeout=5
        ).json()
        pages = pages_res.get("query", {}).get("pages", {})

        for p_id, p_info in pages.items():
            if p_id == "-1":
                continue
            title = p_info.get("title", "")
            revisions = p_info.get("revisions", [])
            if not revisions:
                continue

            content = revisions[0].get("*", "")

            cht_name = ""
            match_tw = re.search(
                r"\|zh_tw\s*=\s*([^\n\|]+)", content, re.IGNORECASE
            )
            if match_tw and match_tw.group(1).strip():
                cht_name = match_tw.group(1).strip().replace("·", "•")
            else:
                match_zh = re.search(
                    r"\|zh\s*=\s*([^\n\|]+)", content, re.IGNORECASE
                )
                if match_zh and match_zh.group(1).strip():
                    cht_name = match_zh.group(1).strip().replace("·", "•")

            if cht_name:
                # 將 "Aventurine • Waveflair" 簡化為 "aventurinewaveflair" 作為 Key
                sanitized_key = sanitize_name(title)
                wiki_map[sanitized_key] = cht_name
                print(f"📖 Wiki 分類庫載入角色: {title} ➡️ {cht_name}")

    except Exception as e:
        print(f"⚠️ 抓取 Wiki Category:Upcoming_Characters 失敗: {e}")

    return wiki_map


def fetch_starrailres_data():
    print("正在從 StarRailRes (index_new) 抓取完整角色資料庫...")
    en_url = "https://raw.githubusercontent.com/Mar-7th/StarRailRes/refs/heads/master/index_new/en/characters.json"
    cht_url = "https://raw.githubusercontent.com/Mar-7th/StarRailRes/refs/heads/master/index_new/cht/characters.json"

    en_res = requests.get(en_url)
    cht_res = requests.get(cht_url)

    en_data = en_res.json() if en_res.status_code == 200 else {}
    cht_data = cht_res.json() if cht_res.status_code == 200 else {}

    return en_data, cht_data


def fetch_prydwen_schedules():
    print("正在從 Prydwen 抓取卡池資訊...")
    url = "https://www.prydwen.gg/star-rail/banners/"
    try:
        res = cffi_requests.get(url, impersonate="chrome110")
        if res.status_code != 200:
            print(f"❌ Prydwen 抓取失敗: HTTP {res.status_code}")
            return []

        soup = BeautifulSoup(res.text, "html.parser")
        schedules = []

        cards = soup.find_all("article", class_="character-banner-card")
        for card in cards:
            name_tag = card.find(class_="banner-name")
            if not name_tag:
                continue
            en_name = name_tag.text.strip()

            path_span = card.find(class_=re.compile(r"path\s+"))
            en_path = (
                path_span.find("strong").text.strip()
                if path_span and path_span.find("strong")
                else ""
            )
            zh_path = PATH_MAP.get(en_path, "未知")

            elem_span = card.find(class_=re.compile(r"element\s+"))
            en_elem = (
                elem_span.find("strong").text.strip()
                if elem_span and elem_span.find("strong")
                else ""
            )
            zh_elem = ELEM_MAP.get(en_elem, "未知")

            meta_div = card.find(class_="banner-phase-meta")
            phase_str = (
                meta_div.find("span").text.strip()
                if meta_div and meta_div.find("span")
                else ""
            )

            version_match = re.search(r"Patch ([\d\.X]+)", phase_str)
            if not version_match:
                continue

            version = version_match.group(1)
            phase_num = 2 if "Phase 2" in phase_str else 1
            half_str = "上" if phase_num == 1 else "下"
            run_str = f"{version}{half_str}"

            schedules.append({
                "en_name": en_name,
                "fallback_path": zh_path,
                "fallback_elem": zh_elem,
                "run": run_str,
            })
            print(f"解析卡池角色: {en_name} -> {run_str}")

        return schedules
    except Exception as e:
        print(f"抓取 Prydwen 發生錯誤: {e}")
        return []


def fetch_latest_data():
    print("正在檢查遠端與公開資料源...")

    existing_data = {"new_patches": [], "new_characters": []}
    try:
        gist_url = f"https://api.github.com/gists/{GIST_ID}"
        gist_res = requests.get(gist_url)
        if gist_res.status_code == 200:
            files = gist_res.json().get("files", {})
            if "hsr_latest_banner.json" in files:
                existing_data = json.loads(
                    files["hsr_latest_banner.json"]["content"]
                )
    except Exception as e:
        print(f"讀取現有 Gist 失敗: {e}")

    updated_chars = existing_data.get("new_characters", [])

    # 清洗舊格式 runs
    for char in updated_chars:
        clean_runs = []
        if "runs" in char and isinstance(char["runs"], list):
            for r in char["runs"]:
                if isinstance(r, str):
                    clean_runs.append(r)
                elif isinstance(r, dict) and "version" in r and "phase" in r:
                    half = "上" if r["phase"] == 1 else "下"
                    clean_runs.append(f"{r['version']}{half}")
        char["runs"] = clean_runs

    # 1. 取得資料庫與 Wiki 預載清單
    en_data, cht_data = fetch_starrailres_data()
    wiki_upcoming_map = fetch_upcoming_wiki_char_map()

    en_sanitized_map = {}
    for cid, info in en_data.items():
        name = info.get("name", "") if isinstance(info, dict) else str(info)
        sanitized = sanitize_name(name)
        if sanitized:
            en_sanitized_map[sanitized] = cid

    schedules = fetch_prydwen_schedules()

    # 建立現有角色的快速查找對照
    existing_char_map_by_cid = {
        c["cid"]: c for c in updated_chars if c.get("cid")
    }
    existing_char_map_by_name = {c["name"]: c for c in updated_chars}

    for sched in schedules:
        en_name = sched["en_name"]
        sanitized_query = sanitize_name(en_name)

        target_cid = None
        target_name = en_name
        path = sched["fallback_path"]
        elem = sched["fallback_elem"]

        # A. 優先比對 StarRailRes 正式解包資料庫
        if sanitized_query in en_sanitized_map:
            target_cid = en_sanitized_map[sanitized_query]
            cht_info = cht_data.get(target_cid, {})

            if isinstance(cht_info, dict):
                target_name = cht_info.get("name", en_name)

                db_path = cht_info.get("path")
                if isinstance(db_path, dict):
                    raw_path = db_path.get("name", path)
                elif isinstance(db_path, str):
                    raw_path = db_path
                else:
                    raw_path = path
                path = PATH_MAP.get(raw_path, raw_path)

                db_elem = cht_info.get("element")
                if isinstance(db_elem, dict):
                    raw_elem = db_elem.get("name", elem)
                elif isinstance(db_elem, str):
                    raw_elem = db_elem
                else:
                    raw_elem = elem
                elem = ELEM_MAP.get(raw_elem, raw_elem)

            elif isinstance(cht_info, str):
                target_name = cht_info

        # B. 備援機制：如果 StarRailRes 還沒更新，自動對照 Wiki Upcoming Category
        if target_name == en_name or not any(
            "\u4e00" <= char <= "\u9fff" for char in target_name
        ):
            if sanitized_query in wiki_upcoming_map:
                target_name = wiki_upcoming_map[sanitized_query]
                print(
                    "✨ 成功從 Wiki Upcoming 分類自動對照繁中名稱:"
                    f" {en_name} ➡️ {target_name}"
                )

        # C. 尋找是否已存在於 Gist 中 (透過 cid 或名稱模糊匹配)
        matched_char = None
        if target_cid and target_cid in existing_char_map_by_cid:
            matched_char = existing_char_map_by_cid[target_cid]
        elif target_name in existing_char_map_by_name:
            matched_char = existing_char_map_by_name[target_name]
        else:
            for char in updated_chars:
                if sanitize_name(char["name"]) == sanitized_query:
                    matched_char = char
                    break

        if matched_char:
            # 自動補全或更新 cid
            if target_cid and not matched_char.get("cid"):
                matched_char["cid"] = target_cid

            # 自動將舊英文名升級為正確繁中名
            if matched_char["name"] != target_name and target_name != en_name:
                print(
                    "🔄 自動將名稱升級為正式中文:"
                    f" {matched_char['name']} -> {target_name}"
                )
                matched_char["name"] = target_name

            if matched_char.get("path") in ["未知", ""] and path != "未知":
                matched_char["path"] = path
            if matched_char.get("elem") in ["未知", ""] and elem != "未知":
                matched_char["elem"] = elem

            if "runs" not in matched_char or not isinstance(
                matched_char["runs"], list
            ):
                matched_char["runs"] = []

            if sched["run"] not in matched_char["runs"]:
                matched_char["runs"].append(sched["run"])
                print(
                    f"📅 自動排程成功: 將 {matched_char['name']} 安排至"
                    f" {sched['run']}"
                )
        else:
            new_char = {
                "cid": target_cid,
                "name": target_name,
                "path": path,
                "elem": elem,
                "runs": [sched["run"]],
            }
            updated_chars.append(new_char)
            if target_cid:
                existing_char_map_by_cid[target_cid] = new_char
            existing_char_map_by_name[target_name] = new_char
            print(
                f"✨ 發現並納入新角色: {target_name} (CID: {target_cid})"
                f" ({path} / {elem})"
            )

    return {
        "new_patches": existing_data.get("new_patches", []),
        "new_characters": updated_chars,
    }


def update_gist(data):
    print("準備將最新資料同步回 GitHub Gist...")
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    payload = {
        "files": {
            "hsr_latest_banner.json": {
                "content": json.dumps(data, ensure_ascii=False, indent=4)
            }
        }
    }

    response = requests.patch(url, headers=headers, json=payload)
    if response.status_code == 200:
        print("✅ Gist 自動更新與排程指派成功！")
    else:
        print(f"❌ 更新失敗: {response.status_code}")


if __name__ == "__main__":
    if not GITHUB_TOKEN:
        print("❌ 找不到 GIST_TOKEN 環境變數。")
    else:
        latest_data = fetch_latest_data()
        update_gist(latest_data)
