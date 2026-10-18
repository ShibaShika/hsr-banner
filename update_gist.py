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
TZ_TW = timezone(timedelta(hours=8))
REQUEST_TIMEOUT = 25
PATCH_NAME_RE = re.compile(r'^\d+\.\d+[上下中]$')
WIKI_API_URL = "https://honkai-star-rail.fandom.com/api.php"

# Regexes for extracting collaboration/upcoming versions and characters
RE_UPCOMING_VERSION_1 = re.compile(r'(?:begin in|release in|start in|in)\s*\[\[Version\s*(\d+\.\d+)\]\]', re.IGNORECASE)
RE_UPCOMING_VERSION_2 = re.compile(r'Version\s+(\d+\.\d+)')
RE_UPCOMING_CHARS = re.compile(r'feature the characters?\s*\[\[([^\]]+)\]\](?:\s*and\s*\[\[([^\]]+)\]\])?', re.IGNORECASE)

PATH_MAP = {
    "Destruction": "毀滅", "Warrior": "毀滅",
    "Hunt": "巡獵", "Rogue": "巡獵",
    "Erudition": "智識", "Mage": "智識",
    "Harmony": "同諧", "Shaman": "同諧",
    "Nihility": "虛無", "Warlock": "虛無",
    "Preservation": "存護", "Knight": "存護",
    "Abundance": "豐饒", "Priest": "豐饒",
    "Remembrance": "記憶", "Memory": "記憶",
    "Elation": "歡愉",
    # 星神命途（未來可能開放為可操作命途），僅做中文化映射，不影響既有判定
    "Propagation": "繁育",
    "Order": "秩序",
    "Trailblaze": "開拓",
    "Beauty": "純美",
    "Enigmata": "神秘",
    "Voracity": "貪饕",
    "Equilibrium": "平衡"
}
PATH_MAP_LOWER = {k.lower(): v for k, v in PATH_MAP.items()}
KNOWN_PATH_NAMES = set(PATH_MAP.values())

# 前端 js/paths.js 已註冊專屬圖示與排序的「核心命途」；其餘命途一律以動態方式保留並由前端通用降級樣式呈現
CORE_PATHS = ("毀滅", "巡獵", "智識", "同諧", "虛無", "存護", "豐饒", "記憶", "歡愉")
UNKNOWN_LABEL = "未知"

ELEM_MAP = {
    "Physical": "物理",
    "Fire": "火",
    "Ice": "冰",
    "Lightning": "雷", "Thunder": "雷",
    "Wind": "風",
    "Quantum": "量子",
    "Imaginary": "虛數"
}

# ──────────────────────────────────────────────────
# 卡池強化模式（Buff Mode）動態標記
#   資料結構：buffs 維持「版本名稱字串陣列」以完全相容既有資料與 editor.html；
#   非預設強化模式則額外寫入 buffTypes: { "<版本>": "<強化模式名稱>" }。
# ──────────────────────────────────────────────────
DEFAULT_BUFF_TYPE = "礪爍新輝"
BUFF_TYPE_MAP = {
    "enhanced": DEFAULT_BUFF_TYPE,
    "enhancement": DEFAULT_BUFF_TYPE,
    "礪爍新輝": DEFAULT_BUFF_TYPE,
    "砺烁新辉": DEFAULT_BUFF_TYPE,
}
RE_BUFF_PARAM = re.compile(r'\|\s*(?:enhanced|enhancement|buff_type|buff_mode)\s*=\s*([^|\n}]*)', re.IGNORECASE)
RE_BUFF_TEMPLATE = re.compile(r'\{\{\s*(?:Enhanced|Enhancement|Buff Mode)\s*(?:\|\s*([^}|]*))?\}\}', re.IGNORECASE)
RE_BUFF_INLINE = re.compile(r'\(\s*(?:Enhanced|Enhancement)\s*(?:[:：]\s*([^)]*))?\)', re.IGNORECASE)


# ──────────────────────────────────────────────────
# 工具函式
# ──────────────────────────────────────────────────
def sanitize_name(name):
    """去除所有非英數字元並轉小寫，用於無障礙模糊匹配"""
    if not name:
        return ""
    name = str(name).replace('&', 'and')
    return re.sub(r'[^a-zA-Z0-9]', '', name).lower()


def normalize_cjk_name(name):
    """標準化 CJK 中文名稱（去除間隔號與空白），用於跨格式比對"""
    if not name:
        return ""
    return re.sub(r'[・·•\s]', '', str(name))


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
    return val.strip().replace('·', '•').replace('・', '•')


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
# 🧭 命途 / 💠 強化模式 動態正規化（遇到未預設的新值一律「保留」而非報錯）
# ──────────────────────────────────────────────────
RE_PATH_PREFIX = re.compile(r'^(?:path(?:\s+of\s+|\s*[/:：]\s*|\s+))?(?:the\s+)?', re.IGNORECASE)


def normalize_path_name(raw):
    """
    將任意來源（StarRailRes ID、Wiki 文字、Wiki 連結、dict）的命途正規化為繁中名稱。
    - 已知命途：映射為繁中（如 Hunt / The Hunt / [[Path/Hunt|The Hunt]] ➡️ 巡獵）
    - 未知新命途：保留清理後的原始名稱（如 Finality ➡️ Finality、繁育 ➡️ 繁育），絕不拋錯
    - 空值：回傳「未知」
    """
    if isinstance(raw, dict):
        raw = raw.get('name') or raw.get('id') or ''
    if raw is None:
        return UNKNOWN_LABEL
    val = clean_wikitext_value(str(raw))
    val = re.sub(r'[\[\]{}]', '', val).strip()
    if not val or val == UNKNOWN_LABEL:
        return UNKNOWN_LABEL
    if val in KNOWN_PATH_NAMES:
        return val
    stripped = RE_PATH_PREFIX.sub('', val).strip() or val
    mapped = PATH_MAP_LOWER.get(stripped.lower()) or PATH_MAP_LOWER.get(val.lower())
    return mapped or stripped


def normalize_buff_type(raw):
    """將強化模式標記正規化；yes/true/空值 ➡️ 預設模式，no/false ➡️ None，未知新模式 ➡️ 保留原名"""
    if raw is None:
        return None
    val = clean_wikitext_value(str(raw)).strip()
    low = val.lower()
    if low in ('no', 'false', '0', 'none', 'n'):
        return None
    if not val or low in ('yes', 'true', '1', 'y'):
        return DEFAULT_BUFF_TYPE
    return BUFF_TYPE_MAP.get(low) or BUFF_TYPE_MAP.get(val) or val


def extract_buff_marker(text):
    """
    從 Wikitext / 表格文字中保守地擷取強化模式標記，找不到時回傳 None。
    支援：|enhanced=yes、|buff_type=新模式、{{Enhancement|新模式}}、(Enhanced)、(Enhancement: 新模式)、礪爍新輝
    """
    if not text:
        return None
    text = str(text)
    for regex in (RE_BUFF_PARAM, RE_BUFF_TEMPLATE, RE_BUFF_INLINE):
        m = regex.search(text)
        if m:
            return normalize_buff_type(m.group(1) if m.group(1) is not None else 'yes')
    if '礪爍新輝' in text or '砺烁新辉' in text:
        return DEFAULT_BUFF_TYPE
    return None


def apply_buff_marker(char, patch, buff_type):
    """
    將強化標記整合至角色資料（保留既有 buffs / buffTypes 不覆蓋其他版本）。
    回傳 True 表示資料有實際變更。
    """
    if not char or not patch or not buff_type:
        return False
    changed = False
    buffs = char.get('buffs')
    if not isinstance(buffs, list):
        buffs = []
    if patch not in buffs:
        buffs.append(patch)
        changed = True
    char['buffs'] = buffs

    if buff_type != DEFAULT_BUFF_TYPE:
        buff_types = char.get('buffTypes')
        if not isinstance(buff_types, dict):
            buff_types = {}
        if buff_types.get(patch) != buff_type:
            buff_types[patch] = buff_type
            changed = True
        char['buffTypes'] = buff_types
    return changed


def get_char_buff_types(char):
    """取得角色所有出現過的強化模式（buffs 預設為礪爍新輝，buffTypes 可覆寫為新模式）"""
    types = []
    buff_types = char.get('buffTypes') if isinstance(char.get('buffTypes'), dict) else {}
    for b in (char.get('buffs') or []):
        if isinstance(b, dict):
            patch, t = b.get('patch'), b.get('type')
        else:
            patch, t = b, None
        raw = t or buff_types.get(patch) or DEFAULT_BUFF_TYPE
        for item in (raw if isinstance(raw, list) else [raw]):
            if item and item not in types:
                types.append(item)
    return types


def collect_paths(chars):
    """依出現順序收集所有角色的命途（排除空值）"""
    seen = []
    for c in chars or []:
        p = c.get('path')
        if isinstance(p, str) and p.strip() and p not in seen:
            seen.append(p)
    return seen


def collect_buff_types(chars):
    seen = []
    for c in chars or []:
        for t in get_char_buff_types(c):
            if t not in seen:
                seen.append(t)
    return seen


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

    today_str = datetime.now(TZ_TW).strftime("%Y/%m/%d")
    header = f"// 更新日期: {today_str}\n"
    if var_name == "RAW_CHARACTERS":
        header += f'const LAST_UPDATED = "{today_str}";\n'
    content = f"{header}\nconst {var_name} = {js_str};\n"

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"💾 已成功寫入專案檔案：{filepath}")


# ──────────────────────────────────────────────────
# 核心資料源：Fandom Wiki 結構化躍遷歷史與排程
# ──────────────────────────────────────────────────
def parse_warp_list_tables(tables, parse_header_date):
    """解析卡池表格並提取排程紀錄與版本日期"""
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
                    # 動態擷取強化模式標記（如「(Enhanced)」或「(Enhancement: 新模式)」）；無標記時不新增欄位
                    row_buff_type = extract_buff_marker(tds[1].get_text(' ', strip=True)) or extract_buff_marker(type_text)
                    for a in tds[1].find_all('a'):
                        title = a.get('title')
                        if title and '/' in title and not title.startswith('File:'):
                            record = {
                                'warp_page': title,
                                'version': current_ver,
                                'start_dt': current_start_dt,
                                'is_collab': is_collab
                            }
                            if row_buff_type:
                                record['buff_type'] = row_buff_type
                            warp_records.append(record)

    return warp_records, version_dates


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

    warp_records, version_dates = parse_warp_list_tables(tables, parse_header_date)

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
    page_to_buff = {}

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

            # 💠 卡池頁面 Wikitext 若帶有強化模式標記，動態保留
            page_buff = extract_buff_marker(content)
            if page_buff:
                page_to_buff[title] = page_buff

    schedules = []
    schedule_index = {}

    for r in warp_records:
        wp = r['warp_page']
        char_list = page_to_chars.get(wp, [])
        run_name = ver_phases.get((r['version'], r['start_dt']))

        if not run_name:
            continue

        buff_type = r.get('buff_type') or page_to_buff.get(wp)

        for char_name in char_list:
            key = (char_name, run_name)
            if key not in schedule_index:
                sched = {
                    'en_name': char_name,
                    'run': run_name,
                    'is_collab': r['is_collab'],
                    'patch_date': r['start_dt'].strftime('%y/%m/%d')
                }
                if buff_type:
                    sched['buff_type'] = buff_type
                schedule_index[key] = sched
                schedules.append(sched)
            elif buff_type and not schedule_index[key].get('buff_type'):
                schedule_index[key]['buff_type'] = buff_type

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


def _parse_upcoming_characters(session, next_p, existing_schedules):
    """
    2. 探測官方前瞻角色 (Category:Upcoming Characters)
    回傳: (upcoming_schedules_增量)
    """
    schedules = []
    try:
        up_res = session.get(WIKI_API_URL, params={
            'action': 'query',
            'list': 'categorymembers',
            'cmtitle': 'Category:Upcoming Characters',
            'cmlimit': 20,
            'format': 'json'
        }, timeout=REQUEST_TIMEOUT).json()
        up_titles = [m['title'] for m in up_res.get('query', {}).get('categorymembers', [])]

        existing_names = {s.get('en_name') for s in existing_schedules}
        for title in up_titles:
            if title in existing_names:
                continue
            schedules.append({
                'en_name': title,
                'run': next_p,
                'is_collab': False,
                'is_preview': True
            })
    except Exception as e:
        print(f"  ⚠️ 探測前瞻角色時發生微小異常: {e}")
    return schedules

def _parse_collaboration_events(session, max_ver):
    """
    1. 探測未來聯動活動 (Category:Collaboration Events)
    回傳: (upcoming_schedules_增量, 更新後的 max_ver)
    """
    schedules = []
    try:
        collab_res = session.get(WIKI_API_URL, params={
            'action': 'query',
            'list': 'categorymembers',
            'cmtitle': 'Category:Collaboration Events',
            'cmlimit': 30,
            'format': 'json'
        }, timeout=REQUEST_TIMEOUT).json()
        collab_titles = [m['title'] for m in collab_res.get('query', {}).get('categorymembers', [])]

        for i in range(0, len(collab_titles), 50):
            batch = collab_titles[i:i + 50]
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
                wt = pinfo.get('revisions', [{}])[0].get('slots', {}).get('main', {}).get('*', '')
                if not wt:
                    continue
                if 'Upcoming' in wt or 'begin in' in wt.lower():
                    m_ver = RE_UPCOMING_VERSION_1.search(wt)
                    if not m_ver:
                        m_ver = RE_UPCOMING_VERSION_2.search(wt)

                    if m_ver:
                        ver_val = float(m_ver.group(1))
                        if ver_val > max_ver:
                            max_ver = ver_val

                        # 提取登場聯動角色
                        chars = RE_UPCOMING_CHARS.findall(wt)
                        for c_tuple in chars:
                            for char_en in c_tuple:
                                if char_en and char_en.strip():
                                    schedules.append({
                                        'en_name': char_en.strip(),
                                        'run': f"{m_ver.group(1)}上",
                                        'is_collab': False,
                                        'is_preview': True
                                    })
    except Exception as e:
        print(f"  ⚠️ 探測聯動情報時發生微小異常: {e}")
    return schedules, max_ver

def fetch_fandom_upcoming_characters_and_patches(session, base_patch, base_date):
    """
    🔮 全自動探測 Fandom Wiki 官方前瞻預告與未來合作角色。
    零字典設計：所有名稱、命途、屬性皆直接由 Wiki 原生 Wikitext 動態提取。
    """
    print("\n🔮 正在自動探測 Fandom Wiki 官方前瞻預告與未來角色...")
    upcoming_schedules = []

    def get_next_patch_and_date(current_patch, current_date_str):
        m = re.match(r'^(\d+)\.(\d+)([上下中])$', current_patch)
        if not m:
            return None, None
        major, minor, phase = int(m.group(1)), int(m.group(2)), m.group(3)
        if phase in ('上', '中'):
            next_p = f"{major}.{minor}下"
        else:
            next_p = f"{major}.{minor + 1}上"

        try:
            dt = datetime.strptime(current_date_str, '%y/%m/%d')
            next_dt = dt + timedelta(days=21)
            next_d_str = next_dt.strftime('%y/%m/%d')
        except Exception:
            next_d_str = current_date_str
        return next_p, next_d_str

    max_ver = float(re.sub(r'[上下中]$', '', base_patch)) if re.match(r'^\d+\.\d+', base_patch) else 4.6

    collab_schedules, max_ver = _parse_collaboration_events(session, max_ver)
    upcoming_schedules.extend(collab_schedules)

    # 2. 探測官方前瞻角色 (Category:Upcoming Characters)
    next_p, next_d = get_next_patch_and_date(base_patch, base_date)
    new_upcoming = _parse_upcoming_characters(session, next_p, upcoming_schedules)
    upcoming_schedules.extend(new_upcoming)

    # 3. 依最大版本號自動推算補齊所有預覽版本節點
    gen_patches = []
    curr_p, curr_d = base_patch, base_date
    while True:
        curr_p, curr_d = get_next_patch_and_date(curr_p, curr_d)
        if not curr_p:
            break
        gen_patches.append({'patch': curr_p, 'date': curr_d, 'isPreview': True})
        m_p = re.match(r'^(\d+\.\d+)下$', curr_p)
        if m_p and float(m_p.group(1)) >= max_ver:
            break
        if len(gen_patches) >= 8:
            break

    print(f"  ✅ 前瞻探測完成：發現 {len(upcoming_schedules)} 筆前瞻預告排程，自動擴充 {len(gen_patches)} 個預估版本節點")
    return upcoming_schedules, gen_patches


def resolve_local_character_info(en_name, en_data, cht_data, sanitized_en_dict=None):
    sanitized = sanitize_name(en_name)
    target_cid = None
    target_name = en_name
    path = "未知"
    elem = "未知"

    # 1. 優先比對 StarRailRes 官方解包資料庫
    if sanitized_en_dict is None:
        sanitized_en_dict = {sanitize_name(info.get("name", "")): cid for cid, info in en_data.items()}

    sanitized_target = sanitize_name(target_name) if target_name else ""
    matched_cid = sanitized_en_dict.get(sanitized) or (sanitized_en_dict.get(sanitized_target) if sanitized_target else None)

    if matched_cid:
        target_cid = matched_cid
        cht_info = cht_data.get(matched_cid, {})
        if isinstance(cht_info, dict):
            target_name = cht_info.get("name", en_name)
            db_path = cht_info.get("path")
            path = normalize_path_name(db_path)

            db_elem = cht_info.get("element")
            raw_elem = db_elem.get("name") if isinstance(db_elem, dict) else db_elem
            elem = ELEM_MAP.get(raw_elem, raw_elem or "未知")

    return target_cid, target_name, path, elem

def enrich_character_info(en_name, en_data, cht_data, wiki_char_cache, session, sanitized_en_dict=None):
    target_cid, target_name, path, elem = resolve_local_character_info(en_name, en_data, cht_data, sanitized_en_dict)

    # 2. 備援向 Fandom Wiki 動態抽取繁中名稱與屬性（零字典，純動態解析）
    if target_name == en_name or not contains_cjk(target_name) or path == "未知" or elem == "未知":
        if en_name in wiki_char_cache:
            w_info = wiki_char_cache[en_name]
        else:
            w_info = query_wiki_character_page(en_name, session)
            wiki_char_cache[en_name] = w_info

        if w_info.get("cht_name") and (target_name == en_name or not contains_cjk(target_name)):
            target_name = w_info["cht_name"]
            print(f"  ✨ Fandom Wiki 成功動態解析繁中名稱: {en_name} ➡️ {target_name}")

        if path == "未知" and w_info.get("path"):
            path = normalize_path_name(w_info["path"])

        if elem == "未知" and w_info.get("elem"):
            elem = ELEM_MAP.get(w_info["elem"], w_info["elem"])

    return target_cid, target_name, path, elem


def query_wiki_character_pages_batch(char_names, session):
    """Batch queries Wiki pages for characters and maps the results back to the original queried names."""
    results = {}
    if not char_names:
        return results

    for name in char_names:
        results[name] = {"cht_name": None, "path": None, "elem": None}

    char_names = list(set(char_names))
    for i in range(0, len(char_names), 50):
        batch = char_names[i:i + 50]
        try:
            res = session.get(WIKI_API_URL, params={
                'action': 'query',
                'titles': '|'.join(batch),
                'prop': 'revisions',
                'rvslots': 'main',
                'rvprop': 'content',
                'redirects': '1',
                'format': 'json'
            }, timeout=REQUEST_TIMEOUT).json()

            query_data = res.get('query', {})

            # Create a mapping from final title to original query name
            title_to_original = {name: name for name in batch}

            # Map normalized titles
            for norm in query_data.get('normalized', []):
                if norm['from'] in title_to_original:
                    original = title_to_original.pop(norm['from'])
                    title_to_original[norm['to']] = original

            # Map redirects
            for redir in query_data.get('redirects', []):
                if redir['from'] in title_to_original:
                    original = title_to_original.pop(redir['from'])
                    title_to_original[redir['to']] = original

            pages = query_data.get('pages', {})
            for pid, p in pages.items():
                if pid == "-1":
                    continue

                title = p.get('title', '')
                original_name = title_to_original.get(title, title)

                content = p.get('revisions', [{}])[0].get('slots', {}).get('main', {}).get('*', '')

                info = {"cht_name": None, "path": None, "elem": None}

                matches = re.findall(r'\|((\d+_)?(zht|zh[-_]?(?:tw|hk)))\s*=\s*([^\n\|\}]+)', content, re.IGNORECASE)
                if not matches:
                    matches = re.findall(r'\|((\d+_)?(zhs|zh))\s*=\s*([^\n\|\}]+)', content, re.IGNORECASE)

                name_dict = {}
                for full_k, prefix, lang, val in matches:
                    cleaned_val = clean_wikitext_value(val)
                    if cleaned_val:
                        name_dict[full_k.lower()] = cleaned_val

                n1 = name_dict.get('1_zht') or name_dict.get('1_zhs')
                n2 = name_dict.get('2_zht') or name_dict.get('2_zhs')
                nz = name_dict.get('zht') or name_dict.get('zhs')

                chosen = None
                if n1 and n2:
                    chosen = n2 if n1 in n2 else n1
                elif nz:
                    chosen = nz
                elif n1:
                    chosen = n1
                elif name_dict:
                    chosen = list(name_dict.values())[0]

                if chosen:
                    info["cht_name"] = chosen

                m_path = re.search(r'\|path\s*=\s*((?:\[\[[^\]]*\]\]|[^\n\|\}])+)', content)
                if m_path:
                    info["path"] = clean_wikitext_value(m_path.group(1))

                m_elem = re.search(r'\|(?:combatType|element)\s*=\s*((?:\[\[[^\]]*\]\]|[^\n\|\}])+)', content)
                if m_elem:
                    info["elem"] = clean_wikitext_value(m_elem.group(1))

                results[original_name] = info

        except Exception as e:
            print(f"  ⚠️ 批次查詢 Wiki 角色頁面失敗: {e}")

    return results

def query_wiki_character_page(char_name, session):
    """單筆查詢 Wiki 角色頁面，內部直接複用批次查詢邏輯"""
    if not char_name:
        return {"cht_name": None, "path": None, "elem": None}
    return query_wiki_character_pages_batch([char_name], session).get(
        char_name, {"cht_name": None, "path": None, "elem": None}
    )


# ──────────────────────────────────────────────────
# 🛡️ 五道安全防護檢驗門檻（Pre-commit Validation Gates）
# ──────────────────────────────────────────────────
def validate_data_integrity(original_chars, original_patches, new_chars, new_patches):
    """
    五道強制安全防護檢驗門檻。
    若有任何一項檢驗不通過，拋出 AssertionError 並立即中斷，絕不寫入專案！
    （註：不可減少／不可逆原則僅限定於非 isPreview 之正式資料，允許預覽資料動態調整）
    五道門檻通過後會再執行「審計 6」：動態命途／強化模式檢查，僅記錄警示、絕不因新命途或新強化模式熔斷，
    並回傳 audit_dynamic_tags() 的報告 dict。
    """
    print("\n🛡️ 正在執行五道安全防護檢驗門檻 (Pre-commit Validation)...")

    # 門檻 1：正式角色數量不減少原則（限定 !isPreview）
    orig_official_chars = [c for c in original_chars if not c.get('isPreview')]
    new_official_chars = [c for c in new_chars if not c.get('isPreview')]
    if len(new_official_chars) < len(orig_official_chars):
        raise AssertionError(
            f"❌ 門檻 1 失敗：角色總數異常減少！(原 {len(orig_official_chars)} 位 ➡️ 現 {len(new_official_chars)} 位)"
        )
    print(f"  ✅ 門檻 1 通過：正式角色總數維持或增加 ({len(orig_official_chars)} ➡️ {len(new_official_chars)})")

    # 門檻 2：正式版本數量不減少原則（限定 !isPreview）
    orig_official_patches = [p for p in original_patches if not p.get('isPreview')]
    new_official_patches = [p for p in new_patches if not p.get('isPreview')]
    if len(new_official_patches) < len(orig_official_patches):
        raise AssertionError(
            f"❌ 門檻 2 失敗：版本總數異常減少！(原 {len(orig_official_patches)} 個 ➡️ 現 {len(new_official_patches)} 個)"
        )
    print(f"  ✅ 門檻 2 通過：正式版本數量維持或增加 ({len(orig_official_patches)} ➡️ {len(new_official_patches)})")

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
        for r in (c.get('runs') or []):
            if r not in patch_names_set:
                raise AssertionError(
                    f"❌ 門檻 4 失敗：角色 [{c.get('name')}] 的排程版本 [{r}] 不存在於版本清單中！"
                )
    print("  ✅ 門檻 4 通過：所有角色的登場排程皆有對應之版本節點")

    # 門檻 5：既有正式角色的歷史排程不可逆原則（限定 !isPreview）
    preview_patch_names = {
        p.get('patch') for p in original_patches if p.get('isPreview')
    } | {
        p.get('patch') for p in new_patches if p.get('isPreview')
    }
    original_char_map = {
        c.get('name'): set(r for r in (c.get('runs') or []) if r not in preview_patch_names)
        for c in original_chars
        if c.get('name') and not c.get('isPreview')
    }
    for c in new_chars:
        name = c.get('name')
        if name in original_char_map:
            orig_runs = original_char_map[name]
            new_runs = set(c.get('runs') or [])
            if not orig_runs.issubset(new_runs):
                missing = orig_runs - new_runs
                raise AssertionError(
                    f"❌ 門檻 5 失敗：角色 [{name}] 的歷史排程遺失：{missing}！"
                )
    print("  ✅ 門檻 5 通過：所有既有角色的歷史排程完全被繼承，未發生歷史資料縮水")
    print("🎉 五道安全檢驗全數通過！資料結構完整且安全無虞。\n")

    # 審計 6（僅警示、絕不熔斷）：動態命途與強化模式自適應檢查
    return audit_dynamic_tags(original_chars, new_chars, patch_names_set)


def audit_dynamic_tags(original_chars, new_chars, patch_names_set=None):
    """
    🧭💠 動態命途 / 強化模式審計：遇到未預設的新命途、新強化模式只會「記錄並保留」，不會拋出例外。
    回傳報告 dict：
      dynamic_paths          目前資料中非核心（js/paths.js 未註冊）的命途
      introduced_paths       本次新出現的命途
      buff_types             目前資料中所有強化模式
      introduced_buff_types  本次新出現的強化模式
      warnings               非致命資料提示（如強化版本不在版本清單中）
    """
    warnings = []
    orig_paths = set(collect_paths(original_chars))
    new_paths = collect_paths(new_chars)
    dynamic_paths = [p for p in new_paths if p not in CORE_PATHS and p != UNKNOWN_LABEL]
    introduced_paths = [p for p in new_paths if p not in orig_paths and p != UNKNOWN_LABEL]

    orig_buff_types = set(collect_buff_types(original_chars))
    buff_types = collect_buff_types(new_chars)
    introduced_buff_types = [t for t in buff_types if t not in orig_buff_types]

    for c in new_chars or []:
        name = c.get('name')
        raw_path = c.get('path')
        if raw_path is not None and not isinstance(raw_path, str):
            warnings.append(f"角色 [{name}] 的命途欄位型別非字串：{raw_path!r}")
        buffs = c.get('buffs') or []
        buff_patches = [b.get('patch') if isinstance(b, dict) else b for b in buffs]
        if patch_names_set is not None:
            for bp in buff_patches:
                if bp and bp not in patch_names_set:
                    warnings.append(f"角色 [{name}] 的強化版本 [{bp}] 不存在於版本清單中")
        bt = c.get('buffTypes')
        if isinstance(bt, dict):
            for bp in bt:
                if bp not in buff_patches:
                    warnings.append(f"角色 [{name}] 的強化模式標記 [{bp}] 沒有對應的 buffs 版本")

    if dynamic_paths:
        print(f"  🧭 審計 6：偵測到非核心命途 {dynamic_paths}，已自動保留並交由前端通用樣式呈現")
    if introduced_buff_types:
        print(f"  💠 審計 6：偵測到新強化模式 {introduced_buff_types}，已自動保留並整合")
    for w in warnings:
        print(f"  ⚠️ 審計 6（非致命）：{w}")
    if not dynamic_paths and not introduced_buff_types and not warnings:
        print("  ✅ 審計 6 通過：命途與強化模式皆屬已註冊範圍")

    return {
        'dynamic_paths': dynamic_paths,
        'introduced_paths': introduced_paths,
        'buff_types': buff_types,
        'introduced_buff_types': introduced_buff_types,
        'warnings': warnings,
    }


# ──────────────────────────────────────────────────
# 輔助函式
# ──────────────────────────────────────────────────
def _format_summary_text(new_patches_added, patch_dates_updated_log, new_chars_added, runs_added_log, name_upgraded_log, dynamic_tags_log=None):
    """產生摘要文字"""
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
    if dynamic_tags_log:
        summary_lines.append(f"🧭 動態命途／強化模式 ({len(dynamic_tags_log)} 項):\n  • " + "\n  • ".join(dynamic_tags_log))
    return "\n".join(summary_lines)


def _build_dynamic_tags_log(report):
    """將 audit_dynamic_tags 報告轉為摘要條目（容忍非 dict 輸入，例如測試中的 Mock）"""
    if not isinstance(report, dict):
        return []
    lines = []
    for p in report.get('introduced_paths') or []:
        lines.append(f"新命途：{p}")
    for t in report.get('introduced_buff_types') or []:
        lines.append(f"新強化模式：{t}")
    return lines


def _generate_summary_and_save(
    original_chars, original_patches, merged_chars, merged_patches,
    new_patches_added, patch_dates_updated_log, new_chars_added,
    runs_added_log, name_upgraded_log, patches_file, chars_file,
    dynamic_tags_log=None
):
    """比對變更、寫入檔案並產生摘要"""
    has_patches_changed = json.dumps(original_patches) != json.dumps(merged_patches)
    has_chars_changed = json.dumps(original_chars) != json.dumps(merged_chars)

    if not has_patches_changed and not has_chars_changed:
        print("✨ 專案資料庫目前已經是最新狀態，無需寫入更新。")
        return True

    # 寫入本地專案檔案
    serialize_js_file('PATCH_DATA', merged_patches, patches_file)
    serialize_js_file('RAW_CHARACTERS', merged_chars, chars_file)

    # 產生日誌摘要檔案（供 CI Commit Message 使用）
    summary_text = _format_summary_text(
        new_patches_added, patch_dates_updated_log, new_chars_added,
        runs_added_log, name_upgraded_log, dynamic_tags_log
    )
    with open(".update_summary.md", "w", encoding="utf-8") as f:
        f.write(summary_text)

    print("\n📝 變更摘要清單：")
    print(summary_text)

    return True


def _merge_characters(original_chars, all_incoming_schedules, session):
    """合併角色清單與排程"""
    en_data, cht_data = fetch_starrailres_data(session)
    wiki_char_cache = {}

    # 深拷貝以避免污染
    merged_chars = json.loads(json.dumps(original_chars))
    originally_preview_char_ids = {id(c) for c in merged_chars if c.get('isPreview')}
    reset_preview_char_ids = set()

    existing_char_map_by_cid = {c['cid']: c for c in merged_chars if c.get('cid')}
    existing_char_map_by_name = {c['name']: c for c in merged_chars if c.get('name')}

    new_chars_added = []
    runs_added_log = []
    name_upgraded_log = []

    sanitized_en_dict = {sanitize_name(info.get("name", "")): cid for cid, info in en_data.items()}

    # Precompute maps for faster lookup
    sanitized_char_map = {sanitize_name(c.get('name', '')): c for c in merged_chars if c.get('name')}
    normalized_cjk_char_map = {normalize_cjk_name(c.get('name', '')): c for c in merged_chars if c.get('name') and contains_cjk(c.get('name', ''))}

    # First pass: pre-calculate the list of characters to batch query from Wiki
    needed_wiki_chars = []
    for sched in all_incoming_schedules:
        en_name = sched['en_name']

        # We only need to check what the local info will be
        _, target_name, path, elem = resolve_local_character_info(en_name, en_data, cht_data, sanitized_en_dict)

        # If any of the conditions for Wiki fallback are met, we add it to the batch
        if target_name == en_name or not contains_cjk(target_name) or path == "未知" or elem == "未知":
            needed_wiki_chars.append(en_name)

    # Batch query Fandom Wiki and populate the cache
    if needed_wiki_chars:
        wiki_results = query_wiki_character_pages_batch(needed_wiki_chars, session)
        wiki_char_cache.update(wiki_results)

    for sched in all_incoming_schedules:
        en_name = sched['en_name']
        run = sched['run']
        is_collab = sched.get('is_collab', False)
        is_preview = sched.get('is_preview', False)
        buff_type = normalize_buff_type(sched.get('buff_type')) if sched.get('buff_type') else None

        target_cid, target_name, path, elem = enrich_character_info(
            en_name, en_data, cht_data, wiki_char_cache, session, sanitized_en_dict
        )

        matched_char = None
        if target_name in existing_char_map_by_name:
            matched_char = existing_char_map_by_name[target_name]
        else:
            sanitized_en_name = sanitize_name(en_name)
            target_is_cjk = contains_cjk(target_name)
            normalized_target_name = normalize_cjk_name(target_name) if target_is_cjk else None

            if sanitized_en_name in sanitized_char_map:
                matched_char = sanitized_char_map[sanitized_en_name]
            elif target_is_cjk and normalized_target_name in normalized_cjk_char_map:
                matched_char = normalized_cjk_char_map[normalized_target_name]

        if not matched_char and target_cid and target_cid in existing_char_map_by_cid:
            matched_char = existing_char_map_by_cid[target_cid]

        if matched_char:
            was_originally_preview = id(matched_char) in originally_preview_char_ids

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

            # 預覽狀態同步：若官方正式實裝上線，移除預覽標記
            if not is_preview and matched_char.get('isPreview'):
                matched_char.pop('isPreview', None)
                print(f"  🎉 角色 [{matched_char.get('name')}] 已正式實裝，移除 isPreview 預覽標記！")

            # 補充或動態覆蓋預覽排程
            if not is_collab and not matched_char.get('isCollab'):
                if 'runs' not in matched_char or not isinstance(matched_char['runs'], list):
                    matched_char['runs'] = []
                if was_originally_preview and id(matched_char) not in reset_preview_char_ids:
                    old_runs = list(matched_char['runs'])
                    matched_char['runs'] = [run]
                    reset_preview_char_ids.add(id(matched_char))
                    if old_runs != [run]:
                        runs_added_log.append(f"{matched_char['name']} ➡️ {run}")
                elif run not in matched_char['runs']:
                    matched_char['runs'].append(run)
                    runs_added_log.append(f"{matched_char['name']} ➡️ {run}")

            # 💠 整合強化模式標記（保留既有 buffs / buffTypes）
            if buff_type and apply_buff_marker(matched_char, run, buff_type):
                runs_added_log.append(f"{matched_char['name']} 💠 {run}【{buff_type}】")
        else:
            new_char = {
                "cid": target_cid or "",
                "name": target_name,
                "path": path,
                "elem": elem,
                "avatar": "",
                "runs": [] if is_collab else [run]
            }
            if is_collab:
                new_char["isCollab"] = run
            if is_preview:
                new_char["isPreview"] = True
            if buff_type:
                apply_buff_marker(new_char, run, buff_type)

            merged_chars.append(new_char)
            if target_cid:
                existing_char_map_by_cid[target_cid] = new_char
            existing_char_map_by_name[target_name] = new_char
            new_chars_added.append(f"{target_name} ({path}/{elem}) ➡️ {run}" + (f"【{buff_type}】" if buff_type else ""))

    return merged_chars, new_chars_added, runs_added_log, name_upgraded_log


def _merge_patches(original_patches, all_incoming_patches):
    """合併版本清單並自動校正日期"""
    today_tw_str = datetime.now(TZ_TW).strftime('%y/%m/%d')

    current_patch_idx = 0
    for idx, p in enumerate(original_patches):
        norm_date = normalize_patch_date(p.get('date'))
        if norm_date and norm_date <= today_tw_str:
            current_patch_idx = idx

    updatable_patch_names = (
        set(p['patch'] for p in original_patches[current_patch_idx:])
        | set(p['patch'] for p in original_patches if p.get('isPreview'))
    )
    current_patch_name = original_patches[current_patch_idx]['patch'] if original_patches else "無"
    print(f"🕒 當前進行中版本：{current_patch_name}，納入日期自動追蹤校正之版本：{sorted(list(updatable_patch_names))}")

    patches_by_name = {}
    for p in original_patches:
        patches_by_name[p['patch']] = dict(p)

    new_patches_added = []
    patch_dates_updated_log = []

    for p in all_incoming_patches:
        name = p['patch']
        if name not in patches_by_name:
            patches_by_name[name] = dict(p)
            new_patches_added.append(name)
        else:
            if not p.get('isPreview') and patches_by_name[name].get('isPreview'):
                patches_by_name[name].pop('isPreview', None)
                print(f"  🎉 版本 [{name}] 已正式發布排程，移除 isPreview 預覽標記！")

            if name in updatable_patch_names:
                old_date = patches_by_name[name].get('date', '')
                new_date = p.get('date', '')
                norm_old = normalize_patch_date(old_date)
                norm_new = normalize_patch_date(new_date)
                if norm_new and norm_new != norm_old:
                    patches_by_name[name]['date'] = norm_new
                    patch_dates_updated_log.append(f"{name}: {old_date} ➡️ {norm_new}")
                    print(f"  📅 自動校正版本日期: [{name}] {old_date} ➡️ {norm_new}")

    merged_patches = sorted(patches_by_name.values(), key=lambda p: (normalize_patch_date(p['date']) or "", p['patch']))
    return merged_patches, new_patches_added, patch_dates_updated_log


# ──────────────────────────────────────────────────
# 深度合併與自動化執行主流程
# ──────────────────────────────────────────────────
def execute_auto_update():
    print("\n" + "=" * 60)
    print("🚀 啟動 HSR Banner 全自動資料更新流程 (直寫 + 安全防護)")
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

    # 2.1 自動探測 Fandom Wiki 前瞻與未來角色 (零字典，原生動態解析)
    base_patch = wiki_patches[-1]['patch'] if wiki_patches else (original_patches[-1]['patch'] if original_patches else '4.6下')
    base_date = wiki_patches[-1]['date'] if wiki_patches else (original_patches[-1]['date'] if original_patches else '26/10/21')

    upcoming_schedules, upcoming_patches = fetch_fandom_upcoming_characters_and_patches(session, base_patch, base_date)

    # 合併版本清單（優先保留正式版本資訊）
    all_incoming_patches = list(wiki_patches)
    known_patch_names = set(p['patch'] for p in all_incoming_patches)
    for p in upcoming_patches:
        if p['patch'] not in known_patch_names:
            all_incoming_patches.append(p)
            known_patch_names.add(p['patch'])

    # 合併角色排程
    all_incoming_schedules = list(schedules)
    for s in upcoming_schedules:
        if not any(x['en_name'] == s['en_name'] and x['run'] == s['run'] for x in all_incoming_schedules):
            all_incoming_schedules.append(s)

    # 3. 合併版本清單（選項 B：僅更新當前版本及未來版本，保護過去歷史版本）
    merged_patches, new_patches_added, patch_dates_updated_log = _merge_patches(
        original_patches, all_incoming_patches
    )

    # 4. 合併角色清單
    merged_chars, new_chars_added, runs_added_log, name_upgraded_log = _merge_characters(
        original_chars, all_incoming_schedules, session
    )

    # 5. 執行五道安全防護檢驗門檻（+ 審計 6：動態命途／強化模式，僅警示不熔斷）
    audit_report = validate_data_integrity(original_chars, original_patches, merged_chars, merged_patches)

    # 6. 比對是否有實質變更、寫入本地專案檔案並產生摘要檔案
    return _generate_summary_and_save(
        original_chars, original_patches, merged_chars, merged_patches,
        new_patches_added, patch_dates_updated_log, new_chars_added,
        runs_added_log, name_upgraded_log, patches_file, chars_file,
        dynamic_tags_log=_build_dynamic_tags_log(audit_report)
    )


# ──────────────────────────────────────────────────
# 程式進入點
# ──────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        success = execute_auto_update()
        if not success:
            raise SystemExit(2)
    except Exception:
        import traceback
        tb = traceback.format_exc()
        print("\n⚠️ 全自動更新流程發生未預期錯誤:", file=sys.stderr)
        print(tb, file=sys.stderr)
        raise SystemExit(1)
