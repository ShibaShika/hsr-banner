import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
import requests
from bs4 import BeautifulSoup

# 強制確保終端輸出採用 UTF-8 編碼，防止 Windows 環境下因 CP950 導致 Emoji 或特殊中文字輸出失敗
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# ──────────────────────────────────────────────────
# 基本設定與常數
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
# 工具函式
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


# ──────────────────────────────────────────────────
# 本地 JS 檔案讀寫解析引擎
# ──────────────────────────────────────────────────
def parse_local_js_array(filepath, var_name):
    """精確解析專案內現有的 js 陣列代碼"""
    if not os.path.exists(filepath):
        print(f"⚠️ 找不到檔案：{filepath}")
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    start_match = re.search(r'const\s+' + var_name + r'\s*=\s*\[', content)
    if not start_match:
        print(f"⚠️ 在 {filepath} 中找不到 {var_name}")
        return []
    start_pos = start_match.end() - 1

    bracket_level = 0
    end_pos = -1
    in_string = False
    string_char = ''

    for i in range(start_pos, len(content)):
        char = content[i]
        if in_string:
            if char == string_char and content[i - 1] != '\\':
                in_string = False
        else:
            if char in ('"', "'"):
                in_string = True
                string_char = char
            elif char == '[':
                bracket_level += 1
            elif char == ']':
                bracket_level -= 1
                if bracket_level == 0:
                    end_pos = i + 1
                    break

    if end_pos == -1:
        return []

    raw_array = content[start_pos:end_pos]
    json_str = re.sub(r'([{\s,])([a-zA-Z_$][a-zA-Z0-9_$]*)\s*:', r'\1"\2":', raw_array)
    json_str = re.sub(r"'([^']*)'", r'"\1"', json_str)
    json_str = re.sub(r',\s*([\]}])', r'\1', json_str)

    try:
        return json.loads(json_str)
    except Exception as e:
        print(f"⚠️ 解析 {filepath} 發生錯誤: {e}")
        return []


def serialize_js_file(var_name, data, filepath):
    """序列化為標準格式並覆寫至 js 檔案（與 editor.html 匯出完全一致）"""
    json_str = json.dumps(data, ensure_ascii=False, indent=4)
    # 僅替換行首縮排的合法 JS key，不誤傷內容
    js_str = re.sub(r'^(\s*)"([a-zA-Z_$][a-zA-Z0-9_$]*)":', r'\1\2:', json_str, flags=re.MULTILINE)

    today_str = datetime.now().strftime("%Y/%m/%d")
    header = f"// 更新日期: {today_str}\n\n"
    content = f"{header}const {var_name} = {js_str};\n"

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"💾 已成功寫入專案檔案：{filepath}")


# ──────────────────────────────────────────────────
# 核心資料源：Fandom Wiki 結構化躍遷歷史與排程
# ──────────────────────────────────────────────────
def fetch_fandom_schedules_and_patches(session):
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
    version_dates = {}

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
        batch = unique_pages[i:i + 50]
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

            m = re.search(r'character_5_F\s*=\s*([^|\n]+)', content)
            if not m:
                m = re.search(r'5\{\{star\}\}\s*Character===?\s*\n\*\s*\{\{Character Intro\|([^}]+)\}\}', content, re.IGNORECASE)

            if m:
                raw_chars = m.group(1).strip()
                raw_chars = re.sub(r'<!--.*?-->', '', raw_chars).strip()
                char_list = [c.strip() for c in raw_chars.split(';') if c.strip()]
                page_to_chars[title] = char_list

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
    sanitized = sanitize_name(en_name)
    target_cid = None
    target_name = en_name
    path = "未知"
    elem = "未知"

    # 0. 優先檢查特殊別名字典
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

    # 2. 備援向 Fandom Wiki 查詢
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

            m_tw = re.search(r'\|(?:zht|zh[-_]?(?:tw|hk))\s*=\s*([^\n\|]+)', content, re.IGNORECASE)
            if m_tw and m_tw.group(1).strip():
                info["cht_name"] = clean_wikitext_value(m_tw.group(1))
            else:
                m_zh = re.search(r'\|(?:zhs|zh)\s*=\s*([^\n\|]+)', content, re.IGNORECASE)
                if m_zh and m_zh.group(1).strip():
                    info["cht_name"] = clean_wikitext_value(m_zh.group(1))

            m_path = re.search(r'\|path\s*=\s*([^\n\|]+)', content)
            if m_path:
                info["path"] = clean_wikitext_value(m_path.group(1))

            m_elem = re.search(r'\|(?:combatType|element)\s*=\s*([^\n\|]+)', content)
            if m_elem:
                info["elem"] = clean_wikitext_value(m_elem.group(1))

    except Exception as e:
        print(f"  ⚠️ 查詢 Wiki 角色頁面 [{char_name}] 失敗: {e}")

    return info


# ──────────────────────────────────────────────────
# 🛡️ 五道安全防護檢驗門檻（Pre-commit Validation Gates）
# ──────────────────────────────────────────────────
def validate_data_integrity(original_chars, original_patches, new_chars, new_patches):
    """
    五道強制安全防護檢驗門檻。
    若有任何一項檢驗不通過，拋出 AssertionError 並立即中斷，絕不寫入專案！
    """
    print("\n🛡️ 正在執行五道安全防護檢驗門檻 (Pre-commit Validation)...")

    # 門檻 1：角色數量不減少原則
    if len(new_chars) < len(original_chars):
        raise AssertionError(
            f"❌ 門檻 1 失敗：角色總數異常減少！(原 {len(original_chars)} 位 ➡️ 現 {len(new_chars)} 位)"
        )
    print(f"  ✅ 門檻 1 通過：角色總數維持或增加 ({len(original_chars)} ➡️ {len(new_chars)})")

    # 門檻 2：版本數量不減少原則
    if len(new_patches) < len(original_patches):
        raise AssertionError(
            f"❌ 門檻 2 失敗：版本總數異常減少！(原 {len(original_patches)} 個 ➡️ 現 {len(new_patches)} 個)"
        )
    print(f"  ✅ 門檻 2 通過：版本數量維持或增加 ({len(original_patches)} ➡️ {len(new_patches)})")

    # 門檻 3：版本名稱規格檢驗
    patch_names_set = set()
    for p in new_patches:
        name = p.get('patch', '')
        date = p.get('date', '')
        if not PATCH_NAME_RE.fullmatch(name):
            raise AssertionError(f"❌ 門檻 3 失敗：版本名稱不合規：{name!r}")
        if not normalize_patch_date(date):
            raise AssertionError(f"❌ 門檻 3 失敗：版本日期不合規：{name} ({date})")
        if name in patch_names_set:
            raise AssertionError(f"❌ 門檻 3 失敗：版本重複定義：{name}")
        patch_names_set.add(name)
    print(f"  ✅ 門檻 3 通過：所有 {len(new_patches)} 個版本命名與日期格式完全合規")

    # 門檻 4：版本閉包防護（孤兒版本防護）
    for c in new_chars:
        for r in c.get('runs', []):
            if r not in patch_names_set:
                raise AssertionError(
                    f"❌ 門檻 4 失敗：角色 [{c.get('name')}] 的排程版本 [{r}] 不存在於版本清單中！"
                )
    print("  ✅ 門檻 4 通過：所有角色的登場排程皆有對應之版本節點")

    # 門檻 5：既有角色的歷史排程不可逆原則
    original_char_map = {c.get('name'): set(c.get('runs', [])) for c in original_chars if c.get('name')}
    for c in new_chars:
        name = c.get('name')
        if name in original_char_map:
            orig_runs = original_char_map[name]
            new_runs = set(c.get('runs', []))
            if not orig_runs.issubset(new_runs):
                missing = orig_runs - new_runs
                raise AssertionError(
                    f"❌ 門檻 5 失敗：角色 [{name}] 的歷史排程遺失：{missing}！"
                )
    print("  ✅ 門檻 5 通過：所有既有角色的歷史排程完全被繼承，未發生歷史資料縮水")
    print("🎉 五道安全檢驗全數通過！資料結構完整且安全無虞。\n")


# ──────────────────────────────────────────────────
# 深度合併與自動化執行主流程
# ──────────────────────────────────────────────────
def execute_auto_update():
    print("\n" + "=" * 60)
    print("🚀 啟動 HSR Banner 全自動資料更新流程 (雙軌直寫 + 安全防護)")
    print("=" * 60)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })

    patches_file = os.path.join("js", "patches.js")
    chars_file = os.path.join("js", "characters.js")

    # 1. 讀取專案既有基準資料
    original_patches = parse_local_js_array(patches_file, 'PATCH_DATA')
    original_chars = parse_local_js_array(chars_file, 'RAW_CHARACTERS')
    print(f"📖 專案現有資料：{len(original_chars)} 位角色、{len(original_patches)} 個版本")

    # 2. 從 Fandom Wiki 抓取排程
    schedules, wiki_patches = fetch_fandom_schedules_and_patches(session)
    if not schedules:
        print("⚠️ 無法取得任何有效的排程資料，觸發保護熔斷！")
        return False

    # 3. 合併版本清單（選項 B：僅更新當前版本及未來版本，保護過去歷史版本）
    # 依台灣時間找出當前正在進行中的版本
    tz_tw = timezone(timedelta(hours=8))
    today_tw_str = datetime.now(tz_tw).strftime('%y/%m/%d')

    current_patch_idx = 0
    for idx, p in enumerate(original_patches):
        norm_date = normalize_patch_date(p.get('date'))
        if norm_date and norm_date <= today_tw_str:
            current_patch_idx = idx

    # 當前版本及之後的所有未來版本均允許自動校正日期
    updatable_patch_names = set(p['patch'] for p in original_patches[current_patch_idx:])
    current_patch_name = original_patches[current_patch_idx]['patch'] if original_patches else "無"
    print(f"🕒 當前進行中版本：{current_patch_name}，納入日期自動追蹤校正之版本：{sorted(list(updatable_patch_names))}")

    patches_by_name = {}
    for p in original_patches:
        patches_by_name[p['patch']] = dict(p)

    new_patches_added = []
    patch_dates_updated_log = []

    for p in wiki_patches:
        name = p['patch']
        if name not in patches_by_name:
            patches_by_name[name] = p
            new_patches_added.append(name)
        elif name in updatable_patch_names:
            old_date = patches_by_name[name].get('date', '')
            new_date = p.get('date', '')
            norm_old = normalize_patch_date(old_date)
            norm_new = normalize_patch_date(new_date)
            if norm_new and norm_new != norm_old:
                patches_by_name[name]['date'] = norm_new
                patch_dates_updated_log.append(f"{name}: {old_date} ➡️ {norm_new}")
                print(f"  📅 自動校正版本日期: [{name}] {old_date} ➡️ {norm_new}")

    # 依日期及版本號排序
    merged_patches = sorted(patches_by_name.values(), key=lambda p: (normalize_patch_date(p['date']) or "", p['patch']))

    # 4. 合併角色清單
    en_data, cht_data = fetch_starrailres_data(session)
    wiki_char_cache = {}

    # 深拷貝以避免污染
    merged_chars = json.loads(json.dumps(original_chars))
    existing_char_map_by_cid = {c['cid']: c for c in merged_chars if c.get('cid')}
    existing_char_map_by_name = {c['name']: c for c in merged_chars if c.get('name')}

    new_chars_added = []
    runs_added_log = []
    name_upgraded_log = []

    for sched in schedules:
        en_name = sched['en_name']
        run = sched['run']
        is_collab = sched.get('is_collab', False)

        target_cid, target_name, path, elem = enrich_character_info(
            en_name, en_data, cht_data, wiki_char_cache, session
        )

        matched_char = None
        if target_name in existing_char_map_by_name:
            matched_char = existing_char_map_by_name[target_name]
        else:
            for char in merged_chars:
                if sanitize_name(char.get('name', '')) == sanitize_name(en_name):
                    matched_char = char
                    break

        if not matched_char and target_cid and target_cid in existing_char_map_by_cid:
            matched_char = existing_char_map_by_cid[target_cid]

        if matched_char:
            # 升級名稱
            if (matched_char.get('name') != target_name and target_name != en_name
                    and not contains_cjk(matched_char.get('name', '')) and contains_cjk(target_name)):
                name_upgraded_log.append(f"{matched_char['name']} ➡️ {target_name}")
                matched_char['name'] = target_name

            # 補全 CID
            if target_cid and (not matched_char.get('cid') or matched_char.get('name') == target_name):
                matched_char['cid'] = target_cid

            # 補全命途/屬性
            if matched_char.get('path') in ["未知", "", None] and path != "未知":
                matched_char['path'] = path
            if matched_char.get('elem') in ["未知", "", None] and elem != "未知":
                matched_char['elem'] = elem

            # 補充排程
            if not is_collab and not matched_char.get('isCollab'):
                if 'runs' not in matched_char or not isinstance(matched_char['runs'], list):
                    matched_char['runs'] = []
                if run not in matched_char['runs']:
                    matched_char['runs'].append(run)
                    runs_added_log.append(f"{matched_char['name']} ➡️ {run}")
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
            merged_chars.append(new_char)
            if target_cid:
                existing_char_map_by_cid[target_cid] = new_char
            existing_char_map_by_name[target_name] = new_char
            new_chars_added.append(f"{target_name} ({path}/{elem}) ➡️ {run}")

    # 5. 執行五道安全防護檢驗門檻
    validate_data_integrity(original_chars, original_patches, merged_chars, merged_patches)

    # 6. 比對是否有實質變更
    has_patches_changed = json.dumps(original_patches) != json.dumps(merged_patches)
    has_chars_changed = json.dumps(original_chars) != json.dumps(merged_chars)

    if not has_patches_changed and not has_chars_changed:
        print("✨ 專案資料庫目前已經是最新狀態，無需寫入更新。")
        return True

    # 7. 寫入本地專案檔案
    serialize_js_file('PATCH_DATA', merged_patches, patches_file)
    serialize_js_file('RAW_CHARACTERS', merged_chars, chars_file)

    # 8. 產生日誌摘要檔案（供 CI Commit Message 使用）
    summary_lines = []
    if new_patches_added:
        summary_lines.append(f"🆕 新增版本 ({len(new_patches_added)} 個): {', '.join(new_patches_added)}")
    if patch_dates_updated_log:
        summary_lines.append(f"📅 版本日期校正 ({len(patch_dates_updated_log)} 項):\n  • " + "\n  • ".join(patch_dates_updated_log))
    if new_chars_added:
        summary_lines.append(f"✨ 發現新角色 ({len(new_chars_added)} 位):\n  • " + "\n  • ".join(new_chars_added))
    if runs_added_log:
        summary_lines.append(f"📅 新增排程登場 ({len(runs_added_log)} 項):\n  • " + "\n  • ".join(runs_added_log))
    if name_upgraded_log:
        summary_lines.append(f"🔄 名稱繁體中文化 ({len(name_upgraded_log)} 位):\n  • " + "\n  • ".join(name_upgraded_log))

    summary_text = "\n".join(summary_lines)
    with open(".update_summary.md", "w", encoding="utf-8") as f:
        f.write(summary_text)

    print("\n📝 變更摘要清單：")
    print(summary_text)

    # 9. 備份同步至 GitHub Gist（相容舊版後台）
    if GITHUB_TOKEN:
        update_gist_backup({
            "new_patches": [p for p in merged_patches if p['patch'] in new_patches_added],
            "new_characters": merged_chars[-len(new_chars_added):] if new_chars_added else []
        }, session)

    return True


def update_gist_backup(data, session):
    print("\n同步備份最新資料至 GitHub Gist...")
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
        res = session.patch(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            print("✅ GitHub Gist 備份同步成功！")
        else:
            print(f"⚠️ Gist 備份狀態碼: {res.status_code}")
    except Exception as e:
        print(f"⚠️ Gist 備份未完成: {e}")


# ──────────────────────────────────────────────────
# 程式進入點
# ──────────────────────────────────────────────────
if __name__ == "__main__":
    success = execute_auto_update()
    if not success:
        raise SystemExit(2)
