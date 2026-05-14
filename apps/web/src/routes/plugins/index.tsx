import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/plugins/')({
  component: PluginsPage,
})

function PluginsPage() {
  return (
    <>
      <section className="page-header">
        <p className="page-kicker">Plugins</p>
        <h1 className="page-title">Plugin Management</h1>
        <p className="page-description">
          Plugin inventory for source, industry, strategy, notification, and executor integrations.
        </p>
      </section>

      <section className="placeholder-grid" aria-label="Plugins overview">
        <PlaceholderPanel title="Installed" copy="Registered plugins with type, version, and health status." />
        <PlaceholderPanel title="Configuration" copy="Schema-driven settings, secrets, validation, and audit trail." />
        <PlaceholderPanel title="Operations" copy="Enable, disable, reload, and inspect dependency failures." />
      </section>
    </>
  )
}

function PlaceholderPanel({ title, copy }: { title: string; copy: string }) {
  return (
    <article className="placeholder-panel">
      <h2 className="placeholder-panel-title">{title}</h2>
      <p className="placeholder-panel-copy">{copy}</p>
    </article>
  )
}
