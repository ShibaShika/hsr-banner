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
    calculateGaps
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
        });

        it("should correctly escape multiple special characters in a single string", () => {
            expect(escapeHtml("<div class=\"test\">Bob & Alice's String</div>"))
                .toBe("&lt;div class=&quot;test&quot;&gt;Bob &amp; Alice&#39;s String&lt;/div&gt;");
            expect(escapeHtml("<<<>>>&&&\"\"\"'''"))
                .toBe("&lt;&lt;&lt;&gt;&gt;&gt;&amp;&amp;&amp;&quot;&quot;&quot;&#39;&#39;&#39;");
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
    const { getCharacterType, buildCharacterHistory, getCharacterTooltip, buildTableHeaderHtml } = require("./js/app.js");


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
});
