import type { CSSProperties } from 'react';

type HeroUIThemeVars = CSSProperties & Record<`--${string}`, string>;

export const heroUITheme: HeroUIThemeVars = {
  '--accent': 'var(--qa-color-primary)',
  '--accent-foreground': 'var(--qa-color-on-primary)',
  '--focus': 'var(--qa-color-primary)',
  '--success': 'var(--qa-color-trading-up)',
  '--success-foreground': 'var(--qa-color-ink)',
  '--danger': 'var(--qa-color-trading-down)',
  '--danger-foreground': 'var(--qa-color-on-primary)',
};
