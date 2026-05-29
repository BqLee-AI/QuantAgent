import { providerPresets } from '../../provider-presets';

/**
 * Deterministic background color from provider name, inspired by Cherry Studio's
 * generateColorFromChar pattern. Uses a fixed palette for visual consistency.
 */
const AVATAR_PALETTE = [
  '#3b82f6', // blue
  '#0ecb81', // green
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // violet
  '#ec4899', // pink
  '#14b8a6', // teal
  '#f97316', // orange
  '#6366f1', // indigo
  '#06b6d4', // cyan
] as const;

function colorFromName(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return AVATAR_PALETTE[Math.abs(hash) % AVATAR_PALETTE.length];
}

function firstCharacter(name: string): string {
  const ch = name.trim().charAt(0);
  return ch.toUpperCase();
}

/**
 * Known provider emoji/symbol from preset definitions for visual identity.
 */
const PRESET_SYMBOLS: Record<string, string> = {
  openai: 'OA',
  anthropic: 'AN',
  deepseek: 'DS',
  qwen: 'QW',
  moonshot: 'MK',
  openrouter: 'OR',
  custom: 'C',
};

function getPresetSymbol(providerName: string): string | null {
  const match = providerPresets.find(
    (p) => p.draft.name.toLowerCase() === providerName.toLowerCase(),
  );
  if (match) return PRESET_SYMBOLS[match.id] ?? null;
  return null;
}

interface ProviderAvatarProps {
  name: string;
  size?: number;
}

export function ProviderAvatar({ name, size = 32 }: ProviderAvatarProps) {
  const bg = colorFromName(name);
  const symbol = getPresetSymbol(name) ?? firstCharacter(name);

  return (
    <span
      aria-hidden="true"
      className="inline-flex shrink-0 items-center justify-center rounded-full border border-[var(--qa-color-hairline)]"
      style={{
        width: size,
        height: size,
        backgroundColor: bg,
        color: '#fff',
        fontSize: size * 0.4,
        fontWeight: 700,
        lineHeight: 1,
      }}
    >
      {symbol}
    </span>
  );
}
