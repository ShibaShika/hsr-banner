import re
import json
import requests

# 未來您可以將此 URL 替換為實際提供 JSON 格式卡池資料的 API (例如 Yatta 或社區 API)
DATA_API_URL = "https://irminsul.gg/hsr/banners"

def fetch_latest_banners():
    """
    此處為爬蟲抓取邏輯。
    針對動態網頁或 API，需解析 JSON 或 HTML DOM。
    因範例網址為動態網頁，此處僅模擬回傳爬取到的最新卡池名單。
    """
    # TODO: 實作 requests 抓取與 BeautifulSoup 解析邏輯
    # 目前先回傳模擬資料，代表我們爬到了 4.4 下半的卡池資訊
    return {
        "遠坂凜": ["4.4下"],
        "吉爾伽美什": ["4.4下"]
    }

def update_html():
    with open('index.html', 'r', encoding='utf-8') as f:
        html_content = f.read()

    new_banner_data = fetch_latest_banners()
    if not new_banner_data:
        print("沒有抓到新資料，結束更新。")
        return

    print(f"準備更新以下資料: {new_banner_data}")

    char_pattern = re.compile(r'const CHARACTERS = (\[.*?\]);', re.DOTALL)
    match = char_pattern.search(html_content)
    
    if match:
        char_json_str = match.group(1)
        try:
            # 確保 JavaScript 物件屬性有雙引號，以符合 Python JSON 解析標準
            clean_json_str = re.sub(r'(\w+):', r'"\1":', char_json_str)
            clean_json_str = clean_json_str.replace("'", '"') # 處理可能的單引號
            characters = json.loads(clean_json_str)
            
            # 將新抓取到的卡池版本，加入到對應角色的 runs 陣列中
            for char in characters:
                name = char.get('name')
                if name in new_banner_data:
                    updated_runs = set(char['runs'] + new_banner_data[name])
                    # 簡單的反向排序以確保最新版本在前面
                    char['runs'] = sorted(list(updated_runs), reverse=True)
            
            new_char_str = json.dumps(characters, ensure_ascii=False, indent=4)
            new_char_str = re.sub(r'"(\w+)":', r'\1:', new_char_str)
            
            new_html_content = html_content.replace(match.group(0), f'const CHARACTERS = {new_char_str};')
            
            with open('index.html', 'w', encoding='utf-8') as f:
                f.write(new_html_content)
            print("index.html 更新成功！")
            
        except json.JSONDecodeError as e:
            print(f"解析 HTML 內的資料失敗: {e}")
    else:
        print("在 index.html 中找不到資料區塊。")

if __name__ == "__main__":
    update_html()
