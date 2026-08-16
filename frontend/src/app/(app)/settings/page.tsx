'use client';

import { CircleCheck, CircleX, KeyRound, RefreshCw } from 'lucide-react';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';

import { SectionCard } from '@/components/charts/chart-card';
import { MetricCard } from '@/components/common/metric-card';
import { PageHeader } from '@/components/layout/top-bar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { API_BASE_URL } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { formatDateTime } from '@/lib/format';
import { useSelectedPortfolio } from '@/lib/portfolio-context';
import { useHealth, useVersion } from '@/lib/queries';
import { clearRapraLocalStorage } from '@/lib/storage';

const COPILOT_KEY = 'rapra.copilotApiKey';

export default function SettingsPage() {
	const { user, signOut } = useAuth();
	const { portfolios, selected } = useSelectedPortfolio();
	const health = useHealth();
	const version = useVersion();
	const [hasKey, setHasKey] = useState(false);

	useEffect(() => {
		setHasKey(Boolean(window.localStorage.getItem(COPILOT_KEY)));
	}, []);

	const online = health.isSuccess && !health.isError;

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
							window.localStorage.removeItem(COPILOT_KEY);
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
				</div>
			</SectionCard>
		</div>
	);
}
