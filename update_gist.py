import json
import os
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# ──────────────────────────────────────────────────
# 設定
# ──────────────────────────────────────────────────
GIST_ID = "53c5bb324cd140fb8751c9812bd5df68"
GITHUB_TOKEN = os.environ.get("GIST_TOKEN")
REQUEST_TIMEOUT = 20
PATCH_NAME_RE = re.compile(r'^\d+\.\d+[上下中]$')

PATH_MAP = {
    "Destruction": "毀滅", "Warrior": "毀滅",
    "Hunt": "巡獵", "Rogue": "巡獵",
    "Erudition": "智識", "Mage": "智識",
    "Harmony": "同諧", "Shaman": "同諧",
    "Nihility": "虛無", "Warlock": "虛無",
    "Preservation": "存護", "Knight": "存護",
    "Abundance": "豐饒", "Priest": "豐饒",
    "Remembrance": "記憶", "Memory": "記憶",
    "Elation": "歡愉"
}

ELEM_MAP = {
    "Physical": "物理",
    "Fire": "火",
    "Ice": "冰",
    "Lightning": "雷", "Thunder": "雷",
    "Wind": "風",
    "Quantum": "量子",
    "Imaginary": "虛數"
}

# ──────────────────────────────────────────────────
# 工具函式
# ──────────────────────────────────────────────────
def sanitize_name(name):
    """去除所有非英數字元並轉小寫，用於模糊比對"""
    if not name:
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', name).lower()

CJK_RE = re.compile(
    r'[\u4e00-\u9fff'
    r'\u3400-\u4dbf'
    r'\uf900-\ufaff'
    r'\U00020000-\U0002A6DF'
    r'\U0002A700-\U0002B73F'
    r'\U0002B740-\U0002B81F'
    r'\U0002B820-\U0002CEAF'
    r'\U0002CEB0-\U0002EBEF'
    r'\U0002F800-\U0002FA1F'
    r']'
)

def contains_cjk(text):
    return bool(text and CJK_RE.search(text))

def clean_wikitext_value(val):
    val = re.sub(r'\[\[(?:[^\|\]]*\|)?([^\]]+)\]\]', r'\1', val)
    return val.strip().replace('·', '•')

def normalize_patch_date(value):
    """將各種日期格式標準化為前端使用的 YY/MM/DD 格式"""
    if not value:
        return None
    if isinstance(value, (int, float)):
        value = datetime.fromtimestamp(value / 1000 if value > 10**11 else value).strftime('%Y-%m-%d')
    value = str(value).strip()
    for fmt in ('%y/%m/%d', '%Y/%m/%d', '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ', '%B %d, %Y'):
        try:
            return datetime.strptime(value, fmt).strftime('%y/%m/%d')
        except ValueError:
            continue
    return None

def clean_invalid_runs(chars):
    """清除 runs 中不符合版本格式的汙染資料（如 '4.X上'）"""
    cleaned_count = 0
    for char in chars:
        if 'runs' in char and isinstance(char['runs'], list):
            original = char['runs']
            char['runs'] = [r for r in original if isinstance(r, str) and PATCH_NAME_RE.fullmatch(r)]
            removed = set(original) - set(char['runs'])
            if removed:
                print(f"🧹 清除 [{char.get('name', '?')}] 的無效版本名：{removed}")
                cleaned_count += 1
    return cleaned_count

def merge_new_patches(existing_patches, new_patch_items):
    """
    合併並依日期排序可驗證的版本清單。
    new_patch_items: list of {'patch': str, 'date': str (YY/MM/DD)}
    """
    patches_by_name = {}
    for patch in (existing_patches or []):
        if not isinstance(patch, dict):
            continue
        name = patch.get('patch')
        date = normalize_patch_date(patch.get('date'))
        if isinstance(name, str) and PATCH_NAME_RE.fullmatch(name) and date:
            patches_by_name[name] = {'patch': name, 'date': date}

    for item in new_patch_items:
        name = item.get('patch')
        date = normalize_patch_date(item.get('date'))
        if not isinstance(name, str) or not PATCH_NAME_RE.fullmatch(name):
            print(f"⚠️ 略過格式不正確的版本：{name!r}")
        elif not date:
            print(f"⚠️ 略過沒有可驗證日期的版本：{name}")
        else:
            if name not in patches_by_name:
                patches_by_name[name] = {'patch': name, 'date': date}
                print(f"📅 收錄新版本：{name} ({date})")

    return sorted(patches_by_name.values(), key=lambda p: (p['date'], p['patch']))


# ──────────────────────────────────────────────────
# 資料來源 A：HoyoLAB 官方遊戲日曆 API（最可靠）
# ──────────────────────────────────────────────────
def fetch_hoyolab_schedules():
    """
    從 HoyoLAB API 抓取當前及近期的卡池活動資料。
    此 API 為官方公開端點，無需登入，不受 Cloudflare 阻擋。
    """
    print("正在從 HoyoLAB 官方遊戲日曆 API 抓取卡池資料...")
    schedules = []
    new_patches = []

    # HoyoLAB 遊戲活動日曆 API（繁中）
    url = "https://bbs-api-os.hoyolab.com/game_record/hkrpg/api/note"
    # 使用公開的遊戲活動 API
    act_url = "https://sg-public-api.hoyolab.com/event/game_record/hkrpg/api/act_calendar"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://act.hoyolab.com/",
        "Accept": "application/json",
        "x-rpc-app_version": "2.42.0",
        "x-rpc-client_type": "5",
        "x-rpc-language": "zh-tw",
    }

    try:
        # 嘗試 HoyoLAB 活動 API（公開版，無需 Cookie）
        gacha_url = "https://sg-public-api.hoyolab.com/event/hkrpg/api/gacha_schedule"
        res = requests.get(gacha_url, headers=headers, timeout=REQUEST_TIMEOUT)
        res.raise_for_status()
        data = res.json()

        if data.get("retcode") == 0 and data.get("data"):
            gacha_list = data["data"].get("gacha_list") or data["data"].get("list") or []
            for item in gacha_list:
                _parse_hoyolab_item(item, schedules, new_patches)

        if schedules:
            print(f"✅ HoyoLAB API 成功取得 {len(schedules)} 筆卡池資料")
            return schedules, new_patches

    except Exception as e:
        print(f"⚠️ HoyoLAB gacha_schedule API 失敗: {e}")

    # 備援：嘗試公告類 API
    try:
        ann_url = "https://sg-public-api.hoyolab.com/announcement/api/getAnnContent"
        params = {
            "game": "hkrpg",
            "game_biz": "hkrpg_global",
            "lang": "zh-tw",
            "bundle_id": "hkrpg_global",
            "platform": "pc",
            "region": "prod_official_asia",
            "uid": "0",
            "announcement_id": "0"
        }
        res = requests.get(ann_url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            data = res.json()
            if data.get("retcode") == 0:
                for item in (data.get("data") or {}).get("list") or []:
                    _parse_hoyolab_item(item, schedules, new_patches)

    except Exception as e:
        print(f"⚠️ HoyoLAB 備援 API 失敗: {e}")

    if schedules:
        print(f"✅ HoyoLAB 備援 API 取得 {len(schedules)} 筆卡池資料")
    return schedules, new_patches


def _parse_hoyolab_item(item, schedules, new_patches):
    """解析單筆 HoyoLAB 卡池活動資料"""
    if not isinstance(item, dict):
        return

    # 嘗試提取角色名稱
    char_name = (item.get("gacha_name") or item.get("character") or
                 item.get("name") or item.get("title") or "")
    # 嘗試提取版本與期別
    version = item.get("version") or item.get("patch") or ""
    phase = item.get("phase") or item.get("half") or 1
    start_time = (item.get("start_time") or item.get("begin_time") or
                  item.get("start_date") or item.get("startDate") or "")

    if not char_name or not version:
        return

    half_str = "下" if str(phase) in ("2", "下") else "上"
    run_str = f"{version}{half_str}"
    patch_date = normalize_patch_date(start_time)

    schedules.append({
        "en_name": str(char_name).strip(),
        "fallback_path": PATH_MAP.get(item.get("path", ""), "未知"),
        "fallback_elem": ELEM_MAP.get(item.get("element", ""), "未知"),
        "run": run_str,
        "patch_date": patch_date
    })
    if patch_date:
        new_patches.append({"patch": run_str, "date": patch_date})
    print(f"  → HoyoLAB 解析: {char_name} → {run_str}")


# ──────────────────────────────────────────────────
# 資料來源 B：Fandom Wiki Category:Upcoming_Characters
# ──────────────────────────────────────────────────
def fetch_upcoming_wiki_char_map():
    """
    透過 Fandom Wiki MediaWiki API 抓取 Upcoming_Characters 分類的繁中譯名。
    使用標準 requests（非 cffi），不依賴 Cloudflare 繞過。
    """
    print("正在從 Fandom Wiki 抓取新角色中文譯名...")
    wiki_map = {}

    try:
        api_url = "https://honkai-star-rail.fandom.com/api.php"
        session = requests.Session()
        session.headers.update({
            "User-Agent": "HSRBannerBot/2.0 (https://github.com/ShibaShika/hsr-banner)"
        })

        # Step 1: 取得分類成員清單
        cat_res = session.get(api_url, params={
            "action": "query",
            "list": "categorymembers",
            "cmtitle": "Category:Upcoming_Characters",
            "cmlimit": "500",
            "format": "json"
        }, timeout=REQUEST_TIMEOUT)
        cat_res.raise_for_status()

        members = cat_res.json().get("query", {}).get("categorymembers", [])
        page_titles = [m["title"] for m in members if "title" in m]

        if not page_titles:
            print("⚠️ Wiki 未找到 Upcoming_Characters 分類成員")
            return wiki_map

        print(f"  → 找到 {len(page_titles)} 個頁面，正在提取繁中名稱...")

        # Step 2: 批次取得頁面 wikitext 內容
        # MediaWiki API 每次最多查 50 個頁面
        for i in range(0, len(page_titles), 50):
            batch = page_titles[i:i+50]
            pages_res = session.get(api_url, params={
                "action": "query",
                "prop": "revisions",
                "titles": "|".join(batch),
                "rvprop": "content",
                "rvslots": "main",
                "format": "json"
            }, timeout=REQUEST_TIMEOUT)
            pages_res.raise_for_status()
            pages = pages_res.json().get("query", {}).get("pages", {})

            for p_id, p_info in pages.items():
                if p_id == "-1":
                    continue
                title = p_info.get("title", "")
                revisions = p_info.get("revisions", [])
                if not revisions:
                    continue

                rev = revisions[0]
                content = (rev.get("*") or
                           rev.get("slots", {}).get("main", {}).get("*", ""))
                if not content:
                    continue

                cht_name = ""
                # 優先取繁中 (zht / zh-tw / zh-hk)
                m = re.search(r'\|(?:zht|zh[-_]?(?:tw|hk))\s*=\s*([^\n\|]+)', content, re.IGNORECASE)
                if m and m.group(1).strip():
                    cht_name = clean_wikitext_value(m.group(1))
                else:
                    m = re.search(r'\|zh\s*=\s*([^\n\|]+)', content, re.IGNORECASE)
                    if m and m.group(1).strip():
                        cht_name = clean_wikitext_value(m.group(1))

                if cht_name:
                    wiki_map[sanitize_name(title)] = cht_name
                    print(f"  → Wiki 譯名: {title} ➡️ {cht_name}")

    except Exception as e:
        print(f"⚠️ Fandom Wiki 抓取失敗: {e}")

    return wiki_map


# ──────────────────────────────────────────────────
# 資料來源 C：StarRailRes 角色資料庫（ID / 路徑 / 屬性）
# ──────────────────────────────────────────────────
def fetch_starrailres_data():
    print("正在從 StarRailRes 抓取角色資料庫...")
    base = "https://raw.githubusercontent.com/Mar-7th/StarRailRes/master/index_new"
    try:
        en_res = requests.get(f"{base}/en/characters.json", timeout=REQUEST_TIMEOUT)
        cht_res = requests.get(f"{base}/cht/characters.json", timeout=REQUEST_TIMEOUT)
        en_res.raise_for_status()
        cht_res.raise_for_status()
        print("  → StarRailRes 資料庫載入成功")
        return en_res.json(), cht_res.json()
    except (requests.RequestException, ValueError) as e:
        raise RuntimeError(f"無法取得 StarRailRes 角色資料：{e}") from e


# ──────────────────────────────────────────────────
# 資料整合主流程
# ──────────────────────────────────────────────────
def fetch_latest_data():
    print("\n" + "="*55)
    print("🚀 開始執行 HSR Banner 自動更新流程")
    print("="*55)

    # Step 1: 從 HoyoLAB 取得卡池排程
    schedules, new_patch_items = fetch_hoyolab_schedules()

    # 🛡️ 熔斷機制
    if not schedules:
        print("\n⚠️ 警告：所有資料來源均無法取得有效卡池資料。")
        print("🛡️ 觸發熔斷保護，停止本次更新，避免空白資料覆蓋現有 Gist。")
        return None

    # Step 2: 從 Gist 讀取現有資料
    existing_data = {"new_patches": [], "new_characters": []}
    try:
        gist_url = f"https://api.github.com/gists/{GIST_ID}"
        gist_res = requests.get(gist_url, timeout=REQUEST_TIMEOUT)
        gist_res.raise_for_status()
        files = gist_res.json().get('files', {})
        gist_file = files.get('hsr_latest_banner.json')
        if not gist_file or 'content' not in gist_file:
            raise RuntimeError('Gist 缺少 hsr_latest_banner.json')
        existing_data = json.loads(gist_file['content'])
        if not isinstance(existing_data, dict):
            raise ValueError('Gist 根節點必須是物件')
        print(f"\n📖 Gist 現有資料：{len(existing_data.get('new_characters', []))} 個角色、{len(existing_data.get('new_patches', []))} 個版本")
    except Exception as e:
        print(f"\n❌ 讀取現有 Gist 失敗: {e}")
        print("🛡️ 停止更新，保護現有資料。")
        return None

    updated_chars = existing_data.get('new_characters', [])

    # Step 3: 清洗舊格式 runs（dict 格式 → str 格式）
    for char in updated_chars:
        if 'runs' in char and isinstance(char['runs'], list):
            clean_runs = []
            for r in char['runs']:
                if isinstance(r, str):
                    clean_runs.append(r)
                elif isinstance(r, dict) and 'version' in r and 'phase' in r:
                    half = "上" if r['phase'] == 1 else "下"
                    clean_runs.append(f"{r['version']}{half}")
            char['runs'] = clean_runs

    # ✨ Step 4: 清洗無效版本名（如 '4.X上'）
    cleaned = clean_invalid_runs(updated_chars)
    if cleaned:
        print(f"\n🧹 已清理 {cleaned} 個角色的無效版本名稱")

    # Step 5: 載入 StarRailRes 資料庫 + Wiki 預載
    en_data, cht_data = fetch_starrailres_data()
    wiki_upcoming_map = fetch_upcoming_wiki_char_map()

    # 建立英文名 → CID 的 sanitize 對照
    en_sanitized_map = {}
    for cid, info in en_data.items():
        name = info.get("name", "") if isinstance(info, dict) else str(info)
        sanitized = sanitize_name(name)
        if sanitized:
            en_sanitized_map[sanitized] = cid

    # 建立現有角色快速查找
    existing_char_map_by_cid = {c['cid']: c for c in updated_chars if c.get('cid')}
    existing_char_map_by_name = {c['name']: c for c in updated_chars}

    print(f"\n🔄 開始處理 {len(schedules)} 筆卡池排程...")

    # Step 6: 整合卡池排程到角色資料
    for sched in schedules:
        en_name = sched['en_name']
        sanitized_query = sanitize_name(en_name)

        target_cid = None
        target_name = en_name
        path = sched['fallback_path']
        elem = sched['fallback_elem']

        # A. 優先比對 StarRailRes 正式解包資料庫
        if sanitized_query in en_sanitized_map:
            target_cid = en_sanitized_map[sanitized_query]
            cht_info = cht_data.get(target_cid, {})
            if isinstance(cht_info, dict):
                target_name = cht_info.get("name", en_name)
                db_path = cht_info.get("path")
                raw_path = db_path.get("name", path) if isinstance(db_path, dict) else (db_path if isinstance(db_path, str) else path)
                path = PATH_MAP.get(raw_path, raw_path)
                db_elem = cht_info.get("element")
                raw_elem = db_elem.get("name", elem) if isinstance(db_elem, dict) else (db_elem if isinstance(db_elem, str) else elem)
                elem = ELEM_MAP.get(raw_elem, raw_elem)
            elif isinstance(cht_info, str):
                target_name = cht_info

        # B. 備援：Wiki Upcoming Category
        if target_name == en_name or not contains_cjk(target_name):
            if sanitized_query in wiki_upcoming_map:
                target_name = wiki_upcoming_map[sanitized_query]
                print(f"  ✨ Wiki 對照: {en_name} ➡️ {target_name}")

        # C. 比對現有 Gist 角色（名稱 > 英文名 sanitize > CID）
        matched_char = None
        if target_name in existing_char_map_by_name:
            matched_char = existing_char_map_by_name[target_name]
        else:
            for char in updated_chars:
                if sanitize_name(char['name']) == sanitized_query:
                    matched_char = char
                    break
        if not matched_char and target_cid and target_cid in existing_char_map_by_cid:
            matched_char = existing_char_map_by_cid[target_cid]

        if matched_char:
            # 自動升級英文名為繁中名
            if (matched_char['name'] != target_name and target_name != en_name
                    and not contains_cjk(matched_char['name']) and contains_cjk(target_name)):
                print(f"  🔄 名稱升級: {matched_char['name']} → {target_name}")
                matched_char['name'] = target_name

            # 補全 cid
            if target_cid and (not matched_char.get('cid') or matched_char['name'] == target_name):
                matched_char['cid'] = target_cid

            # 補全 path / elem
            if matched_char.get('path') in ["未知", ""] and path != "未知":
                matched_char['path'] = path
            if matched_char.get('elem') in ["未知", ""] and elem != "未知":
                matched_char['elem'] = elem

            # 新增 run（聯動角色跳過）
            if matched_char.get('isCollab'):
                matched_char['runs'] = []
            else:
                if 'runs' not in matched_char or not isinstance(matched_char['runs'], list):
                    matched_char['runs'] = []
                if sched['run'] not in matched_char['runs']:
                    matched_char['runs'].append(sched['run'])
                    print(f"  📅 新增排程: {matched_char['name']} → {sched['run']}")
        else:
            new_char = {
                "cid": target_cid,
                "name": target_name,
                "path": path,
                "elem": elem,
                "runs": [sched['run']]
            }
            updated_chars.append(new_char)
            if target_cid:
                existing_char_map_by_cid[target_cid] = new_char
            existing_char_map_by_name[target_name] = new_char
            print(f"  ✨ 新角色: {target_name} (CID: {target_cid}) [{path} / {elem}]")

    result = {
        "new_patches": merge_new_patches(
            existing_data.get('new_patches', []),
            new_patch_items
        ),
        "new_characters": updated_chars
    }

    print(f"\n📊 更新結果：{len(result['new_characters'])} 個角色、{len(result['new_patches'])} 個版本")
    return result


# ──────────────────────────────────────────────────
# 回寫 Gist
# ──────────────────────────────────────────────────
def update_gist(data):
    print("\n準備將最新資料同步回 GitHub Gist...")
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
    try:
        response = requests.patch(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        print("✅ Gist 更新成功！")
        return True
    except requests.RequestException as error:
        print(f"❌ Gist 更新失敗: {error}")
        return False


# ──────────────────────────────────────────────────
# 入口
# ──────────────────────────────────────────────────
if __name__ == "__main__":
    if not GITHUB_TOKEN:
        print("❌ 找不到 GIST_TOKEN 環境變數。")
        raise SystemExit(1)

    latest_data = fetch_latest_data()
    if latest_data is not None:
        if not update_gist(latest_data):
            raise SystemExit(1)
    else:
        print("\n🛑 任務安全終止：保持現有 Gist 資料不變。")
        # 回傳非零 exit code 讓 Actions 標記為失敗，方便通知
        raise SystemExit(2)
