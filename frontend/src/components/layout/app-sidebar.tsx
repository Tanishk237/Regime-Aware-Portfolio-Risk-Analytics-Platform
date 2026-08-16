'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
	Activity,
	BarChart3,
	Bot,
	Briefcase,
	FlaskConical,
	HeartPulse,
	LayoutDashboard,
	LineChart,
	Lightbulb,
	Settings,
	ShieldAlert,
	Upload
} from 'lucide-react';

import {
	Sidebar,
	SidebarContent,
	SidebarGroup,
	SidebarGroupContent,
	SidebarGroupLabel,
	SidebarHeader,
	SidebarMenu,
	SidebarMenuButton,
	SidebarMenuItem,
	useSidebar
} from '@/components/ui/sidebar';

const NAV = [
	{
		label: 'Overview',
		items: [
			{ title: 'Dashboard', url: '/dashboard', icon: LayoutDashboard },
			{ title: 'Portfolios', url: '/portfolios', icon: Briefcase }
		]
	},
	{
		label: 'Data',
		items: [
			{ title: 'Trades', url: '/trades', icon: LineChart },
			{ title: 'Upload CSV', url: '/upload', icon: Upload },
			{ title: 'Market Data', url: '/market', icon: Activity }
		]
	},
	{
		label: 'Intelligence',
		items: [
			{ title: 'Risk Analytics', url: '/risk', icon: ShieldAlert },
			{ title: 'Regime Analytics', url: '/regime', icon: BarChart3 },
			{ title: 'Stress Tests', url: '/stress-tests', icon: FlaskConical },
			{ title: 'Portfolio Health', url: '/portfolio-health', icon: HeartPulse },
			{ title: 'Recommendations', url: '/recommendations', icon: Lightbulb },
			{ title: 'AI Copilot', url: '/ai-copilot', icon: Bot }
		]
	},
	{
		label: 'System',
		items: [{ title: 'Settings', url: '/settings', icon: Settings }]
	}
];

export function AppSidebar() {
	const { state, isMobile, setOpenMobile } = useSidebar();
	const collapsed = state === 'collapsed' && !isMobile;
	const pathname = usePathname();

	return (
		<Sidebar collapsible="icon" className="border-sidebar-border">
			<SidebarHeader className="border-sidebar-border border-b px-3 py-4">
				<Link href="/dashboard" className="flex items-center gap-2.5">
					<span className="bg-gradient-brand text-primary-foreground shadow-elegant flex size-8 shrink-0 items-center justify-center rounded-lg text-sm font-bold">
						R
					</span>

					{!collapsed && (
						<span className="min-w-0">
							<span className="block truncate text-sm font-semibold leading-tight">
								Regime Aware
							</span>
							<span className="text-sidebar-foreground/60 block truncate text-xs">
								Risk Analytics
							</span>
						</span>
					)}
				</Link>
			</SidebarHeader>
			<SidebarContent>
				{NAV.map((group) => (
					<SidebarGroup key={group.label}>
						{!collapsed && <SidebarGroupLabel>{group.label}</SidebarGroupLabel>}
						<SidebarGroupContent>
							<SidebarMenu>
								{group.items.map((item) => {
									const active = pathname === item.url || pathname.startsWith(`${item.url}/`);
									return (
										<SidebarMenuItem key={item.url}>
											<SidebarMenuButton asChild isActive={active} tooltip={item.title}>
												<Link href={item.url} onClick={() => isMobile && setOpenMobile(false)}>
													<item.icon />
													<span>{item.title}</span>
												</Link>
											</SidebarMenuButton>
										</SidebarMenuItem>
									);
								})}
							</SidebarMenu>
						</SidebarGroupContent>
					</SidebarGroup>
				))}
			</SidebarContent>
		</Sidebar>
	);
}
