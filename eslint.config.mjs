import js from '@eslint/js';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  {
    ignores: ['**/dist/**', '**/coverage/**', '**/node_modules/**'],
  },

  js.configs.recommended,

  ...tseslint.configs.recommended,

  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
      },
    },
    rules: {
      '@typescript-eslint/consistent-type-imports': [
        'error',
        {
          prefer: 'type-imports',
          fixStyle: 'inline-type-imports',
        },
      ],
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
        },
      ],
    },
  },

  {
    files: ['scripts/**/*.mjs'],
    languageOptions: {
      globals: {
        process: 'readonly',
      },
    },
  },

  {
    files: ['apps/web/**/*.{ts,tsx}'],
    languageOptions: {
      globals: {
        AbortController: 'readonly',
        document: 'readonly',
        fetch: 'readonly',
        HTMLElement: 'readonly',
        HTMLInputElement: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
        window: 'readonly',
      },
    },
  },

  {
    files: ['**/*.test.ts', '**/*.test.tsx'],
    languageOptions: {
      globals: {
        describe: 'readonly',
        expect: 'readonly',
        it: 'readonly',
        vi: 'readonly',
      },
    },
  },
);
