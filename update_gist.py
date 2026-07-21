import os
import json
import re
import requests
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup

GIST_ID = '53c5bb324cd140fb8751c9812bd5df68'
GITHUB_TOKEN = os.environ.get('GIST_TOKEN')

PATH_MAP = {
    "Destruction": "毀滅",
    "Hunt": "巡獵",
    "Erudition": "智識",
    "Harmony": "同諧",
    "Nihility": "虛無",
    "Preservation": "存護",
    "Abundance": "豐饒",
    "Remembrance": "記憶",
    "Elation": "歡愉"
}

ELEM_MAP = {
    "Physical": "物理",
    "Fire": "火",
    "Ice": "冰",
    "Lightning": "雷",
    "Wind": "風",
    "Quantum": "量子",
    "Imaginary": "虛數"
}

def sanitize_name(name):
    """去除空格與所有非英數字元，並轉為小寫"""
    if not name:
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', name).lower()

def fetch_starrailres_data():
    print("正在從 StarRailRes 抓取完整角色資料庫...")
    en_url = "https://raw.githubusercontent.com/Mar-7th/StarRailRes/refs/heads/master/index/en/characters.json"
    cht_url = "https://raw.githubusercontent.com/Mar-7th/StarRailRes/refs/heads/master/index/cht/characters.json"
    
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
            if not name_tag: continue
            en_name = name_tag.text.strip()
            
            # 解析備用中文命途與屬性
            path_span = card.find(class_=re.compile(r"path\s+"))
            en_path = path_span.find("strong").text.strip() if path_span and path_span.find("strong") else ""
            zh_path = PATH_MAP.get(en_path, "未知")
            
            elem_span = card.find(class_=re.compile(r"element\s+"))
            en_elem = elem_span.find("strong").text.strip() if elem_span and elem_span.find("strong") else ""
            zh_elem = ELEM_MAP.get(en_elem, "未知")
            
            # 抓取版本與階段資訊
            meta_div = card.find(class_="banner-phase-meta")
            phase_str = meta_div.find("span").text.strip() if meta_div and meta_div.find("span") else ""
            
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
                "run": run_str
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
            files = gist_res.json().get('files', {})
            if 'hsr_latest_banner.json' in files:
                existing_data = json.loads(files['hsr_latest_banner.json']['content'])
    except Exception as e:
        print(f"讀取現有 Gist 失敗: {e}")

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

    existing_char_map = {c['name']: c for c in updated_chars}

    # 1. 取得資料庫並建立「英文去符號對照表 -> ID」
    en_data, cht_data = fetch_starrailres_data()
    en_sanitized_map = {}
    for cid, info in en_data.items():
        name = info.get("name", "") if isinstance(info, dict) else str(info)
        sanitized = sanitize_name(name)
        if sanitized:
            en_sanitized_map[sanitized] = cid

    # 2. 爬取 Prydwen 卡池排程
    schedules = fetch_prydwen_schedules()

    for sched in schedules:
        en_name = sched['en_name']
        sanitized_query = sanitize_name(en_name)
        
        target_name = None
        path = sched['fallback_path']
        elem = sched['fallback_elem']
        
        # 3. 透過英文去符號比對資料庫 ID 並取得中文資料
        if sanitized_query in en_sanitized_map:
            cid = en_sanitized_map[sanitized_query]
            cht_info = cht_data.get(cid, {})
            
            if isinstance(cht_info, dict):
                target_name = cht_info.get("name", en_name)
                
                db_path = cht_info.get("path")
                if isinstance(db_path, dict):
                    path = db_path.get("name", path)
                elif isinstance(db_path, str):
                    path = db_path
                    
                db_elem = cht_info.get("element")
                if isinstance(db_elem, str):
                    elem = db_elem
        else:
            target_name = en_name
            print(f"⚠️ 資料庫查無此英文名稱 ({en_name})，將採用原始名稱。")

        if not target_name:
            continue

        if target_name in existing_char_map:
            char_obj = existing_char_map[target_name]
            if char_obj.get('path') in ["未知", ""] and path != "未知":
                char_obj['path'] = path
            if char_obj.get('elem') in ["未知", ""] and elem != "未知":
                char_obj['elem'] = elem
                
            if 'runs' not in char_obj or not isinstance(char_obj['runs'], list):
                char_obj['runs'] = []
                
            if sched['run'] not in char_obj['runs']:
                char_obj['runs'].append(sched['run'])
                print(f"📅 自動排程成功: 將 {target_name} 安排至 {sched['run']}")
        else:
            new_char = {
                "name": target_name,
                "path": path,
                "elem": elem,
                "runs": [sched['run']]
            }
            updated_chars.append(new_char)
            existing_char_map[target_name] = new_char
            print(f"✨ 發現並納入新角色: {target_name} ({path} / {elem})")

    return {
        "new_patches": existing_data.get('new_patches', []),
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
