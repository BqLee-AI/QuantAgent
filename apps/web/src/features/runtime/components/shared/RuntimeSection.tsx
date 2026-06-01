import { Card } from "@heroui/react";
import type { ReactNode } from "react";

interface RuntimeSectionProps {
  children: ReactNode;
  description: string;
  title: string;
  action?: ReactNode;
}

export function RuntimeSection({ action, children, description, title }: RuntimeSectionProps) {
  return (
    <Card className="border border-hairline bg-canvas">
      <div className="border-b border-hairline px-5 py-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="grid gap-1">
            <h2 className="m-0 text-[15px] font-semibold text-ink">{title}</h2>
            <p className="m-0 text-xs leading-5 text-muted">{description}</p>
          </div>
          {action}
        </div>
      </div>
      <div className="p-5">{children}</div>
    </Card>
  );
}
