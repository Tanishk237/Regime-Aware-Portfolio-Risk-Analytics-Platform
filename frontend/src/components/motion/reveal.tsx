import {
	motion,
	useMotionTemplate,
	useMotionValue,
	useReducedMotion,
	useSpring
} from 'motion/react';
import type { ReactNode } from 'react';

import { cn } from '@/lib/utils';

/** Scroll-triggered reveal with a subtle 3D lift. */
export function Reveal({
	children,
	delay = 0,
	className
}: {
	children: ReactNode;
	delay?: number;
	className?: string;
}) {
	const reduceMotion = useReducedMotion();

	return (
		<motion.div
			className={className}
			initial={reduceMotion ? false : { opacity: 0, y: 12, rotateX: 3 }}
			whileInView={{ opacity: 1, y: 0, rotateX: 0 }}
			viewport={{ once: true, margin: '-60px' }}
			transition={{ duration: reduceMotion ? 0 : 0.42, delay, ease: [0.16, 1, 0.3, 1] }}
			style={{ transformPerspective: 1200 }}
		>
			{children}
		</motion.div>
	);
}

/** Staggered container for grids of cards. */
export function RevealGroup({
	children,
	className
}: {
	children: ReactNode[];
	className?: string;
}) {
	return (
		<div className={className}>
			{children.map((child, index) => (
				<Reveal key={index} delay={Math.min(index * 0.05, 0.4)}>
					{child}
				</Reveal>
			))}
		</div>
	);
}

/** Pointer-tracked tilt + spotlight wrapper for KPI cards. */
export function TiltCard({ children, className }: { children: ReactNode; className?: string }) {
	const rx = useSpring(0, { stiffness: 220, damping: 20 });
	const ry = useSpring(0, { stiffness: 220, damping: 20 });
	const mx = useMotionValue(50);
	const my = useMotionValue(50);
	const spotlight = useMotionTemplate`radial-gradient(220px circle at ${mx}% ${my}%, color-mix(in oklch, var(--primary) 16%, transparent), transparent 70%)`;

	return (
		<motion.div
			className={cn('relative h-full rounded-xl', className)}
			style={{ rotateX: rx, rotateY: ry, transformPerspective: 900 }}
			onPointerMove={(event) => {
				const rect = event.currentTarget.getBoundingClientRect();
				const px = (event.clientX - rect.left) / rect.width;
				const py = (event.clientY - rect.top) / rect.height;
				mx.set(px * 100);
				my.set(py * 100);
				ry.set((px - 0.5) * 8);
				rx.set((0.5 - py) * 8);
			}}
			onPointerLeave={() => {
				rx.set(0);
				ry.set(0);
			}}
			whileHover={{ translateY: -2 }}
		>
			<motion.div
				aria-hidden
				className="pointer-events-none absolute inset-0 z-10 rounded-xl opacity-0 transition-opacity duration-300 hover:opacity-100"
				style={{ background: spotlight }}
			/>
			{children}
		</motion.div>
	);
}
