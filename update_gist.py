import json
import os
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# ──────────────────────────────────────────────────
# 基本設定
# ──────────────────────────────────────────────────
GIST_ID = "53c5bb324cd140fb8751c9812bd5df68"
GITHUB_TOKEN = os.environ.get("GIST_TOKEN")
REQUEST_TIMEOUT = 25
PATCH_NAME_RE = re.compile(r'^\d+\.\d+[上下中]$')
WIKI_API_URL = "https://honkai-star-rail.fandom.com/api.php"

PATH_MAP = {
    "Destruction": "毀滅", "Warrior": "毀滅",
    "Hunt": "巡獵", "Rogue": "巡獵",
    "Erudition": "智識", "Mage": "智識",
    "Harmony": "同諧", "Shaman": "同諧",
    "Nihility": "虛無", "Warlock": "虛無",
    "Preservation": "存護", "Knight": "存護",
    "Abundance": "豐饒", "Priest": "豐饒",
    "Remembrance": "記憶", "Memory": "記憶",
    "Elation": "歡愉"
}

ELEM_MAP = {
    "Physical": "物理",
    "Fire": "火",
    "Ice": "冰",
    "Lightning": "雷", "Thunder": "雷",
    "Wind": "風",
    "Quantum": "量子",
    "Imaginary": "虛數"
}

# 特殊角色中文化與別名備援對照表
SPECIAL_NAME_MAP = {
    "Astra Yao": "耀嘉音",
    "Aha": "阿哈",
    "Ellen Joe": "艾蓮•喬",
    "Topaz and Numby": "托帕＆帳帳",
    "Topaz & Numby": "托帕＆帳帳",
    "Pearl": "真珠",
    "Ashveil": "不死途",
    "Mortenax Blade": "千冶•刃",
    "Evanescia": "緋英",
    "Robin • Summeretto": "知更鳥•晴歌",
    "Aventurine • Waveflair": "砂金•戲浪",
    "Hyacine": "風堇",
    "Himeko • Nova": "姬子•啟行",
    "Dan Heng • Permansor Terrae": "丹恆•騰荒",
    "Sparxie": "火花",
    "Evernight": "長夜月"
}

# ──────────────────────────────────────────────────
# 字串清洗與工具函式
# ──────────────────────────────────────────────────
def sanitize_name(name):
    """去除所有非英數字元並轉小寫，用於無障礙模糊匹配"""
    if not name:
        return ""
    name = str(name).replace('&', 'and')
    return re.sub(r'[^a-zA-Z0-9]', '', name).lower()

CJK_RE = re.compile(
    r'[\u4e00-\u9fff'
    r'\u3400-\u4dbf'
    r'\uf900-\ufaff'
    r'\U00020000-\U0002A6DF'
    r'\U0002A700-\U0002B73F'
    r'\U0002B740-\U0002B81F'
    r'\U0002B820-\U0002CEAF'
    r'\U0002CEB0-\U0002EBEF'
    r'\U0002F800-\U0002FA1F'
    r']'
)

def contains_cjk(text):
    return bool(text and CJK_RE.search(text))

def clean_wikitext_value(val):
    if not val:
        return ""
    val = re.sub(r'\[\[(?:[^\|\]]*\|)?([^\]]+)\]\]', r'\1', val)
    val = re.sub(r'<!--.*?-->', '', val)
    return val.strip().replace('·', '•')

def normalize_patch_date(value):
    """標準化日期為 YY/MM/DD"""
    if not value:
        return None
    if isinstance(value, (int, float)):
        value = datetime.fromtimestamp(value / 1000 if value > 10**11 else value).strftime('%Y-%m-%d')
    value = str(value).strip()
    for fmt in ('%y/%m/%d', '%Y/%m/%d', '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ', '%B %d, %Y', '%B %d %Y'):
        try:
            return datetime.strptime(value, fmt).strftime('%y/%m/%d')
        except ValueError:
            continue
    return None

def clean_invalid_runs(chars):
    """清洗歷史殘留的無效版本名稱（例如 '4.X上'）"""
    cleaned_count = 0
    for char in chars:
        if 'runs' in char and isinstance(char['runs'], list):
            original = char['runs']
            char['runs'] = [r for r in original if isinstance(r, str) and PATCH_NAME_RE.fullmatch(r)]
            removed = set(original) - set(char['runs'])
            if removed:
                print(f"🧹 清除 [{char.get('name', '?')}] 的無效版本標籤：{removed}")
                cleaned_count += 1
    return cleaned_count

def merge_new_patches(existing_patches, new_patch_items):
    """合併並排序版本列表"""
    patches_by_name = {}
    for patch in (existing_patches or []):
        if not isinstance(patch, dict):
            continue
        name = patch.get('patch')
        date = normalize_patch_date(patch.get('date'))
        if isinstance(name, str) and PATCH_NAME_RE.fullmatch(name) and date:
            patches_by_name[name] = {'patch': name, 'date': date}

    for item in new_patch_items:
        name = item.get('patch')
        date = normalize_patch_date(item.get('date'))
        if not isinstance(name, str) or not PATCH_NAME_RE.fullmatch(name):
            continue
        elif not date:
            continue
        else:
            if name not in patches_by_name:
                patches_by_name[name] = {'patch': name, 'date': date}
                print(f"📅 收錄新版本：{name} ({date})")

    return sorted(patches_by_name.values(), key=lambda p: (p['date'], p['patch']))


# ──────────────────────────────────────────────────
# 核心資料源：Fandom Wiki 結構化躍遷歷史與排程
# ──────────────────────────────────────────────────
def fetch_fandom_schedules_and_patches(session):
    """
    透過 MediaWiki API 解析 Fandom Wiki 的 Warp/List 頁面，
    自動推導當前與未來卡池的版本號（如 4.6上、4.6下）及 5 星限定角色。
    """
    print("正在從 Fandom Wiki (Warp/List) 抓取官方卡池排程與歷史...")

    parse_res = session.get(WIKI_API_URL, params={
        'action': 'parse',
        'page': 'Warp/List',
        'prop': 'text',
        'format': 'json'
    }, timeout=REQUEST_TIMEOUT).json()

    html = parse_res.get('parse', {}).get('text', {}).get('*', '')
    if not html:
        print("⚠️ 未能取得 Warp/List 的 HTML 內容")
        return [], []

    soup = BeautifulSoup(html, 'html.parser')
    tables = soup.find_all('table')
    if not tables:
        print("⚠️ Warp/List 頁面未發現卡池表格")
        return [], []

    def parse_header_date(s):
        s = s.strip()
        for fmt in ('%B %d, %Y', '%B %d %Y'):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                pass
        return None

    warp_records = []
    version_dates = {}  # ver -> set of datetime

    # 巡覽前 3 個表格：Table 0 (Current), Table 1 (Upcoming), Table 2 (Past)
    for t_idx in range(min(3, len(tables))):
        t = tables[t_idx]
        current_ver = None
        current_start_dt = None
        is_collab = False

        for tr in t.find_all('tr'):
            th = tr.find('th', colspan='2')
            if th:
                text = th.get_text(' ', strip=True)
                m = re.search(r'Version\s+(\d+\.\d+)\s*:\s*([^–—\-\(]+)', text)
                if m:
                    current_ver = m.group(1)
                    start_str = m.group(2).replace('Since', '').strip()
                    current_start_dt = parse_header_date(start_str)
                    is_collab = 'indefinite' in text.lower() or 'collaboration' in text.lower()

                    if current_ver and current_start_dt and not is_collab:
                        if current_ver not in version_dates:
                            version_dates[current_ver] = set()
                        version_dates[current_ver].add(current_start_dt)
                continue

            tds = tr.find_all('td')
            if len(tds) >= 2 and current_ver and current_start_dt:
                type_text = tds[0].get_text(strip=True)
                if 'Character' in type_text:
                    for a in tds[1].find_all('a'):
                        title = a.get('title')
                        if title and '/' in title and not title.startswith('File:'):
                            warp_records.append({
                                'warp_page': title,
                                'version': current_ver,
                                'start_dt': current_start_dt,
                                'is_collab': is_collab
                            })

    # 計算各版本半期標籤（上/下/中）
    ver_phases = {}
    new_patches = []
    for ver in sorted(version_dates.keys(), key=lambda v: [int(x) for x in v.split('.')]):
        dts = sorted(list(version_dates[ver]))
        if len(dts) == 1:
            phase_names = ['上']
        elif len(dts) == 2:
            phase_names = ['上', '下']
        elif len(dts) == 3:
            phase_names = ['上', '中', '下']
        else:
            phase_names = [f'期{i+1}' for i in range(len(dts))]

        for dt, phase_name in zip(dts, phase_names):
            patch_name = f"{ver}{phase_name}"
            ver_phases[(ver, dt)] = patch_name
            new_patches.append({
                'patch': patch_name,
                'date': dt.strftime('%y/%m/%d')
            })

    print(f"✅ 解析出 {len(new_patches)} 個遊戲版本節點，最新版本：{new_patches[-3:]}")

    # 批次查詢卡池對應的 5 星角色
    unique_pages = list(set(r['warp_page'] for r in warp_records))
    page_to_chars = {}

    for i in range(0, len(unique_pages), 50):
        batch = unique_pages[i:i+50]
        res = session.get(WIKI_API_URL, params={
            'action': 'query',
            'prop': 'revisions',
            'titles': '|'.join(batch),
            'rvprop': 'content',
            'rvslots': 'main',
            'format': 'json'
        }, timeout=REQUEST_TIMEOUT).json()

        pages = res.get('query', {}).get('pages', {})
        for pid, pinfo in pages.items():
            title = pinfo.get('title', '')
            content = pinfo.get('revisions', [{}])[0].get('slots', {}).get('main', {}).get('*', '')

            # 提取 5 星角色
            m = re.search(r'character_5_F\s*=\s*([^|\n]+)', content)
            if not m:
                m = re.search(r'5\{\{star\}\}\s*Character===?\s*\n\*\s*\{\{Character Intro\|([^}]+)\}\}', content, re.IGNORECASE)

            if m:
                raw_chars = m.group(1).strip()
                raw_chars = re.sub(r'<!--.*?-->', '', raw_chars).strip()
                # 支援分號分隔的多角色自選池 (如 Indelible Coterie)
                char_list = [c.strip() for c in raw_chars.split(';') if c.strip()]
                page_to_chars[title] = char_list

    # 組裝成排程結果
    schedules = []
    seen_schedule_keys = set()

    for r in warp_records:
        wp = r['warp_page']
        char_list = page_to_chars.get(wp, [])
        run_name = ver_phases.get((r['version'], r['start_dt']))

        if not run_name:
            continue

        for char_name in char_list:
            key = (char_name, run_name)
            if key not in seen_schedule_keys:
                seen_schedule_keys.add(key)
                schedules.append({
                    'en_name': char_name,
                    'run': run_name,
                    'is_collab': r['is_collab'],
                    'patch_date': r['start_dt'].strftime('%y/%m/%d')
                })

    print(f"✅ 成功從 Fandom Wiki 建立 {len(schedules)} 筆角色卡池登場關聯")
    return schedules, new_patches


# ──────────────────────────────────────────────────
# 角色中文化與資訊補全引擎
# ──────────────────────────────────────────────────
def fetch_starrailres_data(session):
    """從 StarRailRes 抓取解包角色庫"""
    print("正在從 StarRailRes 抓取解包角色庫...")
    base = "https://raw.githubusercontent.com/Mar-7th/StarRailRes/master/index_new"
    try:
        en_res = session.get(f"{base}/en/characters.json", timeout=REQUEST_TIMEOUT).json()
        cht_res = session.get(f"{base}/cht/characters.json", timeout=REQUEST_TIMEOUT).json()
        print("  → StarRailRes 解包庫載入成功")
        return en_res, cht_res
    except Exception as e:
        print(f"⚠️ StarRailRes 載入失敗: {e}")
        return {}, {}


def enrich_character_info(en_name, en_data, cht_data, wiki_char_cache, session):
    """
    綜合查詢 StarRailRes 與 Fandom Wiki，為角色補全：
    - 正體中文名稱 (target_name)
    - 遊戲角色 ID (target_cid)
    - 命途 (path)
    - 屬性 (elem)
    """
    sanitized = sanitize_name(en_name)
    target_cid = None
    target_name = en_name
    path = "未知"
    elem = "未知"

    # 0. 優先檢查特殊備援映射
    if en_name in SPECIAL_NAME_MAP:
        target_name = SPECIAL_NAME_MAP[en_name]
    else:
        for k, v in SPECIAL_NAME_MAP.items():
            if sanitize_name(k) == sanitized:
                target_name = v
                break

    # 1. 優先比對 StarRailRes
    for cid, info in en_data.items():
        if sanitize_name(info.get("name", "")) == sanitized or (target_name and sanitize_name(info.get("name", "")) == sanitize_name(target_name)):
            target_cid = cid
            cht_info = cht_data.get(cid, {})
            if isinstance(cht_info, dict):
                target_name = cht_info.get("name", en_name)
                db_path = cht_info.get("path")
                raw_path = db_path.get("name") if isinstance(db_path, dict) else db_path
                path = PATH_MAP.get(raw_path, raw_path or "未知")

                db_elem = cht_info.get("element")
                raw_elem = db_elem.get("name") if isinstance(db_elem, dict) else db_elem
                elem = ELEM_MAP.get(raw_elem, raw_elem or "未知")
            break

    # 2. 若 StarRailRes 尚未更新或名稱非中文，備援向 Fandom Wiki 查詢
    if target_name == en_name or not contains_cjk(target_name) or path == "未知" or elem == "未知":
        if en_name in wiki_char_cache:
            w_info = wiki_char_cache[en_name]
        else:
            w_info = query_wiki_character_page(en_name, session)
            wiki_char_cache[en_name] = w_info

        if w_info.get("cht_name") and (target_name == en_name or not contains_cjk(target_name)):
            target_name = w_info["cht_name"]
            print(f"  ✨ Fandom Wiki 成功補全繁中名稱: {en_name} ➡️ {target_name}")

        if path == "未知" and w_info.get("path"):
            path = PATH_MAP.get(w_info["path"], w_info["path"])

        if elem == "未知" and w_info.get("elem"):
            elem = ELEM_MAP.get(w_info["elem"], w_info["elem"])

    return target_cid, target_name, path, elem


def query_wiki_character_page(char_name, session):
    """向 Fandom Wiki 查詢單一角色頁面中的中文化與命途屬性"""
    info = {"cht_name": None, "path": None, "elem": None}
    try:
        res = session.get(WIKI_API_URL, params={
            'action': 'query',
            'titles': char_name,
            'prop': 'revisions',
            'rvslots': 'main',
            'rvprop': 'content',
            'format': 'json'
        }, timeout=REQUEST_TIMEOUT).json()

        pages = res.get('query', {}).get('pages', {})
        for pid, p in pages.items():
            if pid == "-1":
                continue
            content = p.get('revisions', [{}])[0].get('slots', {}).get('main', {}).get('*', '')

            # 繁中名
            m_tw = re.search(r'\|(?:zht|zh[-_]?(?:tw|hk))\s*=\s*([^\n\|]+)', content, re.IGNORECASE)
            if m_tw and m_tw.group(1).strip():
                info["cht_name"] = clean_wikitext_value(m_tw.group(1))
            else:
                m_zh = re.search(r'\|(?:zhs|zh)\s*=\s*([^\n\|]+)', content, re.IGNORECASE)
                if m_zh and m_zh.group(1).strip():
                    info["cht_name"] = clean_wikitext_value(m_zh.group(1))

            # 命途
            m_path = re.search(r'\|path\s*=\s*([^\n\|]+)', content)
            if m_path:
                info["path"] = clean_wikitext_value(m_path.group(1))

            # 屬性
            m_elem = re.search(r'\|(?:combatType|element)\s*=\s*([^\n\|]+)', content)
            if m_elem:
                info["elem"] = clean_wikitext_value(m_elem.group(1))

    except Exception as e:
        print(f"  ⚠️ 查詢 Wiki 角色頁面 [{char_name}] 失敗: {e}")

    return info


# ──────────────────────────────────────────────────
# 主執行邏輯
# ──────────────────────────────────────────────────
def fetch_latest_data():
    print("\n" + "=" * 55)
    print("🚀 開始執行 HSR Banner 自動更新流程 (Fandom Engine)")
    print("=" * 55)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })

    # Step 1: 抓取 Fandom Wiki 卡池與版本
    schedules, new_patch_items = fetch_fandom_schedules_and_patches(session)

    # 🛡️ 熔斷保護
    if not schedules:
        print("\n⚠️ 警告：無法取得任何有效的卡池排程資料。")
        print("🛡️ 觸發熔斷保護，停止本次更新，避免空白資料覆蓋現有 Gist。")
        return None

    # Step 2: 從 Gist 讀取現有資料
    existing_data = {"new_patches": [], "new_characters": []}
    try:
        gist_url = f"https://api.github.com/gists/{GIST_ID}"
        gist_res = session.get(gist_url, timeout=REQUEST_TIMEOUT)
        gist_res.raise_for_status()
        files = gist_res.json().get('files', {})
        gist_file = files.get('hsr_latest_banner.json')
        if not gist_file or 'content' not in gist_file:
            raise RuntimeError('Gist 缺少 hsr_latest_banner.json')
        existing_data = json.loads(gist_file['content'])
        if not isinstance(existing_data, dict):
            raise ValueError('Gist 根節點必須是物件')
        print(f"\n📖 Gist 現有資料：{len(existing_data.get('new_characters', []))} 個角色、{len(existing_data.get('new_patches', []))} 個版本")
    except Exception as e:
        print(f"\n❌ 讀取現有 Gist 失敗: {e}")
        print("🛡️ 停止更新，保護現有資料。")
        return None

    updated_chars = existing_data.get('new_characters', [])

    # Step 3: 清洗舊格式 runs 與無效版本名
    for char in updated_chars:
        if 'runs' in char and isinstance(char['runs'], list):
            clean_runs = []
            for r in char['runs']:
                if isinstance(r, str):
                    clean_runs.append(r)
                elif isinstance(r, dict) and 'version' in r and 'phase' in r:
                    half = "上" if r['phase'] == 1 else "下"
                    clean_runs.append(f"{r['version']}{half}")
            char['runs'] = clean_runs

    cleaned = clean_invalid_runs(updated_chars)
    if cleaned:
        print(f"🧹 已清理 {cleaned} 個角色的無效版本名稱")

    # Step 4: 載入解包庫與 Wiki 角色快取
    en_data, cht_data = fetch_starrailres_data(session)
    wiki_char_cache = {}

    existing_char_map_by_cid = {c['cid']: c for c in updated_chars if c.get('cid')}
    existing_char_map_by_name = {c['name']: c for c in updated_chars}

    print(f"\n🔄 開始比對與整合 {len(schedules)} 筆排程...")

    # Step 5: 逐筆整合排程
    for sched in schedules:
        en_name = sched['en_name']
        run = sched['run']
        is_collab = sched.get('is_collab', False)

        target_cid, target_name, path, elem = enrich_character_info(
            en_name, en_data, cht_data, wiki_char_cache, session
        )

        # 比對現有角色 (中文名 > sanitize 英文名 > CID)
        matched_char = None
        if target_name in existing_char_map_by_name:
            matched_char = existing_char_map_by_name[target_name]
        else:
            for char in updated_chars:
                if sanitize_name(char.get('name', '')) == sanitize_name(en_name):
                    matched_char = char
                    break

        if not matched_char and target_cid and target_cid in existing_char_map_by_cid:
            matched_char = existing_char_map_by_cid[target_cid]

        if matched_char:
            # 自動升級英文名為正體中文
            if (matched_char.get('name') != target_name and target_name != en_name
                    and not contains_cjk(matched_char.get('name', '')) and contains_cjk(target_name)):
                print(f"  🔄 名稱升級: {matched_char['name']} ➡️ {target_name}")
                matched_char['name'] = target_name

            # 補全 CID
            if target_cid and (not matched_char.get('cid') or matched_char.get('name') == target_name):
                matched_char['cid'] = target_cid

            # 補全命途與屬性
            if matched_char.get('path') in ["未知", "", None] and path != "未知":
                matched_char['path'] = path
            if matched_char.get('elem') in ["未知", "", None] and elem != "未知":
                matched_char['elem'] = elem

            # 更新 runs
            if is_collab or matched_char.get('isCollab'):
                matched_char['runs'] = []
            else:
                if 'runs' not in matched_char or not isinstance(matched_char['runs'], list):
                    matched_char['runs'] = []
                if run not in matched_char['runs']:
                    matched_char['runs'].append(run)
                    print(f"  📅 新增登場版本: {matched_char['name']} ➡️ {run}")
        else:
            new_char = {
                "cid": target_cid,
                "name": target_name,
                "path": path,
                "elem": elem,
                "runs": [] if is_collab else [run]
            }
            if is_collab:
                new_char["isCollab"] = run
            updated_chars.append(new_char)
            if target_cid:
                existing_char_map_by_cid[target_cid] = new_char
            existing_char_map_by_name[target_name] = new_char
            print(f"  ✨ 發現新角色: {target_name} (CID: {target_cid}) [{path}/{elem}] ➡️ {run}")

    result = {
        "new_patches": merge_new_patches(
            existing_data.get('new_patches', []),
            new_patch_items
        ),
        "new_characters": updated_chars
    }

    print(f"\n📊 最終整合：{len(result['new_characters'])} 位角色、{len(result['new_patches'])} 個版本")
    return result


# ──────────────────────────────────────────────────
# 回寫 GitHub Gist
# ──────────────────────────────────────────────────
def update_gist(data):
    print("\n準備將最新資料同步回 GitHub Gist...")
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
    try:
        response = requests.patch(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        print("✅ Gist 自動更新成功！")
        return True
    except requests.RequestException as error:
        print(f"❌ Gist 更新失敗: {error}")
        return False


# ──────────────────────────────────────────────────
# 程式入口
# ──────────────────────────────────────────────────
if __name__ == "__main__":
    if not GITHUB_TOKEN:
        print("⚠️ 未檢測到 GIST_TOKEN 環境變數，將以唯讀/測試模式執行...")
        latest_data = fetch_latest_data()
        if latest_data is not None:
            print("✅ 測試成功：資料解析與整合完全正常！")
        else:
            print("❌ 測試失敗：未能取得有效資料。")
            raise SystemExit(2)
    else:
        latest_data = fetch_latest_data()
        if latest_data is not None:
            if not update_gist(latest_data):
                raise SystemExit(1)
        else:
            print("\n🛑 任務安全終止：保持現有 Gist 資料不變。")
            raise SystemExit(2)
