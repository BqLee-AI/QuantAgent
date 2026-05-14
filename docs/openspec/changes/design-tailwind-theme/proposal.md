# Change: Design Tailwind Theme

## Why

DESIGN.md 已定义完整的视觉规范（色彩、排版、间距、圆角、海拔），但当前 styles.css 使用硬编码的 CSS 值，与 DESIGN.md 的 token 体系完全脱节。本 change 将 DESIGN.md 的设计 token 系统化地映射到 CSS 变量和 Tailwind 主题配置，使全站 UI 与设计规范保持一致，并为后续组件开发提供统一的 utility class 基础。

## What Changes

- 在 styles.css 中定义 CSS 变量，覆盖 DESIGN.md 的色彩、排版、间距、圆角、阴影 token。
- 在 Tailwind v4 的 @theme 指令中注册语义化 utility class（如 `text-ink`、`bg-canvas`、`rounded-card`）。
- 配置 HeroUI 主题，使 primary、danger 等语义与 DESIGN.md 对齐。
- 用 CSS 变量替换 styles.css 和 MainLayout 中的硬编码颜色值。
- 替换字体栈为 Inter（BinanceNova 的开源替代）+ JetBrains Mono（BinancePlex 的替代）。

## Out Of Scope

- 动画和过渡时序。
- 暗色主题切换。
- 组件级重构（仅建立 token 基础，组件改造留给后续 issue）。
- 修改 DESIGN.md 本身。

## Success Criteria

- 修改 CSS 变量后，全站 UI 同步变化。
- 开发者可通过语义 class（如 `bg-primary`、`text-muted`）编写样式，无需记忆具体色值。
- HeroUI 组件的 primary/success/danger 语义与 DESIGN.md 一致。
- `bun run build` 通过。
