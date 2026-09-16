'use client';

import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { usePathname } from 'next/navigation';
import { useEffect } from 'react';

export function PageTransition({ children }: { children: React.ReactNode }) {
	const pathname = usePathname();
	const reduceMotion = useReducedMotion();

	useEffect(() => {
		window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
	}, [pathname]);

	return (
		<AnimatePresence mode="wait" initial={false}>
			<motion.div
				key={pathname}
				initial={reduceMotion ? false : { opacity: 0, y: 8 }}
				animate={{ opacity: 1, y: 0 }}
				exit={reduceMotion ? undefined : { opacity: 0, y: -4 }}
				transition={{ duration: reduceMotion ? 0 : 0.26, ease: [0.22, 1, 0.36, 1] }}
			>
				{children}
			</motion.div>
		</AnimatePresence>
	);
}
