import { Loader2 } from 'lucide-react';

export default function LoadingPage() {
	return (
		<main className="bg-background text-foreground flex min-h-screen items-center justify-center">
			<Loader2 className="text-muted-foreground size-5 animate-spin" />
		</main>
	);
}
