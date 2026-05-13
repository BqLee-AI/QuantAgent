# @quantagent/web

QuantAgent 前端应用 — 事件驱动型量化智能系统的管理控制台与审批工作台。

## 技术栈

| 类别     | 选型                                         |
| -------- | -------------------------------------------- |
| 构建工具 | Vite 8 + TypeScript 6                        |
| UI 框架  | React 19 + HeroUI v3                         |
| 路由     | TanStack Router (基于文件系统的类型安全路由) |
| 数据层   | TanStack Query                               |
| 样式     | Tailwind CSS v4 + 自定义设计令牌             |
| 表单校验 | Zod                                          |
| 代码检查 | OxLint                                       |
| 包管理   | Bun (monorepo workspace)                     |

## 项目结构

```
apps/web/
├── src/
│   ├── app/                  # 应用层
│   │   └── layouts/          # 布局组件 (MainLayout)
│   ├── routes/               # TanStack Router 文件路由
│   │   ├── __root.tsx        # 根路由 + 全局布局
│   │   ├── index.tsx         # / → 重定向到 /events
│   │   ├── events/           # 事件收件箱
│   │   ├── runtime/          # 运行时看板
│   │   ├── approvals/        # 审批中心
│   │   ├── plugins/          # 插件管理
│   │   └── settings/         # 应用设置
│   ├── shared/               # 跨模块共享
│   │   └── ui/               # UI 工具 (cn, theme-primitives)
│   ├── index.css             # 设计令牌 (色彩、圆角、阴影)
│   ├── App.tsx               # Router 引导
│   └── main.tsx              # 入口
├── oxlint.config.ts          # OxLint 规则配置
├── tailwind.config.ts        # Tailwind 主题扩展
├── tsconfig.app.json         # TS 配置 (含 @/* 路径别名)
└── vite.config.ts            # Vite 配置
```

## 开发

```bash
# 安装依赖 (在 monorepo 根目录执行)
bun install

# 启动开发服务器
cd apps/web && bun run dev

# 生产构建
bun run build

# 代码检查
bun run lint
```

## 设计系统

样式基于 `src/index.css` 中定义的 CSS 自定义属性（`--qa-*` 前缀），配合 Tailwind CSS v4 使用。设计令牌涵盖：

- **色彩**: 主色蓝 (`#3b82f6`)、交易涨跌语义色、风险等级色
- **圆角**: 4px / 6px / 8px / 12px / pill
- **阴影**: 卡片级 / 模态级 / 聚焦环
- **字体**: BinanceNova (展示) + BinancePlex (数值)

详细规范参见项目根目录 `DESIGN.md`。
