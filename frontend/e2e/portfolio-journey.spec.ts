import { expect, test, type Locator, type Page, type TestInfo } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const fixturePath = path.resolve(
	path.dirname(fileURLToPath(import.meta.url)),
	'../../testing/sample_portfolio_trades.csv'
);

async function capture(page: Page, testInfo: TestInfo, name: string) {
	const screenshotPath = testInfo.outputPath(`${name}.png`);
	await page.screenshot({ path: screenshotPath });
	await testInfo.attach(name, { path: screenshotPath, contentType: 'image/png' });
}

async function expectMetricPopulated(page: Page, label: string) {
	const testId = `metric-${label
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/(^-|-$)/g, '')}`;
	const value = page.getByTestId(testId).locator('[data-slot="metric-value"]');
	await expect(value).toBeVisible();
	await expect(value).not.toHaveText(/^\s*(?:-|—|Unknown)?\s*$/);
	return value;
}

async function expectInsideViewport(page: Page, locator: Locator) {
	const box = await locator.boundingBox();
	const viewport = page.viewportSize();
	expect(box).not.toBeNull();
	expect(viewport).not.toBeNull();
	if (!box || !viewport) return;

	expect(box.x).toBeGreaterThanOrEqual(0);
	expect(box.y).toBeGreaterThanOrEqual(0);
	expect(box.x + box.width).toBeLessThanOrEqual(viewport.width);
	expect(box.y + box.height).toBeLessThanOrEqual(viewport.height);
}

async function expectNoHorizontalOverflow(page: Page) {
	const hasOverflow = await page.evaluate(
		() => document.documentElement.scrollWidth > window.innerWidth
	);
	expect(hasOverflow).toBe(false);
}

test('protected routes return unauthenticated visitors to login', async ({ page }) => {
	await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
	await expect(page).toHaveURL(/\/login$/);
	await expect(
		page.getByRole('heading', { name: 'See the hidden state behind your portfolio.' })
	).toBeVisible();
});

test('guest can automatically resolve safe CSV formatting issues', async ({ page }) => {
	await page.goto('/login', { waitUntil: 'domcontentloaded' });
	const guestButton = page.getByRole('button', { name: 'Continue as Guest' });
	await expect(guestButton).toBeEnabled();
	await guestButton.click();
	await expect(page).toHaveURL(/\/upload$/, { timeout: 30_000 });

	await page.locator('input[type="file"]').setInputFiles({
		name: 'repairable-portfolio.csv',
		mimeType: 'text/csv',
		buffer: Buffer.from(
			'Symbol,Side,Qty,Trade Date,Execution Price,Currency\n' +
				'" nse:reliance ",purchase,"1,000",18/08/2026,"₹2,450.50", inr\n'
		)
	});

	await expect(page.getByText('Needs attention')).toBeVisible();
	await page.getByRole('button', { name: 'Resolve issues' }).click();
	await expect(page.getByText('Automatic repair complete')).toBeVisible();
	await expect(page.getByText('Required columns verified')).toBeVisible();
	await expect(page.getByRole('button', { name: 'Import 1 trades' })).toBeEnabled();
});

test('guest uploads the repository sample and reaches an explained dashboard', async ({
	page
}, testInfo) => {
	test.setTimeout(240_000);
	let fullIntelligenceRequests = 0;
	page.on('request', (request) => {
		const url = new URL(request.url());
		if (
			request.method() === 'GET' &&
			/^\/api\/v1\/intelligence\/portfolio\/\d+$/.test(url.pathname)
		) {
			fullIntelligenceRequests += 1;
		}
	});
	await page.goto('/login', { waitUntil: 'domcontentloaded' });
	await expect(page.locator('html')).toHaveClass(/dark/);

	const guestButton = page.getByRole('button', { name: 'Continue as Guest' });
	await expect(guestButton).toBeEnabled();
	await guestButton.click();
	await expect(page).toHaveURL(/\/upload$/, { timeout: 30_000 });
	await expect(page.getByRole('heading', { name: 'Import portfolio' })).toBeVisible();

	await page.locator('input[type="file"]').setInputFiles(fixturePath);
	await expect(
		page.getByRole('button', { name: /Selected CSV: sample_portfolio_trades\.csv/ })
	).toBeVisible();
	await expect(page.getByText(/10 trade rows/)).toBeVisible();
	await expect(page.getByText('Required columns verified')).toBeVisible();

	await page.getByRole('button', { name: 'Import 10 trades' }).click();
	await expect(page.getByText('Portfolio created successfully')).toBeVisible({ timeout: 120_000 });
	await expect(page.getByText(/10 trades · 7 positions/)).toBeVisible();
	await page.getByRole('button', { name: 'Open dashboard' }).click();

	await expect(page).toHaveURL(/\/dashboard$/, { timeout: 30_000 });
	await expect(
		page.getByRole('heading', { name: 'Read your portfolio in three layers' })
	).toBeVisible();
	await page.getByRole('button', { name: 'Explore dashboard' }).click();
	await expect(
		page.getByRole('heading', { name: 'Read your portfolio in three layers' })
	).not.toBeVisible();
	await expect(page.getByText('Portfolio value', { exact: true })).toBeVisible();
	await expect(page.getByText('Current regime', { exact: true })).toBeVisible();
	await expect(page.getByText('Continue your analysis')).toBeVisible();
	await expect(page.getByText('Sector allocation', { exact: true })).toBeVisible();
	const technologySector = page.getByRole('button', { name: /Technology/ });
	await expect(technologySector).toBeVisible();
	await technologySector.click();
	await expect(technologySector).toHaveAttribute('aria-pressed', 'true');
	await expect(page.getByText('Period return', { exact: true })).toBeVisible();
	await expect(page.getByText('Worst drawdown', { exact: true })).toBeVisible();
	const cumulativePath = page.locator('.recharts-line-curve').first();
	await expect(cumulativePath).toBeVisible();
	await expect(cumulativePath).toHaveAttribute('d', /^(?!.*NaN).+$/);
	const drawdownPath = page.locator('.recharts-area-curve').first();
	await expect(drawdownPath).toBeVisible();
	await expect(drawdownPath).toHaveAttribute('d', /^(?!.*NaN).+$/);
	await page.mouse.move(1380, 40);
	await capture(page, testInfo, 'dashboard-sector-desktop');
	await expectMetricPopulated(page, 'Max drawdown');
	await expect(page.getByText('Detecting...')).not.toBeVisible();
	expect(fullIntelligenceRequests).toBe(1);
	await expect(page.getByRole('button', { name: /Portfolio alerts, \d+ unread/ })).toBeVisible();
	await page
		.getByTestId('metric-max-drawdown')
		.getByRole('button', { name: 'Explain this metric' })
		.click();
	await expect(page.getByText(/Current value:/)).toBeVisible();
	await page.keyboard.press('Escape');
	await capture(page, testInfo, 'dashboard-desktop');

	await page.getByRole('link', { name: 'Inspect risk' }).click();
	await expect(page.getByRole('heading', { name: 'Risk Analytics' })).toBeVisible();
	await expectMetricPopulated(page, 'Period return');
	await expectMetricPopulated(page, 'Volatility');
	await page.getByRole('link', { name: 'Regime Analytics' }).click();
	await expect(page.getByRole('heading', { name: 'Regime Analytics' })).toBeVisible();
	await expectMetricPopulated(page, 'Current regime');
	const historyCount = await expectMetricPopulated(page, 'History rows');
	expect(Number(await historyCount.textContent())).toBeGreaterThan(0);
	await expect(page.getByText('Why this regime')).toBeVisible();
	await expect(
		page.getByText(/not forecast accuracy or a probability of a future market outcome/i)
	).toBeVisible();

	await page.getByRole('link', { name: 'Stress Tests' }).click();
	await expect(page.getByRole('heading', { name: 'Stress Tests' })).toBeVisible();
	await page.getByRole('button', { name: 'Interpret' }).click();
	await expect(page.getByText('Review interpreted assumptions')).toBeVisible();
	await page.getByLabel('I reviewed these assumptions and want to run this scenario.').check();
	await page.getByRole('button', { name: 'Run scenario' }).click();
	await expectMetricPopulated(page, 'Value after');
	await expect(page.getByText('Method and assumptions')).toBeVisible();

	await page.getByRole('link', { name: 'Portfolio Health' }).click();
	await expect(page.getByRole('heading', { name: 'Portfolio Health' })).toBeVisible();
	await expect(await expectMetricPopulated(page, 'Health score')).toHaveText(/\d+\/100/);

	await page.getByRole('link', { name: 'Recommendations' }).first().click();
	await expect(page.getByRole('heading', { name: 'Recommendations' })).toBeVisible();
	await expectMetricPopulated(page, 'Total actions');
	await expect(page.getByText('Evidence', { exact: true }).first()).toBeVisible();
	await expect(page.getByText('Action', { exact: true }).first()).toBeVisible();

	await page.getByRole('link', { name: 'AI Copilot' }).click();
	await expect(page.getByRole('heading', { name: 'AI Copilot' })).toBeVisible();
	await expect(page.getByText('How to read state fit probability')).toBeVisible();
	await page.getByRole('button', { name: 'Explain my portfolio risk in plain English.' }).click();
	await expect(page.getByRole('heading', { name: 'Portfolio Snapshot' })).toBeVisible();
	await expect(page.getByRole('heading', { name: 'Regime model limitation' })).toBeVisible();
	await expect(page.getByText(/backend facts cited/)).toBeVisible();
	await page.getByRole('tab', { name: 'Reports' }).click();
	await page.getByRole('button', { name: 'Generate' }).click();
	await expect(page.getByRole('heading', { name: 'Daily Report' })).toBeVisible();
	await expect(page.getByText(/local fallback$/).first()).toBeVisible();

	await page.goto('/settings', { waitUntil: 'domcontentloaded' });
	await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();
	await page.getByLabel('Investment horizon in months').fill('36');
	await page.getByLabel('Income objective').fill('Quarterly income');
	await page.getByLabel('Restrictions').fill('No leveraged products');
	await page.getByRole('button', { name: 'Save risk profile' }).click();
	await expect(page.getByText(/Risk profile updated/)).toBeVisible();

	await page.setViewportSize({ width: 390, height: 844 });
	await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
	await expect(page.getByText('Portfolio value', { exact: true })).toBeVisible();
	await expectNoHorizontalOverflow(page);
	await capture(page, testInfo, 'dashboard-mobile');
	await page.getByRole('button', { name: 'Switch to light mode' }).click();
	await expect(page.locator('html')).not.toHaveClass(/dark/);
	await page.waitForTimeout(250);
	await capture(page, testInfo, 'dashboard-mobile-light');

	const responsiveRoutes = [
		{ path: '/portfolios', heading: 'Portfolios' },
		{ path: '/trades', heading: 'Trades' },
		{ path: '/upload', heading: 'Import portfolio' },
		{ path: '/market', heading: 'Market Data' },
		{ path: '/risk', heading: 'Risk Analytics' },
		{ path: '/regime', heading: 'Regime Analytics' },
		{ path: '/stress-tests', heading: 'Stress Tests' },
		{ path: '/portfolio-health', heading: 'Portfolio Health' },
		{ path: '/recommendations', heading: 'Recommendations' },
		{ path: '/ai-copilot', heading: 'AI Copilot' },
		{ path: '/settings', heading: 'Settings' }
	];
	for (const route of responsiveRoutes) {
		await page.goto(route.path, { waitUntil: 'domcontentloaded' });
		await expect(page.getByRole('heading', { name: route.heading })).toBeVisible();
		await expectNoHorizontalOverflow(page);
	}
});

test('authentication remains usable on mobile and in both themes', async ({ page }, testInfo) => {
	await page.setViewportSize({ width: 390, height: 844 });
	await page.goto('/login', { waitUntil: 'domcontentloaded' });

	const guestButton = page.getByRole('button', { name: 'Continue as Guest' });
	const emailInput = page.getByPlaceholder('you@example.com');
	const loginButton = page.getByRole('button', { name: 'Login' });
	await expect(guestButton).toBeVisible();
	await expect(emailInput).toBeVisible();
	await expect(loginButton).toBeVisible();
	await expect(guestButton).toBeEnabled();
	await expect(emailInput).toBeEnabled();
	await expect(loginButton).toBeEnabled();
	await expectInsideViewport(page, guestButton);
	await expectInsideViewport(page, loginButton);
	await emailInput.focus();
	await expect(emailInput).toBeFocused();
	await capture(page, testInfo, 'login-mobile-dark');

	await page.getByRole('button', { name: 'Switch to light mode' }).click();
	await expect(page.locator('html')).not.toHaveClass(/dark/);
	await page.waitForTimeout(250);
	await capture(page, testInfo, 'login-mobile-light');
	await page.getByRole('button', { name: 'Switch to dark mode' }).click();
	await expect(page.locator('html')).toHaveClass(/dark/);

	await expectNoHorizontalOverflow(page);
});
