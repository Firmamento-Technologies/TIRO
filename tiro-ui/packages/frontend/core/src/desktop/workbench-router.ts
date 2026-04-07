import type { RouteObject } from 'react-router-dom';

export const workbenchRoutes = [
  // ── TIRO routes ────────────────────────────────────────────────────────────
  {
    path: '/tiro-cruscotto',
    lazy: () => import('./pages/workspace/tiro-cruscotto/index'),
  },
  {
    path: '/tiro-soggetti',
    lazy: () => import('./pages/workspace/tiro-soggetti/index'),
  },
  {
    path: '/tiro-soggetti/:id',
    lazy: () => import('./pages/workspace/tiro-soggetto-dettaglio/index'),
  },
  {
    path: '/tiro-pipeline',
    lazy: () => import('./pages/workspace/tiro-pipeline/index'),
  },
  {
    path: '/tiro-fascicoli',
    lazy: () => import('./pages/workspace/tiro-fascicoli/index'),
  },
  {
    path: '/tiro-ricerca',
    lazy: () => import('./pages/workspace/tiro-ricerca/index'),
  },
  {
    path: '/tiro-proposte',
    lazy: () => import('./pages/workspace/tiro-proposte/index'),
  },
  {
    path: '/tiro-sistema',
    lazy: () => import('./pages/workspace/tiro-sistema/index'),
  },
  {
    path: '/tiro-login',
    lazy: () => import('./pages/workspace/tiro-login/index'),
  },
  // ── AFFiNE routes (original) ───────────────────────────────────────────────
  {
    path: '/chat',
    lazy: () => import('./pages/workspace/chat/index'),
  },
  {
    path: '/all',
    lazy: () => import('./pages/workspace/all-page/all-page'),
  },
  {
    path: '/collection',
    lazy: () => import('./pages/workspace/all-collection'),
  },
  {
    path: '/collection/:collectionId',
    lazy: () => import('./pages/workspace/collection/index'),
  },
  {
    path: '/tag',
    lazy: () => import('./pages/workspace/all-tag'),
  },
  {
    path: '/tag/:tagId',
    lazy: () => import('./pages/workspace/tag'),
  },
  {
    path: '/trash',
    lazy: () => import('./pages/workspace/trash-page'),
  },
  {
    path: '/:pageId',
    lazy: () => import('./pages/workspace/detail-page/detail-page'),
  },
  {
    path: '/:pageId/attachments/:attachmentId',
    lazy: () => import('./pages/workspace/attachment/index'),
  },
  {
    path: '/journals',
    lazy: () => import('./pages/workspace/journals'),
  },
  {
    path: '/settings',
    lazy: () => import('./pages/workspace/settings'),
  },
  {
    path: '*',
    lazy: () => import('./pages/404'),
  },
] satisfies RouteObject[];
