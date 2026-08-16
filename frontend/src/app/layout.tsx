import type { Metadata } from 'next';

import { RootProviders } from '@/components/layout/root-providers';

import '../styles.css';

export const metadata: Metadata = {
	title: {
		default: 'Regime Aware Portfolio Risk Analytics',
		template: '%s · Regime Aware Portfolio Risk Analytics'
	},
	description:
		'Portfolio risk, market regimes, and decision intelligence for Indian equity portfolios.',
	openGraph: {
		title: 'Regime Aware Portfolio Risk Analytics',
		description: 'Portfolio risk, market regimes, and decision intelligence.',
		type: 'website'
	},
	twitter: {
		card: 'summary_large_image'
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
