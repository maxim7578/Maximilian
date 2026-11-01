import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import adonisjs from '@adonisjs/vite/client'
import tailwindcss from '@tailwindcss/vite'


export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    adonisjs({ entryPoints: ['inertia/app.tsx'], reload: ['resources/views/**/*.edge'] }),
  ],

  /**
   * Define aliases for importing modules from
   * your frontend code
   */
  resolve: {
    /**
     * react-adonis-transmit ships its own React 18 copy. @vitejs/plugin-react 4
     * deduped React automatically; v6 no longer does, and two React copies in
     * the bundle break every hook ("Cannot read properties of null (reading
     * 'useRef')"). Force a single React instance.
     */
    dedupe: ['react', 'react-dom'],
    alias: {
      '~/': `${import.meta.dirname}/inertia/`,
      '@generated': `${import.meta.dirname}/.adonisjs/client/`,
    },
  },
  server: {
    allowedHosts: true // This is for dev environments only. Can be overriden with `__VITE_ADDITIONAL_SERVER_ALLOWED_HOSTS` if needed.
  }
})
