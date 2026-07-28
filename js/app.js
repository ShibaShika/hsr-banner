/* ==========================================================================
   崩壞：星穹鐵道 - 限定躍遷一覽表 主應用程式邏輯 (app.js)
   ========================================================================== */

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

// 🔍 計算角色的精確登場小版本 (如：4.4上)
function getCharDebutVersion(char, patchesList) {
    let earliestPatch = null;

    if (char.isCollab) {
        earliestPatch = char.isCollab;
    } else if (char.runs && char.runs.length > 0) {
        const runIndices = char.runs.map(p => patchesList.indexOf(p)).filter(idx => idx !== -1);
        if (runIndices.length > 0) {
            const minIdx = Math.min(...runIndices);
            earliestPatch = patchesList[minIdx];
        }
    } else if (char.term && char.term.patch) {
        earliestPatch = char.term.patch;
    }

    return earliestPatch || "未登場";
}

// 🔍 智慧計算角色的首次登場「大版本號」（如：1.x, 2.x, 3.x）
function getCharDebutMajorVersion(char, patchesList) {
    let earliestPatch = null;

    if (char.isCollab) {
        earliestPatch = char.isCollab;
    } else if (char.runs && char.runs.length > 0) {
        const runIndices = char.runs.map(p => patchesList.indexOf(p)).filter(idx => idx !== -1);
        if (runIndices.length > 0) {
            const minIdx = Math.min(...runIndices);
            earliestPatch = patchesList[minIdx];
        }
    } else if (char.term && char.term.patch) {
        earliestPatch = char.term.patch;
    }

    if (earliestPatch) {
        const majorNum = earliestPatch.split('.')[0];
        return `${majorNum}.x`;
    }
    return "未知";
}

// 📊 智慧統計分析演算法 (含連續小版本自動合併邏輯)
function calculateCharStats(char, patchesList, activePatchName) {
    if (char.isCollab) {
        return { isCollab: true };
    }

    const currentPatchIdx = patchesList.indexOf(activePatchName);
    let validEndIdx = currentPatchIdx !== -1 ? currentPatchIdx : patchesList.length - 1;

    let isTermActive = false;
    let termLabel = '';
    if (char.term && char.term.patch) {
        const termIdx = patchesList.indexOf(char.term.patch);
        if (termIdx !== -1 && termIdx <= validEndIdx) {
            validEndIdx = termIdx;
            isTermActive = true;
            termLabel = char.term.type === 'pool' ? '星緣' : '聚靈';
        }
    }

    const indices = (char.runs || [])
        .map(p => patchesList.indexOf(p))
        .filter(idx => idx !== -1 && idx <= validEndIdx)
        .sort((a, b) => a - b);

    // 將連續小版本 (如 4.1上 + 4.1下) 自動合併為「同一次/同期 UP 活動」
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

    const totalRuns = events.length;

    if (totalRuns === 0) {
        return {
            totalRuns: '0',
            currentGap: '-',
            maxGap: '-',
            isOverdue: false,
            isTermActive: false,
            termLabel: ''
        };
    }

    const lastEvent = events[events.length - 1];
    const currentGap = validEndIdx - lastEvent.end;

    if (isTermActive) {
        let maxGap = '-';
        if (totalRuns >= 2) {
            const gaps = [];
            for (let i = 1; i < events.length; i++) {
                gaps.push(events[i].start - events[i - 1].end - 1);
            }
            maxGap = `${Math.max(...gaps)}`;
        }
        return {
            totalRuns: `${totalRuns}`,
            currentGap: `已加入${termLabel}`,
            maxGap: maxGap,
            isOverdue: false,
            isTermActive: true,
            termLabel
        };
    }

    if (totalRuns === 1) {
        return {
            totalRuns: '1',
            currentGap: `${currentGap}`,
            maxGap: '-',
            isOverdue: false,
            isTermActive: false,
            termLabel: ''
        };
    }

    const gaps = [];
    for (let i = 1; i < events.length; i++) {
        gaps.push(events[i].start - events[i - 1].end - 1);
    }
    const maxHistoricalGap = Math.max(...gaps);
    const isOverdue = currentGap > maxHistoricalGap;

    return {
        totalRuns: `${totalRuns}`,
        currentGap: `${currentGap}`,
        maxGap: `${maxHistoricalGap}`,
        isOverdue,
        isTermActive: false,
        termLabel: ''
    };
}

// 狀態控制變數
let isCharAscending = false;   // 角色順序 (false: 最新在前 ▼, true: 最舊在前 ▲)
let isPatchAscending = false;  // 版本順序 (false: 最新在左 ◀, true: 最舊在左 ▶)

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
function renderTable() {
    const table = document.getElementById('tracker');
    const patchesList = PATCH_DATA.map(p => p.patch);

    // 1. 決定角色陣列順序
    let CHARACTERS = [...RAW_CHARACTERS].reverse();
    if (isCharAscending) {
        CHARACTERS.reverse();
    }
    const totalChars = CHARACTERS.length;

    // 2. 決定小版本陣列順序
    let displayPatches = [...PATCH_DATA].reverse();
    if (isPatchAscending) {
        displayPatches.reverse();
    }

    const activePatchName = getCurrentPatchName();

    // 解析大版本選單
    const versionSet = new Set();
    CHARACTERS.forEach(char => {
        const majorVer = getCharDebutMajorVersion(char, patchesList);
        if (majorVer !== "未知") {
            versionSet.add(majorVer);
        }
    });
    const uniqueVersions = Array.from(versionSet).sort((a, b) => parseFloat(a) - parseFloat(b));

    const PATH_ORDER = ["毀滅", "巡獵", "智識", "同諧", "虛無", "存護", "豐饒", "記憶", "歡愉"];
    const uniquePaths = PATH_ORDER.filter(p => RAW_CHARACTERS.some(c => c.path === p));
    const uniqueElems = ELEM_ORDER.filter(e => RAW_CHARACTERS.some(c => c.elem === e));

    // 動態產生大版本選項
    const versionContainer = document.getElementById('version-items-container');
    if (versionContainer && versionContainer.children.length === 0) {
        versionContainer.innerHTML = uniqueVersions.map(v => `<label><input type="checkbox" class="version-item" value="${v}"> ${v}</label>`).join('');
    }

    // 動態產生命途選項
    const pathContainer = document.getElementById('path-items-container');
    if (pathContainer && pathContainer.children.length === 0) {
        pathContainer.innerHTML = uniquePaths.map(p => {
            const iconUrl = (typeof PATH_ICONS !== 'undefined' && PATH_ICONS[p]) ? PATH_ICONS[p] : "";
            const iconHtml = iconUrl ? `<img src="${iconUrl}" style="width: 16px; height: 16px; flex-shrink: 0; filter: drop-shadow(0 0 1.5px rgba(0,0,0,0.9));" alt="${p}">` : "";
            return `<label><input type="checkbox" class="path-item" value="${p}"> ${iconHtml}${p}</label>`;
        }).join('');
    }
    
    // 動態產生屬性選項
    const elemContainer = document.getElementById('elem-items-container');
    if (elemContainer && elemContainer.children.length === 0) {
        elemContainer.innerHTML = uniqueElems.map(e => {
            const iconUrl = (typeof ELEM_ICONS !== 'undefined' && ELEM_ICONS[e]) ? ELEM_ICONS[e] : "";
            const iconHtml = iconUrl ? `<img src="${iconUrl}" style="width: 16px; height: 16px; flex-shrink: 0; filter: drop-shadow(0 0 1.5px rgba(0,0,0,0.9));" alt="${e}">` : "";
            return `<label><input type="checkbox" class="elem-item" value="${e}"> ${iconHtml}${e}</label>`;
        }).join('');
    }

    // 動態產生取得方法選項
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

    // 構建表頭 1 (雙軸控制控制項)
    let html = '<thead><tr>';
    html += `<th rowspan="2" class="top-left-cell">
        <div class="top-left-widget">
            <div class="btn-group">
                <button type="button" id="sort-char-btn" class="table-sort-btn" title="切換角色登場順序">角色 ${isCharAscending ? '▲' : '▼'}</button>
                <button type="button" id="sort-patch-btn" class="table-sort-btn" title="切換時間軸順序">版本 ${isPatchAscending ? '▶' : '◀'}</button>
            </div>
            <div class="table-count-badge" id="table-count-badge" title="符合條件的角色數量 / 總角色數量">共 ${totalChars} 位</div>
        </div>
    </th>`;

    displayPatches.forEach(p => {
        const isCurrent = (p.patch === activePatchName);
        const colClass = isCurrent ? ' class="current-patch-col"' : '';
        html += `<th${colClass}>${formatHeaderDate(p.date)}</th>`;
    });

    // 構建表頭 2 (版本號)
    html += `</tr><tr>`;
    displayPatches.forEach(p => {
        const isCurrent = (p.patch === activePatchName);
        const colClass = isCurrent ? ' class="current-patch-col"' : '';
        html += `<th${colClass}>${p.patch}</th>`;
    });
    html += '</tr></thead><tbody>';
    
    // 構建表格主體內容
    CHARACTERS.forEach((char, index) => {
        const fallbackUrl = getFallbackAvatar(char.name);
        const avatarUrl = char.avatar ? char.avatar : fallbackUrl;
        const pathIconUrl = PATH_ICONS[char.path] || "";
        const seqNum = isCharAscending ? (index + 1) : (totalChars - index);
        
        let charType = 'normal';
        if (char.isCollab) {
            charType = 'collab';
        } else if (char.term) {
            if (char.term.type === 'pool') charType = 'pool';
            else if (char.term.type === 'shop') charType = 'shop';
        }

        const hasBuff = char.buffs && char.buffs.length > 0;
        const majorVer = getCharDebutMajorVersion(char, patchesList);
        const debutVer = getCharDebutVersion(char, patchesList);

        const stats = calculateCharStats(char, patchesList, activePatchName);
        let statsTooltip = "";
        if (stats.isCollab) {
            statsTooltip = `【${char.name} - 躍遷資訊】\n• 實裝版本：${debutVer}\n• 長期聯動角色`;
        } else if (stats.isTermActive) {
            statsTooltip = `【${char.name} - 躍遷資訊】\n• 實裝版本：${debutVer}\n• 目前狀態：${stats.currentGap}\n• 歷史最長等待：${stats.maxGap}\n• 總UP次數：${stats.totalRuns}`;
        } else {
            const overdueFlag = stats.isOverdue ? " ⚠️ (超期警報!)" : "";
            statsTooltip = `【${char.name} - 躍遷資訊】\n• 實裝版本：${debutVer}\n• 目前等待：${stats.currentGap}${overdueFlag}\n• 歷史最長等待：${stats.maxGap}\n• 總UP次數：${stats.totalRuns}`;
        }
        
        html += `<tr data-path="${char.path}" data-elem="${char.elem}" data-type="${charType}" data-has-buff="${hasBuff}" data-major-version="${majorVer}" data-name="${char.name}">
            <td class="bg-${char.elem}">
                <div class="char-info-cell" title="${statsTooltip}">
                    <span class="char-seq">${seqNum}</span>
                    ${pathIconUrl ? `<img src="${pathIconUrl}" class="char-path-icon" title="${char.path}">` : '<div class="char-path-icon"></div>'}
                    <img src="${avatarUrl}" class="char-avatar" alt="${char.name}" onerror="this.onerror=null; this.src='${fallbackUrl}';">
                    <span class="char-name">${char.name}</span>
                </div>
            </td>`;
        
        let history = [];
        let currentGap = 0;
        let hasReleased = false;
        let collabSpanAdded = false;

        patchesList.forEach((patch, pIdx) => {
            let cellStatus = 'NONE';
            
            if (char.isCollab) {
                const collabStart = char.isCollab;
                const sIdx = patchesList.indexOf(collabStart);
                const spanCount = Math.min(5, sIdx);
                
                if (pIdx < sIdx) {
                    if (pIdx === sIdx - spanCount) {
                        if (!collabSpanAdded) {
                            history.push({ status: 'COLLAB_SPAN', count: spanCount });
                            collabSpanAdded = true;
                        }
                        return;
                    } else if (pIdx > sIdx - spanCount) {
                        return;
                    }
                } else {
                    const lIdx = patchesList.length - 1; 
                    if (pIdx === sIdx || pIdx === lIdx) {
                        cellStatus = 'COLLAB_START'; 
                    } else {
                        cellStatus = 'COLLAB_EMPTY'; 
                    }
                }
            }
            
            if (char.term) {
                const termIdx = patchesList.indexOf(char.term.patch);
                if (pIdx === termIdx) {
                    history.push({ status: 'TERM_START', type: char.term.type });
                    return;
                } else if (pIdx > termIdx) {
                    history.push({ status: 'TERM_EMPTY', type: char.term.type });
                    return;
                }
            }

            if (cellStatus === 'COLLAB_START') {
                history.push({ status: 'COLLAB' });
            } else if (cellStatus === 'COLLAB_EMPTY') {
                history.push({ status: 'COLLAB_EMPTY' });
            } else if (char.runs && char.runs.includes(patch)) {
                hasReleased = true;
                currentGap = 0;
                history.push({ status: 'UP' });
            } else {
                if (hasReleased) {
                    currentGap++;
                    history.push({ status: 'WAIT', gap: currentGap });
                } else {
                    history.push({ status: 'NONE' });
                }
            }
        });

        let finalHistory = history.reverse();
        if (isPatchAscending) {
            finalHistory.reverse();
        }

        finalHistory.forEach((cell, cellIdx) => {
            const patchObj = displayPatches[cellIdx];
            const isCurrentCol = patchObj && (patchObj.patch === activePatchName);
            const currentColClass = isCurrentCol ? ' current-patch-col' : '';

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

            if (cell.status === 'UP' || cell.status === 'COLLAB') {
                cls = 'img-cell';
                content = `${buffBadgeHtml}<img src="${avatarUrl}" class="grid-avatar" alt="${char.name}" onerror="this.onerror=null; this.src='${fallbackUrl}';"${buffTitleAttr}>`;
            } else if (cell.status === 'COLLAB_EMPTY') {
                cls = `collab-empty bg-${char.elem}`;
                content = buffBadgeHtml;
            } else if (cell.status === 'TERM_START') {
                cls = cell.type === 'pool' ? 'term-pool' : 'term-shop';
                content = `${buffBadgeHtml}${cell.type === 'pool' ? '星緣' : '聚靈'}`;
            } else if (cell.status === 'TERM_EMPTY') {
                cls = cell.type === 'pool' ? 'term-pool-empty' : 'term-shop-empty';
                content = buffBadgeHtml;
            } else if (cell.status === 'NONE') {
                cls = 'none';
                content = `${buffBadgeHtml}-`;
            } else {
                content = `${buffBadgeHtml}${cell.gap}`;
                if (cell.gap <= 3) cls = 'w-low';
                else if (cell.gap <= 7) cls = 'w-med';
                else if (cell.gap <= 12) cls = 'w-high';
                else cls = 'w-crit';
            }
            html += `<td class="${cls}${currentColClass}"${buffTitleAttr}>${content}</td>`;
        });
        html += `</tr>`;
    });
    html += '</tbody>';
    
    table.innerHTML = html;

    function updateColumnIndices() {
        const rows = table.rows;
        for (let r = 0; r < rows.length; r++) {
            let colIdx = 0;
            for (let c = 0; c < rows[r].cells.length; c++) {
                const cell = rows[r].cells[c];
                const span = cell.colSpan || 1;
                cell.dataset.startCol = colIdx;
                cell.dataset.endCol = colIdx + span - 1;
                colIdx += span;
            }
        }
    }
    updateColumnIndices();

    const jumpLatestBtn = document.getElementById('jump-latest-btn');
    const jumpOldestBtn = document.getElementById('jump-oldest-btn');
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

    rebindControlListeners();
}

function setupEventListeners() {
    document.addEventListener('click', (e) => {
        if (e.target && e.target.id === 'sort-char-btn') {
            isCharAscending = !isCharAscending;
            renderTable();
        } else if (e.target && e.target.id === 'sort-patch-btn') {
            isPatchAscending = !isPatchAscending;
            renderTable();
        }
    });

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

    const versionBox = document.getElementById('version-select-box');
    const pathBox = document.getElementById('path-select-box');
    const elemBox = document.getElementById('elem-select-box');
    const typeBox = document.getElementById('type-select-box');
    
    const versionPanel = document.getElementById('version-panel');
    const pathPanel = document.getElementById('path-panel');
    const elemPanel = document.getElementById('elem-panel');
    const typePanel = document.getElementById('type-panel');

    const buffToggleBtn = document.getElementById('buff-toggle-btn');
    const searchInput = document.getElementById('char-search-input');
    const searchClearBtn = document.getElementById('search-clear-btn');
    const resetFiltersBtn = document.getElementById('reset-filters-btn');
    const exportImgBtn = document.getElementById('export-img-btn');

    let onlyBuffs = false;
    buffToggleBtn?.addEventListener('click', () => {
        onlyBuffs = !onlyBuffs;
        buffToggleBtn.classList.toggle('active', onlyBuffs);
        applyFilters();
    });

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

    function clearAllFilters() {
        document.querySelectorAll('.version-item, .path-item, .elem-item, .type-item').forEach(i => i.checked = false);
        if (searchInput) searchInput.value = '';
        onlyBuffs = false;
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

    // 📷 匯出截圖邏輯 (修復 html2canvas sticky 錯位毀滅性 Bug)
    if (exportImgBtn && typeof html2canvas !== 'undefined') {
        exportImgBtn.addEventListener('click', async () => {
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

                const cloneContainer = document.createElement('div');
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
                    if (el.classList.contains('buff-badge')) {
                        el.style.position = 'absolute';
                    } else {
                        el.style.position = 'static';
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
                exportImgBtn.textContent = '📷 截圖';
                exportImgBtn.disabled = false;
            }
        });
    }

    searchInput?.addEventListener('input', applyFilters);
    searchInput?.addEventListener('search', applyFilters);

    const trackerTable = document.getElementById('tracker');
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

        const allCells = trackerTable.querySelectorAll('th, td');
        allCells.forEach(c => {
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

function rebindControlListeners() {
    const versionItems = document.querySelectorAll('.version-item');
    const pathItems = document.querySelectorAll('.path-item');
    const elemItems = document.querySelectorAll('.elem-item');
    const typeItems = document.querySelectorAll('.type-item');

    versionItems.forEach(item => item.removeEventListener('change', applyFilters));
    pathItems.forEach(item => item.removeEventListener('change', applyFilters));
    elemItems.forEach(item => item.removeEventListener('change', applyFilters));
    typeItems.forEach(item => item.removeEventListener('change', applyFilters));

    versionItems.forEach(item => item.addEventListener('change', applyFilters));
    pathItems.forEach(item => item.addEventListener('change', applyFilters));
    elemItems.forEach(item => item.addEventListener('change', applyFilters));
    typeItems.forEach(item => item.addEventListener('change', applyFilters));

    applyFilters();
}

function applyFilters() {
    const table = document.getElementById('tracker');
    if (!table) return;

    const selectedVersions = Array.from(document.querySelectorAll('.version-item')).filter(i => i.checked).map(i => i.value);
    const selectedPaths = Array.from(document.querySelectorAll('.path-item')).filter(i => i.checked).map(i => i.value);
    const selectedElems = Array.from(document.querySelectorAll('.elem-item')).filter(i => i.checked).map(i => i.value);
    const selectedTypes = Array.from(document.querySelectorAll('.type-item')).filter(i => i.checked).map(i => i.value);
    
    const searchInput = document.getElementById('char-search-input');
    const searchClearBtn = document.getElementById('search-clear-btn');
    const resetFiltersBtn = document.getElementById('reset-filters-btn');
    const buffToggleBtn = document.getElementById('buff-toggle-btn');
    
    const keyword = searchInput ? searchInput.value.trim().toLowerCase() : '';
    const onlyBuffs = buffToggleBtn ? buffToggleBtn.classList.contains('active') : false;

    if (searchClearBtn) {
        searchClearBtn.style.display = keyword !== '' ? 'block' : 'none';
    }

    const versionBox = document.getElementById('version-select-box');
    const pathBox = document.getElementById('path-select-box');
    const elemBox = document.getElementById('elem-select-box');
    const typeBox = document.getElementById('type-select-box');

    if (versionBox) versionBox.classList.toggle('active', selectedVersions.length > 0);
    if (pathBox) pathBox.classList.toggle('active', selectedPaths.length > 0);
    if (elemBox) elemBox.classList.toggle('active', selectedElems.length > 0);
    if (typeBox) typeBox.classList.toggle('active', selectedTypes.length > 0);

    const hasActiveFilter = selectedVersions.length > 0 || selectedPaths.length > 0 || selectedElems.length > 0 || selectedTypes.length > 0 || keyword !== '' || onlyBuffs;
    if (resetFiltersBtn) {
        resetFiltersBtn.style.display = hasActiveFilter ? 'inline-flex' : 'none';
    }

    if (versionBox) {
        if (selectedVersions.length === 0) versionBox.textContent = '實裝版本';
        else if (selectedVersions.length <= 2) versionBox.textContent = selectedVersions.join(', ');
        else versionBox.textContent = `${selectedVersions[0]} 等 ${selectedVersions.length} 個`;
    }

    if (pathBox) {
        if (selectedPaths.length === 0) pathBox.textContent = '命途';
        else if (selectedPaths.length <= 2) pathBox.textContent = selectedPaths.join(', ');
        else pathBox.textContent = `${selectedPaths[0]} 等 ${selectedPaths.length} 個`;
    }

    if (elemBox) {
        if (selectedElems.length === 0) elemBox.textContent = '屬性';
        else if (selectedElems.length <= 2) elemBox.textContent = selectedElems.join(', ');
        else elemBox.textContent = `${selectedElems[0]} 等 ${selectedElems.length} 個`;
    }

    const typeLabelMap = { 'normal': '限定躍遷', 'pool': '星緣', 'shop': '聚靈', 'collab': '聯動' };
    if (typeBox) {
        if (selectedTypes.length === 0) typeBox.textContent = '取得方法';
        else if (selectedTypes.length <= 2) typeBox.textContent = selectedTypes.map(t => typeLabelMap[t]).join(', ');
        else typeBox.textContent = `${typeLabelMap[selectedTypes[0]]} 等 ${selectedTypes.length} 個`;
    }

    const rows = table.querySelectorAll('tbody tr:not(.empty-row)');
    let visibleCount = 0;
    const totalChars = RAW_CHARACTERS.length;

    rows.forEach(row => {
        const rowMajorVer = row.getAttribute('data-major-version');
        const rowPath = row.getAttribute('data-path');
        const rowElem = row.getAttribute('data-elem');
        const rowType = row.getAttribute('data-type');
        const hasBuffAttr = row.getAttribute('data-has-buff') === 'true';
        const rowName = row.getAttribute('data-name').toLowerCase();

        const matchVersion = selectedVersions.length === 0 || selectedVersions.includes(rowMajorVer);
        const matchPath = selectedPaths.length === 0 || selectedPaths.includes(rowPath);
        const matchElem = selectedElems.length === 0 || selectedElems.includes(rowElem);
        const matchType = selectedTypes.length === 0 || selectedTypes.includes(rowType);
        const matchName = keyword === '' || rowName.includes(keyword);
        const matchBuff = !onlyBuffs || hasBuffAttr;

        if (matchVersion && matchPath && matchElem && matchType && matchName && matchBuff) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });

    const countBadge = document.getElementById('table-count-badge');
    if (countBadge) {
        if (visibleCount === totalChars) {
            countBadge.textContent = `共 ${totalChars} 位`;
        } else {
            countBadge.textContent = `${visibleCount}/${totalChars} 位`;
        }
    }

    let emptyRow = table.querySelector('tbody tr.empty-row');
    const totalCols = PATCH_DATA.length + 1;
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
        document.getElementById('empty-reset-btn')?.addEventListener('click', () => {
            document.querySelectorAll('.version-item, .path-item, .elem-item, .type-item').forEach(i => i.checked = false);
            if (searchInput) searchInput.value = '';
            if (buffToggleBtn) buffToggleBtn.classList.remove('active');
            applyFilters();
        });
    } else {
        if (emptyRow) {
            emptyRow.style.display = 'none';
        }
    }
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
