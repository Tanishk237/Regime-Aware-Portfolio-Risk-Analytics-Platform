import Image from 'next/image';

import { cn } from '@/lib/utils';

type LatentBrandProps = {
	variant?: 'dark' | 'light';
	size?: 'sm' | 'md';
	showText?: boolean;
	className?: string;
};

export function LatentMark({
	variant = 'dark',
	className
}: {
	variant?: 'dark' | 'light';
	className?: string;
}) {
	const src = variant === 'dark' ? '/brand/latent-tile-dark.png' : '/brand/latent-tile-light.png';
	return (
		<Image
			src={src}
			alt="Latent logo"
			width={96}
			height={96}
			priority
			className={cn('rounded-xl object-contain', className)}
		/>
	);
}

export function LatentBrand({
	variant = 'dark',
	size = 'md',
	showText = true,
	className
}: LatentBrandProps) {
	return (
		<div className={cn('flex items-center gap-3', className)}>
			<LatentMark variant={variant} className={size === 'sm' ? 'size-9' : 'size-12'} />
			{showText ? (
				<div className="min-w-0">
					<p
						className={cn(
							'truncate font-semibold leading-tight',
							size === 'sm' ? 'text-sm' : 'text-lg'
						)}
					>
						Latent
					</p>
					<p className="text-muted-foreground truncate text-xs">Portfolio Regime Intelligence</p>
				</div>
			) : null}
		</div>
	);
}
