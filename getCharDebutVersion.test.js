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
