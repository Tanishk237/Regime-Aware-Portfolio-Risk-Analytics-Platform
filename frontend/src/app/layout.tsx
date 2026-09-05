import type { Metadata } from 'next';

import { RootProviders } from '@/components/layout/root-providers';

import '../styles.css';

export const metadata: Metadata = {
	title: {
		default: 'Latent',
		template: '%s · Latent'
	},
	description: 'Portfolio Regime Intelligence for Indian equity portfolios.',
	icons: {
		icon: [
			{ url: '/icon.png', type: 'image/png' },
			{ url: '/brand/latent-tile-dark.png', type: 'image/png' }
		],
		apple: [{ url: '/apple-icon.png', type: 'image/png' }],
		shortcut: ['/icon.png']
	},
	openGraph: {
		title: 'Latent',
		description: 'Portfolio Regime Intelligence for Indian equity portfolios.',
		images: [{ url: '/brand/latent-header-dark.png', width: 1400, height: 380 }],
		type: 'website'
	},
	twitter: {
		card: 'summary_large_image',
		title: 'Latent',
		description: 'Portfolio Regime Intelligence for Indian equity portfolios.',
		images: ['/brand/latent-header-dark.png']
	}
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
	return (
		<html lang="en" suppressHydrationWarning>
			<body>
				<RootProviders>{children}</RootProviders>
			</body>
		</html>
	);
}
