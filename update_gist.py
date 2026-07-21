import os
import json
import re
import requests
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup

GIST_ID = '53c5bb324cd140fb8751c9812bd5df68'
GITHUB_TOKEN = os.environ.get('GIST_TOKEN')

def build_translation_map():
    print("正在建立英中角色名稱對照表...")
    try:
        # 修正：將 master 改為 main
        en_url = "https://raw.githubusercontent.com/Mar-7th/StarRailRes/main/index/en/characters.json"
        zh_url = "https://raw.githubusercontent.com/Mar-7th/StarRailRes/main/index/zh/characters.json"
        
        en_res = requests.get(en_url)
        zh_res = requests.get(zh_url)
        
        if en_res.status_code != 200 or zh_res.status_code != 200:
            print(f"對照表下載失敗: EN HTTP {en_res.status_code}, ZH HTTP {zh_res.status_code}")
            return {}
            
        en_data = en_res.json()
        zh_data = zh_res.json()
        
        mapping = {}
        for cid, cinfo in en_data.items():
            en_name = cinfo.get("name")
            if cid in zh_data:
                mapping[en_name] = zh_data[cid].get("name")
        return mapping
    except Exception as e:
        print(f"對照表建立失敗: {e}")
        return {}

def fetch_prydwen_schedules():
    print("正在破解防護並抓取 Prydwen 卡池排程...")
    url = "https://www.prydwen.gg/star-rail/banners/"
    try:
        # 使用 curl_cffi 偽裝成 Chrome 110，完美繞過 Cloudflare 驗證
        res = cffi_requests.get(url, impersonate="chrome110")
        if res.status_code != 200:
            print(f"❌ Prydwen 抓取失敗: HTTP {res.status_code}")
            return []

        soup = BeautifulSoup(res.text, "html.parser")
        schedules = []
        
        # 鎖定所有角色卡池的卡片結構
        cards = soup.find_all("article", class_="character-banner-card")
        for card in cards:
            name_tag = card.find(class_="banner-name")
            if not name_tag: continue
            en_name = name_tag.text.strip()
            
            # 抓取版本與階段資訊
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

    # 自動偵測與新增 StarRailRes 的全新角色
    try:
        # 修正：將 master 改為 main
        zh_url = "https://raw.githubusercontent.com/Mar-7th/StarRailRes/main/index/zh/characters.json"
        zh_res = requests.get(zh_url)
        
        if zh_res.status_code == 200:
            zh_data = zh_res.json()
            for char_id, char_info in zh_data.items():
                name = char_info.get('name')
                if name and name not in existing_char_names and not name.startswith("開拓者"):
                    path = char_info.get('path', {}).get('name', '毀滅')
                    elem = char_info.get('element', '火')
                    updated_chars.append({
                        "name": name,
                        "path": path,
                        "elem": elem,
                        "runs": []
                    })
                    existing_char_names.add(name)
                    print(f"✨ 發現並納入新角色: {name}")
        else:
            print(f"抓取新角色資料失敗: HTTP {zh_res.status_code}")
    except Exception as e:
        print(f"抓取新角色資料發生錯誤: {e}")

    # 取得翻譯對照表與 Prydwen 排程，並執行自動指派
    name_map = build_translation_map()
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
