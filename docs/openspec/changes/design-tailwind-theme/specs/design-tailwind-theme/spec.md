# Design Tailwind Theme Specification

## ADDED Requirements

### Requirement: CSS Variable Token Layer

styles.css SHALL 定义 `--qa-*` 原始 CSS 变量覆盖 DESIGN.md 的所有设计 token，包括色彩、排版、间距、圆角和阴影。

#### Scenario: Color tokens defined

- **WHEN** 开发者检查 styles.css
- **THEN** 存在 `--qa-color-*` 原始变量覆盖 DESIGN.md Colors 部分的所有色值
- **AND** 变量命名与 DESIGN.md 的 token 名称语义对应

#### Scenario: Typography tokens defined

- **WHEN** 开发者检查 `apps/web/src/styles/tokens.css`
- **THEN** 存在 `--qa-font-*` 原始变量定义字体栈（Inter + JetBrains Mono）
- **AND** 存在 `--qa-text-*` 原始变量定义 DESIGN.md 各排版层级的 font-size（hero-display、display-lg/md/sm、title-lg/md/sm、body-md/sm、caption）
- **AND** 每层级有对应的 `--qa-text-{level}-lh` 定义 line-height
- **AND** 存在 `--qa-font-weight-*` 原始变量定义字重（regular/medium/semibold/bold）

### Requirement: Tailwind Theme Integration

Tailwind v4 的 @theme 指令 SHALL 注册语义化 utility class，并从 `--qa-*` 原始变量映射到 Tailwind 主题变量。注册范围包括：`--color-*`、`--font-*`（family）、`--font-weight-*`、`--text-*`（size+line-height）、`--spacing-*`、`--radius-*`、`--shadow-*`。

#### Scenario: Semantic color utilities available

- **WHEN** 开发者编写 `text-ink` 或 `bg-primary`
- **THEN** 生成的 CSS 引用对应的 Tailwind 主题 CSS 变量
- **AND** `@theme` 中不存在 `--color-* : var(--color-*)` 或 `--font-* : var(--font-*)` 形式的自引用映射
- **AND** 渲染结果与 DESIGN.md 定义的色值一致
- **AND** `text-ink` 引用的 CSS 变量计算值等于 DESIGN.md 的 `{colors.ink}`（#181a20）
- **AND** `bg-primary` 引用的 CSS 变量计算值等于 DESIGN.md 的 `{colors.primary}`（#3b82f6）

#### Scenario: Typography scale utilities available

- **WHEN** 开发者编写 `text-title-lg` 或 `text-body-md`
- **THEN** 对应的 font-size 与 DESIGN.md typography 层级一致
- **AND** 自动附带该层级的 line-height（通过 `--text-{name}--line-height`）

#### Scenario: Shadow utilities available

- **WHEN** 开发者编写 `shadow-card` 或 `shadow-elevated`
- **THEN** 对应的 box-shadow 与 DESIGN.md elevation token 一致

#### Scenario: Spacing and radius utilities

- **WHEN** 开发者使用 `p-section`、`rounded-card` 等语义 class
- **THEN** 对应的值与 DESIGN.md spacing/rounded token 一致

### Requirement: HeroUI Theme Sync

HeroUI 主题 SHALL 与 DESIGN.md 的色彩语义对齐。

#### Scenario: HeroUI primary color

- **WHEN** 使用 HeroUI 的 Button 或 Input 组件
- **THEN** primary variant 使用 DESIGN.md 的 QuantAgent Blue (#3b82f6)
- **AND** danger variant 使用 trading-down (#f6465d)
- **AND** success variant 使用 trading-up (#0ecb81)

### Requirement: Hardcoded Value Migration

styles.css 和 MainLayout 中的硬编码颜色值 SHALL 替换为 CSS 变量或 Tailwind utility class。

#### Scenario: No hardcoded hex values in components

- **WHEN** 开发者检查 MainLayout.tsx 和 styles.css 的布局样式
- **THEN** 不存在直接的 hex 颜色值（如 `#17202a`）
- **AND** 所有颜色引用 CSS 变量或 Tailwind utility

### Requirement: Font Stack Update

字体栈 SHALL 使用 Inter（BinanceNova 替代）和 JetBrains Mono（BinancePlex 替代），参照 DESIGN.md 的 Note on Font Substitutes。

#### Scenario: Correct font stack

- **WHEN** 应用加载
- **THEN** body 文本使用 Inter 字体栈
- **AND** 数字/价格文本可通过 `.font-mono` 使用 JetBrains Mono

#### Scenario: Font assets hosted locally

- **WHEN** 开发者检查字体资产
- **THEN** Inter variable font 文件存在于 `apps/web/public/fonts/inter/InterVariable.woff2`
- **AND** Inter italic variable font 文件存在于 `apps/web/public/fonts/inter/InterVariable-Italic.woff2`
- **AND** JetBrains Mono variable font 文件存在于 `apps/web/public/fonts/jetbrains-mono/JetBrainsMonoVariable.woff2`
- **AND** JetBrains Mono italic variable font 文件存在于 `apps/web/public/fonts/jetbrains-mono/JetBrainsMonoVariable-Italic.woff2`
- **AND** 对应目录保留 `OFL.txt`

#### Scenario: Font loading wired through HTML and CSS

- **WHEN** 开发者检查 `apps/web/index.html`
- **THEN** `<head>` 预加载 `/fonts/inter/InterVariable.woff2`
- **AND** `<head>` 预加载 `/fonts/jetbrains-mono/JetBrainsMonoVariable.woff2`
- **AND** 两个 preload link 均使用 `rel="preload"`、`as="font"`、`type="font/woff2"` 和 `crossorigin`
- **WHEN** 开发者检查 `apps/web/src/styles.css`
- **THEN** 存在 `@font-face` 注册 `Inter` 和 `JetBrains Mono`
- **AND** 每个 `@font-face` 使用 `font-display: swap`
- **AND** 不引入 FontFace API runtime loading，除非后续明确需要按路由延迟加载字体

#### Scenario: Font licensing is compatible

- **WHEN** 开发者检查字体来源记录
- **THEN** Inter 标记为 SIL Open Font License 1.1
- **AND** JetBrains Mono 标记为 SIL Open Font License 1.1
- **AND** 字体以未修改文件分发，不使用保留字体名发布修改版

### Requirement: Build Verification

所有改动后 `bun run build` SHALL 通过。

#### Scenario: Build passes

- **WHEN** 运行 `bun run build`
- **THEN** tsc 和 vite build 均成功，无错误
