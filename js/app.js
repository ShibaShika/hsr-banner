/* ==========================================================================
   崩壞：星穹鐵道 - 限定躍遷一覽表 主應用程式邏輯 (app.js)
   ========================================================================== */

// 🎨 本地 SVG Data URI 備用頭像產生器 (徹底解決未實裝角色/無頭像時截圖黑屏問題)
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

// 📊 以【當前小版本】或【加入星緣/聚靈時的小版本】為基準計算角色歷史數據
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

    const totalRuns = indices.length;

    if (totalRuns === 0) {
        return {
            totalRuns: '0 次',
            currentGap: isTermActive ? `直接加入${termLabel}` : '未實裝/未登場',
            maxGap: '-',
            avgGap: '-',
            isTermActive,
            termLabel
        };
    }

    const lastRunIdx = indices[indices.length - 1];
    const currentGap = validEndIdx - lastRunIdx;

    if (totalRuns === 1) {
        return {
            totalRuns: '1 次',
            currentGap: `${currentGap} 個小版本`,
            maxGap: `${currentGap} 個小版本`,
            avgGap: `${currentGap} 個小版本`,
            isTermActive,
            termLabel
        };
    }

    const gaps = [];
    for (let i = 1; i < indices.length; i++) {
        gaps.push(indices[i] - indices[i - 1] - 1);
    }

    const maxGap = Math.max(...gaps, currentGap);
    const sumGaps = gaps.reduce((a, b) => a + b, 0);
    const avgGap = (sumGaps / gaps.length).toFixed(1);

    return {
        totalRuns: `${totalRuns} 次`,
        currentGap: `${currentGap} 個小版本`,
        maxGap: `${maxGap} 個小版本`,
        avgGap: `${avgGap} 個小版本`,
        isTermActive,
        termLabel
    };
}

// 主初始化函式
async function initTracker() {
    // 1. 動態讀取 characters.js 的更新日期註解
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

    // 2. 抓取 StarRailRes 官方頭像庫
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

    const CHARACTERS = [...RAW_CHARACTERS].reverse();
    const table = document.getElementById('tracker');
    const patchesList = PATCH_DATA.map(p => p.patch);
    const totalChars = CHARACTERS.length;
    
    const activePatchName = getCurrentPatchName();
    const reversedPatches = [...PATCH_DATA].reverse();

    // 自動解析資料庫中包含的所有大版本號 (如: 1.x, 2.x, 3.x, 4.x...)
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
    document.getElementById('version-items-container').innerHTML = uniqueVersions.map(v => {
        return `<label><input type="checkbox" class="version-item" value="${v}"> ${v} 角色</label>`;
    }).join('');

    // 動態產生命途選項
    document.getElementById('path-items-container').innerHTML = uniquePaths.map(p => {
        const iconUrl = (typeof PATH_ICONS !== 'undefined' && PATH_ICONS[p]) ? PATH_ICONS[p] : "";
        const iconHtml = iconUrl ? `<img src="${iconUrl}" style="width: 16px; height: 16px; flex-shrink: 0; filter: drop-shadow(0 0 1.5px rgba(0,0,0,0.9));" alt="${p}">` : "";
        return `<label><input type="checkbox" class="path-item" value="${p}"> ${iconHtml}${p}</label>`;
    }).join('');
    
    // 動態產生屬性選項
    document.getElementById('elem-items-container').innerHTML = uniqueElems.map(e => {
        const iconUrl = (typeof ELEM_ICONS !== 'undefined' && ELEM_ICONS[e]) ? ELEM_ICONS[e] : "";
        const iconHtml = iconUrl ? `<img src="${iconUrl}" style="width: 16px; height: 16px; flex-shrink: 0; filter: drop-shadow(0 0 1.5px rgba(0,0,0,0.9));" alt="${e}">` : "";
        return `<label><input type="checkbox" class="elem-item" value="${e}"> ${iconHtml}${e}</label>`;
    }).join('');

    // 構建表頭 1 (合併左上角單元格，放置順序按鈕與角色計數)
    let html = '<thead><tr>';
    html += `<th rowspan="2" class="top-left-cell">
        <div class="top-left-widget">
            <button type="button" id="sort-order-btn" class="table-sort-btn" title="點擊切換登場順序 (最新/最舊)">順序 ⬇</button>
            <div class="table-count-badge" id="table-count-badge" title="符合條件的角色數量 / 總角色數量">共 ${totalChars} 位</div>
        </div>
    </th>`;

    reversedPatches.forEach(p => {
        const isCurrent = (p.patch === activePatchName);
        const colClass = isCurrent ? ' class="current-patch-col"' : '';
        html += `<th${colClass}>${formatHeaderDate(p.date)}</th>`;
    });

    // 構建表頭 2 (版本號)
    html += `</tr><tr>`;
    reversedPatches.forEach(p => {
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
        const seqNum = totalChars - index;
        
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

        // 📊 生成【躍遷資訊】Hover 提示 (已改用更精確的登場小版本)
        const stats = calculateCharStats(char, patchesList, activePatchName);
        let statsTooltip = "";
        if (stats.isCollab) {
            statsTooltip = `【${char.name} - 躍遷資訊】\n• 登場版本：${debutVer}\n• 長期聯動角色`;
        } else if (stats.isTermActive) {
            statsTooltip = `【${char.name} - 躍遷資訊】\n• 登場版本：${debutVer}\n• 加入${stats.termLabel}時等待：${stats.currentGap}\n• 歷史最長等待：${stats.maxGap}\n• 平均復刻週期：${stats.avgGap}\n• UP 登場總次數：${stats.totalRuns}`;
        } else {
            statsTooltip = `【${char.name} - 躍遷資訊】\n• 登場版本：${debutVer}\n• 目前等待：${stats.currentGap}\n• 歷史最長等待：${stats.maxGap}\n• 平均復刻週期：${stats.avgGap}\n• UP 登場總次數：${stats.totalRuns}`;
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

        history.reverse().forEach((cell, cellIdx) => {
            const patchObj = reversedPatches[cellIdx];
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
                html += `<td colspan="${cell.count}" class="collab-text${currentColClass}">${buffBadgeHtml}←${dateStr}後長期開放</td>`;
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

    // 精確直欄座標對應
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

    // 🔄 登場順序切換邏輯 (最新在上 ↔ 舊角色在上)
    const sortOrderBtn = document.getElementById('sort-order-btn');
    let isAscending = false;

    if (sortOrderBtn) {
        sortOrderBtn.addEventListener('click', () => {
            isAscending = !isAscending;
            sortOrderBtn.textContent = isAscending ? '順序 ⬆' : '順序 ⬇';

            const tbody = table.querySelector('tbody');
            const charRows = Array.from(tbody.querySelectorAll('tr:not(.empty-row)'));
            const emptyRow = tbody.querySelector('tr.empty-row');

            charRows.reverse().forEach(row => tbody.appendChild(row));
            if (emptyRow) tbody.appendChild(emptyRow);
        });
    }

    // === 綁定左右快速跳轉按鈕 ===
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

    // === 綁定篩選器邏輯 ===
    const versionBox = document.getElementById('version-select-box');
    const pathBox = document.getElementById('path-select-box');
    const elemBox = document.getElementById('elem-select-box');
    const typeBox = document.getElementById('type-select-box');
    
    const versionPanel = document.getElementById('version-panel');
    const pathPanel = document.getElementById('path-panel');
    const elemPanel = document.getElementById('elem-panel');
    const typePanel = document.getElementById('type-panel');
    
    const versionItems = versionPanel.querySelectorAll('.version-item');
    const pathItems = pathPanel.querySelectorAll('.path-item');
    const elemItems = elemPanel.querySelectorAll('.elem-item');
    const typeItems = typePanel.querySelectorAll('.type-item');

    const buffToggleBtn = document.getElementById('buff-toggle-btn');
    const searchInput = document.getElementById('char-search-input');
    const searchClearBtn = document.getElementById('search-clear-btn');
    const resetFiltersBtn = document.getElementById('reset-filters-btn');
    const exportImgBtn = document.getElementById('export-img-btn');

    let onlyBuffs = false;
    buffToggleBtn.addEventListener('click', () => {
        onlyBuffs = !onlyBuffs;
        buffToggleBtn.classList.toggle('active', onlyBuffs);
        applyFilters();
    });

    // 下拉選單點擊展開/隱藏 (互斥收合)
    versionBox.addEventListener('click', (e) => {
        e.stopPropagation();
        pathPanel.classList.remove('show');
        elemPanel.classList.remove('show');
        typePanel.classList.remove('show');
        versionPanel.classList.toggle('show');
    });

    pathBox.addEventListener('click', (e) => {
        e.stopPropagation();
        versionPanel.classList.remove('show');
        elemPanel.classList.remove('show');
        typePanel.classList.remove('show');
        pathPanel.classList.toggle('show');
    });

    elemBox.addEventListener('click', (e) => {
        e.stopPropagation();
        versionPanel.classList.remove('show');
        pathPanel.classList.remove('show');
        typePanel.classList.remove('show');
        elemPanel.classList.toggle('show');
    });

    typeBox.addEventListener('click', (e) => {
        e.stopPropagation();
        versionPanel.classList.remove('show');
        pathPanel.classList.remove('show');
        elemPanel.classList.remove('show');
        typePanel.classList.toggle('show');
    });

    // 點擊空白處自動收合所有選單
    document.addEventListener('click', () => {
        versionPanel.classList.remove('show');
        pathPanel.classList.remove('show');
        elemPanel.classList.remove('show');
        typePanel.classList.remove('show');
    });

    versionPanel.addEventListener('click', (e) => e.stopPropagation());
    pathPanel.addEventListener('click', (e) => e.stopPropagation());
    elemPanel.addEventListener('click', (e) => e.stopPropagation());
    typePanel.addEventListener('click', (e) => e.stopPropagation());

    // 🧹 清除所有篩選條件
    function clearAllFilters() {
        versionItems.forEach(i => i.checked = false);
        pathItems.forEach(i => i.checked = false);
        elemItems.forEach(i => i.checked = false);
        typeItems.forEach(i => i.checked = false);
        searchInput.value = '';
        onlyBuffs = false;
        buffToggleBtn.classList.remove('active');
        applyFilters();
    }

    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener('click', clearAllFilters);
    }

    // 點擊搜尋框內部的 ✕ 清空文字
    if (searchClearBtn) {
        searchClearBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            searchInput.value = '';
            applyFilters();
            searchInput.focus();
        });
    }

    // 📷 匯出圖片 (智慧裁切右側欄位 & 預載圖片防截圖黑屏)
    if (exportImgBtn && typeof html2canvas !== 'undefined') {
        exportImgBtn.addEventListener('click', async () => {
            try {
                exportImgBtn.textContent = '📷 繪製中...';
                exportImgBtn.disabled = true;

                const visibleRows = Array.from(table.querySelectorAll('tbody tr:not(.empty-row)')).filter(r => r.style.display !== 'none');

                if (visibleRows.length === 0) {
                    alert('目前沒有符合條件的角色可供截圖！');
                    return;
                }

                let maxActiveCol = 1;
                visibleRows.forEach(row => {
                    const cells = row.children;
                    let colIndex = 0;
                    for (let c = 0; c < cells.length; c++) {
                        const cell = cells[c];
                        const span = parseInt(cell.getAttribute('colspan') || '1', 10);
                        const isNone = cell.classList.contains('none');
                        
                        if (!isNone && colIndex > 0) {
                            const endCol = colIndex + span - 1;
                            if (endCol > maxActiveCol) {
                                maxActiveCol = endCol;
                            }
                        }
                        colIndex += span;
                    }
                });

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
                    let colIndex = 0;
                    cells.forEach(cell => {
                        const span = parseInt(cell.getAttribute('colspan') || '1', 10);
                        const endCol = colIndex + span - 1;

                        if (colIndex > maxActiveCol) {
                            cell.remove();
                        } else if (endCol > maxActiveCol) {
                            const newSpan = maxActiveCol - colIndex + 1;
                            cell.setAttribute('colspan', newSpan);
                        }
                        colIndex += span;
                    });
                });

                clonedTable.querySelectorAll('*').forEach(el => {
                    el.style.position = 'static';
                    el.style.boxShadow = 'none';
                    el.classList.remove('col-highlight');
                });
                clonedTable.style.zoom = '1';

                cloneContainer.appendChild(clonedTable);
                document.body.appendChild(cloneContainer);

                // 🌟 預先檢驗並等待所有圖片載入完成，若圖片載入失敗 (404/未實裝) 自動轉為本地 SVG Data URI，徹底解決截圖黑屏問題
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

                const link = document.createElement('a');
                link.download = `星穹鐵道_限定躍遷一覽表_${new Date().toISOString().slice(0, 10)}.png`;
                link.href = canvas.toDataURL('image/png');
                link.click();
            } catch (err) {
                console.error('截圖匯出失敗:', err);
                alert('截圖失敗，請重試！');
            } finally {
                exportImgBtn.textContent = '📷 截圖';
                exportImgBtn.disabled = false;
            }
        });
    }

    function applyFilters() {
        const selectedVersions = Array.from(versionItems).filter(i => i.checked).map(i => i.value);
        const selectedPaths = Array.from(pathItems).filter(i => i.checked).map(i => i.value);
        const selectedElems = Array.from(elemItems).filter(i => i.checked).map(i => i.value);
        const selectedTypes = Array.from(typeItems).filter(i => i.checked).map(i => i.value);
        const keyword = searchInput.value.trim().toLowerCase();

        if (searchClearBtn) {
            searchClearBtn.style.display = searchInput.value !== '' ? 'block' : 'none';
        }

        versionBox.classList.toggle('active', selectedVersions.length > 0);
        pathBox.classList.toggle('active', selectedPaths.length > 0);
        elemBox.classList.toggle('active', selectedElems.length > 0);
        typeBox.classList.toggle('active', selectedTypes.length > 0);

        const hasActiveFilter = selectedVersions.length > 0 || selectedPaths.length > 0 || selectedElems.length > 0 || selectedTypes.length > 0 || keyword !== '' || onlyBuffs;
        if (resetFiltersBtn) {
            resetFiltersBtn.style.display = hasActiveFilter ? 'inline-flex' : 'none';
        }

        if (selectedVersions.length === 0) {
            versionBox.textContent = '大版本';
        } else if (selectedVersions.length <= 2) {
            versionBox.textContent = selectedVersions.join(', ');
        } else {
            versionBox.textContent = `${selectedVersions[0]} 等 ${selectedVersions.length} 個`;
        }

        if (selectedPaths.length === 0) {
            pathBox.textContent = '命途';
        } else if (selectedPaths.length <= 2) {
            pathBox.textContent = selectedPaths.join(', ');
        } else {
            pathBox.textContent = `${selectedPaths[0]} 等 ${selectedPaths.length} 個`;
        }

        if (selectedElems.length === 0) {
            elemBox.textContent = '屬性';
        } else if (selectedElems.length <= 2) {
            elemBox.textContent = selectedElems.join(', ');
        } else {
            elemBox.textContent = `${selectedElems[0]} 等 ${selectedElems.length} 個`;
        }

        const typeLabelMap = { 'normal': '限定躍遷', 'pool': '星緣', 'shop': '聚靈', 'collab': '聯動' };
        if (selectedTypes.length === 0) {
            typeBox.textContent = '取得方法';
        } else if (selectedTypes.length <= 2) {
            typeBox.textContent = selectedTypes.map(t => typeLabelMap[t]).join(', ');
        } else {
            typeBox.textContent = `${typeLabelMap[selectedTypes[0]]} 等 ${selectedTypes.length} 個`;
        }

        const rows = table.querySelectorAll('tbody tr:not(.empty-row)');
        let visibleCount = 0;
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

        // 動態更新左上角角色計數標籤
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
            document.getElementById('empty-reset-btn')?.addEventListener('click', clearAllFilters);
        } else {
            if (emptyRow) {
                emptyRow.style.display = 'none';
            }
        }
    }

    versionItems.forEach(item => item.addEventListener('change', applyFilters));
    pathItems.forEach(item => item.addEventListener('change', applyFilters));
    elemItems.forEach(item => item.addEventListener('change', applyFilters));
    typeItems.forEach(item => item.addEventListener('change', applyFilters));

    searchInput.addEventListener('input', applyFilters);
    searchInput.addEventListener('search', applyFilters);

    // 十字高亮邏輯
    const trackerTable = document.getElementById('tracker');

    trackerTable.addEventListener('mouseover', (e) => {
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

    trackerTable.addEventListener('mouseleave', () => {
        trackerTable.querySelectorAll('.col-highlight').forEach(c => c.classList.remove('col-highlight'));
    });

    // 縮放滑桿 (含 LocalStorage 記憶偏好)
    const scaleSlider = document.getElementById('ui-scale-slider');
    const scaleText = document.getElementById('ui-scale-text');

    const savedScale = localStorage.getItem('hsr_ui_scale');
    if (savedScale) {
        scaleSlider.value = savedScale;
        table.style.zoom = savedScale;
        scaleText.textContent = Math.round(savedScale * 100) + '%';
    }

    scaleSlider.addEventListener('input', (e) => {
        const scaleValue = e.target.value;
        table.style.zoom = scaleValue;
        scaleText.textContent = Math.round(scaleValue * 100) + '%';
        localStorage.setItem('hsr_ui_scale', scaleValue);
    });
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
