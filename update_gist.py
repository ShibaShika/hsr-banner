import os
import json
import re
import requests
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup

GIST_ID = '53c5bb324cd140fb8751c9812bd5df68'
GITHUB_TOKEN = os.environ.get('GIST_TOKEN')

def fetch_starrailres_data():
    print("正在從 StarRailRes 抓取完整角色資料...")
    cht_url = "https://raw.githubusercontent.com/Mar-7th/StarRailRes/refs/heads/master/index/cht/characters.json"
    en_url = "https://raw.githubusercontent.com/Mar-7th/StarRailRes/refs/heads/master/index/en/characters.json"
    
    cht_res = requests.get(cht_url)
    en_res = requests.get(en_url)
    
    cht_data = cht_res.json() if cht_res.status_code == 200 else {}
    en_data = en_res.json() if en_res.status_code == 200 else {}
    
    return cht_data, en_data

def build_translation_map(cht_data, en_data):
    print("正在建立英中角色名稱對照表...")
    mapping = {}
    for cid, en_info in en_data.items():
        en_name = en_info.get("name") if isinstance(en_info, dict) else en_info
        cht_info = cht_data.get(cid)
        cht_name = cht_info.get("name") if isinstance(cht_info, dict) else cht_info
        
        if en_name and cht_name:
            mapping[en_name] = cht_name
    return mapping

def fetch_prydwen_schedules():
    print("正在破解防護並抓取 Prydwen 卡池排程...")
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
            
            meta_div = card.find(class_="banner-phase-meta")
            phase_str = meta_div.find("span").text.strip() if meta_div and meta_div.find("span") else ""
            
            version_match = re.search(r"Patch ([\d\.X]+)", phase_str)
            if not version_match: 
                continue 
                
            version = version_match.group(1)
            phase = 2 if "Phase 2" in phase_str else 1
            
            schedules.append({
                "en_name": en_name,
                "version": version,
                "phase": phase
            })
            print(f"解析到排程: {en_name} -> {version} Phase {phase}")
            
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
    existing_char_names = {c['name'] for c in updated_chars}

    # 取得完整的 cht 與 en 資料
    cht_data, en_data = fetch_starrailres_data()
    name_map = build_translation_map(cht_data, en_data)

    # 自動偵測與新增角色（排除 4 星、開拓者、系統字串）
    for char_id, char_info in cht_data.items():
        if not isinstance(char_info, dict):
            continue
            
        name = char_info.get('name')
        rarity = char_info.get('rarity', 5)
        
        # 排除 4 星角色
        if rarity == 4:
            continue
            
        if name and "{NICKNAME}" not in name and not name.startswith("開拓者") and name not in existing_char_names:
            # 抓取命途
            path_val = char_info.get('path', '未知')
            path = path_val.get('name', '未知') if isinstance(path_val, dict) else str(path_val)
            
            # 抓取屬性
            elem_val = char_info.get('element', '未知')
            elem = elem_val.get('name', '未知') if isinstance(elem_val, dict) else str(elem_val)
            
            updated_chars.append({
                "name": name,
                "path": path,
                "elem": elem,
                "runs": []
            })
            existing_char_names.add(name)
            print(f"✨ 發現並納入新 5 星角色: {name} ({path} / {elem})")

    # 取得 Prydwen 排程並自動指派
    schedules = fetch_prydwen_schedules()
    
    for sched in schedules:
        target_name = name_map.get(sched['en_name'], sched['en_name'])
        
        for char in updated_chars:
            if char['name'] == target_name:
                run_exists = any(r.get('version') == sched['version'] and r.get('phase') == sched['phase'] for r in char.get('runs', []))
                
                if not run_exists:
                    char.setdefault('runs', []).append({
                        "version": sched['version'],
                        "phase": sched['phase']
                    })
                    print(f"📅 自動排程成功: 將 {target_name} 安排至 {sched['version']} 上/下半 {sched['phase']}")
                break

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
