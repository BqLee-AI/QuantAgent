# Change: Design Tailwind Theme

## Why

DESIGN.md 已定义完整的视觉规范（色彩、排版、间距、圆角、海拔），但当前 styles.css 使用硬编码的 CSS 值，与 DESIGN.md 的 token 体系完全脱节。本 change 将 DESIGN.md 的设计 token 系统化地映射到 CSS 变量和 Tailwind 主题配置，使全站 UI 与设计规范保持一致，并为后续组件开发提供统一的 utility class 基础。

## What Changes

- 在 `apps/web/src/styles/tokens.css` 中定义 `--qa-*` 原始 CSS 变量，覆盖 DESIGN.md 的色彩、排版、间距、圆角、阴影 token。
- 在 `apps/web/src/styles/tailwind-theme.css` 的 Tailwind v4 @theme 指令中注册语义化 utility class（如 `text-ink`、`bg-canvas`、`rounded-card`），从 `--qa-*` 映射到 Tailwind `--color-*` / `--font-*` 主题变量，避免自引用 token。
- 配置 HeroUI 主题，使 primary、danger 等语义与 DESIGN.md 对齐。
- 用 CSS 变量替换 `apps/web/src/styles/**` 和 MainLayout 中的硬编码颜色值。
- 替换字体栈为 Inter（BinanceNova 的开源替代）+ JetBrains Mono（BinancePlex 的替代）。

## Font Implementation Details

- 生产环境字体使用本地托管，不依赖 CDN。Inter 与 JetBrains Mono 均采用 variable font 的 `woff2` 文件，减少多字重请求数量；CDN 只可用于本地快速验证，不进入提交。
- 字体文件放置在 `apps/web/public/fonts/`：
  - `apps/web/public/fonts/inter/InterVariable.woff2`
  - `apps/web/public/fonts/inter/InterVariable-Italic.woff2`
  - `apps/web/public/fonts/inter/OFL.txt`
  - `apps/web/public/fonts/jetbrains-mono/JetBrainsMonoVariable.woff2`
  - `apps/web/public/fonts/jetbrains-mono/JetBrainsMonoVariable-Italic.woff2`
  - `apps/web/public/fonts/jetbrains-mono/OFL.txt`
- `apps/web/index.html` 需要在 `<head>` 中为首屏字体添加 preload：
  - `<link rel="preload" href="/fonts/inter/InterVariable.woff2" as="font" type="font/woff2" crossorigin />`
  - `<link rel="preload" href="/fonts/jetbrains-mono/JetBrainsMonoVariable.woff2" as="font" type="font/woff2" crossorigin />`
- `apps/web/src/styles.css` 通过 `@font-face` 注册 `Inter` 和 `JetBrains Mono`，设置 `font-display: swap`；不需要额外 FontFace API runtime loading，除非后续出现按路由延迟加载字体的性能需求。
- `openspec/changes/design-tailwind-theme/specs/design-tailwind-theme/spec.md` 记录字体托管与加载要求，`openspec/changes/design-tailwind-theme/tasks.md` 记录资产、`index.html`、`styles.css` 和许可证检查任务。
- 许可证检查清单：
  - Inter 使用 SIL Open Font License 1.1，允许项目内自托管和商业/非商业使用；保留 `OFL.txt`。
  - JetBrains Mono 使用 SIL Open Font License 1.1，允许项目内自托管和商业/非商业使用；保留 `OFL.txt`。
  - 如修改字体文件，不使用保留字体名发布修改版；当前 change 只分发未修改字体文件。

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
