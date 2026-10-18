/* ==========================================================================
   崩壞：星穹鐵道 - 限定躍遷一覽表 主應用程式邏輯 (app.js)
   ========================================================================== */

let cachedTableCells = null;
let cachedRowData = new WeakMap();

// 轉義 HTML 特殊字元，避免 innerHTML 注入或屬性斷裂
const HTML_ESCAPE_MAP = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
    '/': '&#x2F;'
};

function escapeHtml(str) {
    if (str == null) return '';
    return String(str).replace(/[&<>"'/]/g, match => HTML_ESCAPE_MAP[match]);
}

// 🎨 本地 SVG Data URI 備用頭像產生器
function getFallbackAvatar(name) {
    const text = name ? name.trim().charAt(0) : '?';
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
        <rect width="64" height="64" rx="8" fill="#2a2a38"/>
        <text x="32" y="34" font-size="26" font-weight="bold" fill="#ffd700" dominant-baseline="central" text-anchor="middle" font-family="'Microsoft JhengHei', sans-serif">${text}</text>
    </svg>`;
    return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

/* ==========================================================================
   🧭 命途 / 💠 強化模式：動態聚合與「深空琉璃」通用降級（Fallback）
   - 篩選器選項一律由角色資料動態收集；PATH_ORDER / BUFF_ORDER 只決定已知值的排序。
   - 未註冊圖示或樣式的新值，自動降級為純文字琉璃標章與通用金色徽章。
   ========================================================================== */
const DEFAULT_PATH_ORDER = ["毀滅", "巡獵", "智識", "同諧", "虛無", "存護", "豐饒", "記憶", "歡愉"];
const DEFAULT_ELEM_ORDER = ["物理", "火", "冰", "雷", "風", "量子", "虛數", "未知"];
const STAR_RAIL_PATH_ICON_BASE = 'https://raw.githubusercontent.com/Mar-7th/StarRailRes/master/icon/path/';
const FALLBACK_BUFF_ICON = '◆';
const UNKNOWN_VALUE_LABEL = '未知';

function getPathOrder() {
    return (typeof PATH_ORDER !== 'undefined' && Array.isArray(PATH_ORDER)) ? PATH_ORDER : DEFAULT_PATH_ORDER;
}

function getPathIconMap() {
    return (typeof PATH_ICONS !== 'undefined' && PATH_ICONS) ? PATH_ICONS : null;
}

function getDefaultBuffType() {
    return (typeof DEFAULT_BUFF_TYPE !== 'undefined' && DEFAULT_BUFF_TYPE) ? DEFAULT_BUFF_TYPE : '礪爍新輝';
}

// 依註冊表排序：已知值（依註冊順序）→ 新值（依資料出現順序）→ 指定置底值（如「未知」）
function orderByRegistry(values, order, tailValues = []) {
    const registry = Array.isArray(order) ? order : [];
    const known = registry.filter(v => values.includes(v));
    const extra = values.filter(v => !registry.includes(v) && !tailValues.includes(v));
    const tail = tailValues.filter(v => values.includes(v) && !registry.includes(v));
    return [...known, ...extra, ...tail];
}

function collectFieldValues(chars, key, order, tailValues = []) {
    const seen = [];
    (chars || []).forEach(c => {
        const val = c ? c[key] : null;
        if (typeof val === 'string' && val.trim() && !seen.includes(val)) seen.push(val);
    });
    return orderByRegistry(seen, order, tailValues);
}

// 動態提取所有出現過的命途（含未預設的新命途）
function collectPathValues(chars) {
    return collectFieldValues(chars, 'path', getPathOrder(), [UNKNOWN_VALUE_LABEL]);
}

function collectElemValues(chars) {
    const order = (typeof ELEM_ORDER !== 'undefined' && Array.isArray(ELEM_ORDER)) ? ELEM_ORDER : DEFAULT_ELEM_ORDER;
    return collectFieldValues(chars, 'elem', order, [UNKNOWN_VALUE_LABEL]);
}

function isRegisteredPath(path) {
    if (!path) return false;
    const icons = getPathIconMap();
    return Boolean((icons && icons[path]) || getPathOrder().includes(path));
}

// 命途圖示：已註冊 → 專屬圖示；英文原名新命途 → 嘗試 CDN 慣例路徑（失敗時 onerror 降級）；其餘 → 無圖示
function getPathIconUrl(path) {
    if (!path) return '';
    const icons = getPathIconMap();
    if (icons && icons[path]) return icons[path];
    if (/^[A-Za-z][A-Za-z ]*$/.test(path)) {
        return `${STAR_RAIL_PATH_ICON_BASE}${path.replace(/\s+/g, '')}.png`;
    }
    return '';
}

// 解析角色強化紀錄：buffs 字串 = 預設模式；buffTypes[版本] 可覆寫為新模式；亦相容 { patch, type } 物件格式
function getCharBuffEntries(char) {
    if (!char || !Array.isArray(char.buffs)) return [];
    const typeMap = (char.buffTypes && typeof char.buffTypes === 'object') ? char.buffTypes : {};
    const defaultType = getDefaultBuffType();
    const entries = [];
    char.buffs.forEach(b => {
        let patch = b;
        let rawType = null;
        if (b && typeof b === 'object') {
            patch = b.patch;
            rawType = b.type;
        }
        if (!patch) return;
        if (!rawType && Object.prototype.hasOwnProperty.call(typeMap, patch)) {
            rawType = typeMap[patch];
        }
        const types = (Array.isArray(rawType) ? rawType : [rawType]).filter(Boolean);
        (types.length > 0 ? types : [defaultType]).forEach(type => {
            entries.push({ patch: String(patch), type: String(type) });
        });
    });
    return entries;
}

function getCharBuffTypes(char) {
    const types = [];
    getCharBuffEntries(char).forEach(e => {
        if (!types.includes(e.type)) types.push(e.type);
    });
    return types;
}

// 動態提取所有出現過的強化模式標籤
function collectBuffTypes(chars) {
    const seen = [];
    (chars || []).forEach(c => {
        getCharBuffTypes(c).forEach(t => {
            if (!seen.includes(t)) seen.push(t);
        });
    });
    const order = (typeof BUFF_ORDER !== 'undefined' && Array.isArray(BUFF_ORDER)) ? BUFF_ORDER : [getDefaultBuffType()];
    return orderByRegistry(seen, order);
}

function getBuffMeta(type) {
    const registry = (typeof BUFF_META !== 'undefined' && BUFF_META) ? BUFF_META : {};
    if (Object.prototype.hasOwnProperty.call(registry, type)) {
        const meta = registry[type] || {};
        return { icon: meta.icon || '▲', desc: meta.desc || '角色能力加強', isFallback: false };
    }
    if (type === getDefaultBuffType()) {
        return { icon: '▲', desc: '角色能力加強', isFallback: false };
    }
    return { icon: FALLBACK_BUFF_ICON, desc: '卡池強化', isFallback: true };
}

function buildBuffTitle(types) {
    return types.map(t => `【${t}】${getBuffMeta(t).desc}`).join('、');
}

function buildBuffBadgeHtml(types) {
    if (!types || types.length === 0) return '';
    const primary = types[0];
    const meta = getBuffMeta(primary);
    const title = escapeHtml(buildBuffTitle(types));
    if (!meta.isFallback && types.length === 1) {
        return `<span class="buff-badge" title="${title}">${escapeHtml(meta.icon)}</span>`;
    }
    const fallbackCls = meta.isFallback ? ' buff-badge-fallback' : '';
    const multiCls = types.length > 1 ? ' buff-badge-multi' : '';
    return `<span class="buff-badge${fallbackCls}${multiCls}" data-buff-type="${escapeHtml(primary)}" title="${title}">${escapeHtml(meta.icon)}</span>`;
}

// 純文字琉璃標章：取名稱首字（支援 CJK 與代理對）
function getBadgeGlyph(label) {
    const chars = Array.from(String(label == null ? '' : label).trim());
    return chars.length > 0 ? chars[0].toUpperCase() : '?';
}

function buildFallbackBadgeHtml(label, extraClass = '') {
    const safe = escapeHtml(label);
    return `<span class="icon-fallback-badge${extraClass ? ' ' + extraClass : ''}" title="${safe}" aria-label="${safe}" data-fallback-label="${safe}">${escapeHtml(getBadgeGlyph(label))}</span>`;
}

function createFallbackBadgeElement(label, extraClass = '') {
    const span = document.createElement('span');
    span.className = `icon-fallback-badge${extraClass ? ' ' + extraClass : ''}`;
    span.textContent = getBadgeGlyph(label);
    span.title = label || '';
    span.setAttribute('aria-label', label || '');
    span.dataset.fallbackLabel = label || '';
    return span;
}

// 🖼️ 圖示載入失敗（CDN 尚無圖示）時，原地替換為純文字琉璃標章
function handleIconError(img) {
    if (!img || img._hsrFallbackApplied) return null;
    img._hsrFallbackApplied = true;
    img.onerror = null;
    const label = img.getAttribute('data-fallback-label') || img.getAttribute('alt') || img.getAttribute('title') || '';
    const extraClass = img.getAttribute('data-fallback-class') || '';
    const badge = createFallbackBadgeElement(label, extraClass);
    if (img.parentNode) {
        img.parentNode.replaceChild(badge, img);
    }
    return badge;
}

if (typeof window !== 'undefined') {
    window.handleIconError = handleIconError;
}

function buildPathIconHtml(path) {
    if (!path) return '<div class="char-path-icon"></div>';
    const iconUrl = getPathIconUrl(path);
    if (!iconUrl) return buildFallbackBadgeHtml(path, 'char-path-icon path-icon-fallback');
    const safe = escapeHtml(path);
    return `<img src="${iconUrl}" class="char-path-icon" title="${safe}" alt="${safe}" data-fallback-class="char-path-icon path-icon-fallback" onerror="handleIconError(this)">`;
}

// 💠 強化模式按鈕：依資料動態渲染
function getBuffModeButtons() {
    if (typeof document === 'undefined') return [];
    const buttons = Array.from(document.querySelectorAll('.buff-mode-btn'));
    const legacy = document.getElementById('buff-toggle-btn');
    if (legacy && !buttons.includes(legacy)) buttons.push(legacy);
    return buttons;
}

function getButtonBuffType(btn) {
    return (btn && btn.dataset && btn.dataset.buffType) ? btn.dataset.buffType : getDefaultBuffType();
}

function getActiveBuffTypes() {
    return getBuffModeButtons().filter(b => b.classList.contains('active')).map(getButtonBuffType);
}

function setButtonActive(btn, isActive) {
    btn.classList.toggle('active', Boolean(isActive));
    btn.setAttribute('aria-pressed', String(Boolean(isActive)));
}

function buildBuffModeButton(type, isActive) {
    const meta = getBuffMeta(type);
    const isDefault = type === getDefaultBuffType();
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = `toggle-btn buff-mode-btn${meta.isFallback ? ' buff-mode-fallback' : ''}`;
    if (isDefault) btn.id = 'buff-toggle-btn';
    btn.dataset.buffType = type;
    btn.setAttribute('data-tooltip', isDefault ? '僅顯示加強過的角色' : `僅顯示【${type}】強化過的角色`);
    setButtonActive(btn, isActive);

    const icon = document.createElement('span');
    icon.className = 'toggle-icon';
    icon.textContent = meta.icon;
    const label = document.createElement('span');
    label.className = 'buff-mode-label';
    label.textContent = type;

    btn.appendChild(icon);
    btn.appendChild(document.createTextNode(' '));
    btn.appendChild(label);
    return btn;
}

function renderBuffModeButtons(chars) {
    const container = document.getElementById('buff-mode-container');
    if (!container) return;
    const detected = collectBuffTypes(chars);
    const types = detected.length > 0 ? detected : [getDefaultBuffType()];
    const activeTypes = new Set(getActiveBuffTypes());
    const fragment = document.createDocumentFragment();
    types.forEach(type => fragment.appendChild(buildBuffModeButton(type, activeTypes.has(type))));
    container.replaceChildren(fragment);
}

// 依 URL / 程式狀態設定強化按鈕：types 為 null 時代表「預設模式」（舊版 buff=1）
function applyBuffSelection(onlyBuffs, types) {
    const buttons = getBuffModeButtons();
    if (buttons.length === 0) return;
    if (Array.isArray(types) && types.length > 0) {
        const typeSet = new Set(types);
        buttons.forEach(btn => setButtonActive(btn, typeSet.has(getButtonBuffType(btn))));
        return;
    }
    const defaultType = getDefaultBuffType();
    const target = onlyBuffs
        ? (buttons.find(btn => getButtonBuffType(btn) === defaultType) || buttons[0])
        : null;
    buttons.forEach(btn => setButtonActive(btn, btn === target));
}

// 格式化表頭日期
function formatHeaderDate(dateStr) {
    const parts = dateStr.split('/');
    if (parts.length === 3) {
        const yyyy = '20' + parts[0];
        const mmdd = `${parts[1]}/${parts[2]}`;
        return `${yyyy}<br>${mmdd}`;
    }
    return dateStr;
}

// 自動對照 PATCH_DATA 與今日日期（台灣時區 UTC+8），找出當前進行中的卡池小版本名稱
function getCurrentPatchName() {
    if (typeof PATCH_DATA === 'undefined' || !PATCH_DATA || PATCH_DATA.length === 0) return "";
    const twNow = new Date(new Date().getTime() + 8 * 3600 * 1000);
    const todayZero = new Date(twNow.getUTCFullYear(), twNow.getUTCMonth(), twNow.getUTCDate());
    let currentPatch = PATCH_DATA[0].patch;
    
    for (let i = 0; i < PATCH_DATA.length; i++) {
        const parts = (PATCH_DATA[i].date || "").split('/');
        if (parts.length === 3) {
            const fullYear = 2000 + parseInt(parts[0], 10);
            const month = parseInt(parts[1], 10) - 1;
            const day = parseInt(parts[2], 10);
            const patchDate = new Date(fullYear, month, day);
            
            if (patchDate <= todayZero) {
                currentPatch = PATCH_DATA[i].patch;
            } else {
                break;
            }
        }
    }
    return currentPatch;
}

// 🔍 取得角色最早登場的小版本名稱
function getCharEarliestPatch(char, patchesList, patchIndexMap) {
    if (char.isCollab) {
        return char.isCollab;
    }
    if (char.runs && char.runs.length > 0) {
        const runIndices = char.runs.map(p => patchIndexMap ? (patchIndexMap.has(p) ? patchIndexMap.get(p) : -1) : patchesList.indexOf(p)).filter(idx => idx !== -1);
        if (runIndices.length > 0) {
            return patchesList[Math.min(...runIndices)];
        }
    }
    if (char.term && char.term.patch) {
        return char.term.patch;
    }
    return null;
}

// 🔍 計算角色的精確登場小版本 (如：4.4上)
function getCharDebutVersion(char, patchesList, patchIndexMap) {
    return getCharEarliestPatch(char, patchesList, patchIndexMap) || "未登場";
}

// 🔍 智慧計算角色的首次登場「大版本號」（如：1.x, 2.x, 3.x）
function getCharDebutMajorVersion(char, patchesList, patchIndexMap) {
    const earliestPatch = getCharEarliestPatch(char, patchesList, patchIndexMap);
    if (earliestPatch) {
        return `${earliestPatch.split('.')[0]}.x`;
    }
    return "未知";
}

function getPatchIndex(patch, patchesList, patchIndexMap) {
    return patchIndexMap ? (patchIndexMap.has(patch) ? patchIndexMap.get(patch) : -1) : patchesList.indexOf(patch);
}

function getTermStatus(char, validEndIdx, patchesList, patchIndexMap) {
    if (char.term && char.term.patch) {
        const termIdx = getPatchIndex(char.term.patch, patchesList, patchIndexMap);
        if (termIdx !== -1 && termIdx <= validEndIdx) {
            return {
                isTermActive: true,
                validEndIdx: termIdx,
                termLabel: char.term.type === 'pool' ? '星緣' : '聚靈'
            };
        }
    }
    return { isTermActive: false, validEndIdx, termLabel: '' };
}

function mergeContinuousEvents(indices) {
    const events = [];
    if (indices.length > 0) {
        let currentEvent = { start: indices[0], end: indices[0] };
        for (let i = 1; i < indices.length; i++) {
            if (indices[i] === currentEvent.end + 1) {
                currentEvent.end = indices[i];
            } else {
                events.push(currentEvent);
                currentEvent = { start: indices[i], end: indices[i] };
            }
        }
        events.push(currentEvent);
    }
    return events;
}

function calculateGaps(events) {
    const gaps = [];
    for (let i = 1; i < events.length; i++) {
        gaps.push(events[i].start - events[i - 1].end - 1);
    }
    return gaps;
}

// 📊 智慧統計分析演算法 (含連續小版本自動合併邏輯)
function calculateCharStats(char, patchesList, activePatchName, patchIndexMap) {
    if (char.isCollab) {
        return { isCollab: true };
    }

    const currentPatchIdx = getPatchIndex(activePatchName, patchesList, patchIndexMap);
    let initialValidEndIdx = currentPatchIdx !== -1 ? currentPatchIdx : patchesList.length - 1;

    const termStatus = getTermStatus(char, initialValidEndIdx, patchesList, patchIndexMap);
    const validEndIdx = termStatus.validEndIdx;

    const indices = (char.runs || [])
        .map(p => getPatchIndex(p, patchesList, patchIndexMap))
        .filter(idx => idx !== -1 && idx <= validEndIdx)
        .sort((a, b) => a - b);

    // 將連續小版本 (如 4.1上 + 4.1下) 自動合併為「同一次/同期 UP 活動」
    const events = mergeContinuousEvents(indices);
    const totalRuns = events.length;

    if (totalRuns === 0) {
        return { totalRuns: '0', currentGap: '-', maxGap: '-', isOverdue: false, isTermActive: false, termLabel: '' };
    }

    const lastEvent = events[events.length - 1];
    const currentGap = validEndIdx - lastEvent.end;
    const gaps = calculateGaps(events);
    const maxHistoricalGap = gaps.length > 0 ? Math.max(...gaps) : '-';

    if (termStatus.isTermActive) {
        return {
            totalRuns: `${totalRuns}`,
            currentGap: `已加入${termStatus.termLabel}`,
            maxGap: `${maxHistoricalGap}`,
            isOverdue: false,
            isTermActive: true,
            termLabel: termStatus.termLabel
        };
    }

    return {
        totalRuns: `${totalRuns}`,
        currentGap: `${currentGap}`,
        maxGap: `${maxHistoricalGap}`,
        isOverdue: maxHistoricalGap !== '-' && currentGap > maxHistoricalGap,
        isTermActive: false,
        termLabel: ''
    };
}

// 狀態控制變數
let isCharAscending = false;   // 角色順序 (false: 降冪 ▼, true: 升冪 ▲)
let isPatchAscending = false;  // 版本順序 (false: 最新在左 ◀, true: 最舊在左 ▶)
let charSortMode = 'debut-desc'; // 角色排序模式 ('debut-desc' | 'debut-asc' | 'runs-desc' | 'runs-asc' | 'wait-desc' | 'wait-asc')
let isShowPreview = localStorage.getItem('hsr_show_preview') !== null ? (localStorage.getItem('hsr_show_preview') === 'true') : true;
let isRestoringUrl = false;
let activePopoverCell = null;
let isPopoverPinned = false;

const VALID_SORT_MODES = new Set(['debut-desc', 'debut-asc', 'runs-desc', 'runs-asc', 'wait-desc', 'wait-asc']);
const VALID_SORT_FIELDS = new Set(['debut', 'runs', 'wait']);

function parseSortMode(mode = charSortMode, fallbackAsc = isCharAscending) {
    if (typeof mode === 'string' && VALID_SORT_MODES.has(mode)) {
        const [field, dir] = mode.split('-');
        return { field, dir, isAsc: dir === 'asc', mode };
    }
    if (typeof mode === 'string' && VALID_SORT_FIELDS.has(mode)) {
        const dir = fallbackAsc ? 'asc' : 'desc';
        return { field: mode, dir, isAsc: Boolean(fallbackAsc), mode: `${mode}-${dir}` };
    }
    const dir = fallbackAsc ? 'asc' : 'desc';
    return { field: 'debut', dir, isAsc: Boolean(fallbackAsc), mode: `debut-${dir}` };
}

function getSortDescription(mode = charSortMode, isAsc = isCharAscending) {
    const parsed = parseSortMode(mode, isAsc);
    if (parsed.mode === 'debut-desc') return '登場順序 (最新優先)';
    if (parsed.mode === 'debut-asc') return '登場順序 (開服最舊優先)';
    if (parsed.mode === 'wait-desc') return '上次復刻 (最久未復刻優先)';
    if (parsed.mode === 'wait-asc') return '上次復刻 (最近剛復刻優先)';
    if (parsed.mode === 'runs-desc') return 'UP次數 (次數最多優先)';
    if (parsed.mode === 'runs-asc') return 'UP次數 (次數最少優先)';
    return '角色排序';
}

function getSortCharBtnLabel(mode = charSortMode, isAsc = isCharAscending) {
    const parsed = parseSortMode(mode, isAsc);
    const arrow = parsed.isAsc ? '▲' : '▼';
    if (parsed.field === 'wait') return `復刻 ${arrow}`;
    if (parsed.field === 'runs') return `UP數 ${arrow}`;
    return `登場 ${arrow}`;
}

function buildCharSortMenuHtml(currentMode = charSortMode, isAsc = isCharAscending) {
    const parsed = parseSortMode(currentMode, isAsc);
    const activeMode = parsed.mode;

    const renderOption = (mode, label, dir) => {
        const isActive = activeMode === mode;
        return `<button type="button" class="sort-option-btn${isActive ? ' active' : ''}" data-sort-mode="${mode}">
            <span class="sort-opt-name">${escapeHtml(label)}</span>
            <span class="sort-opt-dir">${dir}</span>
        </button>`;
    };

    return `
        <div class="sort-popover-group">
            <div class="sort-group-title">登場順序</div>
            <div class="sort-options-row">
                ${renderOption('debut-desc', '最新', '▼')}
                ${renderOption('debut-asc', '最舊', '▲')}
            </div>
        </div>
        <div class="sort-popover-group">
            <div class="sort-group-title">上次復刻</div>
            <div class="sort-options-row">
                ${renderOption('wait-desc', '最久未復刻', '▼')}
                ${renderOption('wait-asc', '最近復刻', '▲')}
            </div>
        </div>
        <div class="sort-popover-group">
            <div class="sort-group-title">UP 次數</div>
            <div class="sort-options-row">
                ${renderOption('runs-desc', '最多', '▼')}
                ${renderOption('runs-asc', '最少', '▲')}
            </div>
        </div>
    `;
}

function ensureCharSortPopover() {
    let popover = document.getElementById('char-sort-popover');
    if (!popover && typeof document !== 'undefined' && document.body) {
        popover = document.createElement('div');
        popover.id = 'char-sort-popover';
        popover.className = 'char-sort-popover';
        popover.setAttribute('role', 'menu');
        popover.setAttribute('aria-hidden', 'true');
        document.body.appendChild(popover);
    }
    return popover;
}

function showCharSortMenu(anchorBtn) {
    const popover = ensureCharSortPopover();
    if (!popover || !anchorBtn) return;

    popover.innerHTML = buildCharSortMenuHtml(charSortMode, isCharAscending);
    popover.classList.add('show');
    popover.setAttribute('aria-hidden', 'false');

    if (typeof anchorBtn.getBoundingClientRect === 'function') {
        const rect = anchorBtn.getBoundingClientRect();
        const popWidth = popover.offsetWidth || 180;
        const popHeight = popover.offsetHeight || 135;
        const vw = typeof window !== 'undefined' ? (window.innerWidth || 1024) : 1024;
        const vh = typeof window !== 'undefined' ? (window.innerHeight || 768) : 768;

        let left = rect.left;
        if (left + popWidth > vw - 8) {
            left = Math.max(8, vw - popWidth - 8);
        }
        let top = rect.bottom + 4;
        if (top + popHeight > vh - 8) {
            top = Math.max(8, rect.top - popHeight - 4);
        }
        popover.style.left = `${Math.round(left)}px`;
        popover.style.top = `${Math.round(top)}px`;
    }
}

function hideCharSortMenu() {
    const popover = document.getElementById('char-sort-popover');
    if (popover) {
        popover.classList.remove('show');
        popover.setAttribute('aria-hidden', 'true');
    }
}

function toggleCharSortMenu(anchorBtn) {
    const popover = ensureCharSortPopover();
    if (!popover) return;
    if (popover.classList.contains('show')) {
        hideCharSortMenu();
    } else {
        showCharSortMenu(anchorBtn);
    }
}

function updateSortControlsUI() {
    const parsed = parseSortMode(charSortMode, isCharAscending);
    const sortSelect = document.getElementById('char-sort-select');
    const sortDirBtn = document.getElementById('char-sort-dir-btn');
    const sortWrap = document.getElementById('char-sort-wrap') || sortSelect?.closest('.sort-select-wrap');
    const sortCharBtn = document.getElementById('sort-char-btn');

    if (sortSelect) {
        sortSelect.value = parsed.field;
        sortSelect.classList.toggle('active', parsed.mode !== 'debut-desc');
    }
    if (sortDirBtn) {
        sortDirBtn.textContent = parsed.isAsc ? '▲' : '▼';
    }
    if (sortWrap) {
        sortWrap.classList.toggle('active', parsed.mode !== 'debut-desc');
    }
    if (sortCharBtn) {
        sortCharBtn.textContent = getSortCharBtnLabel(charSortMode, isCharAscending);
        sortCharBtn.classList.toggle('active', parsed.mode !== 'debut-desc');
        sortCharBtn.removeAttribute('title');
    }

    const popover = document.getElementById('char-sort-popover');
    if (popover && popover.classList.contains('show')) {
        popover.querySelectorAll('.sort-option-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.sortMode === parsed.mode);
        });
    }
}

// 🔀 角色多維度排序演算法（登場順序／UP次數／上次復刻時間）
function sortCharacters(characters, sortMode, patchesList, activePatchName, patchIndexMap) {
    if (!Array.isArray(characters) || characters.length === 0) return [];
    const { mode } = parseSortMode(sortMode, isCharAscending);

    if (mode === 'debut-asc') {
        return [...characters];
    }
    if (mode === 'debut-desc') {
        return [...characters].reverse();
    }

    const enriched = characters.map((char, origIdx) => {
        const stats = calculateCharStats(char, patchesList || [], activePatchName || '', patchIndexMap);
        const totalRunsNum = stats.isCollab ? 1 : (parseInt(stats.totalRuns, 10) || 0);
        const isNumericWait = !char.isPreview && !stats.isCollab && !stats.isTermActive && stats.currentGap !== '-' && !isNaN(parseInt(stats.currentGap, 10));
        const currentGapNum = isNumericWait ? parseInt(stats.currentGap, 10) : -1;
        return { char, origIdx, stats, totalRunsNum, isNumericWait, currentGapNum };
    });

    if (mode === 'wait-desc') {
        enriched.sort((a, b) => {
            const getBucket = (item) => {
                if (item.isNumericWait) return 0;
                if (item.stats.isTermActive) return 1;
                if (item.stats.isCollab) return 2;
                return 3;
            };
            const bucketA = getBucket(a);
            const bucketB = getBucket(b);
            if (bucketA !== bucketB) return bucketA - bucketB;
            if (bucketA === 0) {
                if (b.currentGapNum !== a.currentGapNum) return b.currentGapNum - a.currentGapNum;
                if (Boolean(b.stats.isOverdue) !== Boolean(a.stats.isOverdue)) return b.stats.isOverdue ? 1 : -1;
            }
            return a.origIdx - b.origIdx;
        });
    } else if (mode === 'wait-asc') {
        enriched.sort((a, b) => {
            const getBucket = (item) => {
                if (item.isNumericWait) return 0;
                if (item.stats.isTermActive) return 1;
                if (item.stats.isCollab) return 2;
                return 3;
            };
            const bucketA = getBucket(a);
            const bucketB = getBucket(b);
            if (bucketA !== bucketB) return bucketA - bucketB;
            if (bucketA === 0) {
                if (a.currentGapNum !== b.currentGapNum) return a.currentGapNum - b.currentGapNum;
            }
            return b.origIdx - a.origIdx;
        });
    } else if (mode === 'runs-desc') {
        enriched.sort((a, b) => {
            const previewA = Boolean(a.char.isPreview) ? 1 : 0;
            const previewB = Boolean(b.char.isPreview) ? 1 : 0;
            if (previewA !== previewB) return previewA - previewB;
            if (b.totalRunsNum !== a.totalRunsNum) return b.totalRunsNum - a.totalRunsNum;
            if (b.currentGapNum !== a.currentGapNum) return b.currentGapNum - a.currentGapNum;
            return a.origIdx - b.origIdx;
        });
    } else if (mode === 'runs-asc') {
        enriched.sort((a, b) => {
            const bucketA = (a.char.isPreview || a.totalRunsNum === 0) ? 1 : 0;
            const bucketB = (b.char.isPreview || b.totalRunsNum === 0) ? 1 : 0;
            if (bucketA !== bucketB) return bucketA - bucketB;
            if (a.totalRunsNum !== b.totalRunsNum) return a.totalRunsNum - b.totalRunsNum;
            if (b.currentGapNum !== a.currentGapNum) return b.currentGapNum - a.currentGapNum;
            return a.origIdx - b.origIdx;
        });
    }

    return enriched.map(item => item.char);
}

// 🔗 解析網址列 Query Params 為狀態物件
function parseUrlState(searchStr) {
    const rawSearch = typeof searchStr === 'string'
        ? searchStr
        : (typeof window !== 'undefined' && window.location ? window.location.search : '');
    const params = new URLSearchParams(rawSearch);

    const parseList = (key) => {
        const val = params.get(key);
        return val ? val.split(',').map(s => s.trim()).filter(Boolean) : [];
    };

    const rawSort = params.get('sort');
    const charSort = rawSort && VALID_SORT_MODES.has(rawSort) ? rawSort : null;
    const rawPsort = params.get('psort');
    const patchSortAsc = rawPsort !== null ? (rawPsort === 'asc' || rawPsort === '1' || rawPsort === 'true') : null;
    const rawPreview = params.get('preview');
    const showPreview = rawPreview !== null ? (rawPreview !== '0' && rawPreview !== 'false') : null;

    // 💠 buff=1 / true：舊版語意（預設強化模式）；buff=模式A,模式B：指定強化模式（支援未來新模式）
    const rawBuff = params.get('buff');
    let onlyBuffs = false;
    let buffTypes = null;
    if (rawBuff === '1' || rawBuff === 'true') {
        onlyBuffs = true;
    } else if (rawBuff && rawBuff !== '0' && rawBuff !== 'false') {
        buffTypes = parseList('buff');
        onlyBuffs = buffTypes.length > 0;
    }

    const state = {
        versions: parseList('ver'),
        paths: parseList('path'),
        elems: parseList('elem'),
        types: parseList('type'),
        keyword: params.get('q') ? params.get('q').trim() : '',
        onlyBuffs,
        showPreview,
        charSort,
        patchSortAsc
    };
    if (buffTypes && buffTypes.length > 0) {
        state.buffTypes = buffTypes;
    }
    return state;
}

// 🔗 根據當前篩選與排序狀態建構 Query String
function buildUrlSearchParams(filterState, extraState = {}) {
    const params = new URLSearchParams();
    if (!filterState) return '';

    if (filterState.selectedVersions && filterState.selectedVersions.length > 0) {
        params.set('ver', filterState.selectedVersions.join(','));
    }
    if (filterState.selectedPaths && filterState.selectedPaths.length > 0) {
        params.set('path', filterState.selectedPaths.join(','));
    }
    if (filterState.selectedElems && filterState.selectedElems.length > 0) {
        params.set('elem', filterState.selectedElems.join(','));
    }
    if (filterState.selectedTypes && filterState.selectedTypes.length > 0) {
        params.set('type', filterState.selectedTypes.join(','));
    }
    if (filterState.keyword) {
        params.set('q', filterState.keyword);
    }
    if (filterState.onlyBuffs) {
        const buffTypes = Array.isArray(filterState.selectedBuffs) ? filterState.selectedBuffs : [];
        const isDefaultOnly = buffTypes.length === 0 || (buffTypes.length === 1 && buffTypes[0] === getDefaultBuffType());
        params.set('buff', isDefaultOnly ? '1' : buffTypes.join(','));
    }

    const mode = extraState.charSortMode !== undefined ? extraState.charSortMode : charSortMode;
    if (mode && mode !== 'debut-desc') {
        params.set('sort', mode);
    }

    const patchAsc = extraState.isPatchAscending !== undefined ? extraState.isPatchAscending : isPatchAscending;
    if (patchAsc) {
        params.set('psort', 'asc');
    }

    return params.toString();
}

function syncStateToUrl() {
    if (isRestoringUrl) return;
    if (typeof window === 'undefined' || !window.history || typeof window.history.replaceState !== 'function') return;

    const state = getFilterState();
    const queryStr = buildUrlSearchParams(state, { charSortMode, isPatchAscending });
    const pathname = window.location ? window.location.pathname : '';
    const hash = window.location ? (window.location.hash || '') : '';
    const newUrl = `${pathname}${queryStr ? '?' + queryStr : ''}${hash}`;
    window.history.replaceState(null, '', newUrl);
}

function restoreStateFromUrl(searchStr) {
    const parsed = parseUrlState(searchStr);
    isRestoringUrl = true;
    try {
        if (parsed.charSort) {
            const sortInfo = parseSortMode(parsed.charSort);
            charSortMode = sortInfo.mode;
            isCharAscending = sortInfo.isAsc;
        } else {
            charSortMode = isCharAscending ? 'debut-asc' : 'debut-desc';
        }
        if (parsed.patchSortAsc !== null) {
            isPatchAscending = parsed.patchSortAsc;
        }
        if (parsed.showPreview !== null) {
            isShowPreview = parsed.showPreview;
        }

        renderTable();

        if (parsed.versions.length > 0) {
            const verSet = new Set(parsed.versions);
            document.querySelectorAll('.version-item').forEach(el => {
                el.checked = verSet.has(el.value);
            });
        }
        if (parsed.paths.length > 0) {
            const pathSet = new Set(parsed.paths);
            document.querySelectorAll('.path-item').forEach(el => {
                el.checked = pathSet.has(el.value);
            });
        }
        if (parsed.elems.length > 0) {
            const elemSet = new Set(parsed.elems);
            document.querySelectorAll('.elem-item').forEach(el => {
                el.checked = elemSet.has(el.value);
            });
        }
        if (parsed.types.length > 0) {
            const typeSet = new Set(parsed.types);
            document.querySelectorAll('.type-item').forEach(el => {
                el.checked = typeSet.has(el.value);
            });
        }

        const searchInput = document.getElementById('char-search-input');
        if (searchInput && parsed.keyword !== '') {
            searchInput.value = parsed.keyword;
        }

        applyBuffSelection(parsed.onlyBuffs, parsed.buffTypes || null);

        updateSortControlsUI();
    } finally {
        isRestoringUrl = false;
    }
    applyFilters();
}

// 主表格渲染與初始化
async function initTracker() {
    // 1. 解析網址參數並優先同步渲染表格與綁定事件，避免網路請求阻塞首屏畫面
    restoreStateFromUrl();
    setupEventListeners();

    // 2. 優先讀取 characters.js 匯出的 LAST_UPDATED 常數，免除重複 fetch
    const updateDateEl = document.getElementById('update-date-text');
    if (typeof LAST_UPDATED !== 'undefined' && LAST_UPDATED) {
        if (updateDateEl) updateDateEl.textContent = LAST_UPDATED;
    } else {
        try {
            const resDate = await fetch('js/characters.js');
            if (resDate && resDate.ok) {
                const text = await resDate.text();
                const match = text.match(/\/\/\s*更新日期[:：]\s*([0-9\/]+)/);
                if (updateDateEl) {
                    updateDateEl.textContent = (match && match[1]) ? match[1] : "未知";
                }
            } else if (updateDateEl) {
                updateDateEl.textContent = "未知";
            }
        } catch (error) {
            console.warn("無法讀取本地更新日期:", error);
            if (updateDateEl) updateDateEl.textContent = "未知";
        }
    }

    // 3. 背景非同步載入 StarRailRes 頭像庫並局部更新 DOM
    try {
        const res = await fetch('https://raw.githubusercontent.com/Mar-7th/StarRailRes/master/index_new/cht/characters.json');
        if (res && res.ok) {
            const data = await res.json();
            const normalize = (n) => n.replace(/[•·]/g, '').replace(/刹/g, '剎');
            const avatarMap = {};
            
            for (const id in data) {
                const officialName = data[id].name;
                const imgUrl = `https://raw.githubusercontent.com/Mar-7th/StarRailRes/master/${data[id].icon}`;
                avatarMap[normalize(officialName)] = imgUrl;
                if (officialName.includes('&')) {
                    avatarMap[normalize(officialName.split('&')[0])] = imgUrl;
                }
            }

            const updatedAvatarByName = new Map();
            RAW_CHARACTERS.forEach(char => {
                const searchName = normalize(char.name);
                if (avatarMap[searchName] && !char.avatar) {
                    char.avatar = avatarMap[searchName];
                }
                if (char.avatar) {
                    updatedAvatarByName.set(char.name, char.avatar);
                }
            });

            const table = document.getElementById('tracker');
            if (table && updatedAvatarByName.size > 0) {
                table.querySelectorAll('img.char-avatar, img.grid-avatar').forEach(img => {
                    const newSrc = updatedAvatarByName.get(img.alt);
                    if (newSrc && img.getAttribute('src') !== newSrc) {
                        img.src = newSrc;
                    }
                });
            }
        }
    } catch (error) {
        console.warn("頭像庫連線失敗，將使用備用頭像：", error);
    }
}

// 🔄 核心渲染表格邏輯
function updateTableColumnIndices(table) {
    cachedTableCells = null;
    const rows = table.rows;
    const rowLen = rows.length;
    for (let r = 0; r < rowLen; r++) {
        let colIdx = 0;
        const cells = rows[r].cells;
        const cellLen = cells.length;
        for (let c = 0; c < cellLen; c++) {
            const cell = cells[c];
            const span = cell.colSpan || 1;
            cell.dataset.startCol = colIdx;
            cell.dataset.endCol = colIdx + span - 1;
            cell._startCol = colIdx;
            cell._endCol = colIdx + span - 1;
            colIdx += span;
        }
    }
}

function updateJumpButtons(jumpLatestBtn, jumpOldestBtn) {
    if (jumpLatestBtn && jumpOldestBtn) {
        if (!isPatchAscending) {
            jumpLatestBtn.textContent = '◀ 最新';
            jumpLatestBtn.title = '快速滾動至最新卡池 (最左側)';
            jumpOldestBtn.textContent = '最舊 ▶';
            jumpOldestBtn.title = '快速滾動至最舊卡池 (最右側)';
        } else {
            jumpLatestBtn.textContent = '◀ 最舊';
            jumpLatestBtn.title = '快速滾動至最舊卡池 (最左側)';
            jumpOldestBtn.textContent = '最新 ▶';
            jumpOldestBtn.title = '快速滾動至最新卡池 (最右側)';
        }
    }
}

function renderFilters(activeCharacters, patchesList, patchIndexMap) {
    const versionSet = new Set();
    activeCharacters.forEach(char => {
        const majorVer = getCharDebutMajorVersion(char, patchesList, patchIndexMap);
        if (majorVer !== "未知") versionSet.add(majorVer);
    });
    const uniqueVersions = Array.from(versionSet).sort((a, b) => parseFloat(a) - parseFloat(b));

    const uniquePaths = collectPathValues(activeCharacters);
    const uniqueElems = collectElemValues(activeCharacters);

    const currentCheckedVersions = new Set(Array.from(document.querySelectorAll('.version-item:checked')).map(i => i.value));
    const currentCheckedPaths = new Set(Array.from(document.querySelectorAll('.path-item:checked')).map(i => i.value));
    const currentCheckedElems = new Set(Array.from(document.querySelectorAll('.elem-item:checked')).map(i => i.value));

    const versionContainer = document.getElementById('version-items-container');
    if (versionContainer) {
        const fragment = document.createDocumentFragment();
        uniqueVersions.forEach(v => {
            const label = document.createElement('label');
            const input = document.createElement('input');
            input.type = 'checkbox';
            input.className = 'version-item';
            input.value = v;
            if (currentCheckedVersions.has(v)) {
                input.checked = true;
            }
            label.appendChild(input);
            label.appendChild(document.createTextNode(` ${v}`));
            fragment.appendChild(label);
        });
        versionContainer.replaceChildren(fragment);
    }

    function renderIconFilterItems(containerId, items, itemClass, checkedSet, iconMap) {
        const container = document.getElementById(containerId);
        if (!container) return;
        const fragment = document.createDocumentFragment();
        items.forEach(val => {
            const label = document.createElement('label');
            const input = document.createElement('input');
            input.type = 'checkbox';
            input.className = itemClass;
            input.value = val;
            if (checkedSet.has(val)) {
                input.checked = true;
            }
            label.appendChild(input);
            label.appendChild(document.createTextNode(' '));

            const iconUrl = (iconMap && iconMap[val]) ? iconMap[val] : "";
            if (iconUrl) {
                const img = document.createElement('img');
                img.src = iconUrl;
                img.alt = val;
                img.title = val;
                img.dataset.fallbackLabel = val;
                img.dataset.fallbackClass = 'filter-icon-fallback';
                img.style.width = '16px';
                img.style.height = '16px';
                img.style.flexShrink = '0';
                img.style.filter = 'drop-shadow(0 0 1.5px rgba(0,0,0,0.9))';
                img.setAttribute('onerror', 'handleIconError(this)');
                img.onerror = function () { handleIconError(this); };
                label.appendChild(img);
            } else if (iconMap) {
                label.appendChild(createFallbackBadgeElement(val, 'filter-icon-fallback'));
            }
            label.appendChild(document.createTextNode(val));
            fragment.appendChild(label);
        });
        container.replaceChildren(fragment);
    }

    renderIconFilterItems(
        'path-items-container',
        uniquePaths,
        'path-item',
        currentCheckedPaths,
        typeof PATH_ICONS !== 'undefined' ? PATH_ICONS : null
    );
    renderIconFilterItems(
        'elem-items-container',
        uniqueElems,
        'elem-item',
        currentCheckedElems,
        typeof ELEM_ICONS !== 'undefined' ? ELEM_ICONS : null
    );

    renderBuffModeButtons(activeCharacters);

    const typeContainer = document.getElementById('type-items-container');
    if (typeContainer && typeContainer.children.length === 0) {
        typeContainer.innerHTML = `
            <label><input type="checkbox" class="type-item" value="normal"> 限定躍遷</label>
            <label class="type-desc-label">
                <input type="checkbox" class="type-item" value="pool">
                <span class="label-stack">
                    <span class="label-title">星緣相邀</span>
                    <span class="label-sub">加入非UP自選池</span>
                </span>
            </label>
            <label class="type-desc-label">
                <input type="checkbox" class="type-item" value="shop">
                <span class="label-stack">
                    <span class="label-title">聚靈鑄星</span>
                    <span class="label-sub">加入兌換商店</span>
                </span>
            </label>
            <label><input type="checkbox" class="type-item" value="collab"> 長期聯動</label>
        `;
    }
}

function getPatchColClass(patch, activePatchName) {
    if (patch.patch === activePatchName) return ' class="current-patch-col"';
    if (patch.isPreview) return ' class="preview-patch-col"';
    return '';
}

function buildTableHeaderHtml(displayPatches, totalChars, activePatchName) {
    let html = '<thead><tr>';
    html += `<th rowspan="2" class="top-left-cell">
        <div class="top-left-widget">
            <div class="btn-group">
                <button type="button" id="sort-char-btn" class="table-sort-btn${charSortMode !== 'debut-desc' ? ' active' : ''}">${getSortCharBtnLabel()}</button>
                <button type="button" id="sort-patch-btn" class="table-sort-btn">版本 ${isPatchAscending ? '◀' : '▶'}</button>
            </div>
            <div class="table-count-badge" id="table-count-badge" title="符合條件的角色數量 / 總角色數量">共 ${totalChars} 位</div>
        </div>
    </th>`;

    displayPatches.forEach(p => {
        html += `<th${getPatchColClass(p, activePatchName)}>${formatHeaderDate(p.date)}</th>`;
    });

    html += `</tr><tr>`;
    displayPatches.forEach(p => {
        html += `<th${getPatchColClass(p, activePatchName)}>${p.patch}</th>`;
    });
    html += '</tr></thead>';
    return html;
}

function getHistoryElement(char, patch, pIdx, state, patchIndexMap) {
    if (char.isCollab) {
        const collabStart = char.isCollab;
        const sIdx = patchIndexMap.has(collabStart) ? patchIndexMap.get(collabStart) : -1;

        if (pIdx < sIdx) {
            return { status: 'COLLAB_BEFORE' };
        } else {
            const lIdx = state.patchesListLength - 1;
            if (pIdx === sIdx || pIdx === lIdx) {
                return { status: 'COLLAB' };
            } else {
                return { status: 'COLLAB_EMPTY' };
            }
        }
    }

    if (char.term) {
        const termIdx = patchIndexMap.has(char.term.patch) ? patchIndexMap.get(char.term.patch) : -1;
        if (pIdx === termIdx) {
            return { status: 'TERM_START', type: char.term.type };
        } else if (pIdx > termIdx) {
            return { status: 'TERM_EMPTY', type: char.term.type };
        }
    }

    if (char.runs && char.runs.includes(patch)) {
        state.hasReleased = true;
        state.currentGap = 0;
        return { status: 'UP' };
    } else {
        if (state.hasReleased) {
            state.currentGap++;
            return { status: 'WAIT', gap: state.currentGap };
        } else {
            return { status: 'NONE' };
        }
    }
}

function buildCharacterHistory(char, patchesList, patchIndexMap) {
    let history = [];
    let state = {
        currentGap: 0,
        hasReleased: false,
        patchesListLength: patchesList.length
    };

    patchesList.forEach((patch, pIdx) => {
        const element = getHistoryElement(char, patch, pIdx, state, patchIndexMap);
        if (element) {
            history.push(element);
        }
    });

    // Process COLLAB_BEFORE cells to create the span while the history is still in chronological order
    if (char.isCollab) {
        let beforeCount = 0;
        let beforeStartIndex = -1;

        for (let i = 0; i < history.length; i++) {
            if (history[i].status === 'COLLAB_BEFORE') {
                if (beforeStartIndex === -1) beforeStartIndex = i;
                beforeCount++;
            }
        }

        if (beforeCount > 0) {
            const spanCount = Math.min(5, beforeCount);
            const spanStartIdx = beforeStartIndex + beforeCount - spanCount;
            for (let i = beforeStartIndex; i < spanStartIdx; i++) {
                history[i] = { status: 'NONE' };
            }
            history[spanStartIdx] = { status: 'COLLAB_SPAN', count: spanCount };
            for (let i = spanStartIdx + 1; i < beforeStartIndex + beforeCount; i++) {
                history[i] = { status: 'HIDDEN' };
            }
        }
    }

    return history;
}

function buildHistoryCellsHtml(char, finalHistory, displayPatches, activePatchName, avatarUrl, fallbackUrl) {
    let html = '';
    const buffEntries = getCharBuffEntries(char);

    finalHistory.forEach((cell, cellIdx) => {
        if (cell.status === 'HIDDEN') return;

        const patchObj = displayPatches[cellIdx];
        const isCurrentCol = patchObj && (patchObj.patch === activePatchName);
        const isPreviewCol = patchObj && Boolean(patchObj.isPreview);
        let currentColClass = '';
        if (isCurrentCol) currentColClass = ' current-patch-col';
        else if (isPreviewCol) currentColClass = ' preview-patch-col';

        const cellBuffTypes = (patchObj && patchObj.patch)
            ? buffEntries.filter(e => e.patch === patchObj.patch).map(e => e.type)
            : [];
        const cellHasBuff = cellBuffTypes.length > 0;
        const buffBadgeHtml = cellHasBuff ? buildBuffBadgeHtml(cellBuffTypes) : '';
        const buffTitleAttr = cellHasBuff ? ` title="${escapeHtml(buildBuffTitle(cellBuffTypes))}"` : '';

        let cls = '';
        let content = '';

        if (cell.status === 'COLLAB_SPAN') {
            let rawDate = char.collabDate || char.isCollab;
            const parts = rawDate.split(/[\/\-]/);
            let dateStr = rawDate;
            if (parts.length === 3) {
                dateStr = `${parts[1]}/${parts[2]}`;
            }
            const arrowText = isPatchAscending ? `${dateStr}後長期開放→` : `←${dateStr}後長期開放`;
            html += `<td colspan="${cell.count}" class="collab-text${currentColClass}">${buffBadgeHtml}${arrowText}</td>`;
            return;
        }

        switch (cell.status) {
            case 'UP':
            case 'COLLAB':
                cls = 'img-cell';
                content = `${buffBadgeHtml}<img src="${avatarUrl}" class="grid-avatar" alt="${escapeHtml(char.name)}" onerror="this.onerror=null; this.src='${fallbackUrl}';"${buffTitleAttr}>`;
                break;
            case 'COLLAB_EMPTY':
            case 'COLLAB_BEFORE':
                cls = `collab-empty bg-${escapeHtml(char.elem)}`;
                content = buffBadgeHtml;
                break;
            case 'TERM_START':
                cls = cell.type === 'pool' ? 'term-pool' : 'term-shop';
                content = `${buffBadgeHtml}${cell.type === 'pool' ? '星緣' : '聚靈'}`;
                break;
            case 'TERM_EMPTY':
                cls = cell.type === 'pool' ? 'term-pool-empty' : 'term-shop-empty';
                content = buffBadgeHtml;
                break;
            case 'NONE':
                cls = 'none';
                content = `${buffBadgeHtml}-`;
                break;
            default:
                content = `${buffBadgeHtml}${cell.gap}`;
                if (cell.gap <= 3) cls = 'w-low';
                else if (cell.gap <= 7) cls = 'w-med';
                else if (cell.gap <= 12) cls = 'w-high';
                else cls = 'w-crit';
                break;
        }
        html += `<td class="${cls}${currentColClass}"${buffTitleAttr}>${content}</td>`;
    });
    return html;
}

function getCharacterTooltip(char, stats, debutVer, isCharPreview) {
    if (isCharPreview) {
        return `【${char.name} - 躍遷資訊】\n• 預定登場：${debutVer}\n• 預覽角色`;
    } else if (stats.isCollab) {
        return `【${char.name} - 躍遷資訊】\n• 實裝版本：${debutVer}\n• 長期聯動角色`;
    } else if (stats.isTermActive) {
        return `【${char.name} - 躍遷資訊】\n• 實裝版本：${debutVer}\n• 目前狀態：${stats.currentGap}\n• 歷史最長等待：${stats.maxGap}\n• 總UP次數：${stats.totalRuns}`;
    } else {
        const overdueFlag = stats.isOverdue ? " ⚠️ (超期警報!)" : "";
        return `【${char.name} - 躍遷資訊】\n• 實裝版本：${debutVer}\n• 目前等待：${stats.currentGap}${overdueFlag}\n• 歷史最長等待：${stats.maxGap}\n• 總UP次數：${stats.totalRuns}`;
    }
}

// 🌌 產生角色統計琉璃浮動資訊卡 HTML
function buildCharPopoverHtml(data) {
    if (!data) return '';
    const name = escapeHtml(data.charName || '');
    const elem = escapeHtml(data.charElem || '');
    const path = escapeHtml(data.charPath || '');
    const debut = escapeHtml(data.debut || '未登場');
    const currentGap = escapeHtml(data.currentGap ?? '-');
    const maxGap = escapeHtml(data.maxGap ?? '-');
    const totalRuns = escapeHtml(data.totalRuns ?? '0');

    const isPreview = data.isPreview === 'true' || data.isPreview === true;
    const isCollab = data.isCollab === 'true' || data.isCollab === true;
    const isTerm = data.isTerm === 'true' || data.isTerm === true;
    const isOverdue = data.isOverdue === 'true' || data.isOverdue === true;
    const isFallbackPath = data.charPath ? !isRegisteredPath(data.charPath) : false;

    const tagsHtml = `
        <span class="popover-tags">
            ${elem ? `<span class="popover-tag">${elem}</span>` : ''}
            ${path ? `<span class="popover-tag${isFallbackPath ? ' popover-tag-fallback' : ''}">${path}</span>` : ''}
        </span>
    `;

    let bodyRowsHtml = '';
    if (isPreview) {
        bodyRowsHtml = `
            <div class="popover-row"><span class="popover-label">預定登場</span><span class="popover-val highlight-purple">${debut}</span></div>
            <div class="popover-row"><span class="popover-label">角色狀態</span><span class="popover-val highlight-purple">🔮 預覽角色</span></div>
        `;
    } else if (isCollab) {
        bodyRowsHtml = `
            <div class="popover-row"><span class="popover-label">實裝版本</span><span class="popover-val">${debut}</span></div>
            <div class="popover-row"><span class="popover-label">角色狀態</span><span class="popover-val highlight-gold">✦ 長期聯動角色</span></div>
        `;
    } else if (isTerm) {
        const maxGapText = maxGap === '-' ? '-' : `${maxGap} 個版本`;
        bodyRowsHtml = `
            <div class="popover-row"><span class="popover-label">實裝版本</span><span class="popover-val">${debut}</span></div>
            <div class="popover-row"><span class="popover-label">目前狀態</span><span class="popover-val highlight-gold">${currentGap}</span></div>
            <div class="popover-row"><span class="popover-label">歷史最長等待</span><span class="popover-val">${maxGapText}</span></div>
            <div class="popover-row"><span class="popover-label">總 UP 次數</span><span class="popover-val">${totalRuns} 次</span></div>
        `;
    } else {
        const waitText = currentGap === '0' ? '當期 UP 中 (0)' : (currentGap === '-' ? '-' : `${currentGap} 個版本`);
        const maxGapText = maxGap === '-' ? '-' : `${maxGap} 個版本`;
        bodyRowsHtml = `
            <div class="popover-row"><span class="popover-label">實裝版本</span><span class="popover-val">${debut}</span></div>
            <div class="popover-row"><span class="popover-label">目前等待</span><span class="popover-val ${isOverdue ? 'highlight-gold' : ''}">${waitText}</span></div>
            <div class="popover-row"><span class="popover-label">歷史最長等待</span><span class="popover-val">${maxGapText}</span></div>
            <div class="popover-row"><span class="popover-label">總 UP 次數</span><span class="popover-val">${totalRuns} 次</span></div>
            ${isOverdue ? '<div class="popover-overdue-alert">⚠️ 超期警報：目前已超越歷史最長等待紀錄！</div>' : ''}
        `;
    }

    return `
        <div class="popover-header">
            <span class="popover-title">${name}</span>
            ${tagsHtml}
        </div>
        <div class="popover-body">
            ${bodyRowsHtml}
        </div>
    `;
}

function ensureCharPopover() {
    let popover = document.getElementById('char-stats-popover');
    if (!popover && typeof document !== 'undefined' && document.body) {
        popover = document.createElement('div');
        popover.id = 'char-stats-popover';
        popover.className = 'char-stats-popover';
        popover.setAttribute('role', 'tooltip');
        popover.setAttribute('aria-hidden', 'true');
        document.body.appendChild(popover);
    }
    return popover;
}

function positionCharPopover(popover, cell) {
    if (!popover || !cell || typeof cell.getBoundingClientRect !== 'function') return;
    const rect = cell.getBoundingClientRect();
    const popWidth = popover.offsetWidth || 225;
    const popHeight = popover.offsetHeight || 135;
    const vw = typeof window !== 'undefined' ? (window.innerWidth || 1024) : 1024;
    const vh = typeof window !== 'undefined' ? (window.innerHeight || 768) : 768;

    let left = rect.right + 10;
    if (left + popWidth > vw - 8) {
        left = Math.max(8, Math.min(rect.left + 8, vw - popWidth - 8));
    }
    let top = rect.top - 4;
    if (top + popHeight > vh - 8) {
        top = Math.max(8, vh - popHeight - 8);
    }
    if (top < 8) top = 8;

    popover.style.left = `${Math.round(left)}px`;
    popover.style.top = `${Math.round(top)}px`;
}

function showCharPopover(cell, pin = false) {
    if (!cell) return;
    const popover = ensureCharPopover();
    if (!popover) return;

    activePopoverCell = cell;
    isPopoverPinned = Boolean(pin);
    popover.innerHTML = buildCharPopoverHtml(cell.dataset);
    popover.classList.add('show');
    popover.classList.toggle('pinned', isPopoverPinned);
    popover.setAttribute('aria-hidden', 'false');
    positionCharPopover(popover, cell);
}

function hideCharPopover() {
    const popover = document.getElementById('char-stats-popover');
    if (popover) {
        popover.classList.remove('show', 'pinned');
        popover.setAttribute('aria-hidden', 'true');
    }
    activePopoverCell = null;
    isPopoverPinned = false;
}

function getCharacterType(char) {
    if (char.isCollab) return 'collab';
    if (char.term) {
        if (char.term.type === 'pool') return 'pool';
        if (char.term.type === 'shop') return 'shop';
    }
    return 'normal';
}

function buildCharacterRowHtml(char, index, totalChars, patchesList, patchIndexMap, displayPatches, activePatchName) {
    const fallbackUrl = getFallbackAvatar(char.name);
    const avatarUrl = char.avatar ? char.avatar : fallbackUrl;
    const pathIconHtml = buildPathIconHtml(char.path);
    const parsedSort = parseSortMode(charSortMode, isCharAscending);
    const isCustomRankSort = parsedSort.field === 'wait' || parsedSort.field === 'runs';
    const seqNum = isCustomRankSort ? (index + 1) : (isCharAscending ? (index + 1) : (totalChars - index));

    const charType = getCharacterType(char);
    const buffTypes = getCharBuffTypes(char);
    const hasBuff = buffTypes.length > 0;
    const buffTypesAttr = buffTypes.length > 0 ? ` data-buff-types="${escapeHtml(buffTypes.join(','))}"` : '';
    const isUnregisteredPath = char.path && !isRegisteredPath(char.path);
    const unregisteredPathAttr = isUnregisteredPath ? ' data-unregistered-path="true"' : '';
    const majorVer = getCharDebutMajorVersion(char, patchesList, patchIndexMap);
    const debutVer = getCharDebutVersion(char, patchesList, patchIndexMap);

    const isCharPreview = Boolean(char.isPreview);
    const stats = calculateCharStats(char, patchesList, activePatchName, patchIndexMap);

    let html = `<tr data-path="${escapeHtml(char.path)}" data-elem="${escapeHtml(char.elem)}" data-type="${charType}" data-has-buff="${hasBuff}"${buffTypesAttr} data-major-version="${escapeHtml(majorVer)}" data-name="${escapeHtml(char.name)}" data-is-preview="${isCharPreview}"${unregisteredPathAttr}>
        <td class="bg-${escapeHtml(char.elem)}${isUnregisteredPath ? ' path-fallback-cell' : ''}">
            <div class="char-info-cell"
                 data-char-name="${escapeHtml(char.name)}"
                 data-char-elem="${escapeHtml(char.elem)}"
                 data-char-path="${escapeHtml(char.path)}"
                 data-debut="${escapeHtml(debutVer)}"
                 data-current-gap="${escapeHtml(stats.currentGap ?? '-')}"
                 data-max-gap="${escapeHtml(stats.maxGap ?? '-')}"
                 data-total-runs="${escapeHtml(stats.totalRuns ?? '0')}"
                 data-is-overdue="${Boolean(stats.isOverdue)}"
                 data-is-collab="${Boolean(stats.isCollab)}"
                 data-is-term="${Boolean(stats.isTermActive)}"
                 data-is-preview="${isCharPreview}">
                <span class="char-seq">${seqNum}</span>
                ${pathIconHtml}
                <img src="${avatarUrl}" class="char-avatar" alt="${escapeHtml(char.name)}" onerror="this.onerror=null; this.src='${fallbackUrl}';">
                <span class="char-name">${escapeHtml(char.name)}</span>
                ${isCharPreview ? '<span class="preview-badge" title="【預覽角色】">🔮</span>' : ''}
            </div>
        </td>`;

    let history = buildCharacterHistory(char, patchesList, patchIndexMap);

    const finalHistory = isPatchAscending ? history : history.reverse();

    html += buildHistoryCellsHtml(char, finalHistory, displayPatches, activePatchName, avatarUrl, fallbackUrl);
    html += `</tr>`;
    return html;
}

function renderTable() {
    cachedTableCells = null;
    cachedRowData = new WeakMap();
    hideCharPopover();
    hideCharSortMenu();
    const table = document.getElementById('tracker');
    if (!table) return;

    // 0. 依據預覽開關篩選可用的版本與角色
    const activePatches = isShowPreview ? PATCH_DATA : PATCH_DATA.filter(p => !p.isPreview);
    const activeCharacters = isShowPreview ? RAW_CHARACTERS : RAW_CHARACTERS.filter(c => !c.isPreview);
    const patchesList = activePatches.map(p => p.patch);

    const patchIndexMap = new Map();
    patchesList.forEach((patch, index) => patchIndexMap.set(patch, index));

    const activePatchName = getCurrentPatchName();

    // 1. 決定角色陣列順序
    if (charSortMode === 'debut-desc' || charSortMode === 'debut-asc') {
        charSortMode = isCharAscending ? 'debut-asc' : 'debut-desc';
    }
    const CHARACTERS = sortCharacters(activeCharacters, charSortMode, patchesList, activePatchName, patchIndexMap);
    const totalChars = CHARACTERS.length;

    updateSortControlsUI();

    // 2. 決定小版本陣列順序
    const displayPatches = isPatchAscending ? [...activePatches] : [...activePatches].reverse();

    renderFilters(CHARACTERS, patchesList, patchIndexMap);

    let html = buildTableHeaderHtml(displayPatches, totalChars, activePatchName);

    html += '<tbody>';
    CHARACTERS.forEach((char, index) => {
        html += buildCharacterRowHtml(char, index, totalChars, patchesList, patchIndexMap, displayPatches, activePatchName);
    });
    html += '</tbody>';
    
    table.innerHTML = html;

    updateTableColumnIndices(table);

    const jumpLatestBtn = document.getElementById('jump-latest-btn');
    const jumpOldestBtn = document.getElementById('jump-oldest-btn');
    updateJumpButtons(jumpLatestBtn, jumpOldestBtn);

    rebindControlListeners();
}

function toggleCharSortDirection() {
    isCharAscending = !isCharAscending;
    const { field } = parseSortMode(charSortMode, isCharAscending);
    charSortMode = `${field}-${isCharAscending ? 'asc' : 'desc'}`;
    renderTable();
    syncStateToUrl();
}

function setupSortingListeners() {
    const sortSelect = document.getElementById('char-sort-select');
    if (sortSelect && !sortSelect._hsrBound) {
        sortSelect._hsrBound = true;
        sortSelect.addEventListener('change', (e) => {
            const val = e.target.value;
            const parsed = parseSortMode(val, isCharAscending);
            charSortMode = parsed.mode;
            isCharAscending = parsed.isAsc;
            renderTable();
            syncStateToUrl();
        });
    }

    const sortDirBtn = document.getElementById('char-sort-dir-btn');
    if (sortDirBtn && !sortDirBtn._hsrBound) {
        sortDirBtn._hsrBound = true;
        sortDirBtn.addEventListener('click', () => {
            toggleCharSortDirection();
        });
    }

    const sortPopover = ensureCharSortPopover();
    if (sortPopover && !sortPopover._hsrBound) {
        sortPopover._hsrBound = true;
        sortPopover.addEventListener('click', (e) => {
            const optionBtn = e.target.closest?.('.sort-option-btn');
            if (!optionBtn || !optionBtn.dataset.sortMode) return;
            e.stopPropagation();
            const mode = optionBtn.dataset.sortMode;
            const parsed = parseSortMode(mode);
            charSortMode = parsed.mode;
            isCharAscending = parsed.isAsc;
            hideCharSortMenu();
            renderTable();
            syncStateToUrl();
        });
    }

    if (!document._hsrSortClickBound) {
        document._hsrSortClickBound = true;
        document.addEventListener('click', (e) => {
            if (e.target && e.target.id === 'sort-char-btn') {
                e.stopPropagation();
                toggleCharSortMenu(e.target);
            } else if (e.target && e.target.id === 'sort-patch-btn') {
                isPatchAscending = !isPatchAscending;
                renderTable();
                syncStateToUrl();
            } else {
                const popover = document.getElementById('char-sort-popover');
                if (popover && popover.classList.contains('show') && !popover.contains(e.target)) {
                    hideCharSortMenu();
                }
            }
        });
    }

    if (!document._hsrSortKeyBound) {
        document._hsrSortKeyBound = true;
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                hideCharSortMenu();
                hideCharPopover();
            }
        });
    }
}

function setupJumpButtons() {
    const tableWrap = document.querySelector('.table-wrap');
    const jumpLatestBtn = document.getElementById('jump-latest-btn');
    const jumpOldestBtn = document.getElementById('jump-oldest-btn');

    if (jumpLatestBtn && tableWrap) {
        jumpLatestBtn.addEventListener('click', () => {
            tableWrap.scrollTo({ left: 0, behavior: 'smooth' });
        });
    }

    if (jumpOldestBtn && tableWrap) {
        jumpOldestBtn.addEventListener('click', () => {
            tableWrap.scrollTo({ left: tableWrap.scrollWidth, behavior: 'smooth' });
        });
    }
}

function setupFilterPanels() {
    const dropdowns = [
        { box: document.getElementById('version-select-box'), panel: document.getElementById('version-panel') },
        { box: document.getElementById('path-select-box'), panel: document.getElementById('path-panel') },
        { box: document.getElementById('elem-select-box'), panel: document.getElementById('elem-panel') },
        { box: document.getElementById('type-select-box'), panel: document.getElementById('type-panel') }
    ];

    dropdowns.forEach(({ box, panel }) => {
        box?.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdowns.forEach(d => {
                if (d.panel !== panel) d.panel?.classList.remove('show');
            });
            panel?.classList.toggle('show');
        });
        panel?.addEventListener('click', (e) => e.stopPropagation());
    });

    document.addEventListener('click', () => {
        dropdowns.forEach(d => d.panel?.classList.remove('show'));
    });
}

function bindBuffModeButtons() {
    getBuffModeButtons().forEach(btn => {
        if (btn._hsrBuffBound) return;
        btn._hsrBuffBound = true;
        btn.addEventListener('click', () => {
            setButtonActive(btn, !btn.classList.contains('active'));
            applyFilters();
        });
    });
}

function setupUtilityToggles() {
    const previewToggleBtn = document.getElementById('preview-toggle-btn');

    if (previewToggleBtn) {
        previewToggleBtn.classList.toggle('active', isShowPreview);
        previewToggleBtn.addEventListener('click', () => {
            isShowPreview = !isShowPreview;
            localStorage.setItem('hsr_show_preview', isShowPreview);
            previewToggleBtn.classList.toggle('active', isShowPreview);
            renderTable();
            applyFilters();
        });
    }

    bindBuffModeButtons();
}

function clearAllFilters() {
    document.querySelectorAll('.version-item, .path-item, .elem-item, .type-item').forEach(i => { i.checked = false; });
    const searchInput = document.getElementById('char-search-input');
    if (searchInput) searchInput.value = '';
    getBuffModeButtons().forEach(btn => setButtonActive(btn, false));
    applyFilters();
}

function setupSearchAndReset() {
    const searchInput = document.getElementById('char-search-input');
    const searchClearBtn = document.getElementById('search-clear-btn');
    const resetFiltersBtn = document.getElementById('reset-filters-btn');

    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener('click', clearAllFilters);
    }

    if (searchClearBtn) {
        searchClearBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (searchInput) searchInput.value = '';
            applyFilters();
            searchInput?.focus();
        });
    }

    searchInput?.addEventListener('input', applyFilters);
    searchInput?.addEventListener('search', applyFilters);
}

function setupExportButton() {
    const exportImgBtn = document.getElementById('export-img-btn');

    // 📷 匯出截圖邏輯 (修復 html2canvas sticky 錯位毀滅性 Bug)
    if (exportImgBtn) {
        exportImgBtn.addEventListener('click', async () => {
            if (typeof html2canvas === 'undefined') {
                alert('截圖功能組件尚未載入完成，請稍後再試！');
                return;
            }
            try {
                exportImgBtn.textContent = '📷 繪製中...';
                exportImgBtn.disabled = true;

                const table = document.getElementById('tracker');
                const visibleRows = Array.from(table.querySelectorAll('tbody tr:not(.empty-row)')).filter(r => r.style.display !== 'none');

                if (visibleRows.length === 0) {
                    alert('目前沒有符合條件的角色可供截圖！');
                    return;
                }

                let minActiveCol = Infinity;
                let maxActiveCol = -1;

                visibleRows.forEach(row => {
                    const cells = Array.from(row.children);
                    let colIdx = 0;
                    cells.forEach(cell => {
                        const span = parseInt(cell.getAttribute('colspan') || '1', 10);
                        
                        const isActiveCell = cell.classList.contains('img-cell') ||
                                             cell.classList.contains('w-low') ||
                                             cell.classList.contains('w-med') ||
                                             cell.classList.contains('w-high') ||
                                             cell.classList.contains('w-crit') ||
                                             cell.classList.contains('term-pool') ||
                                             cell.classList.contains('term-shop');
                        
                        if (isActiveCell && colIdx > 0) {
                            const start = colIdx;
                            const end = colIdx + span - 1;
                            if (start < minActiveCol) minActiveCol = start;
                            if (end > maxActiveCol) maxActiveCol = end;
                        }
                        colIdx += span;
                    });
                });

                if (minActiveCol === Infinity || maxActiveCol === -1) {
                    minActiveCol = 1;
                    maxActiveCol = 1;
                }

                const imgs = Array.from(table.querySelectorAll('img'));
                await Promise.all(imgs.map(img => {
                    if (img.complete && img.naturalWidth !== 0) return Promise.resolve();
                    return new Promise(resolve => {
                        img.onload = resolve;
                        img.onerror = () => {
                            const altName = img.alt || '角';
                            img.src = getFallbackAvatar(altName);
                            resolve();
                        };
                    });
                }));

                const canvas = await html2canvas(table, {
                    backgroundColor: '#101522',
                    scale: 2,
                    useCORS: true,
                    logging: false,
                    scrollX: 0,
                    scrollY: 0,
                    onclone: (clonedDoc) => {
                        const clonedTable = clonedDoc.getElementById('tracker');
                        if (!clonedTable) return;

                        // Set table wrapper to full width/height and visible to prevent clipping
                        const tableWrap = clonedTable.closest('.table-wrap');
                        if (tableWrap) {
                            tableWrap.style.setProperty('overflow', 'visible', 'important');
                            tableWrap.style.setProperty('width', 'fit-content', 'important');
                            tableWrap.style.setProperty('max-width', 'none', 'important');
                            tableWrap.style.setProperty('max-height', 'none', 'important');
                            tableWrap.scrollLeft = 0;
                            tableWrap.scrollTop = 0;
                        }

                        // Apply the trimming logic directly to the clonedTable
                        clonedTable.querySelectorAll('tbody tr').forEach(r => {
                            if (r.style.display === 'none' || r.classList.contains('empty-row')) {
                                r.remove();
                            }
                        });

                        const allClonedRows = clonedTable.querySelectorAll('tr');
                        allClonedRows.forEach(row => {
                            const cells = Array.from(row.children);

                            let colIdx = 0;
                            if (row.parentElement && row.parentElement.tagName.toLowerCase() === 'thead' && !row.querySelector('.top-left-cell')) {
                                colIdx = 1;
                            }

                            cells.forEach(cell => {
                                const span = parseInt(cell.getAttribute('colspan') || '1', 10);
                                const cellStart = colIdx;
                                const cellEnd = colIdx + span - 1;

                                if (cellStart === 0) {
                                    colIdx += span;
                                    return;
                                }

                                const overlapStart = Math.max(cellStart, minActiveCol);
                                const overlapEnd = Math.min(cellEnd, maxActiveCol);

                                if (overlapStart <= overlapEnd) {
                                    const newSpan = overlapEnd - overlapStart + 1;
                                    if (newSpan !== span) {
                                        cell.setAttribute('colspan', newSpan);
                                    }
                                } else {
                                    cell.remove();
                                }
                                colIdx += span;
                            });
                        });

                        // 🌟 關鍵修復：強行取消所有凍結視窗 (sticky) 避免 html2canvas 算錯座標把表頭/角色欄甩出去
                        clonedTable.querySelectorAll('th, td, thead, tr, div, span').forEach(el => {
                            const compStyle = clonedDoc.defaultView.getComputedStyle(el);
                            if (compStyle.position === 'sticky') {
                                el.style.setProperty('position', 'static', 'important');
                                el.style.setProperty('top', 'auto', 'important');
                                el.style.setProperty('left', 'auto', 'important');
                                el.style.setProperty('right', 'auto', 'important');
                                el.style.setProperty('bottom', 'auto', 'important');
                                el.style.setProperty('transform', 'none', 'important');
                            }
                            if (el.classList.contains('buff-badge')) {
                                el.style.setProperty('position', 'absolute', 'important');
                            }
                            el.style.setProperty('box-shadow', 'none', 'important');
                            el.classList.remove('col-highlight');
                        });

                        // 🌟 確保包含角標的儲存格有 relative 作為定位基準
                        clonedTable.querySelectorAll('td, th').forEach(cell => {
                            if (cell.querySelector('.buff-badge')) {
                                cell.style.setProperty('position', 'relative', 'important');
                            }
                        });

                        clonedTable.style.setProperty('zoom', '1', 'important');
                    }
                });

                const imgData = canvas.toDataURL('image/png');
                const newTab = window.open();
                if (newTab) {
                    newTab.document.write(`
                        <!DOCTYPE html>
                        <html lang="zh-TW">
                        <head>
                            <meta charset="UTF-8">
                            <title>星穹鐵道_限定躍遷一覽表_${new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(0, 10)}</title>
                            <style>
                                body {
                                    margin: 0;
                                    background: #0b0e17;
                                    display: flex;
                                    justify-content: center;
                                    align-items: flex-start;
                                    min-height: 100vh;
                                    padding: 20px;
                                    box-sizing: border-box;
                                }
                                img {
                                    max-width: 100%;
                                    height: auto;
                                    border-radius: 8px;
                                    box-shadow: 0 4px 20px rgba(0,0,0,0.8);
                                }
                            </style>
                        </head>
                        <body>
                            <img src="${imgData}" alt="限定躍遷一覽表截圖">
                        </body>
                        </html>
                    `);
                    newTab.document.close();
                } else {
                    alert('新分頁被瀏覽器阻擋，請允許彈出視窗後重試！');
                }
            } catch (err) {
                console.error('截圖繪製失敗:', err);
                alert('截圖失敗，請重試！');
            } finally {
                exportImgBtn.textContent = '📷 截圖';
                exportImgBtn.disabled = false;
            }
        });
    }
}

function setupTableInteractions() {
    const trackerTable = document.getElementById('tracker');
    if (trackerTable && !trackerTable._hsrInteractionsBound) {
        trackerTable._hsrInteractionsBound = true;

        trackerTable.addEventListener('click', (e) => {
            if (e.target?.id === 'empty-reset-btn') {
                clearAllFilters();
                return;
            }
            const infoCell = e.target.closest?.('.char-info-cell');
            if (infoCell) {
                e.stopPropagation();
                if (isPopoverPinned && activePopoverCell === infoCell) {
                    hideCharPopover();
                } else {
                    showCharPopover(infoCell, true);
                }
            }
        });

        trackerTable.addEventListener('mouseover', (e) => {
            const isHoverNone = Boolean(window.matchMedia && window.matchMedia('(hover: none)').matches);

            const infoCell = e.target.closest?.('.char-info-cell');
            if (infoCell && !isHoverNone && !isPopoverPinned) {
                showCharPopover(infoCell, false);
            }

            if (isHoverNone) return;

            const cell = e.target.closest('td, th');
            if (!cell || cell.closest('tr')?.classList.contains('empty-row')) return;

            if (cell.colSpan > 1) {
                trackerTable.querySelectorAll('.col-highlight').forEach(c => c.classList.remove('col-highlight'));
                return;
            }

            const startCol = cell._startCol !== undefined ? cell._startCol : parseInt(cell.dataset.startCol, 10);
            const endCol = cell._endCol !== undefined ? cell._endCol : parseInt(cell.dataset.endCol, 10);

            trackerTable.querySelectorAll('.col-highlight').forEach(c => c.classList.remove('col-highlight'));

            if (endCol === 0 || isNaN(startCol)) return;

            if (!cachedTableCells) {
                cachedTableCells = trackerTable.querySelectorAll('th, td');
            }

            cachedTableCells.forEach(c => {
                if (c.colSpan > 1) return;

                const cStart = c._startCol !== undefined ? c._startCol : parseInt(c.dataset.startCol, 10);
                const cEnd = c._endCol !== undefined ? c._endCol : parseInt(c.dataset.endCol, 10);
                if (cEnd >= startCol && cStart <= endCol && cEnd > 0) {
                    c.classList.add('col-highlight');
                }
            });
        });

        trackerTable.addEventListener('mouseout', (e) => {
            if (isPopoverPinned) return;
            const infoCell = e.target.closest?.('.char-info-cell');
            if (infoCell && (!e.relatedTarget || !infoCell.contains(e.relatedTarget))) {
                hideCharPopover();
            }
        });

        trackerTable.addEventListener('mouseleave', () => {
            trackerTable.querySelectorAll('.col-highlight').forEach(c => c.classList.remove('col-highlight'));
            if (!isPopoverPinned) {
                hideCharPopover();
            }
        });
    }

    const tableWrap = document.querySelector('.table-wrap');
    if (tableWrap && !tableWrap._hsrScrollBound) {
        tableWrap._hsrScrollBound = true;
        tableWrap.addEventListener('scroll', () => {
            if (activePopoverCell) {
                hideCharPopover();
            }
            hideCharSortMenu();
        }, { passive: true });
    }

    if (!document._hsrPopoverOutsideClickBound) {
        document._hsrPopoverOutsideClickBound = true;
        document.addEventListener('click', (e) => {
            if (!activePopoverCell) return;
            const popover = document.getElementById('char-stats-popover');
            if (popover && popover.contains(e.target)) return;
            if (e.target.closest?.('.char-info-cell')) return;
            hideCharPopover();
        });
    }
}

function setupUIScaleSlider() {
    const scaleSlider = document.getElementById('ui-scale-slider');
    const scaleText = document.getElementById('ui-scale-text');

    const savedScale = localStorage.getItem('hsr_ui_scale');
    if (savedScale && scaleSlider && scaleText) {
        scaleSlider.value = savedScale;
        const table = document.getElementById('tracker');
        if (table) table.style.zoom = savedScale;
        scaleText.textContent = Math.round(savedScale * 100) + '%';
    }

    scaleSlider?.addEventListener('input', (e) => {
        const scaleValue = e.target.value;
        const table = document.getElementById('tracker');
        if (table) table.style.zoom = scaleValue;
        if (scaleText) scaleText.textContent = Math.round(scaleValue * 100) + '%';
        localStorage.setItem('hsr_ui_scale', scaleValue);
    });
}

function setupEventListeners() {
    setupSortingListeners();
    setupJumpButtons();
    setupFilterPanels();
    setupUtilityToggles();
    setupSearchAndReset();
    setupExportButton();
    setupTableInteractions();
    setupUIScaleSlider();
}

function rebindControlListeners() {
    const versionItems = document.querySelectorAll('.version-item');
    const pathItems = document.querySelectorAll('.path-item');
    const elemItems = document.querySelectorAll('.elem-item');
    const typeItems = document.querySelectorAll('.type-item');

    versionItems.forEach(item => item.addEventListener('change', applyFilters));
    pathItems.forEach(item => item.addEventListener('change', applyFilters));
    elemItems.forEach(item => item.addEventListener('change', applyFilters));
    typeItems.forEach(item => item.addEventListener('change', applyFilters));

    bindBuffModeButtons();
    applyFilters();
}

function getFilterState() {
    const searchInput = document.getElementById('char-search-input');
    const activeBuffs = getActiveBuffTypes();
    const onlyBuffs = activeBuffs.length > 0;
    const state = {
        selectedVersions: Array.from(document.querySelectorAll('.version-item')).filter(i => i.checked).map(i => i.value),
        selectedPaths: Array.from(document.querySelectorAll('.path-item')).filter(i => i.checked).map(i => i.value),
        selectedElems: Array.from(document.querySelectorAll('.elem-item')).filter(i => i.checked).map(i => i.value),
        selectedTypes: Array.from(document.querySelectorAll('.type-item')).filter(i => i.checked).map(i => i.value),
        keyword: searchInput && searchInput.value ? searchInput.value.trim().toLowerCase() : '',
        onlyBuffs
    };

    const defaultType = getDefaultBuffType();
    const hasCustomBuffSelection = activeBuffs.some(t => t !== defaultType) || activeBuffs.length > 1;
    if (hasCustomBuffSelection) {
        state.selectedBuffs = activeBuffs;
    } else {
        Object.defineProperty(state, 'selectedBuffs', {
            value: activeBuffs,
            enumerable: false,
            configurable: true,
            writable: true
        });
    }
    return state;
}

function updateFilterUI(state) {
    const searchClearBtn = document.getElementById('search-clear-btn');
    const resetFiltersBtn = document.getElementById('reset-filters-btn');

    if (searchClearBtn) {
        searchClearBtn.style.display = state.keyword !== '' ? 'block' : 'none';
    }

    const versionBox = document.getElementById('version-select-box');
    const pathBox = document.getElementById('path-select-box');
    const elemBox = document.getElementById('elem-select-box');
    const typeBox = document.getElementById('type-select-box');

    if (versionBox) versionBox.classList.toggle('active', state.selectedVersions.length > 0);
    if (pathBox) pathBox.classList.toggle('active', state.selectedPaths.length > 0);
    if (elemBox) elemBox.classList.toggle('active', state.selectedElems.length > 0);
    if (typeBox) typeBox.classList.toggle('active', state.selectedTypes.length > 0);

    const hasActiveFilter = state.selectedVersions.length > 0 || state.selectedPaths.length > 0 || state.selectedElems.length > 0 || state.selectedTypes.length > 0 || state.keyword !== '' || state.onlyBuffs;
    if (resetFiltersBtn) {
        resetFiltersBtn.style.display = hasActiveFilter ? 'inline-flex' : 'none';
    }

    const typeLabelMap = { 'normal': '限定躍遷', 'pool': '星緣', 'shop': '聚靈', 'collab': '聯動' };
    const formatSelectBox = (box, selected, defaultLabel, mapFn = x => x) => {
        if (!box) return;
        if (selected.length === 0) box.textContent = defaultLabel;
        else if (selected.length <= 2) box.textContent = selected.map(mapFn).join(', ');
        else box.textContent = `${mapFn(selected[0])} 等 ${selected.length} 個`;
    };

    formatSelectBox(versionBox, state.selectedVersions, '實裝版本');
    formatSelectBox(pathBox, state.selectedPaths, '命途');
    formatSelectBox(elemBox, state.selectedElems, '屬性');
    formatSelectBox(typeBox, state.selectedTypes, '取得方法', t => typeLabelMap[t]);
}

function isRowMatchingFilters(rowData, state) {
    const matchVersion = state.selectedVersions.length === 0 || state.selectedVersions.includes(rowData.majorVer);
    const matchPath = state.selectedPaths.length === 0 || state.selectedPaths.includes(rowData.path);
    const matchElem = state.selectedElems.length === 0 || state.selectedElems.includes(rowData.elem);
    const matchType = state.selectedTypes.length === 0 || state.selectedTypes.includes(rowData.type);
    const matchName = state.keyword === '' || rowData.name.includes(state.keyword);
    const selectedBuffs = Array.isArray(state.selectedBuffs) ? state.selectedBuffs : [];
    let matchBuff = true;
    if (selectedBuffs.length > 0) {
        const rowBuffs = Array.isArray(rowData.buffTypes) && rowData.buffTypes.length > 0
            ? rowData.buffTypes
            : (rowData.hasBuff ? [getDefaultBuffType()] : []);
        matchBuff = selectedBuffs.some(type => rowBuffs.includes(type));
    } else if (state.onlyBuffs) {
        matchBuff = Boolean(rowData.hasBuff);
    }

    return matchVersion && matchPath && matchElem && matchType && matchName && matchBuff;
}

function filterTableRows(table, state) {
    let rowData = cachedRowData.get(table);
    if (!rowData) {
        const rows = table.querySelectorAll('tbody tr:not(.empty-row)');
        rowData = Array.from(rows, row => {
            const hasBuff = row.getAttribute('data-has-buff') === 'true';
            const rawBuffTypes = row.getAttribute('data-buff-types') || '';
            const buffTypes = rawBuffTypes
                ? rawBuffTypes.split(',').map(s => s.trim()).filter(Boolean)
                : (hasBuff ? [getDefaultBuffType()] : []);
            return {
                row,
                majorVer: row.getAttribute('data-major-version'),
                path: row.getAttribute('data-path'),
                elem: row.getAttribute('data-elem'),
                type: row.getAttribute('data-type'),
                hasBuff,
                buffTypes,
                name: (row.getAttribute('data-name') || '').toLowerCase()
            };
        });
        cachedRowData.set(table, rowData);
    }

    let visibleCount = 0;
    const totalChars = rowData.length;

    rowData.forEach(item => {
        if (isRowMatchingFilters(item, state)) {
            item.row.style.display = '';
            visibleCount++;
        } else {
            item.row.style.display = 'none';
        }
    });

    return { visibleCount, totalChars };
}

function updateTableUI(table, visibleCount, totalChars) {
    const countBadge = document.getElementById('table-count-badge');
    if (countBadge) {
        if (visibleCount === totalChars) {
            countBadge.textContent = `共 ${totalChars} 位`;
        } else {
            countBadge.textContent = `${visibleCount}/${totalChars} 位`;
        }
    }

    let emptyRow = table.querySelector('tbody tr.empty-row');
    const headerThs = table.querySelectorAll('thead tr:first-child th');
    const totalCols = headerThs.length > 0 ? headerThs.length : (PATCH_DATA.length + 1);
    if (visibleCount === 0) {
        if (!emptyRow) {
            emptyRow = document.createElement('tr');
            emptyRow.className = 'empty-row';
            emptyRow.innerHTML = `<td colspan="${totalCols}" style="text-align: center; padding: 25px; color: #888; background: #161616; font-size: 13px;">
                沒有符合條件的角色<br>
                <button type="button" id="empty-reset-btn" class="empty-reset-btn">↺ 清除所有條件</button>
            </td>`;
            table.querySelector('tbody').appendChild(emptyRow);
        } else {
            emptyRow.style.display = '';
        }
    } else {
        if (emptyRow) {
            emptyRow.style.display = 'none';
        }
    }
}

function applyFilters() {
    const table = document.getElementById('tracker');
    if (!table) return;

    const state = getFilterState();
    updateFilterUI(state);
    const { visibleCount, totalChars } = filterTableRows(table, state);
    updateTableUI(table, visibleCount, totalChars);
    syncStateToUrl();
}

// 頂部工具列摺疊邏輯
function setupToolbarToggle() {
    const toggleBtn = document.getElementById('toggle-toolbar-btn');
    const toolbarPanel = document.getElementById('toolbar-panel');

    if (toggleBtn && toolbarPanel) {
        toggleBtn.addEventListener('click', () => {
            const isCollapsed = toolbarPanel.classList.toggle('collapsed');
            toggleBtn.classList.toggle('active', !isCollapsed);
            localStorage.setItem('hsr_toolbar_collapsed', isCollapsed);
        });

        const savedState = localStorage.getItem('hsr_toolbar_collapsed');
        if (savedState === 'true' || (savedState === null && window.innerWidth <= 768)) {
            toolbarPanel.classList.add('collapsed');
            toggleBtn.classList.remove('active');
        } else {
            toolbarPanel.classList.remove('collapsed');
            toggleBtn.classList.add('active');
        }
    }
}

// 當 DOM 載入完成後自動執行
document.addEventListener('DOMContentLoaded', () => {
    setupToolbarToggle();
    initTracker();
});

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        getCharEarliestPatch,
        getCharDebutVersion,
        getCharDebutMajorVersion,
        getCurrentPatchName,
        formatHeaderDate,
        escapeHtml,
        getFallbackAvatar,
        calculateCharStats,
        getPatchIndex,
        getTermStatus,
        mergeContinuousEvents,
        calculateGaps,
        getHistoryElement,
        getCharacterType,
        buildCharacterHistory,
        getCharacterTooltip,
        buildCharPopoverHtml,
        showCharPopover,
        hideCharPopover,
        buildCharSortMenuHtml,
        showCharSortMenu,
        hideCharSortMenu,
        toggleCharSortMenu,
        getSortCharBtnLabel,
        getSortDescription,
        setupSortingListeners,
        sortCharacters,
        parseUrlState,
        buildUrlSearchParams,
        restoreStateFromUrl,
        syncStateToUrl,
        buildTableHeaderHtml,
        initTracker,
        updateTableColumnIndices,
        renderTable,
        buildCharacterRowHtml,
        buildHistoryCellsHtml,
        getPatchColClass,
        getFilterState,
        filterTableRows,
        renderFilters,
        setupTableInteractions,
        collectPathValues,
        collectElemValues,
        collectBuffTypes,
        getCharBuffEntries,
        getCharBuffTypes,
        getBuffMeta,
        buildBuffBadgeHtml,
        handleIconError,
        buildPathIconHtml,
        renderBuffModeButtons,
        applyBuffSelection,
        isRegisteredPath,
        getDefaultBuffType
    };
}
