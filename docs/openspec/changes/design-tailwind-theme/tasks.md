# Tasks: Design Tailwind Theme

## 1. CSS Variable Token Layer

- [x] 在 `apps/web/src/styles/tokens.css` 中定义 `:root` `--qa-*` CSS 变量，覆盖 DESIGN.md 的色彩 token（brand、surface、hairline、text、trading、info）。
- [x] 定义排版 token（font-family：`--qa-font-*`、font-size + line-height：`--qa-text-*`/`--qa-text-{level}-lh`、font-weight：`--qa-font-weight-*`）。
- [x] 定义间距 token（4px 基础单元及各级别）。
- [x] 定义圆角 token（xs 到 pill）。
- [x] 定义阴影/elevation token。

## 2. Tailwind v4 @theme 配置

- [x] 在 `apps/web/src/styles/tailwind-theme.css` 中使用 `@theme` 指令注册语义化颜色 utility（`--color-*`），并从 `--qa-*` 原始变量映射，避免 `--color-*` 自引用。
- [x] 注册字体 family utility（`--font-sans`、`--font-mono`）映射 `--qa-font-*`。
- [x] 注册字重 utility（`--font-weight-regular/medium/semibold/bold`）映射 `--qa-font-weight-*`。
- [x] 注册排版 scale utility（`--text-hero-display` 到 `--text-caption`），含 `--line-height` 伴随变量。
- [x] 注册间距 utility（`--spacing-xxs` 到 `--spacing-section`）映射 `--qa-spacing-*`。
- [x] 注册圆角 utility（`--radius-xs` 到 `--radius-pill`）映射 `--qa-radius-*`。
- [x] 注册阴影 utility（`--shadow-card`、`--shadow-elevated`）映射 `--qa-shadow-*`。

## 3. HeroUI 主题同步

- [x] 配置 HeroUIProvider 的 theme，设置 primary、danger、success 色值与 DESIGN.md 对齐。

## 4. 硬编码值迁移

- [x] 替换 `apps/web/src/styles/**` 布局样式中所有硬编码 hex 颜色为 CSS 变量。
- [x] 更新 MainLayout.tsx 中的 inline class 使用 Tailwind utility。

## 5. 字体栈更新

- [x] 更新 `:root` 的 font-family 为 Inter + JetBrains Mono 回退栈。
- [ ] 将 Inter variable font 文件添加到 `apps/web/public/fonts/inter/InterVariable.woff2` 和 `InterVariable-Italic.woff2`。
- [ ] 将 JetBrains Mono variable font 文件添加到 `apps/web/public/fonts/jetbrains-mono/JetBrainsMonoVariable.woff2` 和 `JetBrainsMonoVariable-Italic.woff2`。
- [ ] 在两个字体目录保留对应 `OFL.txt`，确认 Inter 与 JetBrains Mono 均为 SIL Open Font License 1.1 且以未修改字体文件分发。
- [ ] 在 `apps/web/index.html` 的 `<head>` 中 preload `/fonts/inter/InterVariable.woff2` 和 `/fonts/jetbrains-mono/JetBrainsMonoVariable.woff2`，使用 `rel="preload"`、`as="font"`、`type="font/woff2"`、`crossorigin`。
- [ ] 在 `apps/web/src/styles/**` 添加 Inter 与 JetBrains Mono 的 `@font-face`，使用 `font-display: swap`，不添加 FontFace API runtime loading。

## 6. Verification

- [x] 确认 `bun run build` 通过。
- [x] 确认修改 CSS 变量后全站颜色同步变化。
- [x] 确认 HeroUI 组件使用正确的主题色。
- [ ] 确认 `apps/web/index.html`、`apps/web/src/styles/**`、`apps/web/public/fonts/**` 与 `spec.md` 的字体加载要求一致。
