import type { ReactNode } from "react";

export function DetailSectionCard({
  children,
  title,
}: {
  children: ReactNode;
  title: string;
}) {
  return (
    <section className="rounded-2xl border border-hairline bg-surface px-4 py-4">
      <div className="border-b border-hairline pb-3">
        <h2 className="m-0 text-title-sm font-bold text-ink">{title}</h2>
      </div>
      <div className="pt-4">{children}</div>
    </section>
  );
}
