'use client';

import { RefreshCw } from 'lucide-react';
import Link from 'next/link';
import { useEffect } from 'react';

import { Button } from '@/components/ui/button';

export default function GlobalError({
	error,
	reset
}: {
	error: Error & { digest?: string };
	reset: () => void;
}) {
	useEffect(() => {
		console.error(error);
	}, [error]);

	return (
		<html lang="en">
			<body>
				<main className="bg-background text-foreground flex min-h-screen items-center justify-center px-4">
					<section className="max-w-md text-center">
						<div className="bg-primary text-primary-foreground mx-auto mb-4 flex size-10 items-center justify-center rounded-lg text-sm font-bold">
							R
						</div>
						<h1 className="text-xl font-semibold">Something went wrong</h1>
						<p className="text-muted-foreground mt-2 text-sm">
							The dashboard hit an unexpected error. Try again, or return to the dashboard.
						</p>
						<div className="mt-5 flex flex-wrap justify-center gap-2">
							<Button onClick={reset}>
								<RefreshCw className="size-4" /> Try again
							</Button>
							<Button asChild variant="outline">
								<Link href="/dashboard">Dashboard</Link>
							</Button>
						</div>
					</section>
				</main>
			</body>
		</html>
	);
}
