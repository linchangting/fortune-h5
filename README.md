# 今日运势 — 八字算命 H5

移动端优先的八字算命工具 —— 输入生辰八字，结合当日黄历，AI 为你解读每日运势。

## 功能特性

- **专业八字排盘**：四柱（年月日时）+ 藏干 + 十神 + 纳音
- **五行旺衰分析**：旺衰法判断日主强弱，自动推算喜用神/忌神
- **大运流年**：排列十步大运，标注当前大运与流年
- **每日运势**：流日干支与命局交叉分析，评分制运势（事业/财运/感情/健康）
- **黄历整合**：宜忌、值日星神、吉凶时辰
- **幸运提示**：幸运色、幸运数字、幸运方位（基于喜用神五行）
- **AI 解读**：通义千问 LLM 生成自然语言运势解读
- **分享海报**：Canvas 生成国风运势海报
- **历史记录**：最近 30 天运势缓存，打开即看
- **农历选择器**：自定义三列滚动选择器，支持闰月

## 项目结构

```
fortune-h5/
├── frontend/              # H5 前端（原生 HTML/CSS/JS）
│   ├── index.html
│   ├── css/app.css        # 国风设计系统
│   └── js/
│       ├── utils.js       # 工具函数 + localStorage
│       ├── api.js         # API 交互
│       ├── calendar.js    # 农历三列选择器
│       ├── ui.js          # UI 渲染
│       ├── poster.js      # Canvas 海报生成
│       └── app.js         # 主入口 + 状态管理
├── backend/               # FastAPI 后端
│   ├── app/
│   │   ├── calendar_util.py  # 历法数据表 + 转换
│   │   ├── bazi.py           # 八字排盘核心
│   │   ├── wuxing.py         # 五行旺衰 + 喜用神
│   │   ├── dayun.py          # 大运流年
│   │   ├── daily.py          # 每日运势评分
│   │   ├── almanac.py        # 黄历引擎
│   │   ├── llm.py            # LLM 润色层
│   │   ├── main.py           # API 路由
│   │   ├── config.py         # 配置管理
│   │   └── models.py         # 数据模型
│   ├── requirements.txt
│   └── .env.example
├── start.sh               # 一键启动
└── .gitignore
```

## 快速开始

```bash
# 1. 配置 API Key
cp backend/.env.example backend/.env
# 编辑 backend/.env 填入你的 DASHSCOPE_API_KEY

# 2. 一键启动
chmod +x start.sh && ./start.sh
```

浏览器访问 `http://localhost:8080`，手机扫码同局域网 IP 也可访问。

## 技术栈

- **前端**：原生 HTML5 + CSS3 + JavaScript（无框架依赖，适配 H5 / 微信内置浏览器）
- **后端**：Python FastAPI + cnlunar（农历/黄历） + 通义千问 LLM
- **设计**：国风配色（红/金/暖白），移动端优先，支持 PWA

## 命理规则说明

- 年柱以**立春**为界（非正月初一）
- 月柱以**节气**为界
- 时柱 23:00 后算**次日子时**
- 五虎遁月法推算月干，五鼠遁时法推算时干
- 日主旺衰采用**旺衰法**，综合月令、得地、得生、得助判断
- 大运排列：阳年男/阴年女顺排，阴年男/阳年女逆排

## 免责声明

本工具仅供娱乐参考，不构成任何人生、投资或医疗决策建议。
