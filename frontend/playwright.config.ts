import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const frontendDir = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(frontendDir, '..');
const e2eDatabaseUrl = `sqlite:////tmp/latent-playwright-${process.pid}.db`;
const backendPython = process.env['LATENT_PYTHON'] ?? `${rootDir}/venv/bin/python`;

export default defineConfig({
	testDir: './e2e',
	fullyParallel: false,
	workers: 1,
	preserveOutput: 'always',
	retries: process.env['CI'] ? 2 : 0,
	reporter: process.env['CI'] ? 'github' : 'list',
	expect: { timeout: 15_000 },
	use: {
		baseURL: 'http://127.0.0.1:3010',
		navigationTimeout: 60_000,
		trace: 'retain-on-failure',
		screenshot: 'only-on-failure',
		video: 'retain-on-failure'
	},
	projects: [
		{
			name: 'chromium',
			use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } }
		}
	],
	webServer: [
		{
			command: `${backendPython} -m uvicorn src.api.main:app --host 127.0.0.1 --port 8010`,
			cwd: rootDir,
			url: 'http://127.0.0.1:8010/api/v1/health',
			reuseExistingServer: !process.env['CI'],
			timeout: 120_000,
			env: {
				...process.env,
				ENVIRONMENT: 'test',
				DATABASE_URL: e2eDatabaseUrl,
				RUN_MIGRATIONS_ON_STARTUP: 'true',
				CREATE_DB_ON_STARTUP: 'false',
				AUTH_SECRET_KEY: 'playwright-only-secret-key-not-for-production',
				AUTH_COOKIE_SECURE: 'false',
				CORS_ORIGINS: 'http://127.0.0.1:3010',
				LOG_LEVEL: 'WARNING',
				MARKET_DATA_PROVIDER_RETRIES: '1',
				MARKET_DATA_PROVIDER_RETRY_BACKOFF_SECONDS: '0',
				MARKET_DATA_PROVIDER: 'test-fixture',
				NVIDIA_API_KEY: '',
				SENTRY_DSN: ''
			}
		},
		{
			command: 'npm run dev -- --hostname 127.0.0.1 --port 3010',
			cwd: frontendDir,
			url: 'http://127.0.0.1:3010/login',
			reuseExistingServer: !process.env['CI'],
			timeout: 120_000,
			env: {
				...process.env,
				NEXT_DIST_DIR: '.next-e2e',
				NEXT_PUBLIC_API_BASE_URL: 'http://127.0.0.1:8010/api/v1',
				NEXT_PUBLIC_SITE_URL: 'http://127.0.0.1:3010'
			}
		}
	]
});
