import path from 'node:path';

import type { NextConfig } from 'next';

const isProduction = process.env.NODE_ENV === 'production';
const latentApiOrigin = (() => {
	const configured = process.env['LATENT_API_ORIGIN']?.trim();
	if (!configured) return '';
	try {
		const url = new URL(configured);
		if (isProduction && url.protocol !== 'https:') {
			throw new Error('LATENT_API_ORIGIN must use HTTPS in production.');
		}
		return url.origin;
	} catch (error) {
		throw new Error(
			`LATENT_API_ORIGIN must be an absolute backend origin: ${error instanceof Error ? error.message : 'invalid URL'}`
		);
	}
})();
const apiOrigin = (() => {
	try {
		return new URL(process.env['NEXT_PUBLIC_API_BASE_URL'] ?? 'http://localhost:8000/api/v1')
			.origin;
	} catch {
		return '';
	}
})();

const securityHeaders = [
	{ key: 'X-Content-Type-Options', value: 'nosniff' },
	{ key: 'X-Frame-Options', value: 'DENY' },
	{ key: 'Referrer-Policy', value: 'no-referrer' },
	{ key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
	...(isProduction
		? [
				{
					key: 'Strict-Transport-Security',
					value: 'max-age=31536000; includeSubDomains'
				},
				{
					key: 'Content-Security-Policy',
					value: [
						"default-src 'self'",
						"script-src 'self' 'unsafe-inline'",
						"style-src 'self' 'unsafe-inline'",
						"img-src 'self' data: blob:",
						"font-src 'self' data:",
						`connect-src 'self' ${apiOrigin}`.trim(),
						"frame-ancestors 'none'",
						"base-uri 'self'",
						"form-action 'self'"
					].join('; ')
				}
			]
		: [])
];

const nextConfig: NextConfig = {
	reactStrictMode: true,
	poweredByHeader: false,
	output: 'standalone',
	distDir: process.env['NEXT_DIST_DIR'] ?? '.next',
	outputFileTracingRoot: path.join(__dirname),
	async rewrites() {
		if (!latentApiOrigin) return [];
		return [
			{
				source: '/api/v1/:path*',
				destination: `${latentApiOrigin}/api/v1/:path*`
			}
		];
	},
	async headers() {
		return [{ source: '/:path*', headers: securityHeaders }];
	}
};

export default nextConfig;
