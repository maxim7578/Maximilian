import type { HttpContext } from '@adonisjs/core/http'
import type { NextFn } from '@adonisjs/core/types/http'
import BaseInertiaMiddleware from '@adonisjs/inertia/inertia_middleware'
import { SystemService } from '#services/system_service'
import { getAssistantName } from '../utils/assistant_name.js'

/**
 * Shares data with all Inertia pages (replaces the `sharedData` option of
 * "config/inertia.ts" from AdonisJS 6). NOMAD has no sessions or auth, so
 * there are no validation errors or flash messages to share.
 */
export default class InertiaMiddleware extends BaseInertiaMiddleware {
  async share() {
    return {
      appVersion: SystemService.getAppVersion(),
      environment: process.env.NODE_ENV || 'production',
      aiAssistantName: await getAssistantName(),
    }
  }

  async handle(ctx: HttpContext, next: NextFn) {
    await this.init(ctx)

    const output = await next()
    this.dispose(ctx)

    return output
  }
}

declare module '@adonisjs/inertia/types' {
  type MiddlewareSharedProps = InferSharedProps<InertiaMiddleware>
  export interface SharedProps extends MiddlewareSharedProps {}
}
