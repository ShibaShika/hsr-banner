const RAW_CHARACTERS = [
    {
        name: "未知角色",
        path: "歡愉",
        elem: "量子",
        avatar: "",
        runs: [
            "4.5下"
        ]
    },
    {
        name: "希兒",
        path: "巡獵",
        elem: "量子",
        avatar: "",
        runs: [
            "1.0上",
            "1.4下"
        ],
        term: {
            type: "pool",
            patch: "3.2上"
        }
    },
    {
        name: "景元",
        path: "智識",
        elem: "雷",
        avatar: "",
        runs: [
            "1.0下",
            "2.0下",
            "2.7上"
        ]
    },
    {
        name: "銀狼",
        path: "虛無",
        elem: "量子",
        avatar: "",
        runs: [
            "1.1上",
            "1.5下",
            "3.0下",
            "3.5下"
        ],
        term: {
            type: "pool",
            patch: "4.2上"
        }
    },
    {
        name: "羅剎",
        path: "豐饒",
        elem: "虛數",
        avatar: "",
        runs: [
            "1.1下",
            "2.1上"
        ],
        term: {
            type: "shop",
            patch: "3.2上"
        }
    },
    {
        name: "刃",
        path: "毀滅",
        elem: "風",
        avatar: "",
        runs: [
            "1.2上",
            "1.6上",
            "3.4下"
        ],
        term: {
            type: "pool",
            patch: "3.2上"
        }
    },
    {
        name: "卡芙卡",
        path: "虛無",
        elem: "雷",
        avatar: "",
        runs: [
            "1.2下",
            "1.6下",
            "2.5上",
            "3.5上"
        ]
    },
    {
        name: "丹恆•飲月",
        path: "毀滅",
        elem: "虛數",
        avatar: "",
        runs: [
            "1.3上",
            "2.0上",
            "2.6上"
        ]
    },
    {
        name: "符玄",
        path: "存護",
        elem: "量子",
        avatar: "",
        runs: [
            "1.3下",
            "2.2下"
        ],
        term: {
            type: "pool",
            patch: "3.2上"
        }
    },
    {
        name: "鏡流",
        path: "毀滅",
        elem: "冰",
        avatar: "",
        runs: [
            "1.4上",
            "2.1下",
            "3.4下"
        ]
    },
    {
        name: "托帕",
        path: "巡獵",
        elem: "火",
        avatar: "",
        runs: [
            "1.4下",
            "2.2上",
            "2.5下"
        ],
        term: {
            type: "shop",
            patch: "3.7上"
        }
    },
    {
        name: "藿藿",
        path: "豐饒",
        elem: "風",
        avatar: "",
        runs: [
            "1.5上",
            "2.4上",
            "3.1下"
        ],
        term: {
            type: "shop",
            patch: "4.2上"
        }
    },
    {
        name: "銀枝",
        path: "智識",
        elem: "物理",
        avatar: "",
        runs: [
            "1.5下",
            "2.3下"
        ],
        term: {
            type: "pool",
            patch: "4.2上"
        }
    },
    {
        name: "阮•梅",
        path: "同諧",
        elem: "冰",
        avatar: "",
        runs: [
            "1.6上",
            "2.3上"
        ],
        term: {
            type: "shop",
            patch: "3.2上"
        }
    },
    {
        name: "真理醫生",
        path: "巡獵",
        elem: "虛數",
        avatar: "",
        runs: [
            "1.6下",
            "3.2下"
        ]
    },
    {
        name: "黑天鵝",
        path: "虛無",
        elem: "風",
        avatar: "",
        runs: [
            "2.0上",
            "2.5上",
            "4.0上"
        ]
    },
    {
        name: "花火",
        path: "同諧",
        elem: "量子",
        avatar: "",
        runs: [
            "2.0下",
            "2.4下",
            "3.4上",
            "4.0下"
        ]
    },
    {
        name: "黃泉",
        path: "虛無",
        elem: "雷",
        avatar: "",
        runs: [
            "2.1上",
            "2.6下",
            "3.2上"
        ]
    },
    {
        name: "砂金",
        path: "存護",
        elem: "虛數",
        avatar: "",
        runs: [
            "2.1下",
            "2.6下",
            "4.4下"
        ]
    },
    {
        name: "知更鳥",
        path: "同諧",
        elem: "物理",
        avatar: "",
        runs: [
            "2.2上",
            "2.5上",
            "3.0下"
        ],
        term: {
            type: "shop",
            patch: "4.2上"
        }
    },
    {
        name: "波提歐",
        path: "巡獵",
        elem: "物理",
        avatar: "",
        runs: [
            "2.2下",
            "3.0下",
            "4.1下"
        ]
    },
    {
        name: "流螢",
        path: "毀滅",
        elem: "火",
        avatar: "",
        runs: [
            "2.3上",
            "2.7下",
            "3.4下",
            "3.8上",
            "4.2上"
        ]
    },
    {
        name: "翡翠",
        path: "智識",
        elem: "量子",
        avatar: "",
        runs: [
            "2.3下",
            "3.0上"
        ]
    },
    {
        name: "雲璃",
        path: "毀滅",
        elem: "物理",
        avatar: "",
        runs: [
            "2.4上",
            "3.1上"
        ],
        term: {
            type: "pool",
            patch: "4.2上"
        }
    },
    {
        name: "椒丘",
        path: "虛無",
        elem: "火",
        avatar: "",
        runs: [
            "2.4下",
            "3.2上"
        ]
    },
    {
        name: "飛霄",
        path: "巡獵",
        elem: "風",
        avatar: "",
        runs: [
            "2.5上",
            "3.0上",
            "4.2下"
        ]
    },
    {
        name: "靈砂",
        path: "豐饒",
        elem: "火",
        avatar: "",
        runs: [
            "2.5下",
            "3.0上",
            "3.8中"
        ]
    },
    {
        name: "亂破",
        path: "智識",
        elem: "虛數",
        avatar: "",
        runs: [
            "2.6上",
            "4.0下"
        ]
    },
    {
        name: "星期日",
        path: "同諧",
        elem: "虛數",
        avatar: "",
        runs: [
            "2.7上",
            "3.4上",
            "3.8下",
            "4.2下"
        ]
    },
    {
        name: "忘歸人",
        path: "虛無",
        elem: "火",
        avatar: "",
        runs: [
            "2.7下",
            "3.2上",
            "3.8中"
        ]
    },
    {
        name: "大黑塔",
        path: "智識",
        elem: "冰",
        avatar: "",
        runs: [
            "3.0上",
            "3.3上",
            "3.6上"
        ]
    },
    {
        name: "阿格萊雅",
        path: "記憶",
        elem: "雷",
        avatar: "",
        runs: [
            "3.0下",
            "3.3下",
            "3.8下"
        ]
    },
    {
        name: "緹寶",
        path: "同諧",
        elem: "量子",
        avatar: "",
        runs: [
            "3.1上",
            "3.4上",
            "3.7上",
            "4.2下"
        ]
    },
    {
        name: "萬敵",
        path: "毀滅",
        elem: "虛數",
        avatar: "",
        runs: [
            "3.1下",
            "3.7下"
        ]
    },
    {
        name: "遐蝶",
        path: "記憶",
        elem: "量子",
        avatar: "",
        runs: [
            "3.2上",
            "3.7上",
            "4.2上"
        ]
    },
    {
        name: "那刻夏",
        path: "智識",
        elem: "風",
        avatar: "",
        runs: [
            "3.2下",
            "3.6下",
            "4.4下"
        ]
    },
    {
        name: "風堇",
        path: "記憶",
        elem: "風",
        avatar: "",
        runs: [
            "3.3上",
            "3.7上",
            "4.1上"
        ]
    },
    {
        name: "賽飛兒",
        path: "同諧",
        elem: "量子",
        avatar: "",
        runs: [
            "3.3下",
            "3.7下"
        ]
    },
    {
        name: "白厄",
        path: "毀滅",
        elem: "物理",
        avatar: "",
        runs: [
            "3.4上",
            "3.7下",
            "4.3下"
        ]
    },
    {
        name: "Saber",
        path: "毀滅",
        elem: "風",
        avatar: "",
        isCollab: "3.4上",
        runs: []
    },
    {
        name: "Archer",
        path: "巡獵",
        elem: "量子",
        avatar: "",
        isCollab: "3.4上",
        runs: []
    },
    {
        name: "海瑟音",
        path: "虛無",
        elem: "物理",
        avatar: "",
        runs: [
            "3.5上",
            "4.0上"
        ]
    },
    {
        name: "刻律德菈",
        path: "同諧",
        elem: "風",
        avatar: "",
        runs: [
            "3.5下",
            "4.0下",
            "4.4下"
        ]
    },
    {
        name: "長夜月",
        path: "記憶",
        elem: "冰",
        avatar: "",
        runs: [
            "3.6上",
            "4.0上",
            "4.4上"
        ]
    },
    {
        name: "丹恆•騰荒",
        path: "存護",
        elem: "物理",
        avatar: "",
        runs: [
            "3.6下",
            "4.4上"
        ]
    },
    {
        name: "昔漣",
        path: "記憶",
        elem: "冰",
        avatar: "",
        runs: [
            "3.7上",
            "3.7下",
            "4.3下"
        ]
    },
    {
        name: "大理花",
        path: "虛無",
        elem: "火",
        avatar: "",
        runs: [
            "3.8上",
            "4.2上"
        ]
    },
    {
        name: "爻光",
        path: "歡愉",
        elem: "物理",
        avatar: "",
        runs: [
            "4.0上",
            "4.0下",
            "4.3上"
        ]
    },
    {
        name: "火花",
        path: "歡愉",
        elem: "火",
        avatar: "",
        runs: [
            "4.0下",
            "4.4上"
        ]
    },
    {
        name: "不死途",
        path: "巡獵",
        elem: "雷",
        avatar: "",
        runs: [
            "4.1上",
            "4.1下"
        ]
    },
    {
        name: "銀狼LV.999",
        path: "歡愉",
        elem: "虛數",
        avatar: "",
        runs: [
            "4.2上"
        ]
    },
    {
        name: "緋英",
        path: "歡愉",
        elem: "物理",
        avatar: "",
        runs: [
            "4.2下"
        ]
    },
    {
        name: "千冶•刃",
        path: "虛無",
        elem: "火",
        avatar: "",
        runs: [
            "4.3上"
        ]
    },
    {
        name: "姬子•啟行",
        path: "智識",
        elem: "火",
        avatar: "",
        runs: [
            "4.4上"
        ]
    },
    {
        name: "遠坂凜",
        path: "智識",
        elem: "量子",
        avatar: "",
        isCollab: "4.4上",
        runs: []
    },
    {
        name: "吉爾伽美什",
        path: "毀滅",
        elem: "雷",
        avatar: "",
        isCollab: "4.4上",
        runs: []
    }
];
