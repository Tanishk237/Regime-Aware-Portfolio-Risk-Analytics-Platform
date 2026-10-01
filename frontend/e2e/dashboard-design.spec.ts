import { expect, test } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import type { PortfolioIntelligence } from '../src/lib/types';

const fixturePath = path.resolve(
	path.dirname(fileURLToPath(import.meta.url)),
	'../../testing/sample_portfolio_trades.csv'
);

test('dashboard preserves backend figures and disclosure across themes and screen sizes', async ({
	page
}, testInfo) => {
	test.setTimeout(180_000);
	const pageErrors: string[] = [];
	page.on('pageerror', (error) => pageErrors.push(error.message));
	await page.goto('/login');
	await page.getByRole('button', { name: 'Continue as Guest' }).click();
	await expect(page).toHaveURL(/\/upload$/);
	await page.locator('input[type="file"]').setInputFiles(fixturePath);
	await page.getByRole('button', { name: 'Import 10 trades' }).click();
	await expect(page.getByRole('button', { name: 'Open dashboard' })).toBeVisible({
		timeout: 120_000
	});
	const responsePromise = page.waitForResponse(
		(response) =>
			/\/intelligence\/portfolio\/\d+$/.test(new URL(response.url()).pathname) && response.ok()
	);
	await page.getByRole('button', { name: 'Open dashboard' }).click();
	const data: PortfolioIntelligence = await (await responsePromise).json();
	await page.getByRole('button', { name: 'Explore dashboard' }).click();
	const currency = new Intl.NumberFormat('en-IN', {
		style: 'currency',
		currency: data.summary.base_currency ?? 'INR',
		minimumFractionDigits: 2,
		maximumFractionDigits: 2
	});
	expect(data.summary.current_value).toEqual(expect.any(Number));
	expect(data.summary.total_return).toEqual(expect.any(Number));
	await expect(page.getByTestId('holdings-value')).toHaveText(
		currency.format(data.summary.current_value!)
	);
	const returnValue = data.summary.total_return!;
	await expect(page.getByTestId('holdings-return')).toHaveText(
		`${returnValue > 0 ? '+' : ''}${(returnValue * 100).toFixed(2)}%`
	);
	const breakdown = page.getByRole('button', { name: 'Profit / loss breakdown', exact: true });
	await expect(breakdown).toHaveAttribute('aria-expanded', 'false');
	await expect(page.getByText('Unrealized profit / loss', { exact: true })).not.toBeVisible();
	await breakdown.focus();
	await page.keyboard.press('Enter');
	await expect(breakdown).toHaveAttribute('aria-expanded', 'true');
	for (const [label, value] of [
		['Unrealized profit / loss', data.summary.unrealized_pnl],
		['Realized profit / loss', data.summary.realized_pnl],
		['Total profit / loss', data.summary.total_pnl]
	] as const) {
		expect(value).toEqual(expect.any(Number));
		const row = page.getByText(label, { exact: true }).locator('..');
		await expect(row.locator('dd')).toHaveText(currency.format(value!));
	}
	await breakdown.press('Enter');
	for (const title of ['Current-holdings model return', 'Modeled drawdown']) {
		const chart = page.getByRole('region', { name: title });
		await expect(chart.locator('.recharts-area-curve')).toHaveAttribute('d', /^(?!.*NaN).+$/);
		await expect(chart.locator('.recharts-area-area')).toHaveAttribute('fill', /^url\(#/);
	}
	await expect(page.getByRole('link', { name: 'Review evidence', exact: true })).toHaveAttribute(
		'href',
		'/recommendations'
	);
	await expect(page.getByRole('link', { name: 'Explain this', exact: true })).toHaveAttribute(
		'href',
		/^\/ai-copilot\?prompt=/
	);
	const sector = page.getByRole('button', { name: /Technology/ });
	await sector.click();
	await expect(sector).toHaveAttribute('aria-pressed', 'true');
	await expect(page.getByRole('table').getByRole('columnheader')).toHaveText([
		'Holding',
		'Weight',
		'Market value'
	]);
	// Let Recharts finish its JS draw-on animation before visual capture.
	await page.waitForTimeout(1800);
	for (const theme of ['dark', 'light']) {
		if (theme === 'light') await page.getByRole('button', { name: 'Switch to light mode' }).click();
		for (const [width, height] of [
			[1440, 900],
			[1024, 768],
			[390, 844]
		]) {
			await page.setViewportSize({ width: width!, height: height! });
			await expect
				.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth))
				.toBe(true);
			await page.evaluate(() => window.scrollTo(0, 0));
			await expect(page.getByTestId('holdings-value')).toBeVisible();
			await page.screenshot({
				path: testInfo.outputPath(`dashboard-${theme}-${width}.png`),
				fullPage: true
			});
		}
	}

	await page.route(/\/intelligence\/portfolio\/\d+(\?.*)?$/, (route) =>
		route.fulfill({
			json: {
				...data,
				summary: { ...data.summary, current_value: null, total_return: null },
				risk: null,
				warnings: ['Price history is unavailable.'],
				recommendations: []
			}
		})
	);
	await page.reload();
	await expect(page.getByTestId('holdings-value')).toHaveText('—');
	await expect(page.getByTestId('holdings-return')).toHaveText('—');
	await expect(page.getByText('No modeled history', { exact: true })).toHaveCount(2);
	await expect(page.getByText('Price history is unavailable.', { exact: true })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Review available data' })).toHaveAttribute(
		'href',
		'/risk'
	);
	expect(pageErrors).toEqual([]);
});
