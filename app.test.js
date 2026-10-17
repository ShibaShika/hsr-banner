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
    updateTableColumnIndices,
    buildHistoryCellsHtml,
    buildCharacterRowHtml,
    renderTable
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


    describe('calculateCharStats helpers', () => {
        describe('getPatchIndex', () => {
            it('returns index using map', () => {
                const map = new Map();
                map.set('1.0', 0);
                expect(getPatchIndex('1.0', ['1.0', '1.1'], map)).toBe(0);
            });
            it('returns -1 for missing patch using map', () => {
                const map = new Map();
                expect(getPatchIndex('1.0', [], map)).toBe(-1);
            });
            it('returns index using array if no map provided', () => {
                expect(getPatchIndex('1.1', ['1.0', '1.1'], null)).toBe(1);
            });
        });

        describe('getTermStatus', () => {
            it('returns active status for valid term', () => {
                const char = { term: { patch: '1.2', type: 'pool' } };
                const status = getTermStatus(char, 5, ['1.0', '1.1', '1.2'], null);
                expect(status.isTermActive).toBe(true);
                expect(status.validEndIdx).toBe(2);
                expect(status.termLabel).toBe('星緣');
            });
            it('returns active status for diff term type', () => {
                const char = { term: { patch: '1.2', type: 'other' } };
                const status = getTermStatus(char, 5, ['1.0', '1.1', '1.2'], null);
                expect(status.termLabel).toBe('聚靈');
            });
            it('returns false for no term', () => {
                const char = {};
                const status = getTermStatus(char, 5, [], null);
                expect(status.isTermActive).toBe(false);
                expect(status.validEndIdx).toBe(5);
            });
        });

        describe('mergeContinuousEvents', () => {
            it('merges consecutive indices', () => {
                expect(mergeContinuousEvents([1, 2, 4, 5, 6, 8])).toEqual([
                    { start: 1, end: 2 },
                    { start: 4, end: 6 },
                    { start: 8, end: 8 }
                ]);
            });
            it('handles single event', () => {
                expect(mergeContinuousEvents([1])).toEqual([{ start: 1, end: 1 }]);
            });
            it('handles empty events', () => {
                expect(mergeContinuousEvents([])).toEqual([]);
            });
        });

        describe('calculateGaps', () => {
            it('calculates gaps between events correctly', () => {
                const events = [
                    { start: 1, end: 2 },
                    { start: 5, end: 6 }, // gap: 5 - 2 - 1 = 2
                    { start: 10, end: 10 } // gap: 10 - 6 - 1 = 3
                ];
                expect(calculateGaps(events)).toEqual([2, 3]);
            });
            it('returns empty for single event', () => {
                expect(calculateGaps([{ start: 1, end: 2 }])).toEqual([]);
            });
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

    const { escapeHtml } = require("./js/app.js");

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

    const { formatHeaderDate } = require("./js/app.js");

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

    const { getCharDebutVersion } = require("./js/app.js");

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

    const { getFallbackAvatar } = require("./js/app.js");
    const { getHistoryElement, getCharacterType, buildCharacterHistory, getCharacterTooltip, buildTableHeaderHtml } = require("./js/app.js");


    describe('getHistoryElement', () => {
        let patchIndexMap;
        beforeEach(() => {
            patchIndexMap = new Map();
            const patches = ['1.0', '1.1', '1.2', '1.3', '1.4'];
            patches.forEach((p, i) => patchIndexMap.set(p, i));
        });

        it('should handle collab characters before start', () => {
            const state = { collabSpanAdded: false, patchesListLength: 5 };
            const char = { isCollab: '1.2' }; // index 2

            const result1 = getHistoryElement(char, '1.0', 0, state, patchIndexMap);
            expect(result1).toEqual({ status: 'COLLAB_BEFORE' });

            const result2 = getHistoryElement(char, '1.1', 1, state, patchIndexMap);
            expect(result2).toEqual({ status: 'COLLAB_BEFORE' });
        });

        it('should handle collab characters exactly on start patch or end patch', () => {
            const state = { collabSpanAdded: true, patchesListLength: 5 };
            const char = { isCollab: '1.2' }; // index 2

            // pIdx 2 (=== sIdx)
            const result1 = getHistoryElement(char, '1.2', 2, state, patchIndexMap);
            expect(result1).toEqual({ status: 'COLLAB' });

            // pIdx 4 (=== lIdx)
            const result2 = getHistoryElement(char, '1.4', 4, state, patchIndexMap);
            expect(result2).toEqual({ status: 'COLLAB' });
        });

        it('should handle collab characters between start and end patch', () => {
            const state = { collabSpanAdded: true, patchesListLength: 5 };
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

    const { initTracker } = require("./js/app.js");

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
});
