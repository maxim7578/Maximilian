/* eslint-disable prettier/prettier */
/// <reference path="../manifest.d.ts" />

import type { ExtractBody, ExtractErrorResponse, ExtractQuery, ExtractQueryForGet, ExtractRawResponse, ExtractResponse, Method, PathWithRegistry, PatternsByMethod, RouteWithRegistry } from '@tuyau/core/types'
import type { InferInput, SimpleError } from '@vinejs/vine/types'
import type { routes } from './index.ts'

export type ParamValue = string | number | bigint | boolean

export interface Registry {
  'event_stream': {
    methods: ["GET","HEAD"]
    pattern: '/__transmit/events'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'subscribe': {
    methods: ["POST"]
    pattern: '/__transmit/subscribe'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'unsubscribe': {
    methods: ["POST"]
    pattern: '/__transmit/unsubscribe'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'home.index': {
    methods: ["GET","HEAD"]
    pattern: '/'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'home.home': {
    methods: ["GET","HEAD"]
    pattern: '/home'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'chats.inertia': {
    methods: ["GET","HEAD"]
    pattern: '/chat'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'maps.index': {
    methods: ["GET","HEAD"]
    pattern: '/maps'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'supply_depot.index': {
    methods: ["GET","HEAD"]
    pattern: '/supply-depot'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'easy_setup.index': {
    methods: ["GET","HEAD"]
    pattern: '/easy-setup'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'easy_setup.complete': {
    methods: ["GET","HEAD"]
    pattern: '/easy-setup/complete'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'easy_setup.list_curated_categories': {
    methods: ["GET","HEAD"]
    pattern: '/api/easy-setup/curated-categories'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'easy_setup.refresh_manifests': {
    methods: ["POST"]
    pattern: '/api/manifests/refresh'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'collection_updates.check_for_updates': {
    methods: ["POST"]
    pattern: '/api/content-updates/check'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'collection_updates.apply_update': {
    methods: ["POST"]
    pattern: '/api/content-updates/apply'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'collection_updates.apply_all_updates': {
    methods: ["POST"]
    pattern: '/api/content-updates/apply-all'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'settings.system': {
    methods: ["GET","HEAD"]
    pattern: '/settings/system'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'settings.legal': {
    methods: ["GET","HEAD"]
    pattern: '/settings/legal'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'settings.maps': {
    methods: ["GET","HEAD"]
    pattern: '/settings/maps'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'settings.models': {
    methods: ["GET","HEAD"]
    pattern: '/settings/models'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'settings.update': {
    methods: ["GET","HEAD"]
    pattern: '/settings/update'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'settings.zim': {
    methods: ["GET","HEAD"]
    pattern: '/settings/zim'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'settings.zim_remote': {
    methods: ["GET","HEAD"]
    pattern: '/settings/zim/remote-explorer'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'settings.creator_packs': {
    methods: ["GET","HEAD"]
    pattern: '/settings/creator-packs'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'settings.benchmark': {
    methods: ["GET","HEAD"]
    pattern: '/settings/benchmark'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'settings.support': {
    methods: ["GET","HEAD"]
    pattern: '/settings/support'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'settings.advanced': {
    methods: ["GET","HEAD"]
    pattern: '/settings/advanced'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'docs.show': {
    methods: ["GET","HEAD"]
    pattern: '/docs/:slug'
    types: {
      body: {}
      paramsTuple: [ParamValue]
      params: { slug: ParamValue }
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'maps.list_regions': {
    methods: ["GET","HEAD"]
    pattern: '/api/maps/regions'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'maps.styles': {
    methods: ["GET","HEAD"]
    pattern: '/api/maps/styles'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'maps.list_curated_collections': {
    methods: ["GET","HEAD"]
    pattern: '/api/maps/curated-collections'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'maps.fetch_latest_collections': {
    methods: ["POST"]
    pattern: '/api/maps/fetch-latest-collections'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'maps.download_base_assets': {
    methods: ["POST"]
    pattern: '/api/maps/download-base-assets'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'maps.setup_world_basemap': {
    methods: ["POST"]
    pattern: '/api/maps/setup-world-basemap'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'maps.download_remote': {
    methods: ["POST"]
    pattern: '/api/maps/download-remote'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'maps.download_remote_preflight': {
    methods: ["POST"]
    pattern: '/api/maps/download-remote-preflight'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'maps.download_collection': {
    methods: ["POST"]
    pattern: '/api/maps/download-collection'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'maps.global_map_info': {
    methods: ["GET","HEAD"]
    pattern: '/api/maps/global-map-info'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'maps.download_global_map': {
    methods: ["POST"]
    pattern: '/api/maps/download-global-map'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'maps.list_countries': {
    methods: ["GET","HEAD"]
    pattern: '/api/maps/countries'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'maps.list_country_groups': {
    methods: ["GET","HEAD"]
    pattern: '/api/maps/country-groups'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'maps.extract_preflight': {
    methods: ["POST"]
    pattern: '/api/maps/extract-preflight'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'maps.extract_region': {
    methods: ["POST"]
    pattern: '/api/maps/extract'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'maps.list_markers': {
    methods: ["GET","HEAD"]
    pattern: '/api/maps/markers'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'maps.create_marker': {
    methods: ["POST"]
    pattern: '/api/maps/markers'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'maps.update_marker': {
    methods: ["PATCH"]
    pattern: '/api/maps/markers/:id'
    types: {
      body: {}
      paramsTuple: [ParamValue]
      params: { id: ParamValue }
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'maps.delete_marker': {
    methods: ["DELETE"]
    pattern: '/api/maps/markers/:id'
    types: {
      body: {}
      paramsTuple: [ParamValue]
      params: { id: ParamValue }
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'maps.delete': {
    methods: ["DELETE"]
    pattern: '/api/maps/:filename'
    types: {
      body: {}
      paramsTuple: [ParamValue]
      params: { filename: ParamValue }
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'docs.list': {
    methods: ["GET","HEAD"]
    pattern: '/api/docs/list'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'downloads.index': {
    methods: ["GET","HEAD"]
    pattern: '/api/downloads/jobs'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'downloads.filetype': {
    methods: ["GET","HEAD"]
    pattern: '/api/downloads/jobs/:filetype'
    types: {
      body: {}
      paramsTuple: [ParamValue]
      params: { filetype: ParamValue }
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'downloads.remove_job': {
    methods: ["DELETE"]
    pattern: '/api/downloads/jobs/:jobId'
    types: {
      body: {}
      paramsTuple: [ParamValue]
      params: { jobId: ParamValue }
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'downloads.cancel_job': {
    methods: ["POST"]
    pattern: '/api/downloads/jobs/:jobId/cancel'
    types: {
      body: {}
      paramsTuple: [ParamValue]
      params: { jobId: ParamValue }
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'downloads.retry_job': {
    methods: ["POST"]
    pattern: '/api/downloads/jobs/:jobId/retry'
    types: {
      body: {}
      paramsTuple: [ParamValue]
      params: { jobId: ParamValue }
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'open_api.spec': {
    methods: ["GET","HEAD"]
    pattern: '/api/openapi.json'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'open_api.reference': {
    methods: ["GET","HEAD"]
    pattern: '/reference'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'open_api.standalone': {
    methods: ["GET","HEAD"]
    pattern: '/reference/assets/standalone.js'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'ollama.chat': {
    methods: ["POST"]
    pattern: '/api/ollama/chat'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'ollama.available_models': {
    methods: ["GET","HEAD"]
    pattern: '/api/ollama/models'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'ollama.dispatch_model_download': {
    methods: ["POST"]
    pattern: '/api/ollama/models'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'ollama.delete_model': {
    methods: ["DELETE"]
    pattern: '/api/ollama/models'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'ollama.installed_models': {
    methods: ["GET","HEAD"]
    pattern: '/api/ollama/installed-models'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'ollama.unload_chat_models': {
    methods: ["POST"]
    pattern: '/api/ollama/unload-chat-models'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'ollama.configure_remote': {
    methods: ["POST"]
    pattern: '/api/ollama/configure-remote'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'ollama.remote_status': {
    methods: ["GET","HEAD"]
    pattern: '/api/ollama/remote-status'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'nomad_md.show': {
    methods: ["GET","HEAD"]
    pattern: '/api/ai/nomad-md'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'nomad_md.update': {
    methods: ["PUT"]
    pattern: '/api/ai/nomad-md'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'chats.index': {
    methods: ["GET","HEAD"]
    pattern: '/api/chat/sessions'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'chats.store': {
    methods: ["POST"]
    pattern: '/api/chat/sessions'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'chats.destroy_all': {
    methods: ["DELETE"]
    pattern: '/api/chat/sessions/all'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'chats.show': {
    methods: ["GET","HEAD"]
    pattern: '/api/chat/sessions/:id'
    types: {
      body: {}
      paramsTuple: [ParamValue]
      params: { id: ParamValue }
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'chats.update': {
    methods: ["PUT"]
    pattern: '/api/chat/sessions/:id'
    types: {
      body: {}
      paramsTuple: [ParamValue]
      params: { id: ParamValue }
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'chats.destroy': {
    methods: ["DELETE"]
    pattern: '/api/chat/sessions/:id'
    types: {
      body: {}
      paramsTuple: [ParamValue]
      params: { id: ParamValue }
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'chats.add_message': {
    methods: ["POST"]
    pattern: '/api/chat/sessions/:id/messages'
    types: {
      body: {}
      paramsTuple: [ParamValue]
      params: { id: ParamValue }
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'chats.suggestions': {
    methods: ["GET","HEAD"]
    pattern: '/api/chat/suggestions'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'rag.upload': {
    methods: ["POST"]
    pattern: '/api/rag/upload'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'rag.get_stored_files': {
    methods: ["GET","HEAD"]
    pattern: '/api/rag/files'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'rag.get_file_warnings': {
    methods: ["GET","HEAD"]
    pattern: '/api/rag/file-warnings'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'rag.delete_file': {
    methods: ["DELETE"]
    pattern: '/api/rag/files'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'rag.embed_file': {
    methods: ["POST"]
    pattern: '/api/rag/files/embed'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'rag.get_file_content': {
    methods: ["GET","HEAD"]
    pattern: '/api/rag/files/content'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'rag.download_file': {
    methods: ["GET","HEAD"]
    pattern: '/api/rag/files/download'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'rag.get_active_jobs': {
    methods: ["GET","HEAD"]
    pattern: '/api/rag/active-jobs'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'rag.get_failed_jobs': {
    methods: ["GET","HEAD"]
    pattern: '/api/rag/failed-jobs'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'rag.cleanup_failed_jobs': {
    methods: ["DELETE"]
    pattern: '/api/rag/failed-jobs'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'rag.cancel_all_jobs': {
    methods: ["DELETE"]
    pattern: '/api/rag/jobs'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'rag.get_job_status': {
    methods: ["GET","HEAD"]
    pattern: '/api/rag/job-status'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'rag.scan_and_sync': {
    methods: ["POST"]
    pattern: '/api/rag/sync'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'rag.reembed_all': {
    methods: ["POST"]
    pattern: '/api/rag/re-embed-all'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'rag.reset_and_rebuild': {
    methods: ["POST"]
    pattern: '/api/rag/reset-and-rebuild'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'rag.estimate_batch': {
    methods: ["POST"]
    pattern: '/api/rag/estimate-batch'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'rag.policy_prompt_state': {
    methods: ["GET","HEAD"]
    pattern: '/api/rag/policy-prompt-state'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'rag.health': {
    methods: ["GET","HEAD"]
    pattern: '/api/rag/health'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'rag.get_knowledge_collections': {
    methods: ["GET","HEAD"]
    pattern: '/api/rag/collections'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'rag.update_file_collection': {
    methods: ["POST"]
    pattern: '/api/rag/update-collection'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'rag.set_file_active': {
    methods: ["POST"]
    pattern: '/api/rag/files/active'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'rag.rename_knowledge_collection': {
    methods: ["POST"]
    pattern: '/api/rag/rename-collection'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'rag.delete_knowledge_collection': {
    methods: ["POST"]
    pattern: '/api/rag/delete-collection'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'rag.set_knowledge_collection_active': {
    methods: ["POST"]
    pattern: '/api/rag/collection-active'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.get_debug_info': {
    methods: ["GET","HEAD"]
    pattern: '/api/system/debug-info'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.get_system_info': {
    methods: ["GET","HEAD"]
    pattern: '/api/system/info'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.get_internet_status': {
    methods: ["GET","HEAD"]
    pattern: '/api/system/internet-status'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.get_services': {
    methods: ["GET","HEAD"]
    pattern: '/api/system/services'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.affect_service': {
    methods: ["POST"]
    pattern: '/api/system/services/affect'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.install_service': {
    methods: ["POST"]
    pattern: '/api/system/services/install'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.force_reinstall_service': {
    methods: ["POST"]
    pattern: '/api/system/services/force-reinstall'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.uninstall_service': {
    methods: ["POST"]
    pattern: '/api/system/services/uninstall'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.check_service_updates': {
    methods: ["POST"]
    pattern: '/api/system/services/check-updates'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.preflight_check': {
    methods: ["GET","HEAD"]
    pattern: '/api/system/services/preflight'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.suggest_custom_port': {
    methods: ["GET","HEAD"]
    pattern: '/api/system/services/suggest-port'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.preflight_custom_app': {
    methods: ["POST"]
    pattern: '/api/system/services/preflight-custom'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.create_custom_app': {
    methods: ["POST"]
    pattern: '/api/system/services/custom'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.update_custom_app': {
    methods: ["PUT"]
    pattern: '/api/system/services/custom'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.update_custom_app_pull_latest': {
    methods: ["POST"]
    pattern: '/api/system/services/custom/update'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.delete_custom_app': {
    methods: ["DELETE"]
    pattern: '/api/system/services/custom'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.get_custom_app': {
    methods: ["GET","HEAD"]
    pattern: '/api/system/services/custom/:name'
    types: {
      body: {}
      paramsTuple: [ParamValue]
      params: { name: ParamValue }
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.create_link_tile': {
    methods: ["POST"]
    pattern: '/api/system/services/links'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.update_link_tile': {
    methods: ["PUT"]
    pattern: '/api/system/services/links'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.delete_link_tile': {
    methods: ["DELETE"]
    pattern: '/api/system/services/links'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.set_service_custom_url': {
    methods: ["PUT"]
    pattern: '/api/system/services/custom-url'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.get_service_logs': {
    methods: ["GET","HEAD"]
    pattern: '/api/system/services/:name/logs'
    types: {
      body: {}
      paramsTuple: [ParamValue]
      params: { name: ParamValue }
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.get_service_stats': {
    methods: ["GET","HEAD"]
    pattern: '/api/system/services/:name/stats'
    types: {
      body: {}
      paramsTuple: [ParamValue]
      params: { name: ParamValue }
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.get_available_versions': {
    methods: ["GET","HEAD"]
    pattern: '/api/system/services/:name/available-versions'
    types: {
      body: {}
      paramsTuple: [ParamValue]
      params: { name: ParamValue }
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.update_service': {
    methods: ["POST"]
    pattern: '/api/system/services/update'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.set_service_auto_update': {
    methods: ["POST"]
    pattern: '/api/system/services/auto-update'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.get_app_auto_update_status': {
    methods: ["GET","HEAD"]
    pattern: '/api/system/apps/auto-update/status'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.get_content_auto_update_status': {
    methods: ["GET","HEAD"]
    pattern: '/api/system/content/auto-update/status'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.subscribe_to_release_notes': {
    methods: ["POST"]
    pattern: '/api/system/subscribe-release-notes'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.check_latest_version': {
    methods: ["GET","HEAD"]
    pattern: '/api/system/latest-version'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.request_system_update': {
    methods: ["POST"]
    pattern: '/api/system/update'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.get_system_update_status': {
    methods: ["GET","HEAD"]
    pattern: '/api/system/update/status'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.get_system_update_logs': {
    methods: ["GET","HEAD"]
    pattern: '/api/system/update/logs'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'system.get_auto_update_status': {
    methods: ["GET","HEAD"]
    pattern: '/api/system/auto-update/status'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'settings.get_setting': {
    methods: ["GET","HEAD"]
    pattern: '/api/system/settings'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'settings.update_setting': {
    methods: ["PATCH"]
    pattern: '/api/system/settings'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'zim.list': {
    methods: ["GET","HEAD"]
    pattern: '/api/zim/list'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'zim.list_remote': {
    methods: ["GET","HEAD"]
    pattern: '/api/zim/list-remote'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'zim.list_catalog_languages': {
    methods: ["GET","HEAD"]
    pattern: '/api/zim/catalog-languages'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'zim.list_curated_categories': {
    methods: ["GET","HEAD"]
    pattern: '/api/zim/curated-categories'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'zim.download_remote': {
    methods: ["POST"]
    pattern: '/api/zim/download-remote'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'zim.download_category_tier': {
    methods: ["POST"]
    pattern: '/api/zim/download-category-tier'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'zim.upload': {
    methods: ["POST"]
    pattern: '/api/zim/upload'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'zim.get_wikipedia_state': {
    methods: ["GET","HEAD"]
    pattern: '/api/zim/wikipedia'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'zim.select_wikipedia': {
    methods: ["POST"]
    pattern: '/api/zim/wikipedia/select'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'zim.list_custom_libraries': {
    methods: ["GET","HEAD"]
    pattern: '/api/zim/custom-libraries'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'zim.add_custom_library': {
    methods: ["POST"]
    pattern: '/api/zim/custom-libraries'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'zim.remove_custom_library': {
    methods: ["DELETE"]
    pattern: '/api/zim/custom-libraries/:id'
    types: {
      body: {}
      paramsTuple: [ParamValue]
      params: { id: ParamValue }
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'zim.browse_library': {
    methods: ["GET","HEAD"]
    pattern: '/api/zim/browse-library'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'zim.rescan_library': {
    methods: ["POST"]
    pattern: '/api/zim/rescan-library'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'zim.delete': {
    methods: ["DELETE"]
    pattern: '/api/zim/:filename'
    types: {
      body: {}
      paramsTuple: [ParamValue]
      params: { filename: ParamValue }
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'creator_packs.index': {
    methods: ["GET","HEAD"]
    pattern: '/api/creator-packs'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'creator_packs.install': {
    methods: ["POST"]
    pattern: '/api/creator-packs/:id/install'
    types: {
      body: {}
      paramsTuple: [ParamValue]
      params: { id: ParamValue }
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'creator_packs.uninstall': {
    methods: ["DELETE"]
    pattern: '/api/creator-packs/:id'
    types: {
      body: {}
      paramsTuple: [ParamValue]
      params: { id: ParamValue }
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'benchmark.run': {
    methods: ["POST"]
    pattern: '/api/benchmark/run'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'benchmark.run_system': {
    methods: ["POST"]
    pattern: '/api/benchmark/run/system'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'benchmark.run_ai': {
    methods: ["POST"]
    pattern: '/api/benchmark/run/ai'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'benchmark.results': {
    methods: ["GET","HEAD"]
    pattern: '/api/benchmark/results'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'benchmark.latest': {
    methods: ["GET","HEAD"]
    pattern: '/api/benchmark/results/latest'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'benchmark.show': {
    methods: ["GET","HEAD"]
    pattern: '/api/benchmark/results/:id'
    types: {
      body: {}
      paramsTuple: [ParamValue]
      params: { id: ParamValue }
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'benchmark.submit': {
    methods: ["POST"]
    pattern: '/api/benchmark/submit'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'benchmark.update_builder_tag': {
    methods: ["POST"]
    pattern: '/api/benchmark/builder-tag'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'benchmark.comparison': {
    methods: ["GET","HEAD"]
    pattern: '/api/benchmark/comparison'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'benchmark.status': {
    methods: ["GET","HEAD"]
    pattern: '/api/benchmark/status'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'benchmark.rerun_banner': {
    methods: ["GET","HEAD"]
    pattern: '/api/benchmark/rerun-banner'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'benchmark.settings': {
    methods: ["GET","HEAD"]
    pattern: '/api/benchmark/settings'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'benchmark.update_settings': {
    methods: ["POST"]
    pattern: '/api/benchmark/settings'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'drug_reference.index': {
    methods: ["GET","HEAD"]
    pattern: '/drug-reference'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'drug_reference.interactions': {
    methods: ["GET","HEAD"]
    pattern: '/drug-reference/interactions'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'drug_reference.show': {
    methods: ["GET","HEAD"]
    pattern: '/drug-reference/:id'
    types: {
      body: {}
      paramsTuple: [ParamValue]
      params: { id: ParamValue }
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'drug_reference.search': {
    methods: ["GET","HEAD"]
    pattern: '/api/drug-reference/search'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'drug_reference.status': {
    methods: ["GET","HEAD"]
    pattern: '/api/drug-reference/status'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'drug_reference.interactions_api': {
    methods: ["GET","HEAD"]
    pattern: '/api/drug-reference/interactions'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'drug_reference.download': {
    methods: ["POST"]
    pattern: '/api/drug-reference/download'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'drug_reference.ingest': {
    methods: ["POST"]
    pattern: '/api/drug-reference/ingest'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'drug_reference.reset_ingest': {
    methods: ["POST"]
    pattern: '/api/drug-reference/reset-ingest'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'drug_reference.uninstall': {
    methods: ["POST"]
    pattern: '/api/drug-reference/uninstall'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'drug_reference.ingest_log': {
    methods: ["GET","HEAD"]
    pattern: '/api/drug-reference/ingest-log'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'conditions.index': {
    methods: ["GET","HEAD"]
    pattern: '/conditions'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'conditions.show': {
    methods: ["GET","HEAD"]
    pattern: '/conditions/:slug'
    types: {
      body: {}
      paramsTuple: [ParamValue]
      params: { slug: ParamValue }
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
  'conditions.drugs_api': {
    methods: ["GET","HEAD"]
    pattern: '/api/conditions/drugs'
    types: {
      body: {}
      paramsTuple: []
      params: {}
      query: {}
      response: unknown
      errorResponse: unknown
      rawResponse: ExtractRawResponse<unknown>
    }
  }
}

export namespace Route {
  export type Request<Name extends keyof typeof routes> = RouteWithRegistry.Request<typeof routes, Name>
  export type Response<Name extends keyof typeof routes> = RouteWithRegistry.Response<typeof routes, Name>
  export type Params<Name extends keyof typeof routes> = RouteWithRegistry.Params<typeof routes, Name>
  export type Body<Name extends keyof typeof routes> = RouteWithRegistry.Body<typeof routes, Name>
  export type Query<Name extends keyof typeof routes> = RouteWithRegistry.Query<typeof routes, Name>
  export type Error<Name extends keyof typeof routes> = RouteWithRegistry.Error<typeof routes, Name>
}

export namespace Path {
  export type Request<M extends Method, P extends PatternsByMethod<typeof routes, M>> =
    PathWithRegistry.Request<typeof routes, M, P>
  export type Response<M extends Method, P extends PatternsByMethod<typeof routes, M>> =
    PathWithRegistry.Response<typeof routes, M, P>
  export type Params<M extends Method, P extends PatternsByMethod<typeof routes, M>> =
    PathWithRegistry.Params<typeof routes, M, P>
  export type Body<M extends Method, P extends PatternsByMethod<typeof routes, M>> =
    PathWithRegistry.Body<typeof routes, M, P>
  export type Query<M extends Method, P extends PatternsByMethod<typeof routes, M>> =
    PathWithRegistry.Query<typeof routes, M, P>
  export type Error<M extends Method, P extends PatternsByMethod<typeof routes, M>> =
    PathWithRegistry.Error<typeof routes, M, P>
}
