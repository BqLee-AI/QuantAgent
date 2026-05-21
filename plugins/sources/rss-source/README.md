# RSS Source

Official pull source plugin for RSS and Atom feeds.

## Boundary

- Produces `RawEventDraft` records from public feed items.
- Does not start its own polling loop.
- Does not perform industry routing, analysis, notification, or execution.
- Does not store secrets or private feed lists in the plugin package.

Runtime scheduling, retry, rate limit, dedupe, persistence, and audit are handled by QuantAgent core services.

## Config

See `config.schema.json`. Feed URLs belong in a SourceBinding effective config, not in this plugin package.

