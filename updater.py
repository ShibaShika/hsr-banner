import re
import json
import requests

# 真實的隱藏 API 網址 (目前為 4.4.51 測試資料，之後官方換版可動態修改)
DATA_API_URL = "https://static.nanoka.cc/hsr/4.4.51/character.json"

# 建立字典：負責把 API 內的英文屬性與命途，翻譯成網頁使用的中文
ELEM_MAP = {
    "Fire": "火", "Ice": "冰", "Thunder": "雷", 
    "Wind": "風", "Physical": "物理", "Quantum": "量子", "Imaginary": "虛數"
}
PATH_MAP = {
    "Warrior": "毀滅", "Rogue": "巡獵", "Mage": "智識", 
    "Shaman": "同諧", "Warlock": "虛無", "Knight": "存護", 
    "Priest": "豐饒", "Memory": "記憶", "Elation": "歡愉"
}

def fetch_latest_banners():
    """
    透過真實 API 抓取角色資料，並根據 ID 推斷卡池版本。
    """
    try:
        response = requests.get(DATA_API_URL)
        response.raise_for_status()
        raw_data = response.json()
    except Exception as e:
        print(f"抓取 API 失敗: {e}")
        return {}

    # 🌟 這裡就是您的「推斷邏輯」：只要在這裡設定新 ID 對應的卡池即可
    # 未來如果有 4.6 的新角色，只需在這裡新增即可
    target_ids = {
        "1512": "4.5上", # 知更鳥•晴歌
        "1513": "4.5下"  # 砂金•戲浪
    }

    new_banner_data = {}
    
    for char_id, char_info in raw_data.items():
        if char_id in target_ids:
            # 取得原始資料
            raw_name = char_info.get("name", "未知角色")
            raw_elem = char_info.get("damageType", "")
            raw_path = char_info.get("baseType", "")
            
            # 轉換為繁體中文標籤
            name = raw_name.replace("鸟", "鳥") # 簡單的簡繁轉換，視需求增減
            elem = ELEM_MAP.get(raw_elem, "未知")
            path = PATH_MAP.get(raw_path, "未知")
            banner = target_ids[char_id]
            
            # 將整理好的資料存入字典中
            new_banner_data[name] = {
                "runs": [banner],
                "elem": elem,
                "path": path
            }
            print(f"成功解析：{name} ({path}/{elem}) -> 預計卡池: {banner}")

    return new_banner_data

def update_js():
    with open('js/characters.js', 'r', encoding='utf-8') as f:
        js_content = f.read()

    new_banner_data = fetch_latest_banners()
    if not new_banner_data:
        print("沒有抓到需要更新的新角色，結束。")
        return

    char_pattern = re.compile(r'const RAW_CHARACTERS = (\[.*?\]);', re.DOTALL)
    match = char_pattern.search(js_content)
    
    if match:
        char_json_str = match.group(1)
        try:
            clean_json_str = re.sub(r'(?<!")(\b\w+\b)\s*:', r'"\1":', char_json_str)
            clean_json_str = clean_json_str.replace("'", '"')
            
            characters = json.loads(clean_json_str)
            existing_names = {char.get('name') for char in characters}
            
            # 資料比對與合併
            for name, data in new_banner_data.items():
                if name in existing_names:
                    # 既有角色新增復刻
                    for char in characters:
                        if char.get('name') == name:
                            updated_runs = set(char.get('runs', []) + data["runs"])
                            char['runs'] = sorted(list(updated_runs), reverse=True)
                else:
                    # 修改後的寫法：附加在陣列尾端，網頁才會顯示在最上方
                    print(f"將新角色加入資料庫：{name}")
                    characters.append({
                        "name": name,
                        "path": data["path"],
                        "elem": data["elem"],
                        "avatar": "",
                        "runs": data["runs"]
                    })
            
            new_char_str = json.dumps(characters, ensure_ascii=False, indent=4)
            new_char_str = re.sub(r'"(\w+)":', r'\1:', new_char_str)
            new_js_content = js_content.replace(match.group(0), f'const RAW_CHARACTERS = {new_char_str};')
            
            with open('js/characters.js', 'w', encoding='utf-8') as f:
                f.write(new_js_content)
            print("js/characters.js 更新成功！")
            
        except json.JSONDecodeError as e:
            print(f"解析 JS 失敗: {e}")

if __name__ == "__main__":
    update_js()
