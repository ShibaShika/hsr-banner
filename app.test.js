const {
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
    buildHistoryCellsHtml,
    buildCharacterRowHtml,
    renderTable,
    getPatchColClass,
    getFilterState,
    filterTableRows,
    renderFilters,
    setupTableInteractions
} = require('./js/app');

describe('app.js pure functions', () => {

    describe('getCurrentPatchName', () => {
        let originalDate;

        beforeEach(() => {
            originalDate = global.Date;
            global.PATCH_DATA = [];
        });

        afterEach(() => {
            global.Date = originalDate;
            delete global.PATCH_DATA;
        });

        it('returns empty string if PATCH_DATA is undefined or empty', () => {
            expect(getCurrentPatchName()).toBe("");
            delete global.PATCH_DATA;
            expect(getCurrentPatchName()).toBe("");
        });

        it('returns first patch if no patch date is in the past', () => {
            const mockNow = new Date(2024, 0, 1).getTime();
            jest.spyOn(global, 'Date').mockImplementation(function() {
                if (arguments.length === 0) {
                    return new originalDate(mockNow);
                }
                return new originalDate(...arguments);
            });
            global.PATCH_DATA = [
                { patch: '2.2', date: '24/04/01' },
                { patch: '2.3', date: '24/05/01' }
            ];
            expect(getCurrentPatchName()).toBe('2.2');
        });

        it('returns the latest patch date that is in the past or today', () => {
            const mockNow = new Date(2024, 2, 15).getTime();
            jest.spyOn(global, 'Date').mockImplementation(function() {
                if (arguments.length === 0) {
                    return new originalDate(mockNow);
                }
                return new originalDate(...arguments);
            });
            global.PATCH_DATA = [
                { patch: '2.0', date: '24/02/01' },
                { patch: '2.1', date: '24/03/01' },
                { patch: '2.2', date: '24/04/01' }
            ];
            expect(getCurrentPatchName()).toBe('2.1');
        });
    });

    describe('getCharEarliestPatch', () => {
        it('returns isCollab for collab characters', () => {
            const char = { isCollab: 'Collab Patch' };
            expect(getCharEarliestPatch(char)).toBe('Collab Patch');
        });

        it('returns earliest patch from runs using map', () => {
            const char = { runs: ['1.1', '1.2'] };
            const patchesList = ['1.0', '1.1', '1.2'];
            const patchIndexMap = new Map([['1.0', 0], ['1.1', 1], ['1.2', 2]]);
            expect(getCharEarliestPatch(char, patchesList, patchIndexMap)).toBe('1.1');
        });

        it('returns earliest patch from runs using array fallback', () => {
            const char = { runs: ['1.2', '1.1'] };
            const patchesList = ['1.0', '1.1', '1.2'];
            expect(getCharEarliestPatch(char, patchesList)).toBe('1.1');
        });

        it('returns patch from term if no runs and not collab', () => {
            const char = { term: { patch: '1.3' } };
            expect(getCharEarliestPatch(char)).toBe('1.3');
        });

        it('returns null if no matching criteria', () => {
            const char = {};
            expect(getCharEarliestPatch(char)).toBeNull();
        });
    });

    describe('getCharDebutMajorVersion', () => {
        it('returns x version for valid character with runs', () => {
            const char = { runs: ['2.1', '2.2'] };
            const patchesList = ['1.0', '2.0', '2.1', '2.2'];
            expect(getCharDebutMajorVersion(char, patchesList)).toBe('2.x');
        });

        it('returns 未知 if earliest patch not found', () => {
            const char = {};
            expect(getCharDebutMajorVersion(char, [])).toBe('未知');
        });
    });

    describe('getPatchIndex', () => {
        it('returns index using patchIndexMap if available', () => {
            const patchesList = ['1.0', '1.1', '1.2'];
            const patchIndexMap = new Map([['1.0', 0], ['1.1', 1], ['1.2', 2]]);
            expect(getPatchIndex('1.1', patchesList, patchIndexMap)).toBe(1);
        });

        it('returns -1 using patchIndexMap if patch not found', () => {
            const patchesList = ['1.0', '1.1', '1.2'];
            const patchIndexMap = new Map([['1.0', 0], ['1.1', 1], ['1.2', 2]]);
            expect(getPatchIndex('1.3', patchesList, patchIndexMap)).toBe(-1);
        });

        it('returns index using patchesList fallback if patchIndexMap not provided', () => {
            const patchesList = ['1.0', '1.1', '1.2'];
            expect(getPatchIndex('1.1', patchesList, null)).toBe(1);
        });

        it('returns -1 using patchesList fallback if patch not found', () => {
            const patchesList = ['1.0', '1.1', '1.2'];
            expect(getPatchIndex('1.3', patchesList, null)).toBe(-1);
        });
    });

    describe('getTermStatus', () => {
        it('returns default status if no term data', () => {
            const char = {};
            const result = getTermStatus(char, 5, ['1.0', '1.1'], null);
            expect(result).toEqual({ isTermActive: false, validEndIdx: 5, termLabel: '' });
        });

        it('returns default status if term patch not found', () => {
            const char = { term: { patch: '1.3' } };
            const result = getTermStatus(char, 5, ['1.0', '1.1'], null);
            expect(result).toEqual({ isTermActive: false, validEndIdx: 5, termLabel: '' });
        });

        it('returns default status if term index > validEndIdx', () => {
            const char = { term: { patch: '1.2' } };
            const result = getTermStatus(char, 1, ['1.0', '1.1', '1.2'], null);
            expect(result).toEqual({ isTermActive: false, validEndIdx: 1, termLabel: '' });
        });

        it('returns active status for pool term', () => {
            const char = { term: { patch: '1.1', type: 'pool' } };
            const result = getTermStatus(char, 5, ['1.0', '1.1', '1.2'], null);
            expect(result).toEqual({ isTermActive: true, validEndIdx: 1, termLabel: '星緣' });
        });

        it('returns active status for non-pool term', () => {
            const char = { term: { patch: '1.1', type: 'shop' } };
            const result = getTermStatus(char, 5, ['1.0', '1.1', '1.2'], null);
            expect(result).toEqual({ isTermActive: true, validEndIdx: 1, termLabel: '聚靈' });
        });
    });

    describe('mergeContinuousEvents', () => {
        it('returns empty array for empty input', () => {
            expect(mergeContinuousEvents([])).toEqual([]);
        });

        it('merges single index', () => {
            expect(mergeContinuousEvents([1])).toEqual([{ start: 1, end: 1 }]);
        });

        it('merges continuous indices', () => {
            expect(mergeContinuousEvents([1, 2, 3])).toEqual([{ start: 1, end: 3 }]);
        });

        it('handles disjoint indices', () => {
            expect(mergeContinuousEvents([1, 3, 5])).toEqual([
                { start: 1, end: 1 },
                { start: 3, end: 3 },
                { start: 5, end: 5 }
            ]);
        });

        it('handles mixed continuous and disjoint indices', () => {
            expect(mergeContinuousEvents([1, 2, 4, 6, 7, 8, 10])).toEqual([
                { start: 1, end: 2 },
                { start: 4, end: 4 },
                { start: 6, end: 8 },
                { start: 10, end: 10 }
            ]);
        });
    });

    describe('calculateGaps', () => {
        it('returns empty array for empty input', () => {
            expect(calculateGaps([])).toEqual([]);
        });

        it('returns empty array for single event', () => {
            expect(calculateGaps([{ start: 1, end: 2 }])).toEqual([]);
        });

        it('calculates gaps between multiple events correctly', () => {
            const events = [
                { start: 1, end: 2 },
                { start: 4, end: 4 },
                { start: 7, end: 8 }
            ];
            expect(calculateGaps(events)).toEqual([1, 2]);
        });
    });

    describe('calculateCharStats', () => {
        const patchesList = ['1.0上', '1.0下', '1.1上', '1.1下', '1.2上', '1.2下', '1.3上', '1.3下'];
        const patchIndexMap = new Map();
        patchesList.forEach((p, i) => patchIndexMap.set(p, i));

        it('returns collab flag if isCollab', () => {
            expect(calculateCharStats({ isCollab: true }, patchesList, '1.2上', patchIndexMap)).toEqual({ isCollab: true });
        });

        it('calculates stats for zero runs', () => {
            expect(calculateCharStats({ runs: [] }, patchesList, '1.2上', patchIndexMap)).toEqual({
                totalRuns: '0',
                currentGap: '-',
                maxGap: '-',
                isOverdue: false,
                isTermActive: false,
                termLabel: ''
            });
        });

        it('calculates correctly for 1 run', () => {
            expect(calculateCharStats({ runs: ['1.0上'] }, patchesList, '1.2上', patchIndexMap)).toEqual({
                totalRuns: '1',
                currentGap: '4', // 1.2上 is idx 4, 1.0上 is idx 0 -> gap 4
                maxGap: '-',
                isOverdue: false,
                isTermActive: false,
                termLabel: ''
            });
        });

        it('calculates correctly with gaps and overdue', () => {
            expect(calculateCharStats({ runs: ['1.0上', '1.1上', '1.2上'] }, patchesList, '1.3上', patchIndexMap)).toEqual({
                totalRuns: '3',
                currentGap: '2', // 1.3上(6) - 1.2上(4) = 2
                maxGap: '1', // 1.1上(2)-1.0上(0)-1 = 1
                isOverdue: true,
                isTermActive: false,
                termLabel: ''
            });
        });

        it('handles active term', () => {
            expect(calculateCharStats({ runs: ['1.0上', '1.1上'], term: { patch: '1.2上', type: 'pool' } }, patchesList, '1.3上', patchIndexMap)).toEqual({
                totalRuns: '2',
                currentGap: '已加入星緣',
                maxGap: '1',
                isOverdue: false,
                isTermActive: true,
                termLabel: '星緣'
            });
        });
    });

    describe("escapeHtml", () => {
        it("should return empty string for null and undefined", () => {
            expect(escapeHtml(null)).toBe("");
            expect(escapeHtml(undefined)).toBe("");
        });

        it("should return the original string if there are no special characters", () => {
            expect(escapeHtml("Hello World")).toBe("Hello World");
            expect(escapeHtml("12345")).toBe("12345");
            expect(escapeHtml("")).toBe("");
        });

        it("should correctly escape HTML special characters", () => {
            expect(escapeHtml("&")).toBe("&amp;");
            expect(escapeHtml("<")).toBe("&lt;");
            expect(escapeHtml(">")).toBe("&gt;");
            expect(escapeHtml("\"")).toBe("&quot;");
            expect(escapeHtml("'")).toBe("&#39;");
            expect(escapeHtml("/")).toBe("&#x2F;");
        });

        it("should correctly escape multiple special characters in a single string", () => {
            expect(escapeHtml("<div class=\"test\">Bob & Alice's String</div>"))
                .toBe("&lt;div class=&quot;test&quot;&gt;Bob &amp; Alice&#39;s String&lt;&#x2F;div&gt;");
            expect(escapeHtml("<<<>>>&&&\"\"\"'''///"))
                .toBe("&lt;&lt;&lt;&gt;&gt;&gt;&amp;&amp;&amp;&quot;&quot;&quot;&#39;&#39;&#39;&#x2F;&#x2F;&#x2F;");
        });

        it("should coerce non-string inputs to strings and escape them if necessary", () => {
            expect(escapeHtml(123)).toBe("123");
            expect(escapeHtml(true)).toBe("true");
            expect(escapeHtml(false)).toBe("false");

            const obj = { toString: () => "<obj>" };
            expect(escapeHtml(obj)).toBe("&lt;obj&gt;");
        });
    });

    describe("formatHeaderDate", () => {
        it("should correctly format a date string with exactly 3 parts separated by slashes", () => {
            expect(formatHeaderDate("23/10/15")).toBe("2023<br>10/15");
            expect(formatHeaderDate("24/01/01")).toBe("2024<br>01/01");
            expect(formatHeaderDate("99/12/31")).toBe("2099<br>12/31");
        });

        it("should return the original string if it doesn't have exactly 3 parts separated by slashes", () => {
            expect(formatHeaderDate("23/10")).toBe("23/10");
            expect(formatHeaderDate("23-10-15")).toBe("23-10-15");
            expect(formatHeaderDate("2023/10/15/01")).toBe("2023/10/15/01");
            expect(formatHeaderDate("hello")).toBe("hello");
            expect(formatHeaderDate("")).toBe("");
        });
    });

    describe("getCharDebutVersion", () => {
        const patchesList = ["1.0上", "1.0下", "1.1上", "1.1下"];

        it("should return the earliest patch for a regular character", () => {
            const char = { runs: ["1.1上", "1.1下"] };
            expect(getCharDebutVersion(char, patchesList)).toBe("1.1上");
        });

        it("should return 未登場 for a character with no runs, term, or collab info", () => {
            const char = {};
            expect(getCharDebutVersion(char, patchesList)).toBe("未登場");
        });
    });

    describe('getHistoryElement', () => {
        let patchIndexMap;
        beforeEach(() => {
            patchIndexMap = new Map();
            const patches = ['1.0', '1.1', '1.2', '1.3', '1.4'];
            patches.forEach((p, i) => patchIndexMap.set(p, i));
        });

        it('should handle collab characters before start', () => {
            const state = { patchesListLength: 5 };
            const char = { isCollab: '1.2' }; // index 2

            const result1 = getHistoryElement(char, '1.0', 0, state, patchIndexMap);
            expect(result1).toEqual({ status: 'COLLAB_BEFORE' });

            const result2 = getHistoryElement(char, '1.1', 1, state, patchIndexMap);
            expect(result2).toEqual({ status: 'COLLAB_BEFORE' });
        });

        it('should handle collab characters exactly on start patch or end patch', () => {
            const state = { patchesListLength: 5 };
            const char = { isCollab: '1.2' }; // index 2

            // pIdx 2 (=== sIdx)
            const result1 = getHistoryElement(char, '1.2', 2, state, patchIndexMap);
            expect(result1).toEqual({ status: 'COLLAB' });

            // pIdx 4 (=== lIdx)
            const result2 = getHistoryElement(char, '1.4', 4, state, patchIndexMap);
            expect(result2).toEqual({ status: 'COLLAB' });
        });

        it('should handle collab characters between start and end patch', () => {
            const state = { patchesListLength: 5 };
            const char = { isCollab: '1.2' }; // index 2

            // pIdx 3
            const result = getHistoryElement(char, '1.3', 3, state, patchIndexMap);
            expect(result).toEqual({ status: 'COLLAB_EMPTY' });
        });

        it('should handle term characters on start patch', () => {
            const state = {};
            const char = { term: { patch: '1.1', type: 'shop' } }; // index 1

            const result = getHistoryElement(char, '1.1', 1, state, patchIndexMap);
            expect(result).toEqual({ status: 'TERM_START', type: 'shop' });
        });

        it('should handle term characters after start patch', () => {
            const state = {};
            const char = { term: { patch: '1.1', type: 'shop' } }; // index 1

            const result = getHistoryElement(char, '1.2', 2, state, patchIndexMap);
            expect(result).toEqual({ status: 'TERM_EMPTY', type: 'shop' });
        });

        it('should return UP when character is running', () => {
            const state = { hasReleased: false, currentGap: 0 };
            const char = { runs: ['1.1', '1.3'] };

            const result = getHistoryElement(char, '1.1', 1, state, patchIndexMap);
            expect(result).toEqual({ status: 'UP' });
            expect(state.hasReleased).toBe(true);
            expect(state.currentGap).toBe(0);
        });

        it('should return WAIT when character has released but is not running', () => {
            const state = { hasReleased: true, currentGap: 0 };
            const char = { runs: ['1.1', '1.3'] };

            const result = getHistoryElement(char, '1.2', 2, state, patchIndexMap);
            expect(result).toEqual({ status: 'WAIT', gap: 1 });
            expect(state.currentGap).toBe(1);
        });

        it('should return NONE when character has not released and is not running', () => {
            const state = { hasReleased: false, currentGap: 0 };
            const char = { runs: ['1.1', '1.3'] };

            const result = getHistoryElement(char, '1.0', 0, state, patchIndexMap);
            expect(result).toEqual({ status: 'NONE' });
            expect(state.currentGap).toBe(0);
        });
    });

    describe('buildCharacterHistory', () => {
        it('preserves columns before the collab span', () => {
            const patchesList = ['1.0', '1.1', '1.2', '1.3', '1.4', '1.5', '1.6', '1.7'];
            const patchIndexMap = new Map(patchesList.map((patch, index) => [patch, index]));
            const char = { isCollab: '1.6' };

            const history = buildCharacterHistory(char, patchesList, patchIndexMap);

            expect(history).toHaveLength(patchesList.length);
            expect(history.map(cell => cell.status)).toEqual([
                'NONE',
                'COLLAB_SPAN',
                'HIDDEN',
                'HIDDEN',
                'HIDDEN',
                'HIDDEN',
                'COLLAB',
                'COLLAB'
            ]);
            expect(history[1]).toEqual({ status: 'COLLAB_SPAN', count: 5 });
        });
    });

    describe("getFallbackAvatar", () => {
        it("should return a data URI SVG with the first character of the name", () => {
            const svgUri = getFallbackAvatar("Jules");
            expect(svgUri).toContain("data:image/svg+xml;charset=utf-8,");
            // Decode the URI and check if it contains 'J'
            const decodedSvg = decodeURIComponent(svgUri.replace("data:image/svg+xml;charset=utf-8,", ""));
            expect(decodedSvg).toContain(">J<");
        });

        it("should handle empty or null names gracefully", () => {
            const svgUri = getFallbackAvatar("");
            const decodedSvg = decodeURIComponent(svgUri.replace("data:image/svg+xml;charset=utf-8,", ""));
            expect(decodedSvg).toContain(">?<");

            const svgUriNull = getFallbackAvatar(null);
            const decodedSvgNull = decodeURIComponent(svgUriNull.replace("data:image/svg+xml;charset=utf-8,", ""));
            expect(decodedSvgNull).toContain(">?<");
        });

        it("should trim the name before extracting the first character", () => {
            const svgUri = getFallbackAvatar("   Space   ");
            const decodedSvg = decodeURIComponent(svgUri.replace("data:image/svg+xml;charset=utf-8,", ""));
            expect(decodedSvg).toContain(">S<");
        });
    });


    describe('getCharacterType', () => {
        it('should return collab for collab characters', () => {
            expect(getCharacterType({ isCollab: true })).toBe('collab');
        });
        it('should return pool for pool term', () => {
            expect(getCharacterType({ term: { type: 'pool' } })).toBe('pool');
        });
        it('should return shop for shop term', () => {
            expect(getCharacterType({ term: { type: 'shop' } })).toBe('shop');
        });
        it('should return normal by default', () => {
            expect(getCharacterType({})).toBe('normal');
        });
    });

    describe('getCharacterTooltip', () => {
        it('should return correct tooltip for preview character', () => {
            expect(getCharacterTooltip({ name: 'A' }, {}, '2.0', true)).toContain('預定登場');
        });
        it('should return correct tooltip for collab character', () => {
            expect(getCharacterTooltip({ name: 'A' }, { isCollab: true }, '2.0', false)).toContain('長期聯動角色');
        });
        it('should return correct tooltip for active term character', () => {
            expect(getCharacterTooltip({ name: 'A' }, { isTermActive: true, currentGap: 1, maxGap: 2, totalRuns: 3 }, '2.0', false)).toContain('目前狀態：1');
        });
        it('should return correct tooltip for regular character', () => {
            expect(getCharacterTooltip({ name: 'A' }, { isOverdue: true, currentGap: 5, maxGap: 3, totalRuns: 2 }, '2.0', false)).toContain('⚠️ (超期警報!)');
        });
    });




    describe('buildCharacterRowHtml', () => {
        beforeAll(() => {
            global.PATH_ICONS = { "pathA": "pathA.png" };
            global.isCharAscending = true;
            global.isPatchAscending = true;
        });

        afterAll(() => {
            delete global.PATH_ICONS;
        });

        it('returns complete tr with proper data attributes and cells', () => {
            const char = { name: 'Char1', elem: 'Fire', path: 'pathA', isPreview: true };
            const patchesList = ['1.0'];
            const patchIndexMap = new Map([['1.0', 0]]);
            const displayPatches = [{ patch: '1.0' }];
            const activePatchName = '1.0';

            const html = buildCharacterRowHtml(char, 0, 1, patchesList, patchIndexMap, displayPatches, activePatchName);
            expect(html).toContain('<tr data-path="pathA" data-elem="Fire" data-type="normal"');
            expect(html).toContain('data-name="Char1" data-is-preview="true"');
            expect(html).toContain('bg-Fire');
            expect(html).toContain('pathA.png');
            expect(html).toContain('preview-badge');
        });
    });

    describe('renderTable', () => {
        beforeEach(() => {
            document.body.innerHTML = `<table id="tracker"></table><div id="version-items-container"></div>`;
            global.PATCH_DATA = [{ patch: '1.0', isPreview: false, date: '24/01/01' }];
            global.RAW_CHARACTERS = [{ name: 'A', elem: 'Fire', path: 'A' }];
            global.PATH_ICONS = {};
            global.isCharAscending = false;
            global.isPatchAscending = false;
        });

        afterEach(() => {
            document.body.innerHTML = '';
            delete global.PATCH_DATA;
            delete global.RAW_CHARACTERS;
            delete global.isCharAscending;
            delete global.isPatchAscending;
        });

        it('renders nothing if tracker element is missing', () => {
            document.body.innerHTML = '';
            renderTable();
            expect(document.getElementById('tracker')).toBeNull();
        });

        it('renders table headers and body', () => {
            renderTable();
            const tracker = document.getElementById('tracker');
            expect(tracker.innerHTML).toContain('<thead>');
            expect(tracker.innerHTML).toContain('<tbody>');
            expect(tracker.innerHTML).toContain('data-name="A"');
        });
    });

    describe('buildHistoryCellsHtml', () => {
        const fallbackUrl = 'fallback.png';
        const avatarUrl = 'avatar.png';

        it('renders COLLAB_SPAN', () => {
            const char = { isCollab: '1.0' };
            const finalHistory = [{ status: 'COLLAB_SPAN', count: 2 }];
            const displayPatches = [{ patch: '1.0' }];
            const html = buildHistoryCellsHtml(char, finalHistory, displayPatches, '1.0', avatarUrl, fallbackUrl);
            expect(html).toContain('colspan="2"');
            expect(html).toContain('collab-text current-patch-col');
        });

        it('renders UP and COLLAB', () => {
            const char = { name: 'A', buffs: ['1.0'] };
            const finalHistory = [{ status: 'UP' }, { status: 'COLLAB' }];
            const displayPatches = [{ patch: '1.0' }, { patch: '1.1', isPreview: true }];
            const html = buildHistoryCellsHtml(char, finalHistory, displayPatches, '1.0', avatarUrl, fallbackUrl);
            expect(html).toContain('img-cell');
            expect(html).toContain('buff-badge');
            expect(html).toContain('preview-patch-col');
        });

        it('renders TERM_START and TERM_EMPTY', () => {
            const char = {};
            const finalHistory = [
                { status: 'TERM_START', type: 'pool' },
                { status: 'TERM_START', type: 'shop' },
                { status: 'TERM_EMPTY', type: 'pool' },
                { status: 'TERM_EMPTY', type: 'shop' }
            ];
            const displayPatches = [{}, {}, {}, {}];
            const html = buildHistoryCellsHtml(char, finalHistory, displayPatches, '', avatarUrl, fallbackUrl);
            expect(html).toContain('term-pool');
            expect(html).toContain('星緣');
            expect(html).toContain('term-shop');
            expect(html).toContain('聚靈');
            expect(html).toContain('term-pool-empty');
            expect(html).toContain('term-shop-empty');
        });

        it('renders WAIT and NONE', () => {
            const char = {};
            const finalHistory = [
                { status: 'WAIT', gap: 2 },
                { status: 'WAIT', gap: 5 },
                { status: 'WAIT', gap: 10 },
                { status: 'WAIT', gap: 15 },
                { status: 'NONE' },
                { status: 'COLLAB_EMPTY' }
            ];
            const displayPatches = [{}, {}, {}, {}, {}, {}];
            const html = buildHistoryCellsHtml(char, finalHistory, displayPatches, '', avatarUrl, fallbackUrl);
            expect(html).toContain('w-low');
            expect(html).toContain('w-med');
            expect(html).toContain('w-high');
            expect(html).toContain('w-crit');
            expect(html).toContain('none');
            expect(html).toContain('collab-empty');
        });
    });

    describe('buildTableHeaderHtml', () => {
        it('should render header with top-left controls and character count when displayPatches is empty', () => {
            const html = buildTableHeaderHtml([], 10, '2.0');
            expect(html).toContain('<thead><tr>');
            expect(html).toContain('共 10 位');
            expect(html).toContain('</tr></thead>');
        });

        it('should render header with patches and correctly apply current and preview patch column classes', () => {
            const displayPatches = [
                { patch: '2.0', date: '24/01/01' },
                { patch: '2.1', date: '24/02/01' },
                { patch: '2.2', date: '24/03/01', isPreview: true }
            ];
            const html = buildTableHeaderHtml(displayPatches, 15, '2.1');
            expect(html).toContain('共 15 位');
            expect(html).toContain('<th class="current-patch-col">2024<br>02/01</th>');
            expect(html).toContain('<th class="current-patch-col">2.1</th>');
            expect(html).toContain('<th class="preview-patch-col">2024<br>03/01</th>');
            expect(html).toContain('<th class="preview-patch-col">2.2</th>');
            expect(html).toContain('<th>2024<br>01/01</th>');
            expect(html).toContain('<th>2.0</th>');
        });
    });

    describe("updateTableColumnIndices", () => {
        let table;

        beforeEach(() => {
            table = document.createElement('table');
            document.body.appendChild(table);
        });

        afterEach(() => {
            document.body.removeChild(table);
        });

        it("should handle an empty table", () => {
            expect(() => updateTableColumnIndices(table)).not.toThrow();
        });

        it("should correctly calculate startCol and endCol for a simple table", () => {
            table.innerHTML = `
                <tbody>
                    <tr><td>1</td><td>2</td></tr>
                    <tr><td>3</td><td>4</td></tr>
                </tbody>
            `;
            updateTableColumnIndices(table);

            const rows = table.rows;
            expect(rows[0].cells[0].dataset.startCol).toBe("0");
            expect(rows[0].cells[0].dataset.endCol).toBe("0");
            expect(rows[0].cells[1].dataset.startCol).toBe("1");
            expect(rows[0].cells[1].dataset.endCol).toBe("1");

            expect(rows[1].cells[0].dataset.startCol).toBe("0");
            expect(rows[1].cells[0].dataset.endCol).toBe("0");
            expect(rows[1].cells[1].dataset.startCol).toBe("1");
            expect(rows[1].cells[1].dataset.endCol).toBe("1");
            expect(rows[1].cells[1]._startCol).toBe(1);
            expect(rows[1].cells[1]._endCol).toBe(1);
        });

        it("should correctly calculate startCol and endCol for a table with colspans", () => {
            table.innerHTML = `
                <tbody>
                    <tr><td colspan="2">1</td><td>2</td></tr>
                    <tr><td>3</td><td colspan="3">4</td></tr>
                </tbody>
            `;
            updateTableColumnIndices(table);

            const rows = table.rows;
            expect(rows[0].cells[0].dataset.startCol).toBe("0");
            expect(rows[0].cells[0].dataset.endCol).toBe("1");
            expect(rows[0].cells[1].dataset.startCol).toBe("2");
            expect(rows[0].cells[1].dataset.endCol).toBe("2");

            expect(rows[1].cells[0].dataset.startCol).toBe("0");
            expect(rows[1].cells[0].dataset.endCol).toBe("0");
            expect(rows[1].cells[1].dataset.startCol).toBe("1");
            expect(rows[1].cells[1].dataset.endCol).toBe("3");
        });

        it("should correctly handle rows with different number of cells", () => {
             table.innerHTML = `
                <tbody>
                    <tr><td colspan="4">1</td></tr>
                    <tr><td>2</td><td>3</td><td>4</td><td>5</td></tr>
                    <tr><td colspan="2">6</td><td colspan="2">7</td></tr>
                </tbody>
            `;
            updateTableColumnIndices(table);

            const rows = table.rows;
            // Row 0
            expect(rows[0].cells[0].dataset.startCol).toBe("0");
            expect(rows[0].cells[0].dataset.endCol).toBe("3");

            // Row 1
            expect(rows[1].cells[0].dataset.startCol).toBe("0");
            expect(rows[1].cells[0].dataset.endCol).toBe("0");
            expect(rows[1].cells[3].dataset.startCol).toBe("3");
            expect(rows[1].cells[3].dataset.endCol).toBe("3");

            // Row 2
            expect(rows[2].cells[0].dataset.startCol).toBe("0");
            expect(rows[2].cells[0].dataset.endCol).toBe("1");
            expect(rows[2].cells[1].dataset.startCol).toBe("2");
            expect(rows[2].cells[1].dataset.endCol).toBe("3");
        });

        it('uses precomputed columns to highlight the hovered column', () => {
            table.id = 'tracker';
            table.innerHTML = `
                <thead>
                    <tr><th rowspan="2">Name</th><th>Header 1</th><th>Header 2</th></tr>
                    <tr><th>Sub 1</th><th>Sub 2</th></tr>
                </thead>
                <tbody><tr><td>Name</td><td>Value 1</td><td>Value 2</td></tr></tbody>
            `;
            updateTableColumnIndices(table);
            setupTableInteractions();

            table.rows[2].cells[1].dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));

            const highlighted = Array.from(table.querySelectorAll('.col-highlight'));
            expect(highlighted.length).toBeGreaterThan(0);
            highlighted.forEach(cell => {
                expect(cell._startCol).toBeLessThanOrEqual(1);
                expect(cell._endCol).toBeGreaterThanOrEqual(1);
            });
        });
    });

    describe("initTracker", () => {
        let originalFetch;
        let consoleWarnSpy;

        beforeEach(() => {
            originalFetch = global.fetch;
            consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});

            // Setup DOM elements expected by initTracker
            document.body.innerHTML = `
                <span id="update-date-text"></span>
                <table id="tracker"></table>
            `;

            // Mock global variables used in renderTable
            global.PATCH_DATA = [];
            global.RAW_CHARACTERS = [];
        });

        afterEach(() => {
            global.fetch = originalFetch;
            consoleWarnSpy.mockRestore();
            delete global.PATCH_DATA;
            delete global.RAW_CHARACTERS;
            delete global.LAST_UPDATED;
        });

        it("uses LAST_UPDATED constant directly without fetching js/characters.js and updates DOM avatars asynchronously", async () => {
            global.LAST_UPDATED = "2026/10/16";
            global.PATCH_DATA = [{ patch: "1.0上", date: "2023-04-26" }];
            global.RAW_CHARACTERS = [{ cid: "希兒", name: "希兒", path: "巡獵", attr: "量子", runs: ["1.0上"] }];

            global.fetch = jest.fn().mockResolvedValue({
                ok: true,
                json: async () => ({
                    "1102": { name: "希兒", icon: "icon/character/1102.png" }
                })
            });

            await initTracker();

            expect(global.fetch).not.toHaveBeenCalledWith('js/characters.js');
            expect(document.getElementById('update-date-text').textContent).toBe("2026/10/16");
            const img = document.querySelector('#tracker img.char-avatar');
            expect(img).not.toBeNull();
            expect(img.src).toContain("icon/character/1102.png");
        });

        it("logs warning if fetch for characters.js rejects", async () => {
            const mockError = new Error("Network Error");
            global.fetch = jest.fn().mockRejectedValue(mockError);

            await initTracker();

            expect(global.fetch).toHaveBeenCalledWith('js/characters.js');
            expect(consoleWarnSpy).toHaveBeenCalledWith("無法讀取本地更新日期:", mockError);
            expect(document.getElementById('update-date-text').textContent).toBe("未知");
        });

        it("logs warning if fetch for characters.js is not ok", async () => {
            global.fetch = jest.fn().mockResolvedValue({ ok: false });

            await initTracker();

            expect(global.fetch).toHaveBeenCalledWith('js/characters.js');
            expect(document.getElementById('update-date-text').textContent).toBe("未知");
        });
    });

    describe('getPatchColClass', () => {
        it('prioritizes the current patch over the preview class', () => {
            expect(getPatchColClass({ patch: '1.0', isPreview: true }, '1.0')).toBe(' class="current-patch-col"');
        });

        it('marks preview patches and leaves regular patches unclassified', () => {
            expect(getPatchColClass({ patch: '1.1', isPreview: true }, '1.0')).toBe(' class="preview-patch-col"');
            expect(getPatchColClass({ patch: '1.1' }, '1.0')).toBe('');
        });
    });

    describe('getFilterState', () => {
        afterEach(() => {
            document.body.innerHTML = '';
        });

        it('returns defaults when controls are absent', () => {
            expect(getFilterState()).toEqual({
                selectedVersions: [],
                selectedPaths: [],
                selectedElems: [],
                selectedTypes: [],
                keyword: '',
                onlyBuffs: false
            });
        });

        it('reads checked filters, normalized search text, and the buff toggle', () => {
            document.body.innerHTML = `
                <input type="checkbox" class="version-item" value="1.x" checked>
                <input type="checkbox" class="path-item" value="毀滅" checked>
                <input type="checkbox" class="elem-item" value="火" checked>
                <input type="checkbox" class="type-item" value="collab" checked>
                <input id="char-search-input" value="  Kafka  ">
                <button id="buff-toggle-btn" class="active"></button>
            `;

            expect(getFilterState()).toEqual({
                selectedVersions: ['1.x'],
                selectedPaths: ['毀滅'],
                selectedElems: ['火'],
                selectedTypes: ['collab'],
                keyword: 'kafka',
                onlyBuffs: true
            });
        });

        it('normalizes a whitespace-only search term to empty', () => {
            document.body.innerHTML = '<input id="char-search-input" value="   ">';
            expect(getFilterState().keyword).toBe('');
        });
    });

    describe('filterTableRows', () => {
        function createTable() {
            const table = document.createElement('table');
            table.innerHTML = `
                <tbody>
                    <tr data-major-version="1.x" data-path="智識" data-elem="雷" data-type="normal" data-has-buff="true" data-name="景元"></tr>
                    <tr data-major-version="1.x" data-path="虛無" data-elem="雷" data-type="normal" data-has-buff="false" data-name="卡芙卡"></tr>
                    <tr data-major-version="2.x" data-path="智識" data-elem="量子" data-type="pool" data-has-buff="false" data-name="翡翠"></tr>
                    <tr data-major-version="2.x" data-path="巡獵" data-elem="物理" data-type="collab" data-has-buff="true" data-name="飛霄"></tr>
                    <tr class="empty-row"><td>empty</td></tr>
                </tbody>
            `;
            return table;
        }

        const defaultState = () => ({
            selectedVersions: [],
            selectedPaths: [],
            selectedElems: [],
            selectedTypes: [],
            keyword: '',
            onlyBuffs: false
        });

        it.each([
            ['version', { selectedVersions: ['1.x'] }, [0, 1]],
            ['path', { selectedPaths: ['智識'] }, [0, 2]],
            ['element', { selectedElems: ['雷'] }, [0, 1]],
            ['type', { selectedTypes: ['pool', 'collab'] }, [2, 3]],
            ['name', { keyword: '芙卡' }, [1]],
            ['buff', { onlyBuffs: true }, [0, 3]]
        ])('filters rows by %s', (_name, filters, expectedIndexes) => {
            const table = createTable();
            const state = { ...defaultState(), ...filters };

            const result = filterTableRows(table, state);
            const rows = Array.from(table.querySelectorAll('tbody tr:not(.empty-row)'));

            expect(result.visibleCount).toBe(expectedIndexes.length);
            expect(rows.flatMap((row, index) => row.style.display === '' ? [index] : [])).toEqual(expectedIndexes);
        });

        it('excludes the empty row and matches every supported filter', () => {
            const table = createTable();
            const state = defaultState();
            state.selectedVersions = ['1.x'];
            state.selectedPaths = ['智識'];
            state.selectedElems = ['雷'];
            state.selectedTypes = ['normal'];
            state.keyword = '景';
            state.onlyBuffs = true;

            expect(filterTableRows(table, state)).toEqual({ visibleCount: 1, totalChars: 4 });
            expect(table.querySelectorAll('tbody tr')[0].style.display).toBe('');
            expect(table.querySelectorAll('tbody tr')[1].style.display).toBe('none');
            expect(table.querySelectorAll('tbody tr')[4].style.display).toBe('');
        });

        it('filters rows by type, case-normalized name substring, and buffs', () => {
            const table = createTable();
            const state = defaultState();
            state.selectedTypes = ['pool', 'collab'];
            state.keyword = '飛';
            state.onlyBuffs = true;

            expect(filterTableRows(table, state)).toEqual({ visibleCount: 1, totalChars: 4 });
            expect(table.querySelectorAll('tbody tr')[3].style.display).toBe('');
            expect(table.querySelectorAll('tbody tr')[0].style.display).toBe('none');
        });

        it('caches row attributes between filter passes', () => {
            const table = createTable();
            const row = table.querySelector('tbody tr');
            const getAttribute = jest.spyOn(row, 'getAttribute');

            filterTableRows(table, defaultState());
            const firstPassCalls = getAttribute.mock.calls.length;
            filterTableRows(table, { ...defaultState(), onlyBuffs: true });

            expect(firstPassCalls).toBeGreaterThan(0);
            expect(getAttribute).toHaveBeenCalledTimes(firstPassCalls);
            getAttribute.mockRestore();
        });
    });

    describe('renderFilters input escaping', () => {
        afterEach(() => {
            document.body.innerHTML = '';
            delete global.PATH_ORDER;
            delete global.ELEM_ORDER;
        });

        it('escapes generated version, path, and element labels and values', () => {
            const patch = '<img src=x onerror=alert(1)>.0';
            const path = 'Path"><img src=x onerror=alert(1)>';
            const elem = '"><script>alert(1)</script>';
            global.PATH_ORDER = [path];
            global.ELEM_ORDER = [elem];
            document.body.innerHTML = `
                <div id="version-items-container"></div>
                <div id="path-items-container"></div>
                <div id="elem-items-container"></div>
                <div id="type-items-container"></div>
            `;

            renderFilters([{ runs: [patch], path, elem }], [patch], new Map([[patch, 0]]));

            const versionContainer = document.getElementById('version-items-container');
            const pathContainer = document.getElementById('path-items-container');
            const elemContainer = document.getElementById('elem-items-container');
            expect(versionContainer.querySelector('img, script')).toBeNull();
            expect(pathContainer.querySelector('img, script')).toBeNull();
            expect(elemContainer.querySelector('img, script')).toBeNull();
            expect(versionContainer.querySelector('input').value).toBe('<img src=x onerror=alert(1)>.x');
            expect(pathContainer.querySelector('input').value).toBe(path);
            expect(elemContainer.querySelector('input').value).toBe(elem);
        });
    });

    describe('sortCharacters', () => {
        const patchesList = ['1.0上', '1.0下', '1.1上', '1.1下', '1.2上'];
        const patchIndexMap = new Map(patchesList.map((p, idx) => [p, idx]));
        const activePatchName = '1.2上';
        const sampleChars = [
            { name: 'CharOldLongWait', runs: ['1.0上'] },                 // 1 run, currentGap = 4
            { name: 'CharManyRuns', runs: ['1.0下', '1.1下', '1.2上'] },   // 2 events (1.0下, 1.1下+1.2上 merged), currentGap = 0
            { name: 'CharThreeRuns', runs: ['1.0上', '1.1上', '1.2上'] },  // 3 events, currentGap = 0
            { name: 'CharPreview', runs: [], isPreview: true }             // preview, 0 runs
        ];

        it('sorts by debut-desc (latest first) and debut-asc (oldest first)', () => {
            const desc = sortCharacters(sampleChars, 'debut-desc', patchesList, activePatchName, patchIndexMap);
            expect(desc.map(c => c.name)).toEqual(['CharPreview', 'CharThreeRuns', 'CharManyRuns', 'CharOldLongWait']);

            const asc = sortCharacters(sampleChars, 'debut-asc', patchesList, activePatchName, patchIndexMap);
            expect(asc.map(c => c.name)).toEqual(['CharOldLongWait', 'CharManyRuns', 'CharThreeRuns', 'CharPreview']);
        });

        it('sorts by wait-desc (longest waiting first) and wait-asc (most recently rerun first, preview at bottom)', () => {
            const waitDesc = sortCharacters(sampleChars, 'wait-desc', patchesList, activePatchName, patchIndexMap);
            expect(waitDesc[0].name).toBe('CharOldLongWait');
            expect(waitDesc[waitDesc.length - 1].name).toBe('CharPreview');

            const waitAsc = sortCharacters(sampleChars, 'wait-asc', patchesList, activePatchName, patchIndexMap);
            expect(waitAsc[0].name).toBe('CharThreeRuns');
            expect(waitAsc[waitAsc.length - 1].name).toBe('CharPreview');
        });

        it('sorts by runs-desc (most UP runs first) and runs-asc (least UP runs first for released chars)', () => {
            const runsDesc = sortCharacters(sampleChars, 'runs-desc', patchesList, activePatchName, patchIndexMap);
            expect(runsDesc.map(c => c.name)).toEqual(['CharThreeRuns', 'CharManyRuns', 'CharOldLongWait', 'CharPreview']);

            const runsAsc = sortCharacters(sampleChars, 'runs-asc', patchesList, activePatchName, patchIndexMap);
            expect(runsAsc.map(c => c.name)).toEqual(['CharOldLongWait', 'CharManyRuns', 'CharThreeRuns', 'CharPreview']);
        });
    });

    describe('URLSearchParams state sync (parseUrlState, buildUrlSearchParams, restoreStateFromUrl)', () => {
        afterEach(() => {
            document.body.innerHTML = '';
            window.history.replaceState(null, '', '/');
            delete global.PATCH_DATA;
            delete global.RAW_CHARACTERS;
            delete global.PATH_ICONS;
        });

        it('parses URL query parameters accurately', () => {
            const parsed = parseUrlState('?ver=1.x,2.x&path=毀滅&elem=火,冰&type=normal&q=流螢&buff=1&sort=wait-desc&psort=asc&preview=0');
            expect(parsed).toEqual({
                versions: ['1.x', '2.x'],
                paths: ['毀滅'],
                elems: ['火', '冰'],
                types: ['normal'],
                keyword: '流螢',
                onlyBuffs: true,
                showPreview: false,
                charSort: 'wait-desc',
                patchSortAsc: true
            });
        });

        it('builds URL search params and omits default values', () => {
            const qs = buildUrlSearchParams(
                {
                    selectedVersions: ['2.x'],
                    selectedPaths: ['毀滅'],
                    selectedElems: ['火'],
                    selectedTypes: [],
                    keyword: '流螢',
                    onlyBuffs: true
                },
                { charSortMode: 'wait-desc', isPatchAscending: false }
            );
            const params = new URLSearchParams(qs);
            expect(params.get('ver')).toBe('2.x');
            expect(params.get('path')).toBe('毀滅');
            expect(params.get('elem')).toBe('火');
            expect(params.get('q')).toBe('流螢');
            expect(params.get('buff')).toBe('1');
            expect(params.get('sort')).toBe('wait-desc');
            expect(params.has('psort')).toBe(false);
        });

        it('restores filter and sort state from URL and syncs changes back via history.replaceState', () => {
            document.body.innerHTML = `
                <div id="version-items-container"></div>
                <div id="path-items-container"></div>
                <div id="elem-items-container"></div>
                <div id="type-items-container"></div>
                <div class="sort-select-wrap" id="char-sort-wrap">
                    <select id="char-sort-select">
                        <option value="debut">登場順序</option>
                        <option value="runs">UP次數</option>
                        <option value="wait">上次復刻時間</option>
                    </select>
                    <button type="button" id="char-sort-dir-btn">▼</button>
                </div>
                <button id="buff-toggle-btn"></button>
                <input id="char-search-input" value="">
                <table id="tracker"></table>
            `;
            global.PATCH_DATA = [
                { patch: '1.0上', date: '23/04/26' },
                { patch: '2.0上', date: '24/02/06' }
            ];
            global.RAW_CHARACTERS = [
                { name: '希兒', path: '巡獵', elem: '量子', runs: ['1.0上'] },
                { name: '花火', path: '同諧', elem: '量子', runs: ['2.0上'], buffs: ['2.0上'] }
            ];
            global.PATH_ICONS = {};

            const replaceStateSpy = jest.spyOn(window.history, 'replaceState');

            restoreStateFromUrl('?ver=2.x&path=同諧&q=花&buff=1&sort=wait-asc');

            expect(document.getElementById('char-search-input').value).toBe('花');
            expect(document.getElementById('buff-toggle-btn').classList.contains('active')).toBe(true);
            expect(document.getElementById('char-sort-select').value).toBe('wait');
            expect(document.getElementById('char-sort-dir-btn').textContent).toBe('▲');

            const rows = Array.from(document.querySelectorAll('#tracker tbody tr:not(.empty-row)'));
            const visibleRows = rows.filter(r => r.style.display !== 'none');
            expect(visibleRows.length).toBe(1);
            expect(visibleRows[0].getAttribute('data-name')).toBe('花火');

            expect(replaceStateSpy).toHaveBeenCalled();
            expect(window.location.search).toContain('sort=wait-asc');
            replaceStateSpy.mockRestore();
        });
    });

    describe('Character Stats Popover (buildCharPopoverHtml, showCharPopover, hideCharPopover)', () => {
        afterEach(() => {
            document.body.innerHTML = '';
        });

        it('builds glassmorphic popover HTML for regular, overdue, preview, term, and collab characters', () => {
            const overdueHtml = buildCharPopoverHtml({
                charName: '景元',
                charElem: '雷',
                charPath: '智識',
                debut: '1.0下',
                currentGap: '12',
                maxGap: '8',
                totalRuns: '2',
                isOverdue: 'true',
                isPreview: 'false',
                isCollab: 'false',
                isTerm: 'false'
            });
            expect(overdueHtml).toContain('景元');
            expect(overdueHtml).toContain('1.0下');
            expect(overdueHtml).toContain('12 個版本');
            expect(overdueHtml).toContain('8 個版本');
            expect(overdueHtml).toContain('2 次');
            expect(overdueHtml).toContain('popover-overdue-alert');

            const previewHtml = buildCharPopoverHtml({
                charName: '新角色',
                charElem: '冰',
                charPath: '記憶',
                debut: '4.3上',
                isPreview: 'true'
            });
            expect(previewHtml).toContain('預定登場');
            expect(previewHtml).toContain('🔮 預覽角色');
        });

        it('shows and hides popover on .char-info-cell click and outside click', () => {
            document.body.innerHTML = `
                <table id="tracker">
                    <tbody>
                        <tr>
                            <td>
                                <div class="char-info-cell"
                                     data-char-name="希兒"
                                     data-char-elem="量子"
                                     data-char-path="巡獵"
                                     data-debut="1.0上"
                                     data-current-gap="5"
                                     data-max-gap="4"
                                     data-total-runs="2"
                                     data-is-overdue="true">
                                    <span class="char-name">希兒</span>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>
                <div id="char-stats-popover" class="char-stats-popover" aria-hidden="true"></div>
            `;

            setupTableInteractions();
            const infoCell = document.querySelector('.char-info-cell');
            const popover = document.getElementById('char-stats-popover');

            // First click opens and pins popover
            infoCell.dispatchEvent(new MouseEvent('click', { bubbles: true }));
            expect(popover.classList.contains('show')).toBe(true);
            expect(popover.classList.contains('pinned')).toBe(true);
            expect(popover.innerHTML).toContain('希兒');
            expect(popover.innerHTML).toContain('popover-overdue-alert');

            // Clicking outside closes popover
            document.body.dispatchEvent(new MouseEvent('click', { bubbles: true }));
            expect(popover.classList.contains('show')).toBe(false);
        });
    });

    describe('Top-Left Character Sort Popover Menu (buildCharSortMenuHtml, showCharSortMenu, hideCharSortMenu, toggleCharSortMenu)', () => {
        beforeEach(() => {
            document.body.innerHTML = `
                <table id="tracker">
                    <thead>
                        <tr>
                            <th class="top-left-cell">
                                <button type="button" id="sort-char-btn" class="table-sort-btn">登場 ▼</button>
                                <button type="button" id="sort-patch-btn" class="table-sort-btn">版本 ◀</button>
                            </th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
                <div id="char-sort-popover" class="char-sort-popover" role="menu" aria-hidden="true"></div>
            `;
            global.PATCH_DATA = [
                { patch: '1.0上', date: '23/04/26' },
                { patch: '2.0上', date: '24/02/06' }
            ];
            global.RAW_CHARACTERS = [
                { name: '希兒', path: '巡獵', elem: '量子', runs: ['1.0上'] },
                { name: '花火', path: '同諧', elem: '量子', runs: ['2.0上'] }
            ];
            global.PATH_ICONS = {};
        });

        afterEach(() => {
            document.body.innerHTML = '';
            delete global.PATCH_DATA;
            delete global.RAW_CHARACTERS;
            delete global.PATH_ICONS;
        });

        it('returns proper labels and descriptions for all sort dimensions and directions', () => {
            expect(getSortCharBtnLabel('debut-desc', false)).toBe('登場 ▼');
            expect(getSortCharBtnLabel('debut-asc', true)).toBe('登場 ▲');
            expect(getSortCharBtnLabel('wait-desc', false)).toBe('復刻 ▼');
            expect(getSortCharBtnLabel('wait-asc', true)).toBe('復刻 ▲');
            expect(getSortCharBtnLabel('runs-desc', false)).toBe('UP數 ▼');
            expect(getSortCharBtnLabel('runs-asc', true)).toBe('UP數 ▲');

            expect(getSortDescription('debut-desc')).toContain('最新優先');
            expect(getSortDescription('wait-desc')).toContain('最久未復刻優先');
            expect(getSortDescription('runs-desc')).toContain('次數最多優先');
        });

        it('builds menu HTML with all 6 options and marks current mode active', () => {
            const html = buildCharSortMenuHtml('wait-desc', false);
            expect(html).toContain('data-sort-mode="debut-desc"');
            expect(html).toContain('data-sort-mode="debut-asc"');
            expect(html).toContain('data-sort-mode="wait-desc"');
            expect(html).toContain('data-sort-mode="wait-asc"');
            expect(html).toContain('data-sort-mode="runs-desc"');
            expect(html).toContain('data-sort-mode="runs-asc"');
            expect(html).toContain('class="sort-option-btn active" data-sort-mode="wait-desc"');
        });

        it('toggles sort popover open/close on button click and closes on outside click or Escape', () => {
            setupSortingListeners();
            const sortBtn = document.getElementById('sort-char-btn');
            const popover = document.getElementById('char-sort-popover');

            // Open via sortBtn click
            sortBtn.dispatchEvent(new MouseEvent('click', { bubbles: true }));
            expect(popover.classList.contains('show')).toBe(true);
            expect(popover.getAttribute('aria-hidden')).toBe('false');

            // Click option to change sort mode
            const waitOption = popover.querySelector('[data-sort-mode="wait-desc"]');
            expect(waitOption).not.toBeNull();
            waitOption.dispatchEvent(new MouseEvent('click', { bubbles: true }));

            // Popover should close after selection
            expect(popover.classList.contains('show')).toBe(false);

            // Re-open and close with Escape key
            const newSortBtn = document.getElementById('sort-char-btn');
            expect(newSortBtn.textContent).toBe('復刻 ▼');
            newSortBtn.dispatchEvent(new MouseEvent('click', { bubbles: true }));
            expect(popover.classList.contains('show')).toBe(true);

            document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
            expect(popover.classList.contains('show')).toBe(false);
        });
    });
});

