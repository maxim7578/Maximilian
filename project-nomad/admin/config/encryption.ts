import env from '#start/env'
import { defineConfig, drivers } from '@adonisjs/core/encryption'

/**
 * Encryption is used for cookies and signed URLs. NOMAD was created on
 * AdonisJS 6, so the "legacy" driver keeps values encrypted by earlier
 * versions readable. The key is still read from the APP_KEY env variable.
 */
const encryptionConfig = defineConfig({
  default: 'legacy',
  list: {
    legacy: drivers.legacy({
      keys: [env.get('APP_KEY')],
    }),
  },
})

export default encryptionConfig

declare module '@adonisjs/core/types' {
  export interface EncryptorsList extends InferEncryptors<typeof encryptionConfig> {}
}
