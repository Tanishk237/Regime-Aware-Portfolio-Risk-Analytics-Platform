'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { errorMessage } from '@/lib/api';
import { useAuth } from '@/lib/auth';

export default function SignupPage() {
	const router = useRouter();
	const { hydrated, signUp, user } = useAuth();
	const [name, setName] = useState('');
	const [email, setEmail] = useState('');
	const [password, setPassword] = useState('');
	const [confirmPassword, setConfirmPassword] = useState('');
	const [error, setError] = useState<string | null>(null);
	const [submitting, setSubmitting] = useState(false);

	useEffect(() => {
		if (hydrated && user) router.replace('/dashboard');
	}, [hydrated, router, user]);

	const createAccount = async () => {
		setError(null);
		if (password !== confirmPassword) {
			setError('Passwords do not match.');
			return;
		}
		setSubmitting(true);
		try {
			await signUp({ name, email, password });
			router.replace('/dashboard');
		} catch (err) {
			setError(errorMessage(err));
		} finally {
			setSubmitting(false);
		}
	};

	return (
		<main className="bg-surface flex min-h-screen items-center justify-center px-4">
			<Card className="w-full max-w-md p-6">
				<h1 className="text-xl font-semibold">Create Account</h1>
				<p className="text-muted-foreground mt-1 text-sm">
					Create a backend account for your portfolios and analytics.
				</p>
				<form
					className="mt-6 grid gap-4"
					onSubmit={(event) => {
						event.preventDefault();
						void createAccount();
					}}
				>
					<div className="grid gap-1.5">
						<Label htmlFor="name">Full name</Label>
						<Input id="name" value={name} onChange={(event) => setName(event.target.value)} />
					</div>
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
							autoComplete="new-password"
							minLength={8}
							required
							onChange={(event) => setPassword(event.target.value)}
						/>
					</div>
					<div className="grid gap-1.5">
						<Label htmlFor="confirm">Confirm password</Label>
						<Input
							id="confirm"
							type="password"
							value={confirmPassword}
							autoComplete="new-password"
							minLength={8}
							required
							onChange={(event) => setConfirmPassword(event.target.value)}
						/>
					</div>
					{error ? <p className="text-negative text-sm">{error}</p> : null}
					<Button type="submit" disabled={submitting}>
						{submitting ? 'Creating account...' : 'Create Account'}
					</Button>
				</form>
				<p className="text-muted-foreground mt-4 text-center text-xs">
					Already have an account?{' '}
					<Link href="/login" className="text-primary font-medium">
						Log in
					</Link>
				</p>
			</Card>
		</main>
	);
}
