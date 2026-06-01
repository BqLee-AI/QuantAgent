export function formatRelativeMinutes(publishedMinutesAgo: number) {
  return publishedMinutesAgo >= 60
    ? `${Math.floor(publishedMinutesAgo / 60)} 小时前`
    : `${publishedMinutesAgo} 分钟前`
}
