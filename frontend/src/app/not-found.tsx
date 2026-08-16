import Link from 'next/link';

import { Button } from '@/components/ui/button';

export default function NotFoundPage() {
	return (
		<main className="bg-background text-foreground flex min-h-screen items-center justify-center px-4">
			<section className="max-w-md text-center">
				<div className="bg-primary text-primary-foreground mx-auto mb-4 flex size-10 items-center justify-center rounded-lg text-sm font-bold">
					R
				</div>
				<p className="text-muted-foreground text-sm font-medium">404</p>
				<h1 className="mt-1 text-xl font-semibold">Page not found</h1>
				<p className="text-muted-foreground mt-2 text-sm">
					The page you opened does not exist or has moved.
				</p>
				<div className="mt-5 flex justify-center">
					<Button asChild>
						<Link href="/dashboard">Go to dashboard</Link>
					</Button>
				</div>
			</section>
		</main>
	);
}
