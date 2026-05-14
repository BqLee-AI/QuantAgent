import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/settings/')({
  component: SettingsPage,
})

function SettingsPage() {
  return (
    <>
      <section className="page-header">
        <p className="page-kicker">Settings</p>
        <h1 className="page-title">Settings</h1>
        <p className="page-description">
          Local authentication, notification channels, secret references, authorization policy, and realtime status.
        </p>
      </section>

      <section className="placeholder-grid" aria-label="Settings overview">
        <PlaceholderPanel title="Access" copy="Session configuration and capability visibility." />
        <PlaceholderPanel title="Notifications" copy="Channel setup and delivery health for operator alerts." />
        <PlaceholderPanel title="Secrets" copy="Secret references and policy-controlled management entry points." />
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
