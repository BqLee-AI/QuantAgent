import { Button, Chip, Input, ListBox, Select, TextField } from '@heroui/react';
import { Link } from '@tanstack/react-router';
import type { ReactNode } from 'react';

import {
  getImpactTone,
  getPriorityTone,
  getReliabilityTone,
  scoreNeutralTone,
} from '@/features/events/utils/event-score-tones';
import { InfoTag, LinkButton, PageHeader, PageSectionCard, SectionHeader } from '@/shared/ui';

import { useEventListPage } from '../../hooks';
import type { EventFilterGroup, EventFilterOption, EventListItem } from '../../types';
import { buildEventFilterGroups, buildEventSortOptions, eventDecisionTone, formatEventDate, formatEventDecision } from '../../utils';
import type { EventIndustryFilterOption } from '../../utils/event-filter-options';

export function EventListPage() {
  const page = useEventListPage();
  const items = page.eventsQuery.data?.items ?? [];

  return (
    <div className="grid gap-5">
      <PageHeader
        kicker="事件中心"
        title="AI 已筛选新闻事件"
        description="这里只展示 Router Agent 处理后的新闻，默认按系统最新路由时间排序；未处理、未消费或模型失败的 RawEvent 请到运行态页面排查。"
      />

      <EventFilterBar
        groups={buildEventFilterGroups(page.filters.filters, page.industryOptions)}
        industryOptions={page.industryOptions}
        keyword={page.filters.filters.keyword}
        onFilterChange={(groupKey, value) => {
          if (groupKey === 'time') page.filters.setTime(value as typeof page.filters.filters.time);
          if (groupKey === 'industry') page.filters.setIndustry(value as typeof page.filters.filters.industry);
          if (groupKey === 'decision') page.filters.setDecision(value === 'default' ? '' : value as typeof page.filters.filters.decision);
        }}
        onKeywordChange={page.filters.setKeyword}
        onSortChange={(value) => page.filters.setSort(value as typeof page.filters.filters.sort)}
        sortOptions={buildEventSortOptions(page.filters.filters.sort)}
      />

      <PageSectionCard>
        <SectionHeader eyebrow="已路由事件" title={`${items.length} 条新闻`} />
        {page.eventsQuery.isLoading ? <EventStatePanel message="正在读取事件列表..." /> : null}
        {page.eventsQuery.isError ? (
          <EventStatePanel
            tone="danger"
            message={page.eventsQuery.error instanceof Error ? page.eventsQuery.error.message : '事件列表读取失败'}
            action={<Button size="sm" variant="outline" onPress={() => void page.eventsQuery.refetch()}>重试</Button>}
          />
        ) : null}
        {!page.eventsQuery.isLoading && !page.eventsQuery.isError && items.length === 0 ? (
          <EventStatePanel message="当前筛选下没有已路由事件。若 RSS 已抓到但这里没有，请到 /runtime 查看 worker、模型或 Kafka 状态。" />
        ) : null}
        <div className="grid gap-3">
          {items.map((item) => (
            <EventListCard key={item.routed_event_id} item={item} />
          ))}
        </div>
      </PageSectionCard>
    </div>
  );
}

function EventFilterBar({
  groups,
  industryOptions,
  keyword,
  onFilterChange,
  onKeywordChange,
  onSortChange,
  sortOptions,
}: {
  groups: readonly EventFilterGroup[];
  industryOptions: readonly EventIndustryFilterOption[];
  keyword: string;
  onFilterChange: (groupKey: string, value: string) => void;
  onKeywordChange: (keyword: string) => void;
  onSortChange: (value: string) => void;
  sortOptions: readonly EventFilterOption[];
}) {
  const emptyIndustryOptions = industryOptions.length === 0;

  return (
    <section className="rounded-3xl border border-hairline bg-surface/95 p-3 shadow-soft">
      <div className="grid gap-3">
        <TextField aria-label="事件关键词" value={keyword} onChange={onKeywordChange}>
          <Input className="w-full rounded-2xl border-hairline bg-canvas" placeholder="标题 / 摘要 / URL / trace" variant="secondary" />
        </TextField>
        <div className="flex flex-col gap-2 lg:flex-row lg:items-center">
          <div className="grid flex-1 gap-2 sm:grid-cols-2 xl:grid-cols-4">
            {groups.map((group) => (
              <FilterPicker
                key={group.key}
                group={group}
                onSelect={(value) => onFilterChange(group.key, value)}
              />
            ))}
          </div>
          <div className="lg:w-[220px]">
            <OptionPicker
              ariaLabel="选择事件排序方式"
              label="排序"
              onSelect={onSortChange}
              options={sortOptions}
            />
          </div>
        </div>
        {emptyIndustryOptions ? (
          <p className="m-0 text-[12px] font-semibold text-muted">
            未从插件列表读取到可筛选行业包，当前仅提供全部行业筛选。
          </p>
        ) : null}
      </div>
    </section>
  );
}

function FilterPicker({
  group,
  onSelect,
}: {
  group: EventFilterGroup;
  onSelect: (value: string) => void;
}) {
  return (
    <OptionPicker
      ariaLabel={`选择${group.label}`}
      label={group.label}
      onSelect={onSelect}
      options={group.options}
    />
  );
}

function OptionPicker({
  ariaLabel,
  label,
  onSelect,
  options,
}: {
  ariaLabel: string;
  label: string;
  onSelect: (value: string) => void;
  options: readonly EventFilterOption[];
}) {
  const selectedOption = options.find((option) => option.active) ?? options[0];

  return (
    <Select
      aria-label={ariaLabel}
      selectedKey={selectedOption?.value ?? null}
      onSelectionChange={(key) => {
        const nextValue = key === null ? selectedOption?.value : String(key);

        if (nextValue) {
          onSelect(nextValue);
        }
      }}
    >
      <Select.Trigger className="h-auto min-h-14 w-full rounded-2xl border-hairline bg-canvas px-3 py-2 shadow-none">
        <Select.Value>
          <div className="grid min-w-0 gap-0.5 text-left">
            <span className="text-[11px] font-bold text-muted">{label}</span>
            <span className="truncate text-[13px] font-bold text-foreground">
              {selectedOption?.label ?? '请选择'}
            </span>
          </div>
        </Select.Value>
        <Select.Indicator />
      </Select.Trigger>
      <Select.Popover>
        <ListBox aria-label={ariaLabel} className="max-h-80 overflow-y-auto">
          {options.map((option) => (
            <ListBox.Item key={option.value} id={option.value} textValue={option.label}>
              <div className="py-1 text-[13px] font-bold text-foreground">{option.label}</div>
            </ListBox.Item>
          ))}
        </ListBox>
      </Select.Popover>
    </Select>
  );
}

function EventListCard({ item }: { item: EventListItem }) {
  const card = toEventCardDisplay(item);
  const priorityTone = getPriorityTone(card.priorityBand, card.priorityScore);
  const reliabilityTone = getReliabilityTone(card.reliabilityScore);
  const impactTone = card.impactScore === null ? scoreNeutralTone : getImpactTone(card.impactScore);

  return (
    <article className="group overflow-hidden rounded-3xl border border-hairline bg-surface shadow-[0_10px_28px_rgba(15,23,42,0.04)] transition hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-[0_18px_42px_rgba(15,23,42,0.08)]">
      <div className="grid gap-4 p-4 xl:grid-cols-[minmax(0,1fr)_238px] xl:items-start">
        <Link
          className="grid gap-3 rounded-2xl outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
          params={{ eventId: item.raw_event_id }}
          to="/events/$eventId"
        >
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-canvas px-3 py-1 text-[12px] font-extrabold text-muted">
              {card.rankLabel}
            </span>
            <InfoTag>{card.analysisState}</InfoTag>
            <InfoTag>{card.timeLabel}</InfoTag>
            <span className={`rounded-full px-3 py-1 text-body-sm font-bold ${eventDecisionTone(item.decision)}`}>
              {formatEventDecision(item.decision)}
            </span>
            <span className={`rounded-full px-3 py-1 text-body-sm font-bold ${card.impactTagClass}`}>
              {card.impactLabel}
            </span>
          </div>

          <div className="grid gap-2">
            <h3 className="m-0 text-title-sm font-extrabold leading-tight text-foreground group-hover:text-primary">
              {item.title ?? item.url ?? item.raw_event_id}
            </h3>
            <p className="m-0 line-clamp-2 text-body-sm leading-[1.55] text-muted">
              {item.summary ?? 'Router Agent 没有返回摘要。'}
            </p>
            <div className="flex flex-wrap gap-2">
              {card.topicTags.map((tag) => (
                <Chip key={tag} className="bg-surface-soft text-body-sm font-bold text-muted-strong" size="sm" variant="soft">
                  {tag}
                </Chip>
              ))}
            </div>
          </div>
        </Link>

        <div className="grid gap-3 rounded-2xl bg-canvas p-3">
          <div className="grid grid-cols-3 gap-2">
            <ScorePill label="优先级" toneClass={priorityTone.scoreClass} value={card.priorityScore} />
            <ScorePill label="可信度" toneClass={reliabilityTone.scoreClass} value={card.reliabilityScore} />
            <ScorePill label="影响" toneClass={impactTone.scoreClass} value={card.impactScore ?? '待'} />
          </div>
          <div className="rounded-2xl bg-surface px-3 py-2 text-[12px] font-extrabold text-muted-strong">
            {card.verificationLabel}
          </div>
          <div className="flex flex-wrap gap-2 xl:justify-end">
            <LinkButton to="/events/$eventId" params={{ eventId: item.raw_event_id }}>
              查看分析
            </LinkButton>
            <LinkButton to="/events/$eventId/audit" params={{ eventId: item.raw_event_id }} variant="outline">
              审计
            </LinkButton>
          </div>
        </div>
      </div>
    </article>
  );
}

function ScorePill({
  label,
  toneClass = scoreNeutralTone.scoreClass,
  value,
}: {
  label: string;
  toneClass?: string;
  value: number | string;
}) {
  return (
    <div className={`rounded-2xl px-3 py-2 text-center ${toneClass}`}>
      <p className="m-0 text-[11px] font-extrabold opacity-75">{label}</p>
      <p className="m-0 mt-0.5 text-[22px] font-extrabold leading-none">{value}</p>
    </div>
  );
}

function toEventCardDisplay(item: EventListItem) {
  const confidence = toPercent(item.quality.confidence ?? item.router_stage_summary.key_fields.confidence);
  const relevanceScore = parseRelevanceScore(item.relationship_summary);
  const priorityScore = priorityToScore(item.priority);
  const topicTags = [...item.target_industries, ...item.target_topics, ...item.tags].filter(Boolean).slice(0, 6);

  return {
    analysisState: analysisStateLabel(item),
    impactLabel: '影响待行业分析',
    impactScore: null,
    impactTagClass: scoreNeutralTone.tagClass,
    priorityBand: priorityToBand(item.priority),
    priorityScore,
    rankLabel: decisionRankLabel(item),
    reliabilityScore: confidence ?? relevanceScore ?? 60,
    timeLabel: `${formatEventDate(item.published_at)} · ${item.source_name ?? item.source_plugin_id ?? '未知来源'}`,
    topicTags: topicTags.length > 0 ? topicTags : ['Router Agent 已处理'],
    verificationLabel: verificationLabel(item, confidence, relevanceScore),
  };
}

function analysisStateLabel(item: EventListItem): string {
  if (item.decision === 'discard') return 'Router 已丢弃';
  if (item.decision === 'review') return 'Router 需复核';
  return 'Router 已路由';
}

function decisionRankLabel(item: EventListItem): string {
  if (item.priority === 'urgent') return '#S';
  if (item.priority === 'high') return '#A';
  if (item.decision === 'review') return '#R';
  return '#B';
}

function verificationLabel(item: EventListItem, confidence: number | null, relevanceScore: number | null): string {
  const confidenceLabel = confidence === null ? '可信度未给出' : `可信度 ${confidence}`;
  const relevanceLabel = relevanceScore === null ? '相关性未给出' : `相关性 ${relevanceScore}`;
  const nextStage = item.decision === 'route' ? '影响评分待行业 MainAgent' : '暂不进入影响评分';
  return `${confidenceLabel} · ${relevanceLabel} · ${nextStage}`;
}

function priorityToBand(priority: string | null): 'A' | 'B' | 'C' | 'S' {
  if (priority === 'urgent') return 'S';
  if (priority === 'high') return 'A';
  if (priority === 'normal') return 'B';
  return 'C';
}

function priorityToScore(priority: string | null): number {
  if (priority === 'urgent') return 95;
  if (priority === 'high') return 85;
  if (priority === 'normal') return 70;
  return 55;
}

function toPercent(value: unknown): number | null {
  if (typeof value !== 'number' || Number.isNaN(value)) return null;
  return Math.round(value <= 1 ? value * 100 : value);
}

function parseRelevanceScore(value: string | null): number | null {
  if (!value) return null;
  const match = value.match(/(?:^|\/\s*)(0(?:\.\d+)?|1(?:\.0+)?|[1-9]\d?)(?:\s*$)/);
  if (!match) return null;
  const numeric = Number(match[1]);
  if (Number.isNaN(numeric)) return null;
  return Math.round(numeric <= 1 ? numeric * 100 : numeric);
}

function EventStatePanel({
  action,
  message,
  tone = 'neutral',
}: {
  action?: ReactNode;
  message: string;
  tone?: 'danger' | 'neutral';
}) {
  return (
    <div className={tone === 'danger' ? 'mb-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-700' : 'mb-3 rounded-xl border border-hairline bg-canvas p-4 text-muted'}>
      <p className="m-0 text-body-sm">{message}</p>
      {action ? <div className="mt-3">{action}</div> : null}
    </div>
  );
}
