export function requireProviderId(providerId: number | null): number {
  if (providerId === null) {
    // 中文注释：这里必须在本地截断，避免把空选中态误拼成 /providers/null 请求。
    throw new Error('请先选择一个 Provider 再执行该操作。');
  }

  return providerId;
}
