export function formatRelativeMinutes(publishedMinutesAgo: number) {
  return publishedMinutesAgo >= 60
    ? `${Math.floor(publishedMinutesAgo / 60)} 小时前`
    : `${publishedMinutesAgo} 分钟前`
}

export function maskToken(token: string) {
  if (token.length <= 8) {
    return '***'
  }

  return `${token.slice(0, 4)}…${token.slice(-4)}`
}
