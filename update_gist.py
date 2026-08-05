import json
import os
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

GIST_ID = "53c5bb324cd140fb8751c9812bd5df68"
GITHUB_TOKEN = os.environ.get("GIST_TOKEN")
REQUEST_TIMEOUT = 15
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

def sanitize_name(name):
    """去除空格與所有非英數字元（包含 • 等符號），並轉為小寫"""
    if not name:
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', name).lower()

def clean_wikitext_value(val):
    """清洗 Wikitext 中的連結標記 [[ ]] 與取代標點符號"""
    val = re.sub(r'\[\[(?:[^\|\]]*\|)?([^\]]+)\]\]', r'\1', val)
    return val.strip().replace('·', '•')

def normalize_patch_date(value):
    """將資料源的日期標準化為前端使用的 YY/MM/DD 格式。"""
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

def merge_new_patches(existing_patches, schedules):
    """合併並依日期排序可驗證的新增版本，避免不完整資料破壞時間軸。"""
    patches_by_name = {}
    for patch in existing_patches if isinstance(existing_patches, list) else []:
        if not isinstance(patch, dict):
            continue
        name = patch.get('patch')
        date = normalize_patch_date(patch.get('date'))
        if isinstance(name, str) and PATCH_NAME_RE.fullmatch(name) and date:
            patches_by_name[name] = {'patch': name, 'date': date}

    for schedule in schedules:
        name = schedule.get('run')
        date = normalize_patch_date(schedule.get('patch_date'))
        if not isinstance(name, str) or not PATCH_NAME_RE.fullmatch(name):
            print(f"⚠️ 略過格式不正確的版本：{name!r}")
        elif not date:
            print(f"⚠️ 略過沒有可驗證開始日期的版本：{name}")
        else:
            patches_by_name.setdefault(name, {'patch': name, 'date': date})

    return sorted(patches_by_name.values(), key=lambda patch: (patch['date'], patch['patch']))

def fetch_upcoming_wiki_char_map():
    """使用 cffi_requests 繞過 Cloudflare 防護，
    自動連線 Fandom Wiki Category:Upcoming_Characters API 提取新角色的繁體中文譯名
    """
    print("正在從 Fandom Wiki (Upcoming_Characters 分類) 抓取新角色中文譯名...")
    wiki_map = {}

    try:
        api_url = "https://honkai-star-rail.fandom.com/api.php"
        cat_params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": "Category:Upcoming_Characters",
            "cmlimit": "500",
            "format": "json"
        }

        res_obj = cffi_requests.get(api_url, params=cat_params, impersonate="chrome110", timeout=10)
        if res_obj.status_code != 200:
            print(f"⚠️ Fandom API 存取失敗: HTTP {res_obj.status_code}")
            return wiki_map

        res = res_obj.json()
        members = res.get("query", {}).get("categorymembers", [])
        page_titles = [m["title"] for m in members if "title" in m]

        if not page_titles:
            print("⚠️ Wiki 上未找到 Upcoming_Characters 頁面清單")
            return wiki_map

        print(f"🔍 於 Wiki 成功找到 {len(page_titles)} 位新角色頁面，準備提取繁中譯名...")

        pages_params = {
            "action": "query",
            "prop": "revisions",
            "titles": "|".join(page_titles),
            "rvprop": "content",
            "rvslots": "main",
            "format": "json"
        }
        pages_res_obj = cffi_requests.get(api_url, params=pages_params, impersonate="chrome110", timeout=10)
        pages = pages_res_obj.json().get("query", {}).get("pages", {})

        for p_id, p_info in pages.items():
            if p_id == "-1": continue
            title = p_info.get("title", "")
            revisions = p_info.get("revisions", [])
            if not revisions: continue

            rev = revisions[0]
            content = ""
            if "*" in rev:
                content = rev["*"]
            elif "slots" in rev and "main" in rev["slots"] and "*" in rev["slots"]["main"]:
                content = rev["slots"]["main"]["*"]

            if not content: continue

            cht_name = ""
            match_tw = re.search(r'\|(?:zht|zh[-_]?(?:tw|hk))\s*=\s*([^\n\|]+)', content, re.IGNORECASE)
            if match_tw and match_tw.group(1).strip():
                cht_name = clean_wikitext_value(match_tw.group(1))
            else:
                match_zh = re.search(r'\|zh\s*=\s*([^\n\|]+)', content, re.IGNORECASE)
                if match_zh and match_zh.group(1).strip():
                    cht_name = clean_wikitext_value(match_zh.group(1))

            if cht_name:
                sanitized_key = sanitize_name(title)
                wiki_map[sanitized_key] = cht_name
                print(f"📖 Wiki 對照成功載入: {title} ➡️ {cht_name}")

    except Exception as e:
        print(f"⚠️ 抓取 Wiki Category:Upcoming_Characters 發生錯誤: {e}")

    return wiki_map

def fetch_starrailres_data():
    print("正在從 StarRailRes (index_new) 抓取完整角色資料庫...")
    en_url = "https://raw.githubusercontent.com/Mar-7th/StarRailRes/refs/heads/master/index_new/en/characters.json"
    cht_url = "https://raw.githubusercontent.com/Mar-7th/StarRailRes/refs/heads/master/index_new/cht/characters.json"
    
    try:
        en_res = requests.get(en_url, timeout=REQUEST_TIMEOUT)
        cht_res = requests.get(cht_url, timeout=REQUEST_TIMEOUT)
        en_res.raise_for_status()
        cht_res.raise_for_status()
        return en_res.json(), cht_res.json()
    except (requests.RequestException, ValueError) as error:
        raise RuntimeError(f"無法取得 StarRailRes 角色資料：{error}") from error

def parse_next_data_json(json_text):
    """【方法一】直抓 Next.js 底層 __NEXT_DATA__ JSON，免疫版面 DOM 改版"""
    schedules = []
    try:
        data = json.loads(json_text)
        page_props = data.get("props", {}).get("pageProps", {})
        
        # 尋找 pageProps 內可能包含卡池資料的變數
        banner_list = page_props.get("banners") or page_props.get("data") or page_props.get("schedule") or []
        
        if isinstance(banner_list, list):
            for item in banner_list:
                if not isinstance(item, dict): continue
                
                en_name = item.get("name") or item.get("characterName") or item.get("title")
                version = item.get("patch") or item.get("version")
                phase = item.get("phase") or item.get("half")
                patch_date = normalize_patch_date(
                    item.get("startDate") or item.get("start_date") or item.get("date") or item.get("start")
                )
                
                if en_name and version:
                    phase_num = 2 if str(phase) == "2" else 1
                    half_str = "上" if phase_num == 1 else "下"
                    run_str = f"{version}{half_str}"
                    
                    zh_path = PATH_MAP.get(item.get("path", ""), "未知")
                    zh_elem = ELEM_MAP.get(item.get("element", ""), "未知")
                    
                    schedules.append({
                        "en_name": str(en_name).strip(),
                        "fallback_path": zh_path,
                        "fallback_elem": zh_elem,
                        "run": run_str,
                        "patch_date": patch_date
                    })
                    print(f"解析卡池角色 (JSON 模式): {en_name} -> {run_str}")
    except Exception as e:
        print(f"⚠️ __NEXT_DATA__ 解析失敗或結構不吻合: {e}")
        
    return schedules

def fetch_prydwen_schedules():
    print("正在從 Prydwen 抓取卡池資訊...")
    url = "https://www.prydwen.gg/star-rail/banners/"
    try:
        res = cffi_requests.get(url, impersonate="chrome110", timeout=15)
        if res.status_code != 200:
            print(f"❌ Prydwen 存取失敗: HTTP {res.status_code}")
            return []

        soup = BeautifulSoup(res.text, "html.parser")
        schedules = []

        # 優先方案：嘗試抽取 __NEXT_DATA__ 純資料 JSON
        next_data_tag = soup.find("script", id="__NEXT_DATA__")
        if next_data_tag and next_data_tag.string:
            schedules = parse_next_data_json(next_data_tag.string)

        # 備援方案：若 JSON 抽不到資料，自動降級切換回傳統 HTML DOM 爬蟲
        if not schedules:
            print("🔄 JSON 提取無結果，切換至傳統 HTML DOM 解析器...")
            cards = soup.find_all("article", class_="character-banner-card")
            for card in cards:
                name_tag = card.find(class_="banner-name")
                if not name_tag: continue
                en_name = name_tag.text.strip()
                
                path_span = card.find(class_=re.compile(r"path\s+"))
                en_path = path_span.find("strong").text.strip() if path_span and path_span.find("strong") else ""
                zh_path = PATH_MAP.get(en_path, "未知")
                
                elem_span = card.find(class_=re.compile(r"element\s+"))
                en_elem = elem_span.find("strong").text.strip() if elem_span and elem_span.find("strong") else ""
                zh_elem = ELEM_MAP.get(en_elem, "未知")
                
                meta_div = card.find(class_="banner-phase-meta")
                phase_str = meta_div.find("span").text.strip() if meta_div and meta_div.find("span") else ""
                
                version_match = re.search(r"Patch ([\d\.X]+)", phase_str)
                if not version_match: 
                    continue 
                    
                version = version_match.group(1)
                phase_num = 2 if "Phase 2" in phase_str else 1
                half_str = "上" if phase_num == 1 else "下"
                run_str = f"{version}{half_str}"
                date_match = re.search(r'([A-Z][a-z]+\s+\d{1,2},\s+20\d{2})', phase_str)
                patch_date = normalize_patch_date(date_match.group(1)) if date_match else None
                
                schedules.append({
                    "en_name": en_name,
                    "fallback_path": zh_path,
                    "fallback_elem": zh_elem,
                    "run": run_str,
                    "patch_date": patch_date
                })
                print(f"解析卡池角色 (DOM 模式): {en_name} -> {run_str}")
            
        return schedules
    except Exception as e:
        print(f"抓取 Prydwen 發生錯誤: {e}")
        return []

def fetch_latest_data():
    print("正在檢查遠端與公開資料源...")
    
    schedules = fetch_prydwen_schedules()
    
    # 🛡️ 熔斷機制：如果完全沒抓到任何卡池資料（例如被 Cloudflare 強制封鎖或出現驗證碼）
    if not schedules:
        print("⚠️ 警告：無法取得任何有效的卡池資料！(可能遭遇 Cloudflare 攔截或網頁異常)")
        print("🛡️ 觸發保護熔斷機制！停止本次更新，避免空白資料覆蓋原有資料庫。")
        return None

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
    except (requests.RequestException, ValueError, KeyError, RuntimeError) as e:
        print(f"讀取現有 Gist 失敗: {e}")
        print("🛡️ 停止本次更新，避免以不完整資料覆蓋既有 Gist。")
        return None

    updated_chars = existing_data.get('new_characters', [])
    
    # 清洗舊格式 runs
    for char in updated_chars:
        clean_runs = []
        if 'runs' in char and isinstance(char['runs'], list):
            for r in char['runs']:
                if isinstance(r, str):
                    clean_runs.append(r)
                elif isinstance(r, dict) and 'version' in r and 'phase' in r:
                    half = "上" if r['phase'] == 1 else "下"
                    clean_runs.append(f"{r['version']}{half}")
        char['runs'] = clean_runs

    # 1. 取得資料庫與 Wiki 預載清單
    en_data, cht_data = fetch_starrailres_data()
    wiki_upcoming_map = fetch_upcoming_wiki_char_map()

    en_sanitized_map = {}
    for cid, info in en_data.items():
        name = info.get("name", "") if isinstance(info, dict) else str(info)
        sanitized = sanitize_name(name)
        if sanitized:
            en_sanitized_map[sanitized] = cid

    # 建立現有角色的快速查找對照
    existing_char_map_by_cid = {c['cid']: c for c in updated_chars if c.get('cid')}
    existing_char_map_by_name = {c['name']: c for c in updated_chars}

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
        if target_name == en_name or not any('\u4e00' <= char <= '\u9fff' for char in target_name):
            if sanitized_query in wiki_upcoming_map:
                target_name = wiki_upcoming_map[sanitized_query]
                print(f"✨ 成功從 Wiki Upcoming 分類自動對照繁中名稱: {en_name} ➡️ {target_name}")

        # C. 尋找是否已存在於 Gist 中 (透過 cid 或名稱模糊匹配)
        matched_char = None
        if target_cid and target_cid in existing_char_map_by_cid:
            matched_char = existing_char_map_by_cid[target_cid]
        elif target_name in existing_char_map_by_name:
            matched_char = existing_char_map_by_name[target_name]
        else:
            for char in updated_chars:
                if sanitize_name(char['name']) == sanitized_query:
                    matched_char = char
                    break

        if matched_char:
            # 自動補全或更新 cid
            if target_cid and not matched_char.get('cid'):
                matched_char['cid'] = target_cid

            # 自動將舊英文名升級為正確繁中名
            if matched_char['name'] != target_name and target_name != en_name:
                print(f"🔄 自動將名稱升級為正式中文: {matched_char['name']} -> {target_name}")
                matched_char['name'] = target_name

            if matched_char.get('path') in ["未知", ""] and path != "未知":
                matched_char['path'] = path
            if matched_char.get('elem') in ["未知", ""] and elem != "未知":
                matched_char['elem'] = elem
                
            if 'runs' not in matched_char or not isinstance(matched_char['runs'], list):
                matched_char['runs'] = []
                
            if sched['run'] not in matched_char['runs']:
                matched_char['runs'].append(sched['run'])
                print(f"📅 自動排程成功: 將 {matched_char['name']} 安排至 {sched['run']}")
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
            print(f"✨ 發現並納入新角色: {target_name} (CID: {target_cid}) ({path} / {elem})")

    return {
        "new_patches": merge_new_patches(existing_data.get('new_patches', []), schedules),
        "new_characters": updated_chars
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
    
    try:
        response = requests.patch(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        print("✅ Gist 自動更新與排程指派成功！")
        return True
    except requests.RequestException as error:
        print(f"❌ 更新失敗: {error}")
        return False

if __name__ == "__main__":
    if not GITHUB_TOKEN:
        print("❌ 找不到 GIST_TOKEN 環境變數。")
    else:
        latest_data = fetch_latest_data()
        if latest_data is not None:
            if not update_gist(latest_data):
                raise SystemExit(1)
        else:
            print("🛑 任務安全終止：保持現有 Gist 資料不變。")
