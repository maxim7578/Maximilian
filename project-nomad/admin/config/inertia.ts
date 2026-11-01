import { defineConfig } from '@adonisjs/inertia'

/**
 * Data shared with every page is defined in "app/middleware/inertia_middleware.ts"
 * since AdonisJS 7.
 */
const inertiaConfig = defineConfig({
  /**
   * Path to the Edge view that will be used as the root view for Inertia responses
   */
  rootView: 'inertia_layout',

  /**
   * Options for the server-side rendering
   */
  ssr: {
    enabled: false,
    entrypoint: 'inertia/ssr.tsx',
  },
})

export default inertiaConfig
