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
