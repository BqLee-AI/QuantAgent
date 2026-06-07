import { useQuery } from '@tanstack/react-query';

import { useApis } from '@/app/runtime';
import type { PluginRecordResponse } from '@/features/plugins';

import type { EventIndustryFilterOption } from '../utils/event-filter-options';
import { eventKeys } from './events.keys';

export function useEventIndustryOptionsQuery() {
  const { plugins } = useApis();

  return useQuery({
    // 中文注释：行业筛选来自 Registry 里的 industry 插件；页面不硬编码半导体子主题。
    queryFn: async () => buildIndustryFilterOptions(await plugins.listPlugins()),
    queryKey: eventKeys.industryOptions(),
  });
}

function buildIndustryFilterOptions(
  plugins: PluginRecordResponse[],
): EventIndustryFilterOption[] {
  return plugins
    .filter((plugin) => plugin.manifest?.type === 'industry')
    .filter((plugin) => !plugin.id.endsWith('.example'))
    .map((plugin) => ({
      label: industryLabel(plugin.manifest?.name ?? plugin.id),
      value: industryIdFromPluginId(plugin.id),
    }))
    .filter((option, index, options) => options.findIndex((item) => item.value === option.value) === index);
}

function industryIdFromPluginId(pluginId: string): string {
  const segments = pluginId.split('.');
  return segments[segments.length - 1] || pluginId;
}

function industryLabel(name: string): string {
  if (/semiconductor/i.test(name)) return '半导体';
  return name.replace(/\s+Industry Package$/i, '');
}
