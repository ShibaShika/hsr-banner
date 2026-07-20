import re
import json
import requests

# 這裡未來需替換為實際提供 JSON 格式卡池資料的真實 API
DATA_API_URL = "https://irminsul.gg/hsr/banners"

def fetch_latest_banners():
    """
    此處為爬蟲抓取邏輯。
    目前先回傳模擬資料，代表我們爬到了 4.5 版本的兩位新角色。
    """
    # TODO: 實作 requests 抓取與 BeautifulSoup 解析邏輯
    return {
        "新角色A": ["4.5上"],
        "新角色B": ["4.5下"]
    }

def update_js():
    # 1. 改為讀取獨立的資料檔 js/characters.js
    with open('js/characters.js', 'r', encoding='utf-8') as f:
        js_content = f.read()

    new_banner_data = fetch_latest_banners()
    if not new_banner_data:
        print("沒有抓到新資料，結束更新。")
        return

    print(f"準備更新以下資料: {new_banner_data}")

    # 2. 匹配新結構中的 RAW_CHARACTERS 陣列
    char_pattern = re.compile(r'const RAW_CHARACTERS = (\[.*?\]);', re.DOTALL)
    match = char_pattern.search(js_content)
    
    if match:
        char_json_str = match.group(1)
        try:
            # 沿用原本的邏輯，確保 JavaScript 物件屬性有雙引號，以符合 Python JSON 解析標準
            clean_json_str = re.sub(r'(?<!")(\b\w+\b)\s*:', r'"\1":', char_json_str)
            clean_json_str = clean_json_str.replace("'", '"')
            
            characters = json.loads(clean_json_str)
            existing_names = {char.get('name') for char in characters}
            
            # 3. 資料比對與合併
            for name, patches in new_banner_data.items():
                if name in existing_names:
                    # 既有角色：新增復刻版本紀錄
                    for char in characters:
                        if char.get('name') == name:
                            updated_runs = set(char.get('runs', []) + patches)
                            char['runs'] = sorted(list(updated_runs), reverse=True)
                else:
                    # 全新角色：自動新建一筆資料！
                    print(f"發現新角色：{name}，自動加入資料庫！")
                    characters.insert(0, {
                        "name": name,
                        "path": "未知",  # 爬蟲若有抓到可在此填寫變數
                        "elem": "未知",  # 爬蟲若有抓到可在此填寫變數
                        "avatar": "",
                        "runs": patches
                    })
            
            # 將資料轉回 JSON 字串格式
            new_char_str = json.dumps(characters, ensure_ascii=False, indent=4)
            # 將 key 的雙引號拿掉，恢復成漂亮的 JavaScript 屬性風格
            new_char_str = re.sub(r'"(\w+)":', r'\1:', new_char_str)
            
            new_js_content = js_content.replace(match.group(0), f'const RAW_CHARACTERS = {new_char_str};')
            
            with open('js/characters.js', 'w', encoding='utf-8') as f:
                f.write(new_js_content)
            print("js/characters.js 更新成功！")
            
        except json.JSONDecodeError as e:
            print(f"解析 JS 內的資料失敗: {e}")
    else:
        print("在 js/characters.js 中找不到資料區塊。")

if __name__ == "__main__":
    update_js()
