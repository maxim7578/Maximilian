import '@adonisjs/inertia/types'

import type React from 'react'
import type { Prettify } from '@adonisjs/core/types/common'

type ExtractProps<T> =
  T extends React.FC<infer Props>
    ? Prettify<Omit<Props, 'children'>>
    : T extends React.Component<infer Props>
      ? Prettify<Omit<Props, 'children'>>
      : never

declare module '@adonisjs/inertia/types' {
  export interface InertiaPages {
    'about': ExtractProps<(typeof import('../../inertia/pages/about.tsx'))['default']>
    'chat': ExtractProps<(typeof import('../../inertia/pages/chat.tsx'))['default']>
    'conditions/show': ExtractProps<(typeof import('../../inertia/pages/conditions/show.tsx'))['default']>
    'docs/show': ExtractProps<(typeof import('../../inertia/pages/docs/show.tsx'))['default']>
    'drug-reference/index': ExtractProps<(typeof import('../../inertia/pages/drug-reference/index.tsx'))['default']>
    'drug-reference/interactions': ExtractProps<(typeof import('../../inertia/pages/drug-reference/interactions.tsx'))['default']>
    'drug-reference/show': ExtractProps<(typeof import('../../inertia/pages/drug-reference/show.tsx'))['default']>
    'easy-setup/complete': ExtractProps<(typeof import('../../inertia/pages/easy-setup/complete.tsx'))['default']>
    'easy-setup/index': ExtractProps<(typeof import('../../inertia/pages/easy-setup/index.tsx'))['default']>
    'errors/not_found': ExtractProps<(typeof import('../../inertia/pages/errors/not_found.tsx'))['default']>
    'errors/server_error': ExtractProps<(typeof import('../../inertia/pages/errors/server_error.tsx'))['default']>
    'home': ExtractProps<(typeof import('../../inertia/pages/home.tsx'))['default']>
    'maps': ExtractProps<(typeof import('../../inertia/pages/maps.tsx'))['default']>
    'settings/advanced': ExtractProps<(typeof import('../../inertia/pages/settings/advanced.tsx'))['default']>
    'settings/apps': ExtractProps<(typeof import('../../inertia/pages/settings/apps.tsx'))['default']>
    'settings/benchmark': ExtractProps<(typeof import('../../inertia/pages/settings/benchmark.tsx'))['default']>
    'settings/creator-packs': ExtractProps<(typeof import('../../inertia/pages/settings/creator-packs.tsx'))['default']>
    'settings/legal': ExtractProps<(typeof import('../../inertia/pages/settings/legal.tsx'))['default']>
    'settings/maps': ExtractProps<(typeof import('../../inertia/pages/settings/maps.tsx'))['default']>
    'settings/models': ExtractProps<(typeof import('../../inertia/pages/settings/models.tsx'))['default']>
    'settings/support': ExtractProps<(typeof import('../../inertia/pages/settings/support.tsx'))['default']>
    'settings/system': ExtractProps<(typeof import('../../inertia/pages/settings/system.tsx'))['default']>
    'settings/update': ExtractProps<(typeof import('../../inertia/pages/settings/update.tsx'))['default']>
    'settings/zim/index': ExtractProps<(typeof import('../../inertia/pages/settings/zim/index.tsx'))['default']>
    'settings/zim/remote-explorer': ExtractProps<(typeof import('../../inertia/pages/settings/zim/remote-explorer.tsx'))['default']>
    'supply-depot': ExtractProps<(typeof import('../../inertia/pages/supply-depot.tsx'))['default']>
  }
}
