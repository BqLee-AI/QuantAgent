export function PlaceholderPanel({ title, copy }: { title: string; copy: string }) {
  return (
    <article className="placeholder-panel">
      <h2 className="placeholder-panel-title">{title}</h2>
      <p className="placeholder-panel-copy">{copy}</p>
    </article>
  )
}
