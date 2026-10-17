/* ==========================================================================
   崩壞：星穹鐵道 - 限定躍遷一覽表 主應用程式邏輯 (app.js)
   ========================================================================== */

let cachedTableCells = null;

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

// 自動對照 PATCH_DATA 與今日日期，找出當前進行中的卡池小版本名稱
function getCurrentPatchName() {
    if (typeof PATCH_DATA === 'undefined' || !PATCH_DATA || PATCH_DATA.length === 0) return "";
    const today = new Date();
    const todayZero = new Date(today.getFullYear(), today.getMonth(), today.getDate());
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
let isCharAscending = false;   // 角色順序 (false: 最新在前 ▼, true: 最舊在前 ▲)
let isPatchAscending = false;  // 版本順序 (false: 最新在左 ◀, true: 最舊在左 ▶)
let isShowPreview = localStorage.getItem('hsr_show_preview') !== null ? (localStorage.getItem('hsr_show_preview') === 'true') : true;

// 主表格渲染與初始化
async function initTracker() {
    try {
        const resDate = await fetch('js/characters.js');
        if (resDate.ok) {
            const text = await resDate.text();
            const match = text.match(/\/\/\s*更新日期[:：]\s*([0-9\/]+)/);
            if (match && match[1]) {
                document.getElementById('update-date-text').textContent = match[1];
            } else {
                document.getElementById('update-date-text').textContent = "未知";
            }
        } else {
            document.getElementById('update-date-text').textContent = "未知";
        }
    } catch (error) {
        console.warn("無法讀取本地更新日期:", error);
        document.getElementById('update-date-text').textContent = "未知";
    }

    try {
        const res = await fetch('https://raw.githubusercontent.com/Mar-7th/StarRailRes/master/index_new/cht/characters.json');
        if (res.ok) {
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

            RAW_CHARACTERS.forEach(char => {
                const searchName = normalize(char.name);
                if (avatarMap[searchName] && !char.avatar) {
                    char.avatar = avatarMap[searchName];
                }
            });
        }
    } catch (error) {
        console.warn("頭像庫連線失敗，將使用備用頭像：", error);
    }

    renderTable();
    setupEventListeners();
}

// 🔄 核心渲染表格邏輯
function updateTableColumnIndices(table) {
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

    const pathOrder = (typeof PATH_ORDER !== 'undefined') ? PATH_ORDER : ["毀滅", "巡獵", "智識", "同諧", "虛無", "存護", "豐饒", "記憶", "歡愉"];
    const uniquePaths = pathOrder.filter(p => activeCharacters.some(c => c.path === p));
    const elemOrder = (typeof ELEM_ORDER !== 'undefined') ? ELEM_ORDER : ["物理", "火", "冰", "雷", "風", "量子", "虛數", "未知"];
    const uniqueElems = elemOrder.filter(e => activeCharacters.some(c => c.elem === e));

    const currentCheckedVersions = new Set(Array.from(document.querySelectorAll('.version-item:checked')).map(i => i.value));
    const currentCheckedPaths = new Set(Array.from(document.querySelectorAll('.path-item:checked')).map(i => i.value));
    const currentCheckedElems = new Set(Array.from(document.querySelectorAll('.elem-item:checked')).map(i => i.value));

    const versionContainer = document.getElementById('version-items-container');
    if (versionContainer) {
        versionContainer.innerHTML = uniqueVersions.map(v => `<label><input type="checkbox" class="version-item" value="${escapeHtml(v)}" ${currentCheckedVersions.has(v) ? 'checked' : ''}> ${escapeHtml(v)}</label>`).join('');
    }

    const pathContainer = document.getElementById('path-items-container');
    if (pathContainer) {
        pathContainer.innerHTML = uniquePaths.map(p => {
            const iconUrl = (typeof PATH_ICONS !== 'undefined' && PATH_ICONS[p]) ? PATH_ICONS[p] : "";
            const iconHtml = iconUrl ? `<img src="${escapeHtml(iconUrl)}" style="width: 16px; height: 16px; flex-shrink: 0; filter: drop-shadow(0 0 1.5px rgba(0,0,0,0.9));" alt="${escapeHtml(p)}">` : "";
            return `<label><input type="checkbox" class="path-item" value="${escapeHtml(p)}" ${currentCheckedPaths.has(p) ? 'checked' : ''}> ${iconHtml}${escapeHtml(p)}</label>`;
        }).join('');
    }
    
    const elemContainer = document.getElementById('elem-items-container');
    if (elemContainer) {
        elemContainer.innerHTML = uniqueElems.map(e => {
            const iconUrl = (typeof ELEM_ICONS !== 'undefined' && ELEM_ICONS[e]) ? ELEM_ICONS[e] : "";
            const iconHtml = iconUrl ? `<img src="${escapeHtml(iconUrl)}" style="width: 16px; height: 16px; flex-shrink: 0; filter: drop-shadow(0 0 1.5px rgba(0,0,0,0.9));" alt="${escapeHtml(e)}">` : "";
            return `<label><input type="checkbox" class="elem-item" value="${escapeHtml(e)}" ${currentCheckedElems.has(e) ? 'checked' : ''}> ${iconHtml}${escapeHtml(e)}</label>`;
        }).join('');
    }

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

function buildTableHeaderHtml(displayPatches, totalChars, activePatchName) {
    let html = '<thead><tr>';
    html += `<th rowspan="2" class="top-left-cell">
        <div class="top-left-widget">
            <div class="btn-group">
                <button type="button" id="sort-char-btn" class="table-sort-btn" title="切換角色登場順序">角色 ${isCharAscending ? '▲' : '▼'}</button>
                <button type="button" id="sort-patch-btn" class="table-sort-btn" title="切換時間軸順序">版本 ${isPatchAscending ? '◀' : '▶'}</button>
            </div>
            <div class="table-count-badge" id="table-count-badge" title="符合條件的角色數量 / 總角色數量">共 ${totalChars} 位</div>
        </div>
    </th>`;

    displayPatches.forEach(p => {
        const isCurrent = (p.patch === activePatchName);
        const isPreview = Boolean(p.isPreview);
        let colClass = '';
        if (isCurrent) colClass = ' class="current-patch-col"';
        else if (isPreview) colClass = ' class="preview-patch-col"';
        html += `<th${colClass}>${formatHeaderDate(p.date)}</th>`;
    });

    html += `</tr><tr>`;
    displayPatches.forEach(p => {
        const isCurrent = (p.patch === activePatchName);
        const isPreview = Boolean(p.isPreview);
        let colClass = '';
        if (isCurrent) colClass = ' class="current-patch-col"';
        else if (isPreview) colClass = ' class="preview-patch-col"';
        html += `<th${colClass}>${p.patch}</th>`;
    });
    html += '</tr></thead>';
    return html;
}

function getHistoryElement(char, patch, pIdx, state, patchIndexMap) {
    if (char.isCollab) {
        const collabStart = char.isCollab;
        const sIdx = patchIndexMap.has(collabStart) ? patchIndexMap.get(collabStart) : -1;
        const spanCount = Math.min(5, sIdx);

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
        collabSpanAdded: false,
        patchesListLength: patchesList.length
    };

    patchesList.forEach((patch, pIdx) => {
        const element = getHistoryElement(char, patch, pIdx, state, patchIndexMap);
        if (element) {
            history.push(element);
        }
    });

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

    finalHistory.forEach((cell, cellIdx) => {
        if (cell.status === 'HIDDEN') return;

        const patchObj = displayPatches[cellIdx];
        const isCurrentCol = patchObj && (patchObj.patch === activePatchName);
        const isPreviewCol = patchObj && Boolean(patchObj.isPreview);
        let currentColClass = '';
        if (isCurrentCol) currentColClass = ' current-patch-col';
        else if (isPreviewCol) currentColClass = ' preview-patch-col';

        const cellHasBuff = char.buffs && patchObj && char.buffs.includes(patchObj.patch);
        const buffBadgeHtml = cellHasBuff ? '<span class="buff-badge" title="【礪爍新輝】角色能力加強">▲</span>' : '';
        const buffTitleAttr = cellHasBuff ? ' title="【礪爍新輝】角色能力加強"' : '';

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
    const pathIconUrl = PATH_ICONS[char.path] || "";
    const seqNum = isCharAscending ? (index + 1) : (totalChars - index);

    const charType = getCharacterType(char);
    const hasBuff = char.buffs && char.buffs.length > 0;
    const majorVer = getCharDebutMajorVersion(char, patchesList, patchIndexMap);
    const debutVer = getCharDebutVersion(char, patchesList, patchIndexMap);

    const isCharPreview = Boolean(char.isPreview);
    const stats = calculateCharStats(char, patchesList, activePatchName, patchIndexMap);
    const statsTooltip = getCharacterTooltip(char, stats, debutVer, isCharPreview);

    let html = `<tr data-path="${escapeHtml(char.path)}" data-elem="${escapeHtml(char.elem)}" data-type="${charType}" data-has-buff="${hasBuff}" data-major-version="${escapeHtml(majorVer)}" data-name="${escapeHtml(char.name)}" data-is-preview="${isCharPreview}">
        <td class="bg-${escapeHtml(char.elem)}">
            <div class="char-info-cell" title="${escapeHtml(statsTooltip)}">
                <span class="char-seq">${seqNum}</span>
                ${pathIconUrl ? `<img src="${pathIconUrl}" class="char-path-icon" title="${escapeHtml(char.path)}">` : '<div class="char-path-icon"></div>'}
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
    const table = document.getElementById('tracker');
    if (!table) return;

    // 0. 依據預覽開關篩選可用的版本與角色
    const activePatches = isShowPreview ? PATCH_DATA : PATCH_DATA.filter(p => !p.isPreview);
    const activeCharacters = isShowPreview ? RAW_CHARACTERS : RAW_CHARACTERS.filter(c => !c.isPreview);
    const patchesList = activePatches.map(p => p.patch);

    const patchIndexMap = new Map();
    patchesList.forEach((patch, index) => patchIndexMap.set(patch, index));

    // 1. 決定角色陣列順序
    const CHARACTERS = isCharAscending ? [...activeCharacters] : [...activeCharacters].reverse();
    const totalChars = CHARACTERS.length;

    // 2. 決定小版本陣列順序
    const displayPatches = isPatchAscending ? [...activePatches] : [...activePatches].reverse();

    const activePatchName = getCurrentPatchName();

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

function setupSortingListeners() {
    document.addEventListener('click', (e) => {
        if (e.target && e.target.id === 'sort-char-btn') {
            isCharAscending = !isCharAscending;
            renderTable();
        } else if (e.target && e.target.id === 'sort-patch-btn') {
            isPatchAscending = !isPatchAscending;
            renderTable();
        }
    });
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
    const versionBox = document.getElementById('version-select-box');
    const pathBox = document.getElementById('path-select-box');
    const elemBox = document.getElementById('elem-select-box');
    const typeBox = document.getElementById('type-select-box');
    
    const versionPanel = document.getElementById('version-panel');
    const pathPanel = document.getElementById('path-panel');
    const elemPanel = document.getElementById('elem-panel');
    const typePanel = document.getElementById('type-panel');

    versionBox?.addEventListener('click', (e) => {
        e.stopPropagation();
        pathPanel.classList.remove('show');
        elemPanel.classList.remove('show');
        typePanel.classList.remove('show');
        versionPanel.classList.toggle('show');
    });

    pathBox?.addEventListener('click', (e) => {
        e.stopPropagation();
        versionPanel.classList.remove('show');
        elemPanel.classList.remove('show');
        typePanel.classList.remove('show');
        pathPanel.classList.toggle('show');
    });

    elemBox?.addEventListener('click', (e) => {
        e.stopPropagation();
        versionPanel.classList.remove('show');
        pathPanel.classList.remove('show');
        typePanel.classList.remove('show');
        elemPanel.classList.toggle('show');
    });

    typeBox?.addEventListener('click', (e) => {
        e.stopPropagation();
        versionPanel.classList.remove('show');
        pathPanel.classList.remove('show');
        elemPanel.classList.remove('show');
        typePanel.classList.toggle('show');
    });

    document.addEventListener('click', () => {
        versionPanel?.classList.remove('show');
        pathPanel?.classList.remove('show');
        elemPanel?.classList.remove('show');
        typePanel?.classList.remove('show');
    });

    versionPanel?.addEventListener('click', (e) => e.stopPropagation());
    pathPanel?.addEventListener('click', (e) => e.stopPropagation());
    elemPanel?.addEventListener('click', (e) => e.stopPropagation());
    typePanel?.addEventListener('click', (e) => e.stopPropagation());
}

function setupUtilityToggles() {
    const buffToggleBtn = document.getElementById('buff-toggle-btn');
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

    buffToggleBtn?.addEventListener('click', () => {
        buffToggleBtn.classList.toggle('active');
        applyFilters();
    });
}

function setupSearchAndReset() {
    const searchInput = document.getElementById('char-search-input');
    const searchClearBtn = document.getElementById('search-clear-btn');
    const resetFiltersBtn = document.getElementById('reset-filters-btn');
    const buffToggleBtn = document.getElementById('buff-toggle-btn');

    function clearAllFilters() {
        document.querySelectorAll('.version-item, .path-item, .elem-item, .type-item').forEach(i => i.checked = false);
        if (searchInput) searchInput.value = '';
        buffToggleBtn?.classList.remove('active');
        applyFilters();
    }

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
    if (exportImgBtn && typeof html2canvas !== 'undefined') {
        exportImgBtn.addEventListener('click', async () => {
            let cloneContainer = null;
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

                cloneContainer = document.createElement('div');
                cloneContainer.style.position = 'absolute';
                cloneContainer.style.left = '-9999px';
                cloneContainer.style.top = '-9999px';
                cloneContainer.style.width = 'max-content';
                cloneContainer.style.background = '#1e1e1e';
                cloneContainer.style.padding = '12px';
                cloneContainer.style.zIndex = '-9999';

                const clonedTable = table.cloneNode(true);
                
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

                // 🌟 關鍵修復：先掛載到 DOM 樹上，才能正常操作與繪製
                cloneContainer.appendChild(clonedTable);
                document.body.appendChild(cloneContainer);

                // 🌟 關鍵修復：強行取消所有凍結視窗 (sticky) 避免 html2canvas 算錯座標把表頭/角色欄甩出去
                clonedTable.querySelectorAll('th, td, thead, tr, div, span').forEach(el => {
                    const compStyle = window.getComputedStyle(el);
                    if (compStyle.position === 'sticky') {
                        el.style.position = 'relative';
                    }
                    if (el.classList.contains('buff-badge')) {
                        el.style.position = 'absolute';
                    }
                    el.style.boxShadow = 'none';
                    el.classList.remove('col-highlight');
                });

                // 🌟 確保包含角標的儲存格有 relative 作為定位基準
                clonedTable.querySelectorAll('td, th').forEach(cell => {
                    if (cell.querySelector('.buff-badge')) {
                        cell.style.position = 'relative';
                    }
                });

                clonedTable.style.zoom = '1';

                const imgs = Array.from(clonedTable.querySelectorAll('img'));
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

                const canvas = await html2canvas(clonedTable, {
                    backgroundColor: '#1e1e1e',
                    scale: 2,
                    useCORS: true,
                    logging: false
                });

                document.body.removeChild(cloneContainer);
                cloneContainer = null;

                const imgData = canvas.toDataURL('image/png');
                const newTab = window.open();
                if (newTab) {
                    newTab.document.write(`
                        <!DOCTYPE html>
                        <html lang="zh-TW">
                        <head>
                            <meta charset="UTF-8">
                            <title>星穹鐵道_限定躍遷一覽表_${new Date().toISOString().slice(0, 10)}</title>
                            <style>
                                body {
                                    margin: 0;
                                    background: #121212;
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
                if (cloneContainer && cloneContainer.parentNode) {
                    cloneContainer.parentNode.removeChild(cloneContainer);
                }
                exportImgBtn.textContent = '📷 截圖';
                exportImgBtn.disabled = false;
            }
        });
    }
}

function setupTableInteractions() {
    const trackerTable = document.getElementById('tracker');
    trackerTable?.addEventListener('click', (e) => {
        if (e.target?.id !== 'empty-reset-btn') return;
        document.querySelectorAll('.version-item, .path-item, .elem-item, .type-item').forEach(i => { i.checked = false; });
        const searchInputEl = document.getElementById('char-search-input');
        const buffToggleBtnEl = document.getElementById('buff-toggle-btn');
        if (searchInputEl) searchInputEl.value = '';
        buffToggleBtnEl?.classList.remove('active');
        applyFilters();
    });

    trackerTable?.addEventListener('mouseover', (e) => {
        if (window.matchMedia && window.matchMedia('(hover: none)').matches) return;

        const cell = e.target.closest('td, th');
        if (!cell || cell.closest('tr')?.classList.contains('empty-row')) return;

        if (cell.colSpan > 1) {
            trackerTable.querySelectorAll('.col-highlight').forEach(c => c.classList.remove('col-highlight'));
            return;
        }

        const startCol = parseInt(cell.dataset.startCol, 10);
        const endCol = parseInt(cell.dataset.endCol, 10);

        trackerTable.querySelectorAll('.col-highlight').forEach(c => c.classList.remove('col-highlight'));

        if (endCol === 0 || isNaN(startCol)) return;

        if (!cachedTableCells) {
            cachedTableCells = trackerTable.querySelectorAll('th, td');
        }

        cachedTableCells.forEach(c => {
            if (c.colSpan > 1) return;

            const cStart = parseInt(c.dataset.startCol, 10);
            const cEnd = parseInt(c.dataset.endCol, 10);
            if (cEnd >= startCol && cStart <= endCol && cEnd > 0) {
                c.classList.add('col-highlight');
            }
        });
    });

    trackerTable?.addEventListener('mouseleave', () => {
        trackerTable.querySelectorAll('.col-highlight').forEach(c => c.classList.remove('col-highlight'));
    });
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

    applyFilters();
}

function getFilterState() {
    const searchInput = document.getElementById('char-search-input');
    const buffToggleBtn = document.getElementById('buff-toggle-btn');
    
    return {
        selectedVersions: Array.from(document.querySelectorAll('.version-item')).filter(i => i.checked).map(i => i.value),
        selectedPaths: Array.from(document.querySelectorAll('.path-item')).filter(i => i.checked).map(i => i.value),
        selectedElems: Array.from(document.querySelectorAll('.elem-item')).filter(i => i.checked).map(i => i.value),
        selectedTypes: Array.from(document.querySelectorAll('.type-item')).filter(i => i.checked).map(i => i.value),
        keyword: searchInput && searchInput.value ? searchInput.value.trim().toLowerCase() : '',
        onlyBuffs: buffToggleBtn ? buffToggleBtn.classList.contains('active') : false
    };
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

    if (versionBox) {
        if (state.selectedVersions.length === 0) versionBox.textContent = '實裝版本';
        else if (state.selectedVersions.length <= 2) versionBox.textContent = state.selectedVersions.join(', ');
        else versionBox.textContent = `${state.selectedVersions[0]} 等 ${state.selectedVersions.length} 個`;
    }

    if (pathBox) {
        if (state.selectedPaths.length === 0) pathBox.textContent = '命途';
        else if (state.selectedPaths.length <= 2) pathBox.textContent = state.selectedPaths.join(', ');
        else pathBox.textContent = `${state.selectedPaths[0]} 等 ${state.selectedPaths.length} 個`;
    }

    if (elemBox) {
        if (state.selectedElems.length === 0) elemBox.textContent = '屬性';
        else if (state.selectedElems.length <= 2) elemBox.textContent = state.selectedElems.join(', ');
        else elemBox.textContent = `${state.selectedElems[0]} 等 ${state.selectedElems.length} 個`;
    }

    const typeLabelMap = { 'normal': '限定躍遷', 'pool': '星緣', 'shop': '聚靈', 'collab': '聯動' };
    if (typeBox) {
        if (state.selectedTypes.length === 0) typeBox.textContent = '取得方法';
        else if (state.selectedTypes.length <= 2) typeBox.textContent = state.selectedTypes.map(t => typeLabelMap[t]).join(', ');
        else typeBox.textContent = `${typeLabelMap[state.selectedTypes[0]]} 等 ${state.selectedTypes.length} 個`;
    }
}

function isRowMatchingFilters(row, state) {
    const rowMajorVer = row.getAttribute('data-major-version');
    const rowPath = row.getAttribute('data-path');
    const rowElem = row.getAttribute('data-elem');
    const rowType = row.getAttribute('data-type');
    const hasBuffAttr = row.getAttribute('data-has-buff') === 'true';
    const rowName = row.getAttribute('data-name').toLowerCase();

    const matchVersion = state.selectedVersions.length === 0 || state.selectedVersions.includes(rowMajorVer);
    const matchPath = state.selectedPaths.length === 0 || state.selectedPaths.includes(rowPath);
    const matchElem = state.selectedElems.length === 0 || state.selectedElems.includes(rowElem);
    const matchType = state.selectedTypes.length === 0 || state.selectedTypes.includes(rowType);
    const matchName = state.keyword === '' || rowName.includes(state.keyword);
    const matchBuff = !state.onlyBuffs || hasBuffAttr;

    return matchVersion && matchPath && matchElem && matchType && matchName && matchBuff;
}

function filterTableRows(table, state) {
    const rows = table.querySelectorAll('tbody tr:not(.empty-row)');
    let visibleCount = 0;
    const totalChars = rows.length;

    rows.forEach(row => {
        if (isRowMatchingFilters(row, state)) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
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
        calculateGaps
    };
}

// Additional exports for refactored renderTable
if (typeof module !== 'undefined' && module.exports) {
    Object.assign(module.exports, {
        getHistoryElement,
        getCharacterType,
        buildCharacterHistory,
        getCharacterTooltip,
        buildTableHeaderHtml
    });
}

// Export initTracker for testing
if (typeof module !== 'undefined' && module.exports) {
    Object.assign(module.exports, {
        initTracker,
        updateTableColumnIndices
    });
}

// Export additional helpers for testing
if (typeof module !== 'undefined' && module.exports) {
    Object.assign(module.exports, {
        renderTable,
        buildCharacterRowHtml,
        buildHistoryCellsHtml
    });
}
