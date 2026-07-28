/* ==========================================================================
   崩壞：星穹鐵道 - 限定躍遷一覽表 主應用程式邏輯 (app.js)
   ========================================================================== */

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

// 自動對照 PATCH_DATA 與今日日期，找出當前進行中的卡池版本名稱
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

    const PATH_ORDER = ["毀滅", "巡獵", "智識", "同諧", "虛無", "存護", "豐饒", "記憶", "歡愉"];
    const uniquePaths = PATH_ORDER.filter(p => RAW_CHARACTERS.some(c => c.path === p));
    const uniqueElems = ELEM_ORDER.filter(e => RAW_CHARACTERS.some(c => c.elem === e));

    // 動態產生命途選項 (預設全部不勾選)
    document.getElementById('path-items-container').innerHTML = uniquePaths.map(p => {
        const iconUrl = (typeof PATH_ICONS !== 'undefined' && PATH_ICONS[p]) ? PATH_ICONS[p] : "";
        const iconHtml = iconUrl ? `<img src="${iconUrl}" style="width: 16px; height: 16px; flex-shrink: 0; filter: drop-shadow(0 0 1.5px rgba(0,0,0,0.9));" alt="${p}">` : "";
        return `<label><input type="checkbox" class="path-item" value="${p}"> ${iconHtml}${p}</label>`;
    }).join('');
    
    // 動態產生屬性選項 (預設全部不勾選)
    document.getElementById('elem-items-container').innerHTML = uniqueElems.map(e => {
        const iconUrl = (typeof ELEM_ICONS !== 'undefined' && ELEM_ICONS[e]) ? ELEM_ICONS[e] : "";
        const iconHtml = iconUrl ? `<img src="${iconUrl}" style="width: 16px; height: 16px; flex-shrink: 0; filter: drop-shadow(0 0 1.5px rgba(0,0,0,0.9));" alt="${e}">` : "";
        return `<label><input type="checkbox" class="elem-item" value="${e}"> ${iconHtml}${e}</label>`;
    }).join('');

    // 構建表頭 1 (日期)
    let html = '<thead><tr><th></th>';
    reversedPatches.forEach(p => {
        const isCurrent = (p.patch === activePatchName);
        const colClass = isCurrent ? ' class="current-patch-col"' : '';
        html += `<th${colClass}>${formatHeaderDate(p.date)}</th>`;
    });

    // 構建表頭 2 (版本號)
    html += `</tr><tr><th><div style="text-align:center; padding: 0 4px;">&nbsp;</div></th>`;
    reversedPatches.forEach(p => {
        const isCurrent = (p.patch === activePatchName);
        const colClass = isCurrent ? ' class="current-patch-col"' : '';
        html += `<th${colClass}>${p.patch}</th>`;
    });
    html += '</tr></thead><tbody>';
    
    // 構建表格主體內容
    CHARACTERS.forEach((char, index) => {
        const fallbackUrl = `https://ui-avatars.com/api/?name=${encodeURIComponent(char.name)}&background=random&color=fff&size=56&bold=true`;
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
        
        html += `<tr data-path="${char.path}" data-elem="${char.elem}" data-type="${charType}" data-has-buff="${hasBuff}" data-name="${char.name}">
            <td class="bg-${char.elem}">
                <div class="char-info-cell">
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

    // === 綁定篩選器邏輯 ===
    const pathBox = document.getElementById('path-select-box');
    const elemBox = document.getElementById('elem-select-box');
    const typeBox = document.getElementById('type-select-box');
    
    const pathPanel = document.getElementById('path-panel');
    const elemPanel = document.getElementById('elem-panel');
    const typePanel = document.getElementById('type-panel');
    
    const pathItems = pathPanel.querySelectorAll('.path-item');
    const elemItems = elemPanel.querySelectorAll('.elem-item');
    const typeItems = typePanel.querySelectorAll('.type-item');

    const buffToggleBtn = document.getElementById('buff-toggle-btn');
    const searchInput = document.getElementById('char-search-input');
    const searchClearBtn = document.getElementById('search-clear-btn');
    const resetFiltersBtn = document.getElementById('reset-filters-btn');

    let onlyBuffs = false;
    buffToggleBtn.addEventListener('click', () => {
        onlyBuffs = !onlyBuffs;
        buffToggleBtn.classList.toggle('active', onlyBuffs);
        applyFilters();
    });

    // 下拉選單點擊展開/隱藏
    pathBox.addEventListener('click', (e) => {
        e.stopPropagation();
        elemPanel.classList.remove('show');
        typePanel.classList.remove('show');
        pathPanel.classList.toggle('show');
    });

    elemBox.addEventListener('click', (e) => {
        e.stopPropagation();
        pathPanel.classList.remove('show');
        typePanel.classList.remove('show');
        elemPanel.classList.toggle('show');
    });

    typeBox.addEventListener('click', (e) => {
        e.stopPropagation();
        pathPanel.classList.remove('show');
        elemPanel.classList.remove('show');
        typePanel.classList.toggle('show');
    });

    // 點擊空白處自動收合所有選單
    document.addEventListener('click', () => {
        pathPanel.classList.remove('show');
        elemPanel.classList.remove('show');
        typePanel.classList.remove('show');
    });

    pathPanel.addEventListener('click', (e) => e.stopPropagation());
    elemPanel.addEventListener('click', (e) => e.stopPropagation());
    typePanel.addEventListener('click', (e) => e.stopPropagation());

    // 🧹 清除所有篩選條件
    function clearAllFilters() {
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

    function applyFilters() {
        const selectedPaths = Array.from(pathItems).filter(i => i.checked).map(i => i.value);
        const selectedElems = Array.from(elemItems).filter(i => i.checked).map(i => i.value);
        const selectedTypes = Array.from(typeItems).filter(i => i.checked).map(i => i.value);
        const keyword = searchInput.value.trim().toLowerCase();

        // 控制搜尋框內部 ✕ 按鈕的顯示與隱藏
        if (searchClearBtn) {
            searchClearBtn.style.display = searchInput.value !== '' ? 'block' : 'none';
        }

        // 亮燈提示：有勾選時，為按鈕外框加上 active 高亮
        pathBox.classList.toggle('active', selectedPaths.length > 0);
        elemBox.classList.toggle('active', selectedElems.length > 0);
        typeBox.classList.toggle('active', selectedTypes.length > 0);

        // 判斷是否顯示「🧹 清除」按鈕
        const hasActiveFilter = selectedPaths.length > 0 || selectedElems.length > 0 || selectedTypes.length > 0 || keyword !== '' || onlyBuffs;
        if (resetFiltersBtn) {
            resetFiltersBtn.style.display = hasActiveFilter ? 'inline-flex' : 'none';
        }

        // 更新命途 UI 文字
        if (selectedPaths.length === 0) {
            pathBox.textContent = '命途';
        } else if (selectedPaths.length <= 2) {
            pathBox.textContent = selectedPaths.join(', ');
        } else {
            pathBox.textContent = `${selectedPaths[0]} 等 ${selectedPaths.length} 個`;
        }

        // 更新屬性 UI 文字
        if (selectedElems.length === 0) {
            elemBox.textContent = '屬性';
        } else if (selectedElems.length <= 2) {
            elemBox.textContent = selectedElems.join(', ');
        } else {
            elemBox.textContent = `${selectedElems[0]} 等 ${selectedElems.length} 個`;
        }

        // 更新取得方法 UI 文字
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
            const rowPath = row.getAttribute('data-path');
            const rowElem = row.getAttribute('data-elem');
            const rowType = row.getAttribute('data-type');
            const hasBuffAttr = row.getAttribute('data-has-buff') === 'true';
            const rowName = row.getAttribute('data-name').toLowerCase();

            const matchPath = selectedPaths.length === 0 || selectedPaths.includes(rowPath);
            const matchElem = selectedElems.length === 0 || selectedElems.includes(rowElem);
            const matchType = selectedTypes.length === 0 || selectedTypes.includes(rowType);
            const matchName = keyword === '' || rowName.includes(keyword);
            const matchBuff = !onlyBuffs || hasBuffAttr;

            if (matchPath && matchElem && matchType && matchName && matchBuff) {
                row.style.display = '';
                visibleCount++;
            } else {
                row.style.display = 'none';
            }
        });

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

    // 縮放滑桿
    const scaleSlider = document.getElementById('ui-scale-slider');
    const scaleText = document.getElementById('ui-scale-text');

    scaleSlider.addEventListener('input', (e) => {
        const scaleValue = e.target.value;
        table.style.zoom = scaleValue;
        scaleText.textContent = Math.round(scaleValue * 100) + '%';
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
