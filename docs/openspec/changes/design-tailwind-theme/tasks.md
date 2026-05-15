# Tasks: Design Tailwind Theme

## 1. CSS Variable Token Layer

- [x] 在 styles.css 中定义 `:root` CSS 变量，覆盖 DESIGN.md 的色彩 token（brand、surface、hairline、text、trading、info）。
- [x] 定义排版 token（font-family、font-size、font-weight、line-height）。
- [x] 定义间距 token（4px 基础单元及各级别）。
- [x] 定义圆角 token（xs 到 pill）。
- [x] 定义阴影/elevation token。

## 2. Tailwind v4 @theme 配置

- [x] 在 styles.css 中使用 `@theme` 指令注册语义化颜色 utility（`--color-*`）。
- [x] 注册排版 utility（`--font-*`、`--text-*`）。
- [x] 注册间距 utility（`--spacing-*`）。
- [x] 注册圆角 utility（`--radius-*`）。

## 3. HeroUI 主题同步

- [x] 配置 HeroUIProvider 的 theme，设置 primary、danger、success 色值与 DESIGN.md 对齐。

## 4. 硬编码值迁移

- [x] 替换 styles.css 布局样式中所有硬编码 hex 颜色为 CSS 变量。
- [x] 更新 MainLayout.tsx 中的 inline class 使用 Tailwind utility。

## 5. 字体栈更新

- [x] 更新 `:root` 的 font-family 为 Inter + JetBrains Mono 回退栈。

## 6. Verification

- [x] 确认 `bun run build` 通过。
- [x] 确认修改 CSS 变量后全站颜色同步变化。
- [x] 确认 HeroUI 组件使用正确的主题色。
