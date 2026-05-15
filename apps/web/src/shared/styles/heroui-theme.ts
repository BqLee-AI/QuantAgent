import type { CSSProperties } from 'react';

type HeroUIThemeVars = CSSProperties & Record<`--${string}`, string>;

export const heroUITheme: HeroUIThemeVars = {
  '--accent': '#3b82f6',
  '--accent-foreground': '#ffffff',
  '--focus': '#3b82f6',
  '--success': '#0ecb81',
  '--success-foreground': '#181a20',
  '--danger': '#f6465d',
  '--danger-foreground': '#ffffff',
};
