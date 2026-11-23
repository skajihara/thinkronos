/** Feature modules must not import each other; share code through src/shared (conventions 3.3). */
module.exports = {
  forbidden: [
    {
      name: 'no-cross-feature-import',
      severity: 'error',
      from: { path: '^src/features/([^/]+)/' },
      to: { path: '^src/features/([^/]+)/', pathNot: '^src/features/$1/' },
    },
    {
      name: 'shared-does-not-import-features',
      severity: 'error',
      from: { path: '^src/shared/' },
      to: { path: '^src/features/' },
    },
    { name: 'no-circular', severity: 'error', from: {}, to: { circular: true } },
  ],
  options: {
    doNotFollow: { path: 'node_modules' },
    tsConfig: { fileName: 'tsconfig.app.json' },
    exclude: { path: '\\.d\\.ts$' },
  },
}
