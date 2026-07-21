import os
import json
import requests

GIST_ID = '53c5bb324cd140fb8751c9812bd5df68'
GITHUB_TOKEN = os.environ.get('GIST_TOKEN')

def fetch_latest_data():
    print("正在檢查遠端與公開資料源...")
    
    # 1. 先把現有的 Gist 內容抓下來，避免覆蓋掉您手動整理好的資料
    existing_data = {"new_patches": [], "new_characters": []}
    try:
        gist_url = f"https://api.github.com/gists/{GIST_ID}"
        gist_res = requests.get(gist_url)
        if gist_res.status_code == 200:
            files = gist_res.json().get('files', {})
            if 'hsr_latest_banner.json' in files:
                existing_data = json.loads(files['hsr_latest_banner.json']['content'])
    except Exception as e:
        print(f"讀取現有 Gist 失敗，將建立新結構: {e}")

    existing_char_names = {c['name'] for c in existing_data.get('new_characters', [])}

    # 2. 從公開的 StarRailRes 角色索引資料庫抓取最新角色清單
    target_url = "https://raw.githubusercontent.com/Mar-7th/StarRailRes/master/index/zh/characters.json"
    new_chars_to_add = []
    
    try:
        res = requests.get(target_url)
        if res.status_code == 200:
            chars_map = res.json()
            # 檢查每一位角色，如果名字不在我們現有的清單中，就自動納入
            for char_id, char_info in chars_map.items():
                name = char_info.get('name')
                if name and name not in existing_char_names and not name.startswith("開拓者"):
                    path = char_info.get('path', {}).get('name', '毀滅')
                    elem = char_info.get('element', '火')
                    
                    new_chars_to_add.append({
                        "name": name,
                        "path": path,
                        "elem": elem,
                        "runs": []
                    })
                    print(f"發現新角色: {name} ({path}/{elem})")
    except Exception as e:
        print(f"抓取外部角色資料發生錯誤: {e}")

    # 3. 合併資料
    updated_patches = existing_data.get('new_patches', [])
    updated_chars = existing_data.get('new_characters', []) + new_chars_to_add

    return {
        "new_patches": updated_patches,
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
        print("✅ Gist 自動更新成功！")
    else:
        print(f"❌ 更新失敗: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    if not GITHUB_TOKEN:
        print("❌ 找不到 GIST_TOKEN 環境變數。")
    else:
        latest_data = fetch_latest_data()
        update_gist(latest_data)
