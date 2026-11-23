// Conventional Commits. Scope is optional; if used, it must be in the allowlist (G-04).
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'scope-empty': [0],
    'scope-enum': [2, 'always', ['api', 'web', 'worker', 'db', 'ai', 'infra', 'docs', 'spike', 'deps', 'deps-dev']],
    'subject-case': [0],
    'header-max-length': [2, 'always', 100],
  },
};
