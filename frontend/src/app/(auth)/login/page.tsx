'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { AuthShell } from '@/components/auth/auth-shell';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { errorMessage } from '@/lib/api';
import { useAuth } from '@/lib/auth';

export default function LoginPage() {
	const router = useRouter();
	const { hydrated, signIn, user } = useAuth();
	const [email, setEmail] = useState('');
	const [password, setPassword] = useState('');
	const [error, setError] = useState<string | null>(null);
	const [submitting, setSubmitting] = useState(false);

	useEffect(() => {
		if (hydrated && user) router.replace('/dashboard');
	}, [hydrated, router, user]);

	const login = async () => {
		setError(null);
		setSubmitting(true);
		try {
			await signIn({ email, password });
			router.replace('/dashboard');
		} catch (err) {
			setError(errorMessage(err));
		} finally {
			setSubmitting(false);
		}
	};

	return (
		<AuthShell
			title="Welcome back"
			subtitle="Sign in to enter your Latent workspace."
			footer={
				<>
					New to the platform?{' '}
					<Link href="/signup" className="text-primary font-medium">
						Create account
					</Link>
				</>
			}
		>
			<form
				className="grid gap-4"
				onSubmit={(event) => {
					event.preventDefault();
					void login();
				}}
			>
				<div className="grid gap-1.5">
					<Label htmlFor="email">Email</Label>
					<Input
						id="email"
						type="email"
						value={email}
						autoComplete="email"
						required
						onChange={(event) => setEmail(event.target.value)}
					/>
				</div>
				<div className="grid gap-1.5">
					<Label htmlFor="password">Password</Label>
					<Input
						id="password"
						type="password"
						value={password}
						autoComplete="current-password"
						required
						onChange={(event) => setPassword(event.target.value)}
					/>
				</div>
				{error ? <p className="text-negative text-sm">{error}</p> : null}
				<Button type="submit" disabled={submitting}>
					{submitting ? 'Logging in...' : 'Login'}
				</Button>
			</form>
		</AuthShell>
	);
}
