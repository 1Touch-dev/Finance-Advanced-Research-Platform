module.exports = {
  extends: [
    './base.js',
    'plugin:react/recommended',
    'plugin:react/jsx-runtime',
    'prettier',
  ],
  settings: {
    react: {
      version: 'detect',
    },
  },
  env: {
    browser: true,
  },
};
