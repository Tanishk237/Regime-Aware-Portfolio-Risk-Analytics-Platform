import type { ReactNode } from 'react';

import { cn } from '@/lib/utils';

/** Minimal, dependency-free markdown renderer for AI output. */
export function MarkdownResponse({ content, className }: { content: string; className?: string }) {
	const blocks: ReactNode[] = [];
	const lines = content.replace(/\r\n/g, '\n').split('\n');
	let list: string[] = [];
	let code: string[] | null = null;

	const flushList = (key: string) => {
		if (list.length === 0) return;
		blocks.push(
			<ul key={key} className="my-2 list-disc space-y-1 pl-5">
				{list.map((item, index) => (
					<li key={index}>{inline(item)}</li>
				))}
			</ul>
		);
		list = [];
	};

	lines.forEach((raw, index) => {
		const line = raw.trimEnd();
		if (line.startsWith('```')) {
			if (code) {
				blocks.push(
					<pre
						key={`code-${index}`}
						className="bg-surface-strong my-2 overflow-x-auto rounded-md p-3 text-xs"
					>
						<code>{code.join('\n')}</code>
					</pre>
				);
				code = null;
			} else {
				flushList(`list-${index}`);
				code = [];
			}
			return;
		}
		if (code) {
			code.push(raw);
			return;
		}
		if (/^\s*[-*]\s+/.test(line)) {
			list.push(line.replace(/^\s*[-*]\s+/, ''));
			return;
		}
		flushList(`list-${index}`);
		if (/^#{1,6}\s/.test(line)) {
			const level = line.match(/^#+/)?.[0].length ?? 1;
			const text = line.replace(/^#+\s*/, '');
			blocks.push(
				<p
					key={`h-${index}`}
					className={cn('mb-1 mt-3 font-semibold', level <= 2 ? 'text-base' : 'text-sm')}
				>
					{inline(text)}
				</p>
			);
			return;
		}
		if (/^\s*\|.*\|\s*$/.test(line)) {
			blocks.push(
				<p key={`t-${index}`} className="num text-xs">
					{line}
				</p>
			);
			return;
		}
		if (line.trim() === '') return;
		blocks.push(
			<p key={`p-${index}`} className="my-1.5 leading-relaxed">
				{inline(line)}
			</p>
		);
	});
	flushList('list-end');

	return <div className={cn('text-sm', className)}>{blocks}</div>;
}

function inline(text: string): ReactNode {
	const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g).filter(Boolean);
	return parts.map((part, index) => {
		if (part.startsWith('**') && part.endsWith('**')) {
			return (
				<strong key={index} className="font-semibold">
					{part.slice(2, -2)}
				</strong>
			);
		}
		if (part.startsWith('`') && part.endsWith('`')) {
			return (
				<code key={index} className="num bg-surface-strong rounded px-1 py-0.5 text-[0.85em]">
					{part.slice(1, -1)}
				</code>
			);
		}
		if (part.startsWith('*') && part.endsWith('*') && part.length > 2) {
			return <em key={index}>{part.slice(1, -1)}</em>;
		}
		return <span key={index}>{part}</span>;
	});
}
