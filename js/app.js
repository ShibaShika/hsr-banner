/* ==========================================================================
   《崩壞：星穹鐵道》限定躍遷歷史檢視器 - UI-UX-Pro-Max 邏輯引擎
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  // 1. 初始化星空繪製引擎 (Canvas Starfield)
  initStarfield();

  // 2. 狀態管理 (App State)
  const state = {
    starFilter: 'all',     // 'all', '5', '4'
    typeFilter: 'all',     // 'all', 'character', 'lightcone'
    searchQuery: '',
    viewMode: 'grid',      // 'grid', 'timeline'
    statsVisible: false
  };

  // 3. 元素引用 (DOM Elements)
  const bannerContainer = document.getElementById('banner-container');
  const versionJumpLinks = document.getElementById('version-jump-links');
  const globalSearch = document.getElementById('global-search');
  
  // 4. 事件監聽設定 (Event Listeners)
  setupEventListeners(state);

  // 5. 核心渲染 (Render Pipeline)
  renderApp(state);

  // ========================================================================
  // ⭐ 核心函式庫
  // ========================================================================

  function renderApp(currentState) {
    if (!bannerContainer) return;
    bannerContainer.innerHTML = '';

    // 取得資料源（來自 elements.js / characters.js 等數據檔） [source: 1]
    const bannerData = window.HSR_ELEMENTS || window.HSR_DATA || [];
    
    if (bannerData.length === 0) {
      bannerContainer.innerHTML = `<div style="text-align:center; padding: 4rem; color: var(--text-muted);">
        <i class="fa-solid fa-spinner fa-spin" style="font-size: 2rem; margin-bottom: 1rem;"></i>
        <p>資料載入中，或未找到相關數據...</p>
      </div>`;
      return;
    }

    // 更新數據統計 Drawer
    updateStats(bannerData);

    // 按版本分組 (Group By Version)
    const groupedByVersion = groupByVersion(bannerData, currentState);

    // 渲染版本速達 Jump Bar
    renderJumpBar(Object.keys(groupedByVersion));

    // 渲染各版本與卡片
    Object.keys(groupedByVersion).sort().reverse().forEach(ver => {
      const items = groupedByVersion[ver];
      if (items.length === 0) return;

      const versionSection = document.createElement('div');
      versionSection.className = 'version-group';
      versionSection.id = `version-${ver.replace('.', '-')}`;

      versionSection.innerHTML = `
        <h2 class="version-title">
          <i class="fa-solid fa-meteor"></i> Version ${ver}
        </h2>
        <div class="banner-grid">
          ${items.map(item => createCardHTML(item)).join('')}
        </div>
      `;

      bannerContainer.appendChild(versionSection);
    });
  }

  // 創建單張躍遷卡片 HTML
  function createCardHTML(item) {
    const starClass = item.star === 5 ? 'star-5' : 'star-4';
    const tagStar = item.star ? `${item.star}★` : '5★';
    const tagType = item.type === 'lightcone' ? '光錐' : '角色';
    const imagePath = item.image || item.icon || 'https://via.placeholder.com/300x180/0f1522/f3d193?text=HSR+Warp';

    return `
      <div class="banner-card ${starClass}" data-star="${item.star || 5}">
        <div class="banner-image">
          <img src="${imagePath}" alt="${item.name || '躍遷物'}" loading="lazy" onerror="this.src='https://via.placeholder.com/300x180/0f1522/f3d193?text=HSR+Warp'">
        </div>
        <div class="banner-info">
          <div class="banner-name">${item.name || '未知躍遷'}</div>
          <div class="banner-tags">
            <span class="tag-badge" style="color: ${item.star === 5 ? 'var(--hsr-gold)' : 'var(--hsr-purple)'}">${tagStar}</span>
            <span class="tag-badge">${tagType}</span>
            ${item.element ? `<span class="tag-badge">${item.element}</span>` : ''}
            ${item.path ? `<span class="tag-badge">${item.path}</span>` : ''}
          </div>
        </div>
      </div>
    `;
  }

  // 分組與過濾邏輯
  function groupByVersion(data, currentState) {
    const grouped = {};

    data.forEach(item => {
      // 1. 搜尋過濾
      if (currentState.searchQuery) {
        const query = currentState.searchQuery.toLowerCase();
        const matchName = item.name && item.name.toLowerCase().includes(query);
        const matchVer = item.version && item.version.toString().includes(query);
        if (!matchName && !matchVer) return;
      }

      // 2. 星級過濾
      if (currentState.starFilter !== 'all') {
        if (item.star && item.star.toString() !== currentState.starFilter) return;
      }

      // 3. 類型過濾
      if (currentState.typeFilter !== 'all') {
        if (item.type && item.type !== currentState.typeFilter) return;
      }

      const ver = item.version || '1.0';
      if (!grouped[ver]) grouped[ver] = [];
      grouped[ver].push(item);
    });

    return grouped;
  }

  // 渲染版本 Jump Bar
  function renderJumpBar(versions) {
    if (!versionJumpLinks) return;
    versionJumpLinks.innerHTML = versions.sort().reverse().map(ver => `
      <button class="jump-chip" onclick="document.getElementById('version-${ver.replace('.', '-')}').scrollIntoView({behavior: 'smooth'})">
        v${ver}
      </button>
    `).join('');
  }

  // 統計數據計算
  function updateStats(data) {
    const totalCount = data.length;
    const star5Count = data.filter(d => d.star === 5).length;
    
    const elTotal = document.getElementById('stat-total-banners');
    const el5Star = document.getElementById('stat-5star-count');
    const elLatest = document.getElementById('stat-latest-ver');

    if (elTotal) elTotal.textContent = totalCount;
    if (el5Star) el5Star.textContent = star5Count;
    if (elLatest && data.length > 0) {
      const versions = [...new Set(data.map(d => d.version))].sort();
      elLatest.textContent = `v${versions[versions.length - 1] || '4.0'}`;
    }
  }

  // 事件觸發整合
  function setupEventListeners(currentState) {
    // 全局搜尋
    if (globalSearch) {
      globalSearch.addEventListener('input', (e) => {
        currentState.searchQuery = e.target.value;
        renderApp(currentState);
      });
    }

    // 篩選按鈕 (Pills)
    document.querySelectorAll('.pill-group .pill').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const parent = e.target.closest('.pill-group');
        parent.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
        e.target.classList.add('active');

        if (e.target.dataset.star) currentState.starFilter = e.target.dataset.star;
        if (e.target.dataset.type) currentState.typeFilter = e.target.dataset.type;

        renderApp(currentState);
      });
    });

    // 視圖切換 (Grid vs Timeline)
    const btnGrid = document.getElementById('view-grid');
    const btnTimeline = document.getElementById('view-timeline');

    if (btnGrid && btnTimeline) {
      btnGrid.addEventListener('click', () => {
        btnGrid.classList.add('active');
        btnTimeline.classList.remove('active');
        bannerContainer.className = 'banner-container view-mode-grid';
      });

      btnTimeline.addEventListener('click', () => {
        btnTimeline.classList.add('active');
        btnGrid.classList.remove('active');
        bannerContainer.className = 'banner-container view-mode-timeline';
      });
    }

    // Drawer 開關
    const btnStats = document.getElementById('btn-toggle-stats');
    const statsPanel = document.getElementById('stats-panel');
    const closeStats = document.getElementById('close-stats');

    if (btnStats && statsPanel) {
      btnStats.addEventListener('click', () => {
        statsPanel.classList.toggle('hidden');
      });
    }
    if (closeStats) {
      closeStats.addEventListener('click', () => statsPanel.classList.add('hidden'));
    }

    // 手機版 Drawer Modal
    const btnMobileFilter = document.getElementById('btn-mobile-filter');
    const mobileDrawer = document.getElementById('mobile-filter-drawer');
    const closeDrawer = document.getElementById('close-drawer');

    if (btnMobileFilter && mobileDrawer) {
      btnMobileFilter.addEventListener('click', () => mobileDrawer.classList.add('active'));
    }
    if (closeDrawer && mobileDrawer) {
      closeDrawer.addEventListener('click', () => mobileDrawer.classList.remove('active'));
    }

    // 長圖分享匯出 (html2canvas)
    const btnExport = document.getElementById('btn-export-image');
    if (btnExport) {
      btnExport.addEventListener('click', () => {
        alert('🚀 正在為開拓者生成高質感歷史圖卡，請稍候...');
        html2canvas(document.body).then(canvas => {
          const link = document.createElement('a');
          link.download = 'HSR-Warp-History.png';
          link.href = canvas.toDataURL();
          link.click();
        });
      });
    }
  }

  // 🌌 動態星空粒子背景繪製邏輯
  function initStarfield() {
    const canvas = document.getElementById('starfield-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const stars = Array.from({ length: 80 }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      size: Math.random() * 1.8 + 0.2,
      alpha: Math.random(),
      speed: Math.random() * 0.01 + 0.003
    }));

    function animate() {
      ctx.clearRect(0, 0, width, height);
      stars.forEach(s => {
        s.alpha += s.speed;
        if (s.alpha > 1 || s.alpha < 0) s.speed = -s.speed;
        ctx.fillStyle = `rgba(243, 209, 147, ${Math.abs(s.alpha) * 0.6})`;
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.size, 0, Math.PI * 2);
        ctx.fill();
      });
      requestAnimationFrame(animate);
    }

    animate();

    window.addEventListener('resize', () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    });
  }
});
