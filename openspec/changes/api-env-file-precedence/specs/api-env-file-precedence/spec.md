## ADDED Requirements

### Requirement: API dotenv files override repository dotenv files

QuantAgent API SHALL allow the repository root `.env` and `apps/api` dotenv files to define the same variable, and the `apps/api` dotenv value SHALL win at the file layer. Real process environment variables SHALL continue to override all dotenv files.

#### Scenario: API dotenv overrides duplicate root variable

- **WHEN** the repository root `.env` defines `DATABASE_URL=postgresql+psycopg://root:root@localhost:15432/rootdb`
- **AND** `apps/api/.env` defines `DATABASE_URL=postgresql+psycopg://api:api@localhost:15432/apidb`
- **AND** no real process environment variable named `DATABASE_URL` is set
- **THEN** `quantagent.api.config.settings.Settings` resolves `DATABASE_URL` from `apps/api/.env`

#### Scenario: Process environment overrides API dotenv

- **WHEN** the repository root `.env` and `apps/api/.env` both define `LOG_LEVEL`
- **AND** the real process environment defines `LOG_LEVEL=ERROR`
- **THEN** `quantagent.api.config.settings.Settings` resolves `LOG_LEVEL` to `ERROR`

### Requirement: API supports environment-specific dotenv files

QuantAgent API SHALL support environment-specific dotenv files under `apps/api` without loading unrelated environments. The selected `APP_ENV` SHALL control which `apps/api/.env.<APP_ENV>` and `apps/api/.env.<APP_ENV>.local` files are considered.

#### Scenario: Test environment dotenv is selected

- **WHEN** `APP_ENV=test` is selected by a real process environment variable or by the base dotenv layers
- **AND** `apps/api/.env` defines `AUTH_ENABLED=true`
- **AND** `apps/api/.env.test` defines `AUTH_ENABLED=false`
- **THEN** `quantagent.api.config.settings.Settings` uses the test-specific `AUTH_ENABLED=false` value
- **AND** dotenv files for unrelated environments such as `apps/api/.env.production` are not loaded

#### Scenario: Base local dotenv can select environment-specific dotenv

- **WHEN** no real process environment variable named `APP_ENV` is set
- **AND** `apps/api/.env.local` defines `APP_ENV=staging`
- **AND** `apps/api/.env.staging` defines `LOG_LEVEL=WARNING`
- **THEN** `quantagent.api.config.settings.Settings` considers `apps/api/.env.staging`
- **AND** resolves `LOG_LEVEL` to `WARNING`

#### Scenario: Local environment override wins within the selected environment

- **WHEN** `APP_ENV=staging` is selected
- **AND** `apps/api/.env.staging` defines `API_HOST=127.0.0.1`
- **AND** `apps/api/.env.staging.local` defines `API_HOST=0.0.0.0`
- **THEN** `quantagent.api.config.settings.Settings` resolves `API_HOST` to `0.0.0.0`

### Requirement: API dotenv templates preserve secret safety

QuantAgent API SHALL document a multi-environment dotenv template strategy while keeping real `.env` files and `.env.*` files out of source control unless they are explicit `.example` templates.

#### Scenario: Production template does not contain real secrets

- **WHEN** the repository provides an API production dotenv template
- **THEN** the template uses placeholder or empty values for `AUTH_ADMIN_PASSWORD`, `AUTH_SESSION_SECRET`, database credentials and external service credentials
- **AND** the documentation states that real production secrets MUST come from process environment variables, CI secrets, deployment secrets or a future Secret Manager

#### Scenario: Real environment files remain ignored

- **WHEN** a developer creates `apps/api/.env.local`, `apps/api/.env.test`, `apps/api/.env.staging`, `apps/api/.env.production` or `apps/api/.env.<APP_ENV>.local`
- **THEN** Git does not treat those files as normal source files
- **AND** `.example` templates needed for collaboration remain commit-eligible

### Requirement: Docker Compose configuration does not invert API dotenv priority

QuantAgent local Docker Compose configuration SHALL not cause root `.env` values to override `apps/api` dotenv values for API application settings.

#### Scenario: Compose config preserves API override intent

- **WHEN** root `.env` and `apps/api/.env` both define an API application setting such as `APP_ENV`, `DATABASE_URL`, `RUNTIME_DIR`, `LOG_LEVEL`, `AUTH_ENABLED` or `AUTH_SESSION_SECRET`
- **AND** the API is started through the repository Docker Compose entrypoint
- **THEN** the resulting API process configuration does not give the root `.env` value higher priority than the `apps/api` value solely because Compose expanded root `.env` into `environment:`
- **AND** `api.environment` does not hard-inject API application settings from root `.env` for `APP_ENV`, `DATABASE_URL`, `RUNTIME_DIR`, `LOG_LEVEL`, `AUTH_*` or `API_*`

#### Scenario: Compose still supports container-specific database URL

- **WHEN** the API is started through Docker Compose
- **THEN** the API can still receive a container-reachable `DATABASE_URL` such as a `db:5432` URL
- **AND** host-local API execution can still use a host-reachable `DATABASE_URL` such as a `localhost:15432` URL
