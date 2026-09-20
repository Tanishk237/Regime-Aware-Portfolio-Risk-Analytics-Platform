import Link from 'next/link';
import type { ReactNode } from 'react';

import { LatentBrand } from '@/components/brand/latent-brand';
import { Button } from '@/components/ui/button';

export function LegalPage({ title, children }: { title: string; children: ReactNode }) {
	return (
		<main className="bg-background text-foreground min-h-screen">
			<header className="border-border border-b">
				<div className="mx-auto flex max-w-4xl items-center justify-between px-5 py-4">
					<LatentBrand size="sm" />
					<Button asChild variant="outline" size="sm">
						<Link href="/login">Back to Latent</Link>
					</Button>
				</div>
			</header>
			<article className="mx-auto max-w-4xl px-5 py-10 sm:py-14">
				<h1 className="text-3xl font-medium sm:text-4xl">{title}</h1>
				<p className="text-muted-foreground mt-2 text-sm">Effective 18 September 2026</p>
				<div className="legal-copy mt-8 space-y-7 text-sm leading-7 sm:text-base">{children}</div>
			</article>
		</main>
	);
}

export function LegalSection({ title, children }: { title: string; children: ReactNode }) {
	return (
		<section className="space-y-2">
			<h2 className="text-xl font-medium">{title}</h2>
			<div className="text-muted-foreground space-y-2">{children}</div>
		</section>
	);
}
