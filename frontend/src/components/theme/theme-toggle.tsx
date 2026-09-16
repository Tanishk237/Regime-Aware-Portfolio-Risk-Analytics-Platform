'use client';

import { Moon, Sun } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { useTheme } from '@/components/theme/theme-provider';
import { cn } from '@/lib/utils';

export function ThemeToggle({ className }: { className?: string }) {
	const { theme, toggleTheme } = useTheme();
	const nextTheme = theme === 'dark' ? 'light' : 'dark';

	return (
		<Tooltip>
			<TooltipTrigger asChild>
				<Button
					variant="ghost"
					size="icon"
					aria-label={`Switch to ${nextTheme} mode`}
					onClick={toggleTheme}
					className={cn('shrink-0', className)}
				>
					{theme === 'dark' ? <Moon className="size-4" /> : <Sun className="size-4" />}
				</Button>
			</TooltipTrigger>
			<TooltipContent>Switch to {nextTheme} mode</TooltipContent>
		</Tooltip>
	);
}
