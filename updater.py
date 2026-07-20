import re
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# 1. 目標網址 (此處以示意網址為例，您可以根據實際爬取的來源切換)
# 備註：爬蟲邏輯非常依賴對方網站的 HTML 結構。若對方網站改版，這裡的 find() 邏輯就需要更新。
URL = "https://irminsul.gg/hsr/banners"

def fetch_latest_banners():
    """模擬從外部網站爬取最新卡池資料的邏輯"""
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(URL, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 這裡放置實際解析對方網頁 DOM 的邏輯
        # 為了確保教學能直接執行不出錯，我們這邊先返回一組模擬的新增資料結構
        # 實際應用中，您會將 soup.find_all(...) 抓到的資料轉成以下格式
        new_data = {
            # 假設抓到未來 4.4 下半的角色
            "遠坂凜": ["4.4下"],
            "吉爾伽美什": ["4.4下"]
        }
        return new_data
    except Exception as e:
        print(f"抓取資料失敗: {e}")
        return {}

def update_html():
    with open('index.html', 'r', encoding='utf-8') as f:
        html_content = f.read()

    # 抓取最新的資料
    new_banner_data = fetch_latest_banners()
    if not new_banner_data:
        print("沒有抓到新資料，結束更新。")
        return

    print(f"抓取到新資料: {new_banner_data}")

    # 使用正規表達式提取原有的 CHARACTERS 陣列
    char_pattern = re.compile(r'const CHARACTERS = (\[.*?\]);', re.DOTALL)
    match = char_pattern.search(html_content)
    
    if match:
        char_json_str = match.group(1)
        # 將 JavaScript 陣列字串轉換為 Python 字典/列表
        # 注意：這要求原本的 HTML 內的 JS 陣列格式必須非常接近標準 JSON（屬性名需有雙引號）
        try:
            # 簡單清理 JS 語法以符合 Python JSON 格式
            clean_json_str = re.sub(r'(\w+):', r'"\1":', char_json_str)
            characters = json.loads(clean_json_str)
            
            # 更新資料
            for char in characters:
                if char['name'] in new_banner_data:
                    # 合併並去除重複的版本，然後排序
                    updated_runs = set(char['runs'] + new_banner_data[char['name']])
                    char['runs'] = sorted(list(updated_runs), reverse=True)
            
            # 將更新後的資料轉回字串
            new_char_str = json.dumps(characters, ensure_ascii=False, indent=4)
            # 將 Python 字典的 key 雙引號去掉，使其貼合原有的 JS 格式
            new_char_str = re.sub(r'"(\w+)":', r'\1:', new_char_str)
            
            # 替換回原來的 HTML 內容
            new_html_content = html_content.replace(match.group(0), f'const CHARACTERS = {new_char_str};')
            
            with open('index.html', 'w', encoding='utf-8') as f:
                f.write(new_html_content)
            print("index.html 更新成功！")
            
        except json.JSONDecodeError as e:
            print(f"解析 HTML 內的 JSON 失敗: {e}")
    else:
        print("在 index.html 中找不到 CHARACTERS 區塊。")

if __name__ == "__main__":
    update_html()
