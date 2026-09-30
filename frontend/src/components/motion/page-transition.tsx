'use client';

import { motion, useReducedMotion } from 'motion/react';
import { usePathname } from 'next/navigation';
import { useEffect } from 'react';

export function PageTransition({ children }: { children: React.ReactNode }) {
	const pathname = usePathname();
	const reduceMotion = useReducedMotion();

	useEffect(() => {
		window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
	}, [pathname]);

	return (
		<motion.div
			key={pathname}
			initial={reduceMotion ? false : { y: 6 }}
			animate={{ y: 0 }}
			transition={{ duration: reduceMotion ? 0 : 0.2, ease: 'easeOut' }}
		>
			{children}
		</motion.div>
	);
}
