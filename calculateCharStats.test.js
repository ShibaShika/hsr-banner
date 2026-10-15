const { calculateCharStats, getPatchIndex, getTermStatus, mergeContinuousEvents, calculateGaps } = require('./js/app');

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
