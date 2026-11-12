// 🏷️ 取得方法（Acquisition Type）註冊表（非白名單）
// - 核心四類為 normal（限定躍遷）、pool（星緣相邀）、shop（聚靈鑄星）、collab（長期聯動）。
// - 任何未在此註冊之未來新取得方法（如新常駐商店、新常駐池、全新系統名），
//   前端會自動從 RAW_CHARACTERS 動態收集並套用「深空琉璃通用降級風格（Fallback Style）」，無需修改程式碼。
const DEFAULT_ACQUISITION_TYPE = "normal";

const TYPE_ORDER = ["normal", "pool", "shop", "collab"];

const TYPE_META = {
    "normal": {
        label: "限定躍遷",
        shortLabel: "限定躍遷",
        desc: ""
    },
    "pool": {
        label: "星緣相邀",
        shortLabel: "星緣",
        desc: "加入非UP自選池",
        cellClass: "term-pool",
        emptyClass: "term-pool-empty"
    },
    "shop": {
        label: "聚靈鑄星",
        shortLabel: "聚靈",
        desc: "加入兌換商店",
        cellClass: "term-shop",
        emptyClass: "term-shop-empty"
    },
    "collab": {
        label: "長期聯動",
        shortLabel: "聯動",
        desc: ""
    },
    "stellar": {
        label: "群星躍遷",
        shortLabel: "群星",
        desc: "加入常駐躍遷池",
        cellClass: "term-stellar",
        emptyClass: "term-stellar-empty"
    }
};

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { DEFAULT_ACQUISITION_TYPE, TYPE_ORDER, TYPE_META };
}
