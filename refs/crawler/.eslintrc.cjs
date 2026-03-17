module.exports = {
  env: {
    browser: true,
    es2021: true,
  },
  extends: ['airbnb-base', 'airbnb-typescript/base'],
  overrides: [
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    tsconfigRootDir: __dirname,
    project: './tsconfig.json',
  },
  rules: {
    'max-len': ['warn', { code: 120 }],
    'no-await-in-loop': 'off',
    // Removed 'ForOfStatement'
    'no-restricted-syntax': ['error', 'ForInStatement', 'LabeledStatement', 'WithStatement'],
    'no-console': 'off',
    'no-continue': 'off',
    'prefer-template': 'off',
    'no-multi-assign': 'off',
    'func-names': 'off',
    'no-cond-assign': ['error', 'except-parens'],
    'no-param-reassign': ['error', { props: false }],
    'object-curly-newline': ['error', { ExportDeclaration: { multiline: true, minProperties: 4 } }],
    '@typescript-eslint/no-floating-promises': ['error'],
    '@typescript-eslint/member-delimiter-style': ['error'],
  },
};
