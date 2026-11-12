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
    "novaflare": DEFAULT_BUFF_TYPE,
    "礪爍新輝": DEFAULT_BUFF_TYPE,
    "砺烁新辉": DEFAULT_BUFF_TYPE,
    "affinitive eidolon": "奇緣星魂",
    "affinitive eidolons": "奇緣星魂",
    "奇緣星魂": "奇緣星魂",
    "奇缘星魂": "奇緣星魂",
}
RE_BUFF_PARAM = re.compile(r'\|\s*(?:enhanced|enhancement|buff_type|buff_mode)\s*=\s*([^|\n}]*)', re.IGNORECASE)
RE_BUFF_TEMPLATE = re.compile(r'\{\{\s*(?:Enhanced|Enhancement|Buff Mode)\s*(?:\|\s*([^}|]*))?\}\}', re.IGNORECASE)
RE_BUFF_INLINE = re.compile(r'\(\s*(?:Enhanced|Enhancement)\s*(?:[:：]\s*([^)]*))?\)', re.IGNORECASE)

# ──────────────────────────────────────────────────
# 角色取得方式（Acquisition Method）動態標記
#   資料結構：向下相容單一 term: { type, patch } 物件；
#   若同一角色後續再新增其他永久取得途徑，則保留所有階段於 terms: [{ type, patch }, ...]，
#   並讓 term 指向最新取得階段。
# ──────────────────────────────────────────────────
DEFAULT_ACQUISITION_TYPE = "normal"
CORE_ACQUISITION_TYPES = ("normal", "pool", "shop", "collab", "stellar")
ACQUISITION_TYPE_MAP = {
    "normal": "normal",
    "limited": "normal",
    "character event warp": "normal",
    "限定躍遷": "normal",
    "限定": "normal",
    "pool": "pool",
    "celestial invitation": "pool",
    "non-featured": "pool",
    "星緣相邀": "pool",
    "星缘相邀": "pool",
    "shop": "shop",
    "stellar convergence": "shop",
    "exchange shop": "shop",
    "store": "shop",
    "聚靈鑄星": "shop",
    "聚灵铸星": "shop",
    "collab": "collab",
    "collaboration": "collab",
    "character collaboration warp": "collab",
    "長期聯動": "collab",
    "长期联动": "collab",
    "聯動": "collab",
    "連動": "collab",
    "stellar": "stellar",
    "stellar warp": "stellar",
    "regular warp": "stellar",
    "permanent": "stellar",
    "群星躍遷": "stellar",
    "群星跃迁": "stellar",
}

# 常駐 5 星與主角群（絕不誤加入限定角色追蹤清單，也不在取得方式補齊流程誤建）
STANDARD_FIVE_STAR_CIDS = frozenset({
    "1003", "1004", "1101", "1104", "1107", "1209", "1211",
    "8001", "8002", "8003", "8004", "8005", "8006", "8007", "8008",
})
STANDARD_FIVE_STAR_NAMES = frozenset({
    "himeko", "welt", "bronya", "gepard", "clara", "yanqing", "bailu", "trailblazer",
    "姬子", "瓦爾特", "布洛妮婭", "傑帕德", "克拉拉", "彥卿", "白露", "開拓者",
})
_WARP_POOL_SESSION_CACHE = {}


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


def is_standard_five_star(name="", cid=""):
    """判定是否為常駐 5 星或主角群（避免誤將常駐角色視為限定特殊取得）"""
    if cid and str(cid).strip() in STANDARD_FIVE_STAR_CIDS:
        return True
    if not name:
        return False
    raw = str(name).strip()
    if raw in STANDARD_FIVE_STAR_NAMES or raw.lower() in STANDARD_FIVE_STAR_NAMES:
        return True
    if sanitize_name(raw) in STANDARD_FIVE_STAR_NAMES:
        return True
    return False


def normalize_acquisition_type(raw):
    """將取得方式名稱正規化；known key ➡️ pool/shop/collab/stellar，未知未來系統 ➡️ 保留原名"""
    if raw is None:
        return None
    val = re.sub(r'\{\{\s*(?:Main|Transclude)\s*\|\s*([^|}]+)[^}]*\}\}', r'\1', str(raw), flags=re.IGNORECASE)
    val = clean_wikitext_value(val)
    val = re.sub(r'<[^>]+>', '', val).strip()
    if not val:
        return None
    low = val.lower()
    if low in ('no', 'false', '0', 'none', 'n'):
        return None
    return ACQUISITION_TYPE_MAP.get(low) or ACQUISITION_TYPE_MAP.get(val) or val


def _extract_valid_char_terms(char):
    """擷取角色既有非聯動 term/terms 紀錄清單（依出現順序去重）"""
    if not isinstance(char, dict) or char.get('isCollab'):
        return []
    entries = []
    seen = set()

    def _push(raw_entry):
        if not isinstance(raw_entry, dict):
            return
        t = normalize_acquisition_type(raw_entry.get('type'))
        p = str(raw_entry.get('patch') or '').strip()
        if not t or t in (DEFAULT_ACQUISITION_TYPE, 'collab'):
            return
        key = (t, p)
        if key not in seen:
            seen.add(key)
            entries.append({'type': t, 'patch': p})

    _push(char.get('term'))
    raw_terms = char.get('terms')
    if isinstance(raw_terms, list):
        for item in raw_terms:
            _push(item)
    return entries


def get_char_acquisition_types(char):
    """取得角色所有出現過的取得方式鍵值清單（collab／pool／shop／stellar／未知系統／normal）"""
    if not isinstance(char, dict):
        return []
    if char.get('isCollab'):
        return ['collab']
    terms = _extract_valid_char_terms(char)
    if not terms:
        return [DEFAULT_ACQUISITION_TYPE]
    seen = []
    for entry in terms:
        t = entry.get('type')
        if t and t not in seen:
            seen.append(t)
    return seen or [DEFAULT_ACQUISITION_TYPE]


def collect_acquisition_types(chars):
    """依出現順序收集所有角色的取得方式型別（含動態未來系統）"""
    seen = []
    for c in chars or []:
        for t in get_char_acquisition_types(c):
            if t not in seen:
                seen.append(t)
    return seen


def _patch_sort_rank(patch_name, patch_order_map=None):
    """計算版本階段排序鍵（優先採用 patches 清單索引，否則依數字與上/中/下解析）"""
    if patch_order_map and patch_name in patch_order_map:
        return (0, patch_order_map[patch_name], 0, 0)
    m = re.match(r'^(\d+)\.(\d+)([上中下])$', str(patch_name or '').strip())
    if not m:
        return (1, 9999, 9999, 9)
    phase_rank = {'上': 0, '中': 1, '下': 2}.get(m.group(3), 9)
    return (1, int(m.group(1)), int(m.group(2)), phase_rank)


def apply_acquisition_marker(char, acq_type, patch, patch_order_map=None):
    """
    將取得方式標記整合至角色資料（保留既有手動/歷史版本不覆蓋，並於累積多階段時維護 terms 陣列）。
    回傳 True 表示資料有實際變更。
    """
    norm_type = normalize_acquisition_type(acq_type)
    patch_str = str(patch or '').strip()
    if not isinstance(char, dict) or char.get('isCollab'):
        return False
    if not norm_type or norm_type in (DEFAULT_ACQUISITION_TYPE, 'collab') or not patch_str:
        return False

    existing = _extract_valid_char_terms(char)
    if any(e.get('type') == norm_type for e in existing):
        return False

    combined = existing + [{'type': norm_type, 'patch': patch_str}]
    combined.sort(key=lambda e: _patch_sort_rank(e.get('patch'), patch_order_map))

    old_term = char.get('term')
    old_terms = char.get('terms')
    new_term = dict(combined[-1])
    char['term'] = new_term
    if len(combined) > 1:
        char['terms'] = [dict(e) for e in combined]
    else:
        char.pop('terms', None)

    return char.get('term') != old_term or char.get('terms') != old_terms


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

    # 批次查詢卡池對應的 5 星角色（與非 UP 自選池 character_5、卡池 type）
    unique_pages = list(set(r['warp_page'] for r in warp_records))
    page_to_chars = {}
    page_to_nonfeatured = {}
    page_to_warp_type = {}
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
        if not isinstance(res, dict):
            continue

        pages = res.get('query', {}).get('pages', {})
        if not isinstance(pages, dict):
            continue
        for pid, pinfo in pages.items():
            title = pinfo.get('title', '')
            content = pinfo.get('revisions', [{}])[0].get('slots', {}).get('main', {}).get('*', '')

            m = re.search(r'character_5_F\s*=\s*([^|\n]+)', content)
            if not m:
                m = re.search(r'5\{\{star\}\}\s*Character===?\s*\n\*\s*\{\{Character Intro\|([^}]+)\}\}', content, re.IGNORECASE)

            char_list = []
            if m:
                raw_chars = m.group(1).strip()
                raw_chars = re.sub(r'<!--.*?-->', '', raw_chars).strip()
                char_list = [c.strip() for c in raw_chars.split(';') if c.strip()]
                page_to_chars[title] = char_list

            m_nf = re.search(r'\|\s*character_5\s*=\s*([^\r\n|\}]+)', content)
            if m_nf:
                raw_nf = re.sub(r'<!--.*?-->', '', m_nf.group(1)).strip()
                featured_set = set(char_list)
                nf_list = [
                    c.strip() for c in raw_nf.split(';')
                    if c.strip() and c.strip() not in featured_set and not is_standard_five_star(c.strip())
                ]
                if nf_list:
                    page_to_nonfeatured[title] = nf_list

            m_type = re.search(r'\|\s*type\s*=\s*([^\r\n|\}]+)', content, re.IGNORECASE)
            if m_type:
                raw_wt = re.sub(r'<!--.*?-->', '', clean_wikitext_value(m_type.group(1))).strip()
                if raw_wt:
                    page_to_warp_type[title] = raw_wt

            # 💠 卡池頁面 Wikitext 若帶有強化模式標記，動態保留
            page_buff = extract_buff_marker(content)
            if page_buff:
                page_to_buff[title] = page_buff

    schedules = []
    schedule_index = {}
    pool_snapshots = []
    pool_earliest = {}
    indefinite_warp_acqs = []

    sorted_warp_records = sorted(
        warp_records,
        key=lambda rec: (rec.get('start_dt') or datetime.max, rec.get('warp_page', ''))
    )
    for r in sorted_warp_records:
        wp = r['warp_page']
        run_name = ver_phases.get((r['version'], r['start_dt']))
        if not run_name:
            continue
        for nf_name in page_to_nonfeatured.get(wp, []):
            if nf_name not in pool_earliest:
                pool_earliest[nf_name] = run_name
                pool_snapshots.append({'en_name': nf_name, 'patch': run_name})

    for r in warp_records:
        wp = r['warp_page']
        char_list = page_to_chars.get(wp, [])
        run_name = ver_phases.get((r['version'], r['start_dt']))
        is_collab_row = bool(r.get('is_collab'))

        if not run_name and is_collab_row:
            raw_wt = page_to_warp_type.get(wp, '')
            wt_low = raw_wt.lower()
            resolved_run = resolve_patch_by_date(
                r['start_dt'].strftime('%y/%m/%d'),
                new_patches,
                version_hint=r['version'],
            )
            if wt_low and 'collaboration' not in wt_low and 'event warp' not in wt_low:
                if resolved_run:
                    for char_name in char_list:
                        indefinite_warp_acqs.append({
                            'en_name': char_name,
                            'patch': resolved_run,
                            'warp_type': raw_wt,
                        })
                continue
            run_name = resolved_run

        if not run_name:
            continue

        buff_type = r.get('buff_type') or page_to_buff.get(wp)

        for char_name in char_list:
            key = (char_name, run_name)
            if key not in schedule_index:
                sched = {
                    'en_name': char_name,
                    'run': run_name,
                    'is_collab': is_collab_row,
                    'patch_date': r['start_dt'].strftime('%y/%m/%d')
                }
                if is_collab_row and r.get('start_dt'):
                    sched['collab_date'] = r['start_dt'].strftime('%Y/%m/%d')
                if buff_type:
                    sched['buff_type'] = buff_type
                schedule_index[key] = sched
                schedules.append(sched)
            else:
                if buff_type and not schedule_index[key].get('buff_type'):
                    schedule_index[key]['buff_type'] = buff_type
                if is_collab_row and r.get('start_dt') and not schedule_index[key].get('collab_date'):
                    schedule_index[key]['collab_date'] = r['start_dt'].strftime('%Y/%m/%d')

    _WARP_POOL_SESSION_CACHE[id(session)] = {
        'pool_snapshots': pool_snapshots,
        'indefinite_warp_acqs': indefinite_warp_acqs,
    }
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
        if not isinstance(en_res, dict) or not isinstance(cht_res, dict):
            return {}, {}
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


def _query_wiki_list(session, list_name, extra_params):
    """共用的 Fandom MediaWiki API list 查詢輔助函式（對 Mock 與網路異常安全降級）"""
    try:
        params = {'action': 'query', 'list': list_name, 'format': 'json'}
        params.update(extra_params)
        res = session.get(WIKI_API_URL, params=params, timeout=REQUEST_TIMEOUT).json()
        if not isinstance(res, dict):
            return []
        query_data = res.get('query', {})
        if not isinstance(query_data, dict):
            return []
        items = query_data.get(list_name, [])
        return items if isinstance(items, list) else []
    except Exception:
        return []


def _fetch_wiki_pages_content(session, titles, with_redirects=True):
    """共用的 Fandom Wiki 批次頁面內容查詢（每批 50 筆，自動追隨 normalized 與 redirects）"""
    results = {}
    unique_titles = list(dict.fromkeys(str(t).strip() for t in (titles or []) if t and str(t).strip()))
    if not unique_titles:
        return results

    for i in range(0, len(unique_titles), 50):
        batch = unique_titles[i:i + 50]
        try:
            params = {
                'action': 'query',
                'titles': '|'.join(batch),
                'prop': 'revisions',
                'rvslots': 'main',
                'rvprop': 'content',
                'format': 'json',
            }
            if with_redirects:
                params['redirects'] = '1'

            res = session.get(WIKI_API_URL, params=params, timeout=REQUEST_TIMEOUT).json()
            if not isinstance(res, dict):
                continue
            query_data = res.get('query', {})
            if not isinstance(query_data, dict):
                continue

            title_to_originals = {t: [t] for t in batch}
            for mapping_key in ('normalized', 'redirects'):
                items = query_data.get(mapping_key, [])
                if not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    src = item.get('from')
                    dst = item.get('to')
                    if src and dst and src in title_to_originals:
                        origins = title_to_originals.pop(src)
                        title_to_originals.setdefault(dst, []).extend(origins)

            pages = query_data.get('pages', {})
            if not isinstance(pages, dict):
                continue
            for pid, p in pages.items():
                if str(pid) == "-1" or not isinstance(p, dict) or 'missing' in p:
                    continue
                title = p.get('title', '')
                revs = p.get('revisions', [])
                if not isinstance(revs, list) or not revs or not isinstance(revs[0], dict):
                    continue
                content = revs[0].get('slots', {}).get('main', {}).get('*', '')
                if not isinstance(content, str):
                    continue
                page_entry = {"title": title, "content": content}
                for orig in title_to_originals.get(title, [title]):
                    results[orig] = page_entry
        except Exception as e:
            print(f"  ⚠️ 批次查詢 Wiki 頁面內容失敗: {e}")

    return results


def query_wiki_character_pages_batch(char_names, session):
    """Batch queries Wiki pages for characters and maps the results back to the original queried names."""
    results = {}
    if not char_names:
        return results

    for name in char_names:
        results[name] = {"cht_name": None, "path": None, "elem": None}

    pages_map = _fetch_wiki_pages_content(session, list(set(char_names)), with_redirects=True)
    for original_name, page_entry in pages_map.items():
        content = page_entry.get("content", "")
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

    return results


def query_wiki_character_page(char_name, session):
    """單筆查詢 Wiki 角色頁面，內部直接複用批次查詢邏輯"""
    if not char_name:
        return {"cht_name": None, "path": None, "elem": None}
    return query_wiki_character_pages_batch([char_name], session).get(
        char_name, {"cht_name": None, "path": None, "elem": None}
    )


def extract_zht_official_name(wikitext):
    """從 Fandom {{Other Languages}} 抽取繁中正式譯名（|zht 或 |zh-tw）"""
    if not wikitext:
        return None
    m = re.search(r'\|\s*(?:zht|zh[-_]tw)[ \t]*=[ \t]*([^\r\n|\}]+)', wikitext, re.IGNORECASE)
    if not m:
        return None
    val = clean_wikitext_value(m.group(1))
    val = re.sub(r'<[^>]+>', '', val).strip()
    return val or None


def extract_event_start_date(wikitext, fallback_title=""):
    """從活動/版本 Wikitext 的 time_start / release_date 或子頁標題抽取 YY/MM/DD 日期"""
    if wikitext:
        for field in ('time_start', 'release_date', 'start_date', 'date'):
            m = re.search(rf'\|\s*{field}[ \t]*=[ \t]*([^\r\n|\}}]+)', wikitext, re.IGNORECASE)
            if m:
                raw = clean_wikitext_value(m.group(1))
                raw = re.sub(r'<[^>]+>', '', raw).strip()
                m_iso = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', raw)
                if m_iso:
                    norm = normalize_patch_date(m_iso.group(1))
                    if norm:
                        return norm
                trimmed = re.sub(r'\s+\d{1,2}:\d{2}(?::\d{2})?.*$', '', raw).strip()
                norm = normalize_patch_date(trimmed)
                if norm:
                    return norm
    if fallback_title:
        m_title_date = re.search(r'/(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b', fallback_title)
        if m_title_date:
            norm = normalize_patch_date(m_title_date.group(1))
            if norm:
                return norm
    return None


def resolve_patch_by_date(date_str, patches, version_hint=None):
    """依據發布日期 (YY/MM/DD 或 ISO) 與可選版本號提示，精確對應版本排程中的 上／中／下 階段"""
    if not patches:
        return None
    target_date = normalize_patch_date(date_str) if date_str else None
    valid_patches = [p for p in patches if isinstance(p, dict) and p.get('patch')]
    if version_hint:
        ver_re = re.compile(rf'^{re.escape(str(version_hint).strip())}[上中下]$')
        candidates = [p for p in valid_patches if ver_re.match(p['patch'])]
    else:
        candidates = valid_patches
    if not candidates:
        return None

    phase_rank = {'上': 0, '中': 1, '下': 2}

    def _sort_key(p):
        name = p.get('patch', '')
        m = re.match(r'^(\d+)\.(\d+)([上中下])$', name)
        ver_tuple = (int(m.group(1)), int(m.group(2)), phase_rank.get(m.group(3), 9)) if m else (999, 999, 9)
        return (normalize_patch_date(p.get('date')) or '99/99/99', ver_tuple)

    sorted_cands = sorted(candidates, key=_sort_key)
    if not target_date:
        return sorted_cands[0]['patch'] if version_hint else None

    dated_cands = [
        (normalize_patch_date(p.get('date')), p['patch'])
        for p in sorted_cands
        if normalize_patch_date(p.get('date'))
    ]
    matched = [patch_name for p_date, patch_name in dated_cands if p_date <= target_date]
    if matched:
        return matched[-1]
    return sorted_cands[0]['patch'] if version_hint else None


def _extract_event_titles_from_item(wikitext):
    """從物品頁 (如 Acheron's Affinitive Eidolon) 抽取關聯活動頁面標題清單"""
    if not wikitext:
        return []
    events = []
    seen = set()
    for m in re.finditer(r'\|\s*event\d*[ \t]*=[ \t]*([^\r\n|\}]+)', wikitext, re.IGNORECASE):
        val = clean_wikitext_value(m.group(1))
        val = re.sub(r'<[^>]+>', '', val).strip()
        if val and val not in seen:
            seen.add(val)
            events.append(val)
    for m in re.finditer(r'\|\s*source\d*[ \t]*=[ \t]*([^\r\n\}]+)', wikitext, re.IGNORECASE):
        for link_m in re.finditer(r'\[\[([^|\]]+)(?:\|[^\]]+)?\]\]', m.group(1)):
            target = link_m.group(1).strip()
            if target and not target.lower().startswith(('file:', 'category:')) and target not in seen:
                seen.add(target)
                events.append(target)
    return events


def _extract_novaflare_chars(wikitext):
    """從 Novaflare 波次子頁抽出強化角色英文名清單"""
    if not wikitext:
        return []
    chars = []
    seen = set()
    for m in re.finditer(r'\{\{\s*Character\s+(?:Intro|Card)\s*\|\s*([^|}\r\n]+)', wikitext, re.IGNORECASE):
        name = clean_wikitext_value(m.group(1))
        if name and name not in seen:
            seen.add(name)
            chars.append(name)
    return chars


def _fetch_novaflare_buffs(session, patches):
    """自動探測 Fandom Novaflare 及其所有日期子頁（如 Novaflare/2025-07-02）"""
    records = []
    subpages = _query_wiki_list(session, 'allpages', {
        'apprefix': 'Novaflare/',
        'apnamespace': 0,
        'aplimit': 500,
    })
    wave_titles = []
    for item in subpages:
        title = item.get('title', '') if isinstance(item, dict) else ''
        if not title or not title.startswith('Novaflare/'):
            continue
        suffix = title[len('Novaflare/'):]
        if '/' in suffix or 'trial' in suffix.lower():
            continue
        wave_titles.append(title)

    if not wave_titles:
        return records

    pages_map = _fetch_wiki_pages_content(session, ['Novaflare'] + wave_titles, with_redirects=True)
    main_content = pages_map.get('Novaflare', {}).get('content', '')
    buff_type = normalize_buff_type(extract_zht_official_name(main_content) or 'Novaflare') or DEFAULT_BUFF_TYPE

    for title in wave_titles:
        content = pages_map.get(title, {}).get('content', '')
        if not content:
            continue
        date_str = extract_event_start_date(content, fallback_title=title)
        m_ver = re.search(r'\[\[Version\s*(\d+\.\d+)', content, re.IGNORECASE)
        version_hint = m_ver.group(1) if m_ver else None
        resolved_patch = resolve_patch_by_date(date_str, patches, version_hint=version_hint)
        if not resolved_patch:
            continue
        for en_name in _extract_novaflare_chars(content):
            records.append({'en_name': en_name, 'patch': resolved_patch, 'buff_type': buff_type})

    return records


def _fetch_affinitive_eidolon_buffs(session, patches):
    """自動探測 Category:Affinitive Eidolons，並依物品關聯活動起日／版本發布日推算精確階段"""
    records = []
    members = _query_wiki_list(session, 'categorymembers', {
        'cmtitle': 'Category:Affinitive Eidolons',
        'cmnamespace': 0,
        'cmlimit': 500,
    })
    member_titles = [
        m.get('title', '') for m in members
        if isinstance(m, dict) and m.get('title') and not m.get('title', '').startswith('Category:')
    ]
    if not member_titles:
        return records

    pages_map = _fetch_wiki_pages_content(session, ['Affinitive Eidolon'] + member_titles, with_redirects=True)
    main_content = pages_map.get('Affinitive Eidolon', {}).get('content', '')
    default_ae_type = normalize_buff_type(extract_zht_official_name(main_content) or 'Affinitive Eidolon')

    parsed_entries = []
    for title in member_titles:
        content = pages_map.get(title, {}).get('content', '')
        if not content:
            continue
        m_char = re.search(r'\|\s*character[ \t]*=[ \t]*([^\r\n|\}]+)', content, re.IGNORECASE)
        if not m_char:
            continue
        en_name = clean_wikitext_value(m_char.group(1))
        if not en_name:
            continue

        m_lvl = re.search(r'\|\s*level[ \t]*=[ \t]*([^\r\n|\}]+)', content, re.IGNORECASE)
        raw_level = clean_wikitext_value(m_lvl.group(1)) if m_lvl else ''
        buff_type = normalize_buff_type(raw_level) if raw_level else None
        buff_type = buff_type or default_ae_type

        m_ch = re.search(r'\{\{\s*Change History\s*\|\s*(\d+\.\d+)', content, re.IGNORECASE)
        version_hint = m_ch.group(1) if m_ch else None

        parsed_entries.append({
            'en_name': en_name,
            'buff_type': buff_type,
            'version_hint': version_hint,
        })

    if not parsed_entries:
        return records

    # 批次查詢各角色專屬奇緣星魂物品頁（例如 "Acheron's Affinitive Eidolon"）以取得關聯活動名稱
    unique_names = list(dict.fromkeys(e['en_name'] for e in parsed_entries))
    item_titles = [f"{name}'s Affinitive Eidolon" for name in unique_names]
    item_pages = _fetch_wiki_pages_content(session, item_titles, with_redirects=True)

    char_events = {}
    all_aux_titles = []
    for name in unique_names:
        item_entry = item_pages.get(f"{name}'s Affinitive Eidolon")
        if item_entry:
            ev_list = _extract_event_titles_from_item(item_entry.get('content', ''))
            if ev_list:
                char_events[name] = ev_list
                all_aux_titles.extend(ev_list)

    for entry in parsed_entries:
        vh = entry['version_hint']
        if vh:
            all_aux_titles.append(f"Version/{vh}")

    aux_pages = _fetch_wiki_pages_content(session, all_aux_titles, with_redirects=True) if all_aux_titles else {}

    for entry in parsed_entries:
        en_name = entry['en_name']
        version_hint = entry['version_hint']
        ev_dates = []
        for ev_title in char_events.get(en_name, []):
            ev_content = aux_pages.get(ev_title, {}).get('content', '')
            d = extract_event_start_date(ev_content)
            if d:
                ev_dates.append(d)

        release_date = min(ev_dates) if ev_dates else None
        if not release_date and version_hint:
            ver_content = aux_pages.get(f"Version/{version_hint}", {}).get('content', '')
            release_date = extract_event_start_date(ver_content)

        resolved_patch = resolve_patch_by_date(release_date, patches, version_hint=version_hint)
        if not resolved_patch or not entry['buff_type']:
            continue

        records.append({
            'en_name': en_name,
            'patch': resolved_patch,
            'buff_type': entry['buff_type'],
        })

    return records


def fetch_fandom_character_buffs(session, patches):
    """整合探測 Fandom Wiki 各強化系統頁面並回傳去重後的角色強化排程清單"""
    if not patches:
        return []
    combined = []
    seen = set()
    for collector in (_fetch_novaflare_buffs, _fetch_affinitive_eidolon_buffs):
        try:
            items = collector(session, patches)
        except Exception as e:
            print(f"  ⚠️ 探測角色強化系統時發生異常 ({collector.__name__}): {e}")
            items = []
        for rec in items:
            key = (rec.get('en_name'), rec.get('patch'), rec.get('buff_type'))
            if all(key) and key not in seen:
                seen.add(key)
                combined.append(rec)
    return combined


# ──────────────────────────────────────────────────
# 🎁 角色取得方式（Acquisition Method）全自動探測引擎
#   - 優先序：官方 Change History（精確版別）／主頁商店清單／動態 Store 分頁／群星躍遷／角色頁面回退
#   - 零字典設計：遇到未來全新取得管道或新商店頁面，自動保留並抽取繁中官方名稱
# ──────────────────────────────────────────────────
_MONTH_DATE_RE = re.compile(
    r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b',
    re.IGNORECASE,
)
_ISO_DATE_RE = re.compile(r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b')
_IGNORE_WIKI_LINK_PREFIXES = (
    'file:', 'image:', 'category:', 'special:', 'template:', 'version ', 'warp/',
    'store', 'shop', 'character event warp', 'stellar convergence', 'celestial invitation',
    'stellar warp', 'golden companion spirit', 'silver companion spirit', 'light cone memory shard',
)


def _split_version_sections(wikitext):
    """切分 Change History 頁面中的各版本段落，回傳 [(version_str, body), ...]"""
    if not isinstance(wikitext, str) or not wikitext.strip():
        return []
    header_re = re.compile(
        r'(?m)^[ \t]*(?:={2,4}[ \t]*)?(?:\[\[[ \t]*)?Version[ \t]+(\d+\.\d+)(?:\|[^\]]+)?(?:[ \t]*\]\])?[ \t]*(?:={2,4})?[ \t]*$',
        re.IGNORECASE,
    )
    matches = list(header_re.finditer(wikitext))
    sections = []
    for idx, m in enumerate(matches):
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(wikitext)
        sections.append((m.group(1), wikitext[start:end]))
    return sections


def _extract_inline_dates(text):
    """從 Wikitext 段落中抽取 ISO 或英文月份日期並正規化為 YY/MM/DD 清單"""
    if not isinstance(text, str) or not text:
        return []
    dates = []
    for m in _ISO_DATE_RE.finditer(text):
        norm = normalize_patch_date(m.group(1))
        if norm and norm not in dates:
            dates.append(norm)
    for m in _MONTH_DATE_RE.finditer(text):
        raw_str = f"{m.group(1)} {m.group(2)}, {m.group(3)}"
        for fmt in ('%B %d, %Y',):
            try:
                norm = datetime.strptime(raw_str, fmt).strftime('%y/%m/%d')
                if norm not in dates:
                    dates.append(norm)
            except ValueError:
                pass
    return dates


def _parse_character_names_from_block(wikitext):
    """
    從 Change History 段落、{{Item List}}、{{Item}} 或 {{Character Card}} 抽取角色英文名稱清單。
    自動略過 Light Cone / Relic / Material 等非角色項目與常駐 5 星。
    """
    if not isinstance(wikitext, str) or not wikitext.strip():
        return []

    names = []
    seen = set()

    def _add_candidate(raw_name):
        cleaned = clean_wikitext_value(str(raw_name))
        cleaned = re.sub(r'<!--.*?-->', '', cleaned).strip()
        if not cleaned or '=' in cleaned:
            return
        low = cleaned.lower()
        if any(low.startswith(p) for p in _IGNORE_WIKI_LINK_PREFIXES):
            return
        if is_standard_five_star(cleaned):
            return
        if cleaned not in seen:
            seen.add(cleaned)
            names.append(cleaned)

    # 1. {{Item List|...}} / {{Card List|...}} / {{Cards|...}}（支援多行與 type=Character）
    for m in re.finditer(r'\{\{\s*(?:Item\s+List|Card\s+List|Cards)\s*\|([\s\S]*?)\}\}', wikitext, re.IGNORECASE):
        inner = m.group(1)
        m_type = re.search(r'(?:^|\|)\s*type\s*=\s*([^|\r\n]+)', inner, re.IGNORECASE)
        if m_type and m_type.group(1).strip().lower() not in ('character', 'characters'):
            continue
        for seg in re.split(r'\|', inner):
            seg_clean = seg.strip()
            if not seg_clean:
                continue
            if re.match(r'^[a-zA-Z0-9_]+\s*=', seg_clean):
                continue
            for item in re.split(r'[;\r\n]+', seg_clean):
                if item.strip():
                    _add_candidate(item)

    # 2. {{Item|Name|type=Character}} / {{Character Card|Name}} / {{Character Intro|Name}}
    for m in re.finditer(r'\{\{\s*Item\s*\|([^|}\r\n]+)(?:\|([^}]*))?\}\}', wikitext, re.IGNORECASE):
        params = m.group(2) or ''
        m_type = re.search(r'\btype\s*=\s*([^|\r\n]+)', params, re.IGNORECASE)
        if m_type and m_type.group(1).strip().lower() not in ('character', 'characters'):
            continue
        if m_type:
            _add_candidate(m.group(1))

    for m in re.finditer(r'\{\{\s*Character(?:\s+(?:Intro|Card|Avatar))?\s*\|([^|}\r\n]+)', wikitext, re.IGNORECASE):
        _add_candidate(m.group(1))

    # 3. 一般條列中的 [[Character]] 連結（避開已知非角色段與純光錐條目）
    for line in wikitext.splitlines():
        line_low = line.lower()
        if any(skip in line_low for skip in ('light cone', 'type=light cone', 'type=relic', 'removed from', 'no longer available')):
            continue
        if '{{' in line and 'item list' in line_low:
            continue
        for link_m in re.finditer(r'\[\[([^|\]]+)(?:\|[^\]]+)?\]\]', line):
            _add_candidate(link_m.group(1))

    return names


def parse_shop_character_items(wikitext):
    """
    從 {{Shop|...}} 模板抽取角色兌換項目（含可選日期/版本提示），自動略過光錐、素材與常駐 5 星。
    回傳 [{'en_name': ..., 'date': ..., 'version_hint': ...}, ...]
    """
    if not isinstance(wikitext, str) or '{{Shop' not in wikitext:
        return []

    results = []
    seen = set()

    # 若頁面有分區標題，記錄每個位置最近的標題，判斷是否明確為角色區段／排除光錐與雜項區段
    sec_re = re.compile(r'(?m)^={2,4}\s*([^=\r\n]+?)\s*={2,4}')
    sec_matches = list(sec_re.finditer(wikitext))

    def _heading_at(pos):
        last = ''
        for sm in sec_matches:
            if sm.start() <= pos:
                last = sm.group(1).strip().lower()
            else:
                break
        return last

    for m in re.finditer(r'\{\{\s*Shop\s*\|([\s\S]*?)\n\}\}', wikitext, re.IGNORECASE):
        heading_low = _heading_at(m.start())
        if any(k in heading_low for k in ('light cone', 'relic', 'material', 'consumable', 'cosmetic')):
            continue
        body = m.group(1)
        body_low = body.lower()
        has_explicit_char_type = bool(re.search(r'type(?:\{\{=\}\}|=)\s*characters?\b', body_low))
        is_char_heading = 'character' in heading_low

        # 若此 {{Shop}} 區塊既不在明確「Character」分區下，也未標記任何 type=Character 項目，則整體略過
        if not has_explicit_char_type and not is_char_heading:
            continue

        for line in body.splitlines():
            line_str = line.strip()
            if not line_str.startswith('|'):
                continue
            row_body = line_str[1:].strip()
            if not row_body or re.match(r'^(?:shop|currency|note|total|sort)\s*=', row_body, re.IGNORECASE):
                continue
            parts = [p.strip() for p in row_body.split(';;')]
            if not parts or not parts[0]:
                continue

            item_raw = parts[0]
            # 第一欄若本身為 key=val（如 name=... 或 item=...），改從對應欄位取值
            if re.match(r'^[a-zA-Z0-9_]+\s*=', item_raw):
                m_named = re.match(r'^(?:item|name|character)\s*=\s*(.+)$', item_raw, re.IGNORECASE)
                if not m_named:
                    continue
                item_raw = m_named.group(1).strip()

            row_lower = row_body.lower()
            m_type = re.search(r'type(?:\{\{=\}\}|=)\s*([a-zA-Z ]+)', row_lower)
            if m_type and m_type.group(1).strip() not in ('character', 'characters'):
                continue
            # 若同一個 {{Shop}} 區塊中有部分列明確標示 type=Character，未標示的列多為貨幣／道具（例如旅伴金靈、變量骰子），應予以略過
            if has_explicit_char_type and not m_type:
                continue
            if not m_type and 'light cone' in row_lower:
                continue

            # 檢查是否有專屬角色顯示名或內建日期
            candidate = clean_wikitext_value(item_raw)
            if not candidate or is_standard_five_star(candidate):
                continue
            row_dates = _extract_inline_dates(row_body)
            m_ver = re.search(r'Version\s*(\d+\.\d+)', row_body, re.IGNORECASE)

            key = candidate.lower()
            if key not in seen:
                seen.add(key)
                results.append({
                    'en_name': candidate,
                    'date': row_dates[0] if row_dates else None,
                    'version_hint': m_ver.group(1) if m_ver else None,
                })

    return results


def _batch_resolve_version_dates(session, version_strs):
    """批次查詢 Version/<ver> 頁面起始日，回傳 {ver_str: YY/MM/DD}"""
    versions = list(dict.fromkeys(str(v).strip() for v in (version_strs or []) if v))
    if not versions or session is None:
        return {}
    ver_titles = [f"Version/{v}" for v in versions]
    pages_map = _fetch_wiki_pages_content(session, ver_titles, with_redirects=True)
    resolved = {}
    for v in versions:
        content = pages_map.get(f"Version/{v}", {}).get('content', '')
        d = extract_event_start_date(content)
        if d:
            resolved[v] = d
    return resolved


def _resolve_acq_patch(ver_str, candidate_dates, patches, ver_date_map=None):
    """將版本號＋候選日期解析為精確版本階段名稱（如 4.7上）"""
    valid_dates = [d for d in (candidate_dates or []) if d]
    chosen_date = min(valid_dates) if valid_dates else None
    if not chosen_date and ver_str and ver_date_map:
        chosen_date = ver_date_map.get(ver_str)
    return resolve_patch_by_date(chosen_date, patches, version_hint=ver_str)


def _fetch_pool_acquisitions(session, patches, warp_pool_snapshots=None):
    """自動探測「星緣相邀（pool）」：Change History 主軸 + 卡池頁 character_5 回退"""
    records = []
    seen_chars = set()

    pages_map = _fetch_wiki_pages_content(
        session,
        ['Character Event Warp/Change History', 'Celestial Invitation'],
        with_redirects=True,
    )
    ch_content = pages_map.get('Character Event Warp/Change History', {}).get('content', '')
    sections = _split_version_sections(ch_content)

    # 預先收集各段所需版本起始日
    relevant_sections = []
    needed_versions = []
    for ver_str, body in sections:
        body_low = body.lower()
        if any(k in body_low for k in ('added', 'celestial invitation', 'non-promoted', 'non-featured')):
            chars = _parse_character_names_from_block(body)
            if chars:
                relevant_sections.append((ver_str, body, chars))
                needed_versions.append(ver_str)

    ver_date_map = _batch_resolve_version_dates(session, needed_versions)

    for ver_str, body, chars in relevant_sections:
        resolved_patch = _resolve_acq_patch(ver_str, _extract_inline_dates(body), patches, ver_date_map)
        if not resolved_patch:
            continue
        for en_name in chars:
            records.append({'en_name': en_name, 'acq_type': 'pool', 'patch': resolved_patch})
            seen_chars.add(sanitize_name(en_name))

    # 若 Celestial Invitation 頁本身另有未見於 Change History 的角色清單，安全補全
    ci_content = pages_map.get('Celestial Invitation', {}).get('content', '')
    if ci_content:
        m_ci_ver = re.search(r'\{\{\s*Change History\s*\|\s*(\d+\.\d+)', ci_content, re.IGNORECASE)
        ci_ver = m_ci_ver.group(1) if m_ci_ver else None
        ci_dates = _batch_resolve_version_dates(session, [ci_ver]) if ci_ver else {}
        ci_patch = _resolve_acq_patch(ci_ver, [], patches, ci_dates) if ci_ver else None
        if ci_patch:
            for item in parse_shop_character_items(ci_content):
                en_name = item['en_name']
                if sanitize_name(en_name) not in seen_chars:
                    records.append({'en_name': en_name, 'acq_type': 'pool', 'patch': ci_patch})
                    seen_chars.add(sanitize_name(en_name))

    # 回退：若 Change History 尚未編輯，從即時卡池頁 character_5（依時間排序最早首次出現）補齊
    for snap in (warp_pool_snapshots or []):
        en_name = str(snap.get('en_name', '')).strip()
        patch = str(snap.get('patch', '')).strip()
        if not en_name or not patch or is_standard_five_star(en_name):
            continue
        s_key = sanitize_name(en_name)
        if s_key and s_key not in seen_chars:
            seen_chars.add(s_key)
            records.append({'en_name': en_name, 'acq_type': 'pool', 'patch': patch})

    return records


def _fetch_shop_acquisitions(session, patches):
    """自動探測「聚靈鑄星（shop）」：Stellar Convergence/Change History + Stellar Convergence 主表"""
    records = []
    seen_chars = set()

    pages_map = _fetch_wiki_pages_content(
        session,
        ['Stellar Convergence/Change History', 'Stellar Convergence', 'Stellar Companions'],
        with_redirects=True,
    )
    ch_content = pages_map.get('Stellar Convergence/Change History', {}).get('content', '')
    sc_content = pages_map.get('Stellar Convergence', {}).get('content', '')
    sc_event_content = pages_map.get('Stellar Companions', {}).get('content', '')

    sections = _split_version_sections(ch_content)
    section_entries = []
    needed_versions = []
    for ver_str, body in sections:
        char_section_text = body
        m_char_sub = re.search(
            r'Added to Character Redemption\s*:?([\s\S]*?)(?:\*\s*Added to (?:Light Cone|Relic|Material)|$)',
            body,
            re.IGNORECASE,
        )
        if m_char_sub:
            char_section_text = m_char_sub.group(1)
        elif 'light cone redemption' in body.lower() and 'character' not in body.lower():
            continue

        chars = _parse_character_names_from_block(char_section_text)
        if chars:
            section_entries.append((ver_str, body, chars))
            needed_versions.append(ver_str)

    m_sc_ver = re.search(r'\{\{\s*Change History\s*\|\s*(\d+\.\d+)', sc_content or '', re.IGNORECASE)
    sc_base_ver = m_sc_ver.group(1) if m_sc_ver else None
    if sc_base_ver:
        needed_versions.append(sc_base_ver)

    ver_date_map = _batch_resolve_version_dates(session, needed_versions)

    for ver_str, body, chars in section_entries:
        resolved_patch = _resolve_acq_patch(ver_str, _extract_inline_dates(body), patches, ver_date_map)
        if not resolved_patch:
            continue
        for en_name in chars:
            records.append({'en_name': en_name, 'acq_type': 'shop', 'patch': resolved_patch})
            seen_chars.add(sanitize_name(en_name))

    # 主表 {{Shop|shop=Stellar Convergence}} 補全（例如首波 3.2 上登場的 阮•梅 與 羅剎）
    shop_items = parse_shop_character_items(sc_content)
    if shop_items:
        sc_event_date = extract_event_start_date(sc_event_content)
        for item in shop_items:
            en_name = item['en_name']
            s_key = sanitize_name(en_name)
            if not s_key or s_key in seen_chars:
                continue
            item_ver = item.get('version_hint') or sc_base_ver
            item_dates = [d for d in (item.get('date'), sc_event_date) if d]
            resolved_patch = _resolve_acq_patch(item_ver, item_dates, patches, ver_date_map)
            if resolved_patch:
                records.append({'en_name': en_name, 'acq_type': 'shop', 'patch': resolved_patch})
                seen_chars.add(s_key)

    return records


def _fetch_stellar_warp_acquisitions(session, patches):
    """自動探測「群星躍遷（stellar）」：若有原限定 5 星轉入常駐群星躍遷池，自動追蹤"""
    records = []
    pages_map = _fetch_wiki_pages_content(
        session,
        ['Stellar Warp', 'Stellar Warp/Change History'],
        with_redirects=True,
    )
    sw_content = pages_map.get('Stellar Warp', {}).get('content', '')
    ch_content = pages_map.get('Stellar Warp/Change History', {}).get('content', '')
    if not ch_content and not sw_content:
        return records

    acq_type = normalize_acquisition_type(extract_zht_official_name(sw_content) or 'Stellar Warp') or 'stellar'
    sections = _split_version_sections(ch_content)
    section_entries = []
    needed_versions = []
    for ver_str, body in sections:
        char_lines = [
            ln for ln in body.splitlines()
            if 'character' in ln.lower() and 'added' in ln.lower() and 'light cone' not in ln.lower()
        ]
        if not char_lines:
            continue
        chars = _parse_character_names_from_block('\n'.join(char_lines))
        if chars:
            section_entries.append((ver_str, body, chars))
            needed_versions.append(ver_str)

    ver_date_map = _batch_resolve_version_dates(session, needed_versions)
    for ver_str, body, chars in section_entries:
        resolved_patch = _resolve_acq_patch(ver_str, _extract_inline_dates(body), patches, ver_date_map)
        if not resolved_patch:
            continue
        for en_name in chars:
            records.append({'en_name': en_name, 'acq_type': acq_type, 'patch': resolved_patch})

    return records


def _fetch_dynamic_store_acquisitions(session, patches):
    """
    動態探索 Store 頁與 Category:Stores 下所有未硬編碼的新角色兌換商店。
    若未來官方新增全新商店系統（例如 5.x 新商店），自動擷取官方繁中名稱與上架階段。
    """
    records = []
    pages_map = _fetch_wiki_pages_content(session, ['Store'], with_redirects=True)
    store_content = pages_map.get('Store', {}).get('content', '')

    cat_members = _query_wiki_list(session, 'categorymembers', {
        'cmtitle': 'Category:Stores',
        'cmnamespace': 0,
        'cmlimit': 100,
    })

    ignored_stores = {
        'store', 'shop', 'stellar convergence',
        'embers exchange', 'gift of stardust', 'light cone manifest',
        'jokes come true', 'outfit show window', 'fashion item',
        'contract shop', 'oneiric pouch', 'stellar purchase',
    }
    candidate_titles = []
    seen_titles = set()

    def _push_store_title(t):
        cleaned = clean_wikitext_value(str(t or '')).split('#')[0].strip()
        if not cleaned or cleaned.lower() in ignored_stores:
            return
        if '/' in cleaned and cleaned.lower().endswith('/change history'):
            return
        if cleaned.lower() not in seen_titles:
            seen_titles.add(cleaned.lower())
            candidate_titles.append(cleaned)

    for m in re.finditer(r'\{\{\s*(?:Main|Transclude)\s*\|([^|}\r\n]+)', store_content, re.IGNORECASE):
        _push_store_title(m.group(1))
    for item in cat_members:
        if isinstance(item, dict) and item.get('title'):
            _push_store_title(item['title'])

    if not candidate_titles:
        return records

    shop_pages = _fetch_wiki_pages_content(session, candidate_titles, with_redirects=True)
    shops_with_chars = []
    for title in candidate_titles:
        content = shop_pages.get(title, {}).get('content', '')
        if not content:
            continue
        items = parse_shop_character_items(content)
        if items:
            shops_with_chars.append((title, content, items))

    if not shops_with_chars:
        return records

    ch_titles = [f"{title}/Change History" for title, _, _ in shops_with_chars]
    ch_pages = _fetch_wiki_pages_content(session, ch_titles, with_redirects=True)

    needed_versions = []
    parsed_shops = []
    for title, content, items in shops_with_chars:
        raw_type_name = extract_zht_official_name(content) or title
        acq_type = normalize_acquisition_type(raw_type_name)
        ch_content = ch_pages.get(f"{title}/Change History", {}).get('content', '')
        sections = _split_version_sections(ch_content)
        section_entries = []
        for ver_str, body in sections:
            chars = _parse_character_names_from_block(body)
            if chars:
                section_entries.append((ver_str, body, chars))
                needed_versions.append(ver_str)

        m_ch = re.search(r'\{\{\s*Change History\s*\|\s*(\d+\.\d+)', content, re.IGNORECASE)
        base_ver = m_ch.group(1) if m_ch else None
        if base_ver:
            needed_versions.append(base_ver)
        for item in items:
            if item.get('version_hint'):
                needed_versions.append(item['version_hint'])

        parsed_shops.append((acq_type, base_ver, items, section_entries))

    ver_date_map = _batch_resolve_version_dates(session, needed_versions)

    for acq_type, base_ver, items, section_entries in parsed_shops:
        if not acq_type:
            continue
        found_in_store = set()
        for ver_str, body, chars in section_entries:
            resolved_patch = _resolve_acq_patch(ver_str, _extract_inline_dates(body), patches, ver_date_map)
            if not resolved_patch:
                continue
            for en_name in chars:
                records.append({'en_name': en_name, 'acq_type': acq_type, 'patch': resolved_patch})
                found_in_store.add(sanitize_name(en_name))

        for item in items:
            en_name = item['en_name']
            s_key = sanitize_name(en_name)
            if not s_key or s_key in found_in_store:
                continue
            item_ver = item.get('version_hint') or base_ver
            item_dates = [item['date']] if item.get('date') else []
            resolved_patch = _resolve_acq_patch(item_ver, item_dates, patches, ver_date_map)
            if resolved_patch:
                records.append({'en_name': en_name, 'acq_type': acq_type, 'patch': resolved_patch})
                found_in_store.add(s_key)

    return records


def _fetch_character_page_acquisition_signals(session, patches, target_en_names, already_found_pairs, warp_acq_records=None):
    """
    萬用安全網：從角色個人 Wiki 頁面偵測 `{{Shop Availability}}` / `how_to_obtain` 新永久管道 / `{{Non-Featured}}`
    （以及 Warp/List 中的非聯動永久池），補齊主頁或 Change History 尚未覆蓋的取得方式。
    """
    records = []
    seen_pairs = set(already_found_pairs or set())

    # 1. 先處理 Warp/List 中偵測到的非聯動無限期卡池（例如未來新永久躍遷池）
    if warp_acq_records:
        wt_titles = list(dict.fromkeys(r['warp_type'] for r in warp_acq_records if r.get('warp_type')))
        wt_pages = _fetch_wiki_pages_content(session, wt_titles, with_redirects=True) if wt_titles else {}
        for r in warp_acq_records:
            en_name = r.get('en_name', '').strip()
            patch = r.get('patch', '').strip()
            raw_wt = r.get('warp_type', '').strip()
            if not en_name or not patch or not raw_wt or is_standard_five_star(en_name):
                continue
            wt_content = wt_pages.get(raw_wt, {}).get('content', '')
            acq_type = normalize_acquisition_type(extract_zht_official_name(wt_content) or raw_wt)
            pair = (sanitize_name(en_name), acq_type)
            if acq_type and acq_type not in (DEFAULT_ACQUISITION_TYPE, 'collab') and pair not in seen_pairs:
                seen_pairs.add(pair)
                records.append({'en_name': en_name, 'acq_type': acq_type, 'patch': patch})

    # 2. 掃描追蹤中角色的 Wiki 主頁，探測尚未收錄的永久商店／取得方式連結
    clean_targets = [
        str(n).strip() for n in (target_en_names or [])
        if isinstance(n, str) and str(n).strip() and not is_standard_five_star(str(n).strip())
    ]
    if not clean_targets:
        return records

    char_pages = _fetch_wiki_pages_content(session, clean_targets, with_redirects=True)
    candidate_char_links = []
    candidate_link_titles = []
    seen_links = set()

    ignored_obtain_targets = {
        'character event warp', 'stellar warp', 'warp', 'collaboration warp',
        'stellar convergence', 'celestial invitation',
    }

    for en_name in clean_targets:
        content = char_pages.get(en_name, {}).get('content', '')
        if not isinstance(content, str) or not content:
            continue

        # 檢查 {{Shop Availability|...|shop=ShopName}} 中明確指定的 shop= 參數（注意：第一參數為道具／角色名稱而非商店名稱）
        for m in re.finditer(r'\{\{\s*Shop\s+Availability\s*\|([^}]*)\}\}', content, re.IGNORECASE):
            m_shop_arg = re.search(r'\bshop\s*=\s*([^|}\r\n]+)', m.group(1), re.IGNORECASE)
            if m_shop_arg:
                shop_title = clean_wikitext_value(m_shop_arg.group(1))
                if shop_title and shop_title.lower() not in seen_links:
                    seen_links.add(shop_title.lower())
                    candidate_link_titles.append(shop_title)
                if shop_title:
                    candidate_char_links.append((en_name, shop_title))

        # 檢查 |how_to_obtain 欄位中非單純限時躍遷的永久連結
        m_hto = re.search(r'\|\s*how_to_obtain\s*=\s*([\s\S]*?)(?=\n\s*\||\}\})', content, re.IGNORECASE)
        if m_hto:
            hto_text = m_hto.group(1)
            for link_m in re.finditer(r'\[\[([^|\]]+)(?:\|[^\]]+)?\]\]', hto_text):
                target = clean_wikitext_value(link_m.group(1)).split('#')[0].strip()
                t_low = target.lower()
                if not target or any(t_low.startswith(p) for p in _IGNORE_WIKI_LINK_PREFIXES):
                    continue
                if t_low in ignored_obtain_targets or sanitize_name(target) == sanitize_name(en_name):
                    continue
                if t_low not in seen_links:
                    seen_links.add(t_low)
                    candidate_link_titles.append(target)
                candidate_char_links.append((en_name, target))

        # 若角色頁有 {{Non-Featured}} 且尚未記錄 pool，檢查頁面段落內的明確版本提示
        if (sanitize_name(en_name), 'pool') not in seen_pairs and re.search(r'\{\{\s*Non-Featured\b', content, re.IGNORECASE):
            for m_nf_ver in re.finditer(
                r'(?:Celestial Invitation|Non-Featured|Character Event Warp)[^\r\n]*?(?:Version\s*(\d+\.\d+)|(\d{4}[-/]\d{1,2}[-/]\d{1,2}))',
                content,
                re.IGNORECASE,
            ):
                ver_hint = m_nf_ver.group(1)
                date_hint = normalize_patch_date(m_nf_ver.group(2)) if m_nf_ver.group(2) else None
                ver_dates = _batch_resolve_version_dates(session, [ver_hint]) if ver_hint and not date_hint else {}
                p_name = _resolve_acq_patch(ver_hint, [date_hint] if date_hint else [], patches, ver_dates)
                if p_name:
                    seen_pairs.add((sanitize_name(en_name), 'pool'))
                    records.append({'en_name': en_name, 'acq_type': 'pool', 'patch': p_name})
                    break

    if not candidate_char_links or not candidate_link_titles:
        return records

    link_pages = _fetch_wiki_pages_content(session, candidate_link_titles, with_redirects=True)
    # 只保留確定是永久商店／永久兌換／非限時卡池的目標頁（自動過濾一般限時 Character Event Warp 頁面）
    valid_target_info = {}
    ch_query_titles = []
    for title in candidate_link_titles:
        content = link_pages.get(title, {}).get('content', '')
        if not isinstance(content, str) or not content:
            continue
        low = content.lower()
        m_inf_type = re.search(r'\|\s*type\s*=\s*([^\r\n|\}]+)', content, re.IGNORECASE)
        inf_type = clean_wikitext_value(m_inf_type.group(1)).lower() if m_inf_type else ''
        if any(bad in inf_type for bad in ('event warp', 'character', 'light cone', 'relic', 'material', 'item')) or inf_type == 'event':
            continue
        is_permanent_source = (
            bool(re.search(r'\{\{\s*shop\s*(?:\||$)', low))
            or inf_type in ('store', 'shop', 'standard', 'permanent')
            or '[[category:stores' in low
            or ('permanent' in low and 'warp' in inf_type)
        )
        if is_permanent_source:
            raw_label = extract_zht_official_name(content) or title
            acq_type = normalize_acquisition_type(raw_label)
            if acq_type and acq_type not in (DEFAULT_ACQUISITION_TYPE, 'collab'):
                m_base_ver = re.search(r'\{\{\s*Change History\s*\|\s*(\d+\.\d+)', content, re.IGNORECASE)
                valid_target_info[title] = {
                    'acq_type': acq_type,
                    'content': content,
                    'base_ver': m_base_ver.group(1) if m_base_ver else None,
                    'date': extract_event_start_date(content),
                }
                ch_query_titles.append(f"{title}/Change History")

    if not valid_target_info:
        return records

    ch_pages = _fetch_wiki_pages_content(session, ch_query_titles, with_redirects=True) if ch_query_titles else {}
    needed_vers = []
    target_ver_map = {}
    for title, info in valid_target_info.items():
        if info['base_ver']:
            needed_vers.append(info['base_ver'])
        ch_content = ch_pages.get(f"{title}/Change History", {}).get('content', '')
        if ch_content:
            per_char_ver = {}
            for ver_str, body in _split_version_sections(ch_content):
                for cn in _parse_character_names_from_block(body):
                    s_cn = sanitize_name(cn)
                    if s_cn and s_cn not in per_char_ver:
                        per_char_ver[s_cn] = (ver_str, _extract_inline_dates(body))
                        needed_vers.append(ver_str)
            target_ver_map[title] = per_char_ver

    ver_date_map = _batch_resolve_version_dates(session, needed_vers)
    for en_name, target in candidate_char_links:
        info = valid_target_info.get(target)
        if not info:
            continue
        acq_type = info['acq_type']
        s_en = sanitize_name(en_name)
        if (s_en, acq_type) in seen_pairs:
            continue
        ver_tuple = target_ver_map.get(target, {}).get(s_en)
        if ver_tuple:
            ver_str, inline_dates = ver_tuple
        else:
            ver_str = info['base_ver']
            inline_dates = [info['date']] if info.get('date') else []
        resolved_patch = _resolve_acq_patch(ver_str, inline_dates, patches, ver_date_map)
        if resolved_patch:
            seen_pairs.add((s_en, acq_type))
            records.append({'en_name': en_name, 'acq_type': acq_type, 'patch': resolved_patch})

    return records


def fetch_fandom_acquisition_methods(session, patches, target_en_names=None):
    """
    整合探測 Fandom Wiki 各取得途徑頁面（星緣相邀／聚靈鑄星／群星躍遷／動態 Store／角色主頁），
    回傳去重後之 [{'en_name', 'acq_type', 'patch'}, ...] 清單。
    """
    if not patches or session is None:
        return []

    cache_entry = _WARP_POOL_SESSION_CACHE.get(id(session), {})
    warp_pool_snapshots = cache_entry.get('pool_snapshots', [])
    indefinite_warp_acqs = cache_entry.get('indefinite_warp_acqs', [])

    combined = []
    seen = set()

    def _extend(items):
        for rec in items or []:
            en_name = str(rec.get('en_name', '')).strip()
            acq_type = normalize_acquisition_type(rec.get('acq_type'))
            patch = str(rec.get('patch', '')).strip()
            if not en_name or not acq_type or not patch or is_standard_five_star(en_name):
                continue
            key = (sanitize_name(en_name), acq_type)
            if key not in seen:
                seen.add(key)
                combined.append({'en_name': en_name, 'acq_type': acq_type, 'patch': patch})

    for fn in (
        lambda: _fetch_pool_acquisitions(session, patches, warp_pool_snapshots=warp_pool_snapshots),
        lambda: _fetch_shop_acquisitions(session, patches),
        lambda: _fetch_stellar_warp_acquisitions(session, patches),
        lambda: _fetch_dynamic_store_acquisitions(session, patches),
    ):
        try:
            _extend(fn())
        except Exception as e:
            print(f"  ⚠️ 探測角色取得方式時發生異常: {e}")

    try:
        _extend(_fetch_character_page_acquisition_signals(
            session,
            patches,
            target_en_names=target_en_names,
            already_found_pairs=seen,
            warp_acq_records=indefinite_warp_acqs,
        ))
    except Exception as e:
        print(f"  ⚠️ 探測角色主頁取得方式時發生異常: {e}")

    return combined


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

    # 門檻 4：版本閉包防護（孤兒版本防護：包含 runs、isCollab、term.patch、terms[].patch）
    for c in new_chars:
        for r in (c.get('runs') or []):
            if r not in patch_names_set:
                raise AssertionError(
                    f"❌ 門檻 4 失敗：角色 [{c.get('name')}] 的排程版本 [{r}] 不存在於版本清單中！"
                )
        collab_patch = c.get('isCollab')
        if isinstance(collab_patch, str) and collab_patch and collab_patch not in patch_names_set:
            raise AssertionError(
                f"❌ 門檻 4 失敗：聯動角色 [{c.get('name')}] 的聯動版本 [{collab_patch}] 不存在於版本清單中！"
            )
        term = c.get('term')
        if isinstance(term, dict) and term.get('patch') and term['patch'] not in patch_names_set:
            raise AssertionError(
                f"❌ 門檻 4 失敗：角色 [{c.get('name')}] 的取得版本 [{term['patch']}] 不存在於版本清單中！"
            )
        for t_entry in (c.get('terms') or []):
            if isinstance(t_entry, dict) and t_entry.get('patch') and t_entry['patch'] not in patch_names_set:
                raise AssertionError(
                    f"❌ 門檻 4 失敗：角色 [{c.get('name')}] 的複合取得版本 [{t_entry['patch']}] 不存在於版本清單中！"
                )
    print("  ✅ 門檻 4 通過：所有角色的登場與取得排程皆有對應之版本節點")

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
    🧭💠🎁 動態命途 / 強化模式 / 取得方式審計：遇到未預設的新命途、新強化模式或新取得方式只會「記錄並保留」，不會拋出例外。
    回傳報告 dict：
      dynamic_paths                目前資料中非核心（js/paths.js 未註冊）的命途
      introduced_paths             本次新出現的命途
      buff_types                   目前資料中所有強化模式
      introduced_buff_types        本次新出現的強化模式
      dynamic_acquisition_types    目前資料中非核心（js/types.js 未註冊）的取得方式
      introduced_acquisition_types 本次新出現的取得方式
      warnings                     非致命資料提示（如強化版本不在版本清單中）
    """
    warnings = []
    orig_paths = set(collect_paths(original_chars))
    new_paths = collect_paths(new_chars)
    dynamic_paths = [p for p in new_paths if p not in CORE_PATHS and p != UNKNOWN_LABEL]
    introduced_paths = [p for p in new_paths if p not in orig_paths and p != UNKNOWN_LABEL]

    orig_buff_types = set(collect_buff_types(original_chars))
    buff_types = collect_buff_types(new_chars)
    introduced_buff_types = [t for t in buff_types if t not in orig_buff_types]

    orig_acq_types = set(collect_acquisition_types(original_chars))
    acq_types = collect_acquisition_types(new_chars)
    dynamic_acquisition_types = [t for t in acq_types if t not in CORE_ACQUISITION_TYPES]
    introduced_acquisition_types = [t for t in acq_types if t not in orig_acq_types]

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
        term = c.get('term')
        if term is not None and (not isinstance(term, dict) or not term.get('type')):
            warnings.append(f"角色 [{name}] 的取得方式 term 格式不完整：{term!r}")
        terms = c.get('terms')
        if terms is not None:
            if not isinstance(terms, list):
                warnings.append(f"角色 [{name}] 的複合取得方式 terms 型別非陣列")
            else:
                for t_entry in terms:
                    if not isinstance(t_entry, dict) or not t_entry.get('type'):
                        warnings.append(f"角色 [{name}] 的複合取得方式條目缺漏 type：{t_entry!r}")

    if dynamic_paths:
        print(f"  🧭 審計 6：偵測到非核心命途 {dynamic_paths}，已自動保留並交由前端通用樣式呈現")
    if introduced_buff_types:
        print(f"  💠 審計 6：偵測到新強化模式 {introduced_buff_types}，已自動保留並整合")
    if dynamic_acquisition_types:
        print(f"  🎁 審計 6：偵測到非核心取得方式 {dynamic_acquisition_types}，已自動保留並交由前端通用樣式呈現")
    if introduced_acquisition_types:
        print(f"  🎁 審計 6：偵測到新取得方式 {introduced_acquisition_types}，已自動保留並整合")
    for w in warnings:
        print(f"  ⚠️ 審計 6（非致命）：{w}")
    if not dynamic_paths and not introduced_buff_types and not dynamic_acquisition_types and not introduced_acquisition_types and not warnings:
        print("  ✅ 審計 6 通過：命途、強化模式與取得方式皆屬已註冊範圍")

    return {
        'dynamic_paths': dynamic_paths,
        'introduced_paths': introduced_paths,
        'buff_types': buff_types,
        'introduced_buff_types': introduced_buff_types,
        'dynamic_acquisition_types': dynamic_acquisition_types,
        'introduced_acquisition_types': introduced_acquisition_types,
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
        summary_lines.append(f"🧭 動態命途／強化／取得方式 ({len(dynamic_tags_log)} 項):\n  • " + "\n  • ".join(dynamic_tags_log))
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
    for a in report.get('introduced_acquisition_types') or []:
        lines.append(f"新取得方式：{a}")
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


def _build_char_lookup_context(chars, en_data, cht_data):
    """建立角色匹配索引（供主合併流程與強化排程套用共同複用）"""
    sanitized_en_dict = {sanitize_name(info.get("name", "")): cid for cid, info in en_data.items()}
    return {
        'en_data': en_data,
        'cht_data': cht_data,
        'sanitized_en_dict': sanitized_en_dict,
        'by_cid': {c['cid']: c for c in chars if c.get('cid')},
        'by_name': {c['name']: c for c in chars if c.get('name')},
        'by_sanitized': {sanitize_name(c.get('name', '')): c for c in chars if c.get('name')},
        'by_cjk': {
            normalize_cjk_name(c.get('name', '')): c
            for c in chars
            if c.get('name') and contains_cjk(c.get('name', ''))
        },
    }


def _find_matched_char(en_name, target_cid, target_name, ctx):
    """依名稱、清理後英名、簡繁歸一名稱與 CID 匹配現有角色"""
    if target_name in ctx['by_name']:
        return ctx['by_name'][target_name]
    sanitized_en = sanitize_name(en_name)
    if sanitized_en in ctx['by_sanitized']:
        return ctx['by_sanitized'][sanitized_en]
    if contains_cjk(target_name):
        norm_cjk = normalize_cjk_name(target_name)
        if norm_cjk in ctx['by_cjk']:
            return ctx['by_cjk'][norm_cjk]
    if target_cid and target_cid in ctx['by_cid']:
        return ctx['by_cid'][target_cid]
    return None


def _register_char_in_context(char, ctx):
    """將新建或升級後的角色註冊回匹配索引"""
    name = char.get('name')
    cid = char.get('cid')
    if cid:
        ctx['by_cid'][cid] = char
    if name:
        ctx['by_name'][name] = char
        ctx['by_sanitized'][sanitize_name(name)] = char
        if contains_cjk(name):
            ctx['by_cjk'][normalize_cjk_name(name)] = char


def _merge_characters(original_chars, all_incoming_schedules, session):
    """合併角色清單與排程"""
    en_data, cht_data = fetch_starrailres_data(session)
    wiki_char_cache = {}

    # 深拷貝以避免污染
    merged_chars = json.loads(json.dumps(original_chars))
    originally_preview_char_ids = {id(c) for c in merged_chars if c.get('isPreview')}
    reset_preview_char_ids = set()

    ctx = _build_char_lookup_context(merged_chars, en_data, cht_data)
    sanitized_en_dict = ctx['sanitized_en_dict']

    new_chars_added = []
    runs_added_log = []
    name_upgraded_log = []

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
        collab_date = sched.get('collab_date')
        is_preview = sched.get('is_preview', False)
        buff_type = normalize_buff_type(sched.get('buff_type')) if sched.get('buff_type') else None

        target_cid, target_name, path, elem = enrich_character_info(
            en_name, en_data, cht_data, wiki_char_cache, session, sanitized_en_dict
        )

        matched_char = _find_matched_char(en_name, target_cid, target_name, ctx)

        if matched_char:
            was_originally_preview = id(matched_char) in originally_preview_char_ids

            # 升級名稱
            if (matched_char.get('name') != target_name and target_name != en_name
                    and not contains_cjk(matched_char.get('name', '')) and contains_cjk(target_name)):
                name_upgraded_log.append(f"{matched_char['name']} ➡️ {target_name}")
                matched_char['name'] = target_name

            # 補全 CID（並同步更新查找索引）
            if target_cid and (not matched_char.get('cid') or matched_char.get('name') == target_name):
                matched_char['cid'] = target_cid
                _register_char_in_context(matched_char, ctx)

            # 補全命途/屬性
            if matched_char.get('path') in ["未知", "", None] and path != "未知":
                matched_char['path'] = path
            if matched_char.get('elem') in ["未知", "", None] and elem != "未知":
                matched_char['elem'] = elem

            # 預覽狀態同步：若官方正式實裝上線，移除預覽標記
            if not is_preview and matched_char.get('isPreview'):
                matched_char.pop('isPreview', None)
                print(f"  🎉 角色 [{matched_char.get('name')}] 已正式實裝，移除 isPreview 預覽標記！")

            # 聯動／常規排程同步
            if is_collab:
                if was_originally_preview or not matched_char.get('runs'):
                    matched_char['runs'] = []
                if matched_char.get('isCollab') != run:
                    matched_char['isCollab'] = run
                    runs_added_log.append(f"{matched_char['name']} 🤝 {run}（聯動）")
                if collab_date and matched_char.get('collabDate') != collab_date:
                    matched_char['collabDate'] = collab_date
            elif not matched_char.get('isCollab'):
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
                if collab_date:
                    new_char["collabDate"] = collab_date
            if is_preview:
                new_char["isPreview"] = True
            if buff_type:
                apply_buff_marker(new_char, run, buff_type)

            merged_chars.append(new_char)
            _register_char_in_context(new_char, ctx)
            new_chars_added.append(f"{target_name} ({path}/{elem}) ➡️ {run}" + (f"【{buff_type}】" if buff_type else ""))

    return merged_chars, new_chars_added, runs_added_log, name_upgraded_log


def apply_buff_schedules(merged_chars, buff_records, session=None, runs_added_log=None, en_data=None, cht_data=None, wiki_char_cache=None):
    """
    將 Fandom Wiki 強化排程套用至既有追蹤角色（僅豐富已有角色，絕不誤將常駐角色加入限定池）。
    回傳實際新增/更新的強化筆數。
    """
    if not buff_records or not merged_chars:
        return 0

    if en_data is None or cht_data is None:
        if session is not None:
            en_data, cht_data = fetch_starrailres_data(session)
        else:
            en_data, cht_data = {}, {}

    ctx = _build_char_lookup_context(merged_chars, en_data, cht_data)
    sanitized_en_dict = ctx['sanitized_en_dict']
    local_cache = wiki_char_cache if wiki_char_cache is not None else {}

    if session is not None:
        needed_wiki = []
        for rec in buff_records:
            en_name = str(rec.get('en_name', '')).strip()
            if not en_name or en_name in local_cache:
                continue
            target_cid, target_name, _, _ = resolve_local_character_info(en_name, en_data, cht_data, sanitized_en_dict)
            if not _find_matched_char(en_name, target_cid, target_name, ctx) and (target_name == en_name or not contains_cjk(target_name)):
                needed_wiki.append(en_name)
        if needed_wiki:
            local_cache.update(query_wiki_character_pages_batch(needed_wiki, session))

    updated_count = 0
    for rec in buff_records:
        en_name = str(rec.get('en_name', '')).strip()
        patch = str(rec.get('patch', '')).strip()
        buff_type = normalize_buff_type(rec.get('buff_type'))
        if not en_name or not patch or not buff_type:
            continue

        if session is not None:
            target_cid, target_name, _, _ = enrich_character_info(
                en_name, en_data, cht_data, local_cache, session, sanitized_en_dict
            )
        else:
            target_cid, target_name, _, _ = resolve_local_character_info(
                en_name, en_data, cht_data, sanitized_en_dict
            )

        matched_char = _find_matched_char(en_name, target_cid, target_name, ctx)
        if not matched_char:
            continue

        if apply_buff_marker(matched_char, patch, buff_type):
            updated_count += 1
            if runs_added_log is not None:
                runs_added_log.append(f"{matched_char['name']} 💠 {patch}【{buff_type}】")

    if updated_count > 0:
        print(f"  💠 自動同步強化紀錄：共套用 {updated_count} 筆強化資料")

    return updated_count


def apply_acquisition_schedules(
    merged_chars, acq_records, patches=None, session=None,
    runs_added_log=None, en_data=None, cht_data=None, wiki_char_cache=None
):
    """
    將 Fandom Wiki 角色取得方式排程（星緣相邀／聚靈鑄星／群星躍遷／動態未來商店或途徑）
    套用至既有追蹤角色（絕不誤將常駐 5 星加入追蹤清單，且保留既有手動版本不覆蓋）。
    回傳實際新增/更新的取得紀錄筆數。
    """
    if not acq_records or not merged_chars:
        return 0

    if en_data is None or cht_data is None:
        if session is not None:
            en_data, cht_data = fetch_starrailres_data(session)
        else:
            en_data, cht_data = {}, {}

    en_dict = en_data if isinstance(en_data, dict) else {}
    cht_dict = cht_data if isinstance(cht_data, dict) else {}
    ctx = _build_char_lookup_context(merged_chars, en_dict, cht_dict)
    sanitized_en_dict = ctx['sanitized_en_dict']
    local_cache = wiki_char_cache if wiki_char_cache is not None else {}

    patch_names_set = {
        p['patch'] for p in (patches or [])
        if isinstance(p, dict) and p.get('patch')
    }
    patch_order_map = {
        p['patch']: idx for idx, p in enumerate(patches or [])
        if isinstance(p, dict) and p.get('patch')
    }

    if session is not None:
        needed_wiki = []
        for rec in acq_records:
            en_name = str(rec.get('en_name', '')).strip()
            if not en_name or en_name in local_cache or is_standard_five_star(en_name):
                continue
            target_cid, target_name, _, _ = resolve_local_character_info(en_name, en_dict, cht_dict, sanitized_en_dict)
            if not _find_matched_char(en_name, target_cid, target_name, ctx) and (target_name == en_name or not contains_cjk(target_name)):
                needed_wiki.append(en_name)
        if needed_wiki:
            local_cache.update(query_wiki_character_pages_batch(needed_wiki, session))

    updated_count = 0
    for rec in acq_records:
        en_name = str(rec.get('en_name', '')).strip()
        patch = str(rec.get('patch', '')).strip()
        acq_type = normalize_acquisition_type(rec.get('acq_type'))
        if not en_name or not patch or not acq_type:
            continue
        if is_standard_five_star(en_name):
            continue
        if patch_names_set and patch not in patch_names_set:
            continue

        if session is not None:
            target_cid, target_name, _, _ = enrich_character_info(
                en_name, en_dict, cht_dict, local_cache, session, sanitized_en_dict
            )
        else:
            target_cid, target_name, _, _ = resolve_local_character_info(
                en_name, en_dict, cht_dict, sanitized_en_dict
            )

        if is_standard_five_star(en_name, target_cid):
            continue

        matched_char = _find_matched_char(en_name, target_cid, target_name, ctx)
        if not matched_char or is_standard_five_star(matched_char.get('name', ''), matched_char.get('cid', '')):
            continue

        if apply_acquisition_marker(matched_char, acq_type, patch, patch_order_map=patch_order_map):
            updated_count += 1
            if runs_added_log is not None:
                runs_added_log.append(f"{matched_char['name']} 🎁 {patch}【{acq_type}】")

    if updated_count > 0:
        print(f"  🎁 自動同步角色取得方式：共套用 {updated_count} 筆取得紀錄")

    return updated_count


def _extract_tracked_en_names(chars, en_data):
    """依據 StarRailRes 英文角色資料反查目前已追蹤角色的 Wiki 英文頁名清單"""
    if not chars:
        return []
    en_dict = en_data if isinstance(en_data, dict) else {}
    names = []
    seen = set()
    for c in chars:
        if not isinstance(c, dict) or c.get('isCollab') or is_standard_five_star(c.get('name', ''), c.get('cid', '')):
            continue
        cid = str(c.get('cid') or '').strip()
        en_name = en_dict.get(cid, {}).get('name') if cid and isinstance(en_dict.get(cid), dict) else None
        if not en_name:
            raw_name = str(c.get('name') or '').strip()
            if raw_name and not contains_cjk(raw_name):
                en_name = raw_name
        if en_name and en_name not in seen:
            seen.add(en_name)
            names.append(en_name)
    return names


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

    # 4.1 自動同步角色強化系統（Novaflare 礪爍新輝／Category:Affinitive Eidolons 奇緣星魂）
    buff_records = fetch_fandom_character_buffs(session, merged_patches)
    if buff_records:
        apply_buff_schedules(merged_chars, buff_records, session=session, runs_added_log=runs_added_log)

    # 4.2 自動同步角色取得方式（星緣相邀／聚靈鑄星／群星躍遷／動態未來商店與途徑）
    en_data_res, cht_data_res = fetch_starrailres_data(session)
    tracked_en_names = _extract_tracked_en_names(merged_chars, en_data_res)
    acq_records = fetch_fandom_acquisition_methods(session, merged_patches, target_en_names=tracked_en_names)
    if acq_records:
        apply_acquisition_schedules(
            merged_chars,
            acq_records,
            patches=merged_patches,
            session=session,
            runs_added_log=runs_added_log,
            en_data=en_data_res,
            cht_data=cht_data_res,
        )

    # 5. 執行五道安全防護檢驗門檻（+ 審計 6：動態命途／強化模式／取得方式，僅警示不熔斷）
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
