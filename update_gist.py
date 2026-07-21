import os
import json
import requests

# ==========================================
# 1. 設定區塊 (請替換為您的 GIST_ID)
# 例如您的網址是 https://gist.github.com/ShibaShika/53c5bb324cd140fb8751c9812bd5df68
# 那麼 GIST_ID 就是 53c5bb324cd140fb8751c9812bd5df68
# ==========================================
GIST_ID = '53c5bb324cd140fb8751c9812bd5df68'
GITHUB_TOKEN = os.environ.get('GIST_TOKEN')

def fetch_latest_data():
    """
    這裡負責去外部資料站抓取資料。
    (目前先寫好一個固定的新資料做測試，確認機器人能成功修改 Gist 後，
    我們下一階段再來替換成真實的 API 網址)
    """
    print("正在獲取最新卡池資訊...")
    
    # 模擬抓取到的最新資料
    mock_data = {
        "new_patches": [
            { "patch": "9.9上", "date": "26/12/31" },
            { "patch": "9.9下", "date": "27/01/21" }
        ],
        "new_characters": [
            { "name": "全自動化測試角色", "path": "同諧", "elem": "量子", "runs": ["9.9上"] }
        ]
    }
    return mock_data

def update_gist(data):
    """將抓到的資料更新回 GitHub Gist"""
    print("準備更新 Gist...")
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    
    # 這裡的 'hsr_latest_banner.json' 必須跟您當初建立 Gist 時的檔名一模一樣
    payload = {
        "files": {
            "hsr_latest_banner.json": {
                "content": json.dumps(data, ensure_ascii=False, indent=4)
            }
        }
    }
    
    response = requests.patch(url, headers=headers, json=payload)
    if response.status_code == 200:
        print("✅ Gist 更新成功！")
    else:
        print(f"❌ 更新失敗: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    if not GITHUB_TOKEN:
        print("❌ 找不到 GIST_TOKEN 環境變數，請確認 GitHub Secrets 設定。")
    else:
        latest_data = fetch_latest_data()
        update_gist(latest_data)
