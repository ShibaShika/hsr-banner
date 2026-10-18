// 💠 卡池強化模式（Buff Mode）註冊表
// - 角色資料中的 buffs 為「版本名稱字串陣列」，預設皆屬 DEFAULT_BUFF_TYPE。
// - 非預設的新強化模式以 buffTypes: { "<版本>": "<強化模式名稱>" } 標記。
// - 未在 BUFF_META 註冊的新模式，前端會自動套用「深空琉璃通用風格（Fallback Style）」，無需修改程式碼。
const DEFAULT_BUFF_TYPE = "礪爍新輝";

const BUFF_ORDER = ["礪爍新輝"];

const BUFF_META = {
    "礪爍新輝": { icon: "▲", desc: "角色能力加強" }
};
