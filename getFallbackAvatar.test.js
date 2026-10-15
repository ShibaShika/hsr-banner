const { getFallbackAvatar } = require("./js/app.js");

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
