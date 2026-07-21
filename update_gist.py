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

def build_name_mapping():
    print("正在建立精確的英中角色名稱對照表...")
    try:
        en_url = "https://raw.githubusercontent.com/Mar-7th/StarRailRes/refs/heads/master/index_new/en/characters.json"
        zh_url = "https://raw.githubusercontent.com/Mar-7th/StarRailRes/refs/heads/master/index_new/cht/characters.json"
        
        en_res = requests.get(en_url)
        zh_res = requests.get(zh_url)
        
        if en_res.status_code != 200 or zh_res.status_code != 200:
            return {}
            
        en_data = en_res.json()
        zh_data = zh_res.json()
        
        mapping = {}
        for cid, en_info in en_data.items():
            en_name = en_info.get("name") if isinstance(en_info, dict) else en_info
            zh_info = zh_data.get(cid)
            zh_name = zh_info.get("name") if isinstance(zh_info, dict) else zh_info
            
            if en_name and zh_name:
                mapping[en_name] = zh_name
                # 同時建立小寫對應以防萬一
                mapping[en_name.lower()] = zh_name
        return mapping
    except Exception as e:
        print(f"建立對照表發生錯誤: {e}")
        return {}

def fetch_prydwen_schedules(name_map):
    print("正在從 Prydwen 抓取 5 星角色卡池排程...")
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
            
            # 優先使用對照表轉成中文，若無則保留英文
            zh_name = name_map.get(en_name, name_map.get(en_name.lower(), en_name))
            
            # 解析命途與屬性
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
            
            # 轉換成編輯器標準字串格式 (例如 "4.4上")
            run_str = f"{version}{half_str}"
            
            schedules.append({
                "name": zh_name,
                "path": zh_path,
                "elem": zh_elem,
                "run": run_str
            })
            print(f"解析 5 星角色: {zh_name} ({en_name}) | {zh_path} | {zh_elem} -> {run_str}")
            
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
    existing_char_map = {c['name']: c for c in updated_chars}

    name_map = build_name_mapping()
    schedules = fetch_prydwen_schedules(name_map)
    
    for sched in schedules:
        target_name = sched['name']
        
        if target_name in existing_char_map:
            char_obj = existing_char_map[target_name]
            
            if char_obj.get('path') in ["未知", ""] and sched['path'] != "未知":
                char_obj['path'] = sched['path']
            if char_obj.get('elem') in ["未知", ""] and sched['elem'] != "未知":
                char_obj['elem'] = sched['elem']
                
            # 確保 runs 是純字串陣列，並避免重複
            if 'runs' not in char_obj or not isinstance(char_obj['runs'], list):
                char_obj['runs'] = []
                
            if sched['run'] not in char_obj['runs']:
                char_obj['runs'].append(sched['run'])
                print(f"📅 自動排程成功: 將 {target_name} 安排至 {sched['run']}")
        else:
            new_char = {
                "name": target_name,
                "path": sched['path'],
                "elem": sched['elem'],
                "runs": [sched['run']]
            }
            updated_chars.append(new_char)
            existing_char_map[target_name] = new_char
            print(f"✨ 發現並納入新 5 星角色: {target_name} ({sched['path']} / {sched['elem']})")

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
