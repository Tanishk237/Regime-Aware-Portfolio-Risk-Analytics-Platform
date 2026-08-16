import js from '@eslint/js';
import nextPlugin from '@next/eslint-plugin-next';
import eslintPluginPrettier from 'eslint-plugin-prettier/recommended';
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';
import tseslint from 'typescript-eslint';

export default tseslint.config(
	{
		ignores: [
			'.next',
			'dist',
			'next-env.d.ts',
			'node_modules',
			'src/routes',
			'src/router.tsx',
			'src/routeTree.gen.ts',
			'src/start.ts',
			'src/server.ts'
		]
	},
	{
		extends: [js.configs.recommended, ...tseslint.configs.recommended],
		files: ['**/*.{ts,tsx}'],
		languageOptions: {
			ecmaVersion: 2020,
			globals: globals.browser
		},
		plugins: {
			'@next/next': nextPlugin,
			'react-hooks': reactHooks
		},
		rules: {
			...nextPlugin.configs.recommended.rules,
			...nextPlugin.configs['core-web-vitals'].rules,
			...reactHooks.configs.recommended.rules,
			'@typescript-eslint/no-unused-vars': 'off'
		}
	},
	eslintPluginPrettier
);
