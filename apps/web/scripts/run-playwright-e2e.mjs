import { spawn } from 'node:child_process';
import path from 'node:path';
import process from 'node:process';

const host = '127.0.0.1';
const port = 5173;
const baseUrl = `http://${host}:${port}`;
const viteCommand = process.platform === 'win32' ? 'vite.cmd' : 'vite';
const playwrightCommand = process.platform === 'win32' ? 'playwright.cmd' : 'playwright';
const viteArgs = ['--host', host, '--port', String(port), '--strictPort'];
const playwrightArgs = ['test', '--project=chromium-e2e', ...process.argv.slice(2)];

let ownedServer = null;
let playwrightProcess = null;

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function isServerReady() {
  try {
    const response = await fetch(baseUrl, { redirect: 'manual' });
    return response.ok || response.status < 500;
  } catch {
    return false;
  }
}

async function waitForServer(timeoutMs) {
  const startedAt = Date.now();

  while (Date.now() - startedAt < timeoutMs) {
    if (await isServerReady()) {
      return;
    }

    if (ownedServer?.exitCode !== null && ownedServer?.exitCode !== undefined) {
      throw new Error(`Vite dev server exited early with code ${ownedServer.exitCode}.`);
    }

    await wait(250);
  }

  throw new Error(`Timed out after ${timeoutMs}ms waiting for ${baseUrl}.`);
}

function spawnViteServer() {
  return spawn(viteCommand, viteArgs, {
    cwd: process.cwd(),
    env: {
      ...process.env,
      PATH: [
        path.join(process.cwd(), 'node_modules', '.bin'),
        process.env.PATH ?? '',
      ].filter(Boolean).join(path.delimiter),
    },
    stdio: 'inherit',
    windowsHide: true,
  });
}

function spawnPlaywright() {
  return spawn(playwrightCommand, playwrightArgs, {
    cwd: process.cwd(),
    env: {
      ...process.env,
      PATH: [
        path.join(process.cwd(), 'node_modules', '.bin'),
        process.env.PATH ?? '',
      ].filter(Boolean).join(path.delimiter),
      PLAYWRIGHT_TEST_BASE_URL: baseUrl,
    },
    stdio: 'inherit',
    windowsHide: true,
  });
}

async function stopOwnedServer() {
  if (!ownedServer || ownedServer.exitCode !== null && ownedServer.exitCode !== undefined) {
    return;
  }

  ownedServer.kill('SIGTERM');
  await wait(1_000);

  if (ownedServer.exitCode === null || ownedServer.exitCode === undefined) {
    ownedServer.kill('SIGKILL');
  }

  if (ownedServer.exitCode !== null && ownedServer.exitCode !== undefined) {
    return;
  }

  await new Promise((resolve) => ownedServer.once('exit', resolve));
}

async function stopPlaywrightProcess() {
  if (!playwrightProcess || playwrightProcess.exitCode !== null && playwrightProcess.exitCode !== undefined) {
    return;
  }

  playwrightProcess.kill('SIGTERM');
  await wait(1_000);

  if (playwrightProcess.exitCode === null || playwrightProcess.exitCode === undefined) {
    playwrightProcess.kill('SIGKILL');
  }

  if (playwrightProcess.exitCode !== null && playwrightProcess.exitCode !== undefined) {
    return;
  }

  await new Promise((resolve) => playwrightProcess.once('exit', resolve));
}

async function main() {
  if (!(await isServerReady())) {
    ownedServer = spawnViteServer();
    await waitForServer(30_000);
  }

  playwrightProcess = spawnPlaywright();
  const exitCode = await new Promise((resolve, reject) => {
    playwrightProcess.once('error', reject);
    playwrightProcess.once('exit', (code, signal) => {
      if (signal) {
        resolve(1);
        return;
      }

      resolve(code ?? 1);
    });
  });

  await stopOwnedServer();
  process.exit(exitCode);
}

const shutdown = async () => {
  await stopPlaywrightProcess();
  await stopOwnedServer();
  process.exit(1);
};

process.on('SIGINT', () => {
  void shutdown();
});

process.on('SIGTERM', () => {
  void shutdown();
});

void main().catch(async (error) => {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
  await stopOwnedServer();
  process.exit(1);
});
