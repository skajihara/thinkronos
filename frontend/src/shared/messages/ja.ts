/** UI strings (conventions 5: keep them out of components). */
export const ja = {
  appName: 'Thinkronos',
  health: {
    checking: 'APIに接続しています…',
    ok: 'APIとデータベースに接続できています',
    degraded: 'APIは動いていますが、データベースに接続できません',
    unreachable: 'APIに接続できません',
    retry: 'もう一度確かめる',
  },
  theme: {
    label: '表示の色',
    light: 'ライト',
    dark: 'ダーク',
    system: '端末に合わせる',
  },
} as const
