import type { ReactNode } from 'react';
import { Card, Chip } from '@heroui/react';
import { cn } from '@/shared/ui/cn';

type SemanticTone = 'info' | 'risk-increase' | 'risk-reduce' | 'approval-expiring';

const BADGE_TONE_CLASS: Record<SemanticTone, string> = {
  info: 'qa-badge-info',
  'risk-increase': 'qa-badge-risk-increase',
  'risk-reduce': 'qa-badge-risk-reduce',
  'approval-expiring': 'qa-badge-approval-expiring',
};

const HEROUI_TONE_MAP: Record<SemanticTone, 'accent' | 'danger' | 'success' | 'warning'> = {
  info: 'accent',
  'risk-increase': 'danger',
  'risk-reduce': 'success',
  'approval-expiring': 'warning',
};

const METRIC_TONE_CLASS: Record<SemanticTone, string> = {
  info: 'text-primary',
  'risk-increase': 'text-risk-increase',
  'risk-reduce': 'text-risk-reduce',
  'approval-expiring': 'text-approval-expiring',
};

type PageHeroStat = {
  label: string;
  tone?: SemanticTone;
  value: string;
};

type PageHeroProps = {
  actions?: ReactNode;
  description: string;
  eyebrow?: string;
  stats?: PageHeroStat[];
  title: string;
};

type SectionCardProps = {
  children: ReactNode;
  className?: string;
  description?: string;
  footer?: ReactNode;
  title: string;
};

export function EventBadge({ children, tone }: { children: ReactNode; tone: SemanticTone }) {
  return (
    <Chip
      color={HEROUI_TONE_MAP[tone]}
      variant="soft"
      className={cn('qa-event-badge', BADGE_TONE_CLASS[tone])}
    >
      {children}
    </Chip>
  );
}

export function MetricCard({
  label,
  tone = 'info',
  value,
}: {
  label: string;
  tone?: SemanticTone;
  value: string;
}) {
  return (
    <div className="qa-metric-card">
      <div className="qa-metric-label">{label}</div>
      <div className={cn('qa-metric-value', METRIC_TONE_CLASS[tone])}>{value}</div>
    </div>
  );
}

export function PageHero({ actions, description, eyebrow, stats, title }: PageHeroProps) {
  return (
    <section className="qa-page-hero">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-3xl space-y-3">
          {eyebrow ? <p className="qa-list-kicker">{eyebrow}</p> : null}
          <h1 className="text-display-sm font-semibold text-ink md:text-[2.5rem]">{title}</h1>
          <p className="max-w-2xl text-body-md text-muted-strong">{description}</p>
        </div>
        {actions ? (
          <div className="flex w-full flex-col gap-3 sm:w-auto sm:flex-row">{actions}</div>
        ) : null}
      </div>

      {stats?.length ? (
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {stats.map((stat) => (
            <MetricCard key={stat.label} label={stat.label} tone={stat.tone} value={stat.value} />
          ))}
        </div>
      ) : null}
    </section>
  );
}

export function SectionCard({ children, className, description, footer, title }: SectionCardProps) {
  return (
    <Card variant="default" className={cn('qa-panel', className)}>
      <Card.Header className="flex flex-col gap-2 border-b border-hairline-light px-6 py-5">
        <Card.Title className="text-title-md font-semibold text-ink">{title}</Card.Title>
        {description ? (
          <Card.Description className="text-body-md text-muted">{description}</Card.Description>
        ) : null}
      </Card.Header>
      <Card.Content className="px-6 py-5">{children}</Card.Content>
      {footer ? (
        <Card.Footer className="border-t border-hairline-light px-6 py-4">{footer}</Card.Footer>
      ) : null}
    </Card>
  );
}
