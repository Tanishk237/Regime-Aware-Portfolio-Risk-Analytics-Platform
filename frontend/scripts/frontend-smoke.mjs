import { existsSync } from 'node:fs';
import path from 'node:path';

const root = process.cwd();

const requiredPaths = [
	'package-lock.json',
	'next.config.ts',
	'.env.example',
	'src/app/error.tsx',
	'src/app/layout.tsx',
	'src/app/loading.tsx',
	'src/app/not-found.tsx',
	'src/app/(app)/dashboard/page.tsx',
	'src/app/(app)/portfolios/page.tsx',
	'src/app/(app)/portfolios/[id]/page.tsx',
	'src/app/(app)/trades/page.tsx',
	'src/app/(app)/upload/page.tsx',
	'src/app/(app)/market/page.tsx',
	'src/app/(app)/risk/page.tsx',
	'src/app/(app)/regime/page.tsx',
	'src/app/(app)/stress-tests/page.tsx',
	'src/app/(app)/portfolio-health/page.tsx',
	'src/app/(app)/recommendations/page.tsx',
	'src/app/(app)/ai-copilot/page.tsx',
	'src/app/(app)/settings/page.tsx',
	'src/components/charts/chart-card.tsx',
	'src/components/common/data-table.tsx',
	'src/components/domain/finance.tsx',
	'src/components/layout/app-sidebar.tsx',
	'src/components/layout/top-bar.tsx',
	'src/lib/api.ts',
	'src/lib/auth-events.ts',
	'src/lib/copilot.ts',
	'src/lib/api/auth.ts',
	'src/lib/api/adapters.ts',
	'src/lib/api/analytics.ts',
	'src/lib/api/market.ts',
	'src/lib/api/portfolio.ts',
	'src/lib/api/query-keys.ts',
	'src/lib/api/system.ts',
	'src/lib/queries.ts',
	'src/lib/storage.ts',
	'src/lib/types.ts'
];

const forbiddenPaths = [
	'vite.config.ts',
	'bun.lock',
	'bunfig.toml',
	'src/components/app-sidebar.tsx',
	'src/components/top-bar.tsx',
	'src/components/data-table.tsx',
	'src/router.tsx',
	'src/start.ts'
];

const missing = requiredPaths.filter((filePath) => !existsSync(path.join(root, filePath)));
const forbidden = forbiddenPaths.filter((filePath) => existsSync(path.join(root, filePath)));

if (missing.length || forbidden.length) {
	if (missing.length) console.error(`Missing required frontend files:\n${missing.join('\n')}`);
	if (forbidden.length)
		console.error(`Legacy frontend files still present:\n${forbidden.join('\n')}`);
	process.exit(1);
}

console.log('Frontend smoke check passed.');
