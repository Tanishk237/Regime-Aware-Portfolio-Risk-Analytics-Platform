'use client';

import { Eye, EyeOff } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { AuthFooterLink, AuthShell } from '@/components/auth/auth-shell';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { errorMessage } from '@/lib/api';
import { useAuth } from '@/lib/auth';

export default function LoginPage() {
	const router = useRouter();
	const { hydrated, signIn, user } = useAuth();
	const [email, setEmail] = useState('');
	const [password, setPassword] = useState('');
	const [showPassword, setShowPassword] = useState(false);
	const [rememberMe, setRememberMe] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [submitting, setSubmitting] = useState(false);

	useEffect(() => {
		if (hydrated && user) router.replace('/dashboard');
	}, [hydrated, router, user]);

	const login = async () => {
		setError(null);
		setSubmitting(true);
		try {
			await signIn({ email, password, rememberMe });
			router.replace('/dashboard');
		} catch (err) {
			setError(errorMessage(err));
		} finally {
			setSubmitting(false);
		}
	};

	return (
		<AuthShell
			title="Welcome to Latent"
			subtitle="Sign in or continue as a guest to explore your regime workspace."
			footer={
				<AuthFooterLink label="New to Latent?" href="/signup">
					Create account
				</AuthFooterLink>
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
					<Label htmlFor="email" className="text-sm font-medium text-white">
						Email
					</Label>
					<Input
						id="email"
						type="email"
						placeholder="you@example.com"
						value={email}
						autoComplete="email"
						required
						className="h-10 border-white/10 bg-[#111827] text-white shadow-none transition-colors duration-200 ease-in-out placeholder:text-slate-500 focus-visible:border-[#0EA5E9] focus-visible:ring-[#0EA5E9]/40"
						onChange={(event) => setEmail(event.target.value)}
					/>
				</div>
				<div className="grid gap-1.5">
					<Label htmlFor="password" className="text-sm font-medium text-white">
						Password
					</Label>
					<div className="relative">
						<Input
							id="password"
							type={showPassword ? 'text' : 'password'}
							value={password}
							autoComplete="current-password"
							required
							className="h-10 border-white/10 bg-[#111827] pr-11 text-white shadow-none transition-colors duration-200 ease-in-out placeholder:text-slate-500 focus-visible:border-[#0EA5E9] focus-visible:ring-[#0EA5E9]/40"
							onChange={(event) => setPassword(event.target.value)}
						/>
						<Button
							type="button"
							variant="ghost"
							size="icon"
							aria-label={showPassword ? 'Hide password' : 'Show password'}
							className="text-muted-foreground absolute right-1 top-1/2 size-8 -translate-y-1/2 shadow-none transition-colors duration-200 ease-in-out hover:bg-white/[0.04] hover:text-white"
							onClick={() => setShowPassword((current) => !current)}
						>
							{showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
						</Button>
					</div>
				</div>
				<Label
					htmlFor="remember-login"
					className="text-muted-foreground flex cursor-pointer items-start gap-2 text-sm font-normal leading-5"
				>
					<Checkbox
						id="remember-login"
						checked={rememberMe}
						onCheckedChange={(checked) => setRememberMe(checked === true)}
						aria-label="Remember this login"
						className="mt-0.5"
					/>
					<span>
						Remember me on this device
						<span className="block text-xs">
							Leave unchecked to require this login screen again after the tab session ends.
						</span>
					</span>
				</Label>
				{error ? <p className="text-negative text-sm">{error}</p> : null}
				<Button
					type="submit"
					disabled={submitting}
					className="h-10 bg-gradient-to-r from-[#0EA5E9] to-[#6366F1] font-medium text-white shadow-none transition-all duration-200 ease-in-out hover:border-[#0EA5E9]/40 hover:shadow-[0_0_20px_rgba(14,165,233,0.2)]"
				>
					{submitting ? 'Logging in...' : 'Login'}
				</Button>
			</form>
		</AuthShell>
	);
}
