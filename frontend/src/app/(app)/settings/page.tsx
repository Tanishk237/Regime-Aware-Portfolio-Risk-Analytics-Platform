'use client';

import { CircleCheck, CircleX, KeyRound, RefreshCw } from 'lucide-react';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';

import { SectionCard } from '@/components/charts/chart-card';
import { MetricCard } from '@/components/common/metric-card';
import { PageHeader } from '@/components/layout/top-bar';
import { Button } from '@/components/ui/button';
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
	DialogTrigger
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Slider } from '@/components/ui/slider';
import { Textarea } from '@/components/ui/textarea';
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue
} from '@/components/ui/select';
import { API_BASE_URL, errorMessage } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { formatDateTime } from '@/lib/format';
import { useSelectedPortfolio } from '@/lib/portfolio-context';
import { useHealth, useRiskProfile, useVersion } from '@/lib/queries';
import { clearRapraLocalStorage } from '@/lib/storage';

const COPILOT_KEY = 'latent.copilotApiKey';

export default function SettingsPage() {
	const { user, signOut, deleteAccount } = useAuth();
	const { portfolios, selected } = useSelectedPortfolio();
	const health = useHealth();
	const version = useVersion();
	const profile = useRiskProfile();
	const [hasKey, setHasKey] = useState(false);
	const [tolerance, setTolerance] = useState<'conservative' | 'moderate' | 'aggressive'>(
		'moderate'
	);
	const [horizon, setHorizon] = useState(60);
	const [drawdownLimit, setDrawdownLimit] = useState(0.2);
	const [liquidity, setLiquidity] = useState<'low' | 'medium' | 'high'>('medium');
	const [income, setIncome] = useState('');
	const [restrictions, setRestrictions] = useState('');
	const [deletePassword, setDeletePassword] = useState('');
	const [deleteConfirmation, setDeleteConfirmation] = useState('');
	const [deletingAccount, setDeletingAccount] = useState(false);

	useEffect(() => {
		setHasKey(Boolean(window.sessionStorage.getItem(COPILOT_KEY)));
	}, []);

	useEffect(() => {
		if (!profile.data) return;
		setTolerance(profile.data.tolerance);
		setHorizon(profile.data.horizon_months);
		setDrawdownLimit(profile.data.max_drawdown_tolerance);
		setLiquidity(profile.data.liquidity_needs);
		setIncome(profile.data.income_requirement ?? '');
		setRestrictions(profile.data.restrictions.join('\n'));
	}, [profile.data]);

	const saveProfile = async () => {
		try {
			await profile.update.mutateAsync({
				tolerance,
				horizon_months: horizon,
				max_drawdown_tolerance: drawdownLimit,
				liquidity_needs: liquidity,
				income_requirement: income.trim() || null,
				restrictions: restrictions
					.split('\n')
					.map((item) => item.trim())
					.filter(Boolean)
			});
			toast.success('Risk profile updated. Recommendations will use these preferences.');
		} catch (error) {
			toast.error(errorMessage(error));
		}
	};

	const online = health.isSuccess && !health.isError;

	const permanentlyDeleteAccount = async () => {
		if (deleteConfirmation !== 'DELETE') return;
		setDeletingAccount(true);
		try {
			await deleteAccount(deletePassword);
			toast.success('Your account and portfolio data were permanently deleted.');
		} catch (error) {
			toast.error(errorMessage(error));
		} finally {
			setDeletingAccount(false);
		}
	};

	return (
		<div className="space-y-4">
			<PageHeader
				title="Settings"
				description="Connection, account, and local storage controls for this workspace."
				actions={
					<Button
						size="sm"
						variant="outline"
						onClick={() => {
							void health.refetch();
							void version.refetch();
						}}
					>
						<RefreshCw className="size-3.5" /> Recheck
					</Button>
				}
			/>

			<div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
				<MetricCard
					label="Backend status"
					value={
						<span className="inline-flex items-center gap-1.5">
							{online ? (
								<CircleCheck className="text-positive size-4" />
							) : (
								<CircleX className="text-negative size-4" />
							)}
							{online ? 'Online' : 'Unreachable'}
						</span>
					}
					loading={health.isLoading}
					tone={online ? 'positive' : 'negative'}
				/>
				<MetricCard
					label="Database"
					value={String(health.data?.database ?? '-')}
					loading={health.isLoading}
				/>
				<MetricCard
					label="API version"
					value={String(version.data?.version ?? '-')}
					hint={version.data?.environment ? String(version.data.environment) : undefined}
					loading={version.isLoading}
				/>
				<MetricCard label="Portfolios" value={portfolios.length} hint={selected?.name} />
			</div>

			<SectionCard title="Backend connection">
				<div className="grid gap-1.5">
					<Label htmlFor="base-url" className="text-muted-foreground text-xs">
						API base URL
					</Label>
					<Input id="base-url" readOnly value={API_BASE_URL} className="num h-9" />
				</div>
				<p className="text-muted-foreground mt-2 text-xs">
					Last checked {formatDateTime(new Date().toISOString())}
				</p>
			</SectionCard>

			<SectionCard
				title="Personal risk profile"
				description="These preferences tune recommendation thresholds. They never change the underlying market or portfolio measurements."
			>
				<div className="grid gap-4 lg:grid-cols-2">
					<div className="grid gap-1.5">
						<Label>Risk tolerance</Label>
						<Select
							value={tolerance}
							onValueChange={(value) => setTolerance(value as typeof tolerance)}
						>
							<SelectTrigger>
								<SelectValue />
							</SelectTrigger>
							<SelectContent>
								<SelectItem value="conservative">Conservative</SelectItem>
								<SelectItem value="moderate">Moderate</SelectItem>
								<SelectItem value="aggressive">Aggressive</SelectItem>
							</SelectContent>
						</Select>
					</div>
					<div className="grid gap-1.5">
						<Label>Liquidity need</Label>
						<Select
							value={liquidity}
							onValueChange={(value) => setLiquidity(value as typeof liquidity)}
						>
							<SelectTrigger>
								<SelectValue />
							</SelectTrigger>
							<SelectContent>
								<SelectItem value="low">Low</SelectItem>
								<SelectItem value="medium">Medium</SelectItem>
								<SelectItem value="high">High</SelectItem>
							</SelectContent>
						</Select>
					</div>
					<div className="grid gap-1.5">
						<Label htmlFor="horizon">Investment horizon in months</Label>
						<Input
							id="horizon"
							type="number"
							min={1}
							max={600}
							value={horizon}
							onChange={(event) =>
								setHorizon(Math.max(1, Math.min(600, Number(event.target.value))))
							}
						/>
					</div>
					<div className="grid gap-2">
						<Label>Maximum drawdown tolerance: {(drawdownLimit * 100).toFixed(0)}%</Label>
						<Slider
							value={[drawdownLimit * 100]}
							min={1}
							max={90}
							step={1}
							onValueChange={([value]) => setDrawdownLimit((value ?? 20) / 100)}
						/>
					</div>
					<div className="grid gap-1.5">
						<Label htmlFor="income">Income objective</Label>
						<Input
							id="income"
							value={income}
							onChange={(event) => setIncome(event.target.value)}
							placeholder="Optional, for example quarterly income"
						/>
					</div>
					<div className="grid gap-1.5">
						<Label htmlFor="restrictions">Restrictions</Label>
						<Textarea
							id="restrictions"
							value={restrictions}
							onChange={(event) => setRestrictions(event.target.value)}
							placeholder={'One restriction per line\nNo tobacco exposure'}
						/>
					</div>
				</div>
				<Button
					className="mt-4"
					onClick={() => void saveProfile()}
					disabled={profile.isLoading || profile.update.isPending}
				>
					{profile.update.isPending ? <RefreshCw className="size-4 animate-spin" /> : null} Save
					risk profile
				</Button>
			</SectionCard>

			<SectionCard title="AI Copilot key">
				<div className="flex flex-wrap items-center justify-between gap-3">
					<span className="inline-flex items-center gap-2 text-sm">
						<KeyRound className="text-muted-foreground size-4" />
						{hasKey ? 'A key is saved on this device.' : 'No key saved yet.'}
					</span>
					<Button
						size="sm"
						variant="outline"
						disabled={!hasKey}
						onClick={() => {
							window.sessionStorage.removeItem(COPILOT_KEY);
							setHasKey(false);
							toast.success('Copilot key removed');
						}}
					>
						Remove key
					</Button>
				</div>
			</SectionCard>

			<SectionCard title="Account">
				<dl className="grid gap-3 text-sm sm:grid-cols-2">
					<div>
						<dt className="text-muted-foreground text-xs uppercase">Name</dt>
						<dd className="font-medium">{user?.name ?? '-'}</dd>
					</div>
					<div>
						<dt className="text-muted-foreground text-xs uppercase">Email</dt>
						<dd className="font-medium">{user?.email ?? '-'}</dd>
					</div>
				</dl>
				<Separator className="my-4" />
				<div className="flex flex-wrap gap-2">
					<Button size="sm" variant="outline" onClick={signOut}>
						Sign out
					</Button>
					<Button
						size="sm"
						variant="destructive"
						onClick={() => {
							clearRapraLocalStorage();
							void signOut();
							toast.success('Local app data cleared');
						}}
					>
						Clear local data
					</Button>
					{!user?.isGuest ? (
						<Dialog>
							<DialogTrigger asChild>
								<Button size="sm" variant="destructive">
									Delete account
								</Button>
							</DialogTrigger>
							<DialogContent>
								<DialogHeader>
									<DialogTitle>Permanently delete account</DialogTitle>
									<DialogDescription>
										This deletes every portfolio, trade, report, alert, and saved preference owned
										by this account. This action cannot be undone.
									</DialogDescription>
								</DialogHeader>
								<div className="grid gap-3">
									<div className="grid gap-1.5">
										<Label htmlFor="delete-password">Current password</Label>
										<Input
											id="delete-password"
											type="password"
											autoComplete="current-password"
											value={deletePassword}
											onChange={(event) => setDeletePassword(event.target.value)}
										/>
									</div>
									<div className="grid gap-1.5">
										<Label htmlFor="delete-confirmation">Type DELETE to confirm</Label>
										<Input
											id="delete-confirmation"
											value={deleteConfirmation}
											onChange={(event) => setDeleteConfirmation(event.target.value)}
										/>
									</div>
								</div>
								<DialogFooter>
									<Button
										variant="destructive"
										disabled={deletingAccount || !deletePassword || deleteConfirmation !== 'DELETE'}
										onClick={() => void permanentlyDeleteAccount()}
									>
										{deletingAccount ? <RefreshCw className="size-4 animate-spin" /> : null}
										Delete account and data
									</Button>
								</DialogFooter>
							</DialogContent>
						</Dialog>
					) : null}
				</div>
			</SectionCard>
		</div>
	);
}
