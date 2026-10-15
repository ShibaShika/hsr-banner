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
