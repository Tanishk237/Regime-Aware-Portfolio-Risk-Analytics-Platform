import Image from 'next/image';

import { cn } from '@/lib/utils';

type LatentBrandProps = {
	variant?: 'dark' | 'light' | 'auto';
	size?: 'sm' | 'md';
	showText?: boolean;
	className?: string;
};

export function LatentMark({
	variant = 'auto',
	className
}: {
	variant?: 'dark' | 'light' | 'auto';
	className?: string;
}) {
	if (variant === 'auto') {
		return (
			<span className={cn('relative block overflow-hidden rounded-xl', className)}>
				<Image
					src="/brand/latent-tile-light.png"
					alt="Latent logo"
					fill
					loading="eager"
					sizes="48px"
					className="object-contain dark:hidden"
				/>
				<Image
					src="/brand/latent-tile-dark.png"
					alt=""
					fill
					loading="eager"
					sizes="48px"
					aria-hidden
					className="hidden object-contain dark:block"
				/>
			</span>
		);
	}

	const src = variant === 'dark' ? '/brand/latent-tile-dark.png' : '/brand/latent-tile-light.png';
	return (
		<Image
			src={src}
			alt="Latent logo"
			width={96}
			loading="eager"
			height={96}
			className={cn('rounded-xl object-contain', className)}
		/>
	);
}

export function LatentBrand({
	variant = 'auto',
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
