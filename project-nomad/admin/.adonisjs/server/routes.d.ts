import '@adonisjs/core/types/http'

type ParamValue = string | number | bigint | boolean

export type ScannedRoutes = {
  ALL: {
    'event_stream': { paramsTuple?: []; params?: {} }
    'subscribe': { paramsTuple?: []; params?: {} }
    'unsubscribe': { paramsTuple?: []; params?: {} }
    'home.index': { paramsTuple?: []; params?: {} }
    'home.home': { paramsTuple?: []; params?: {} }
    'chats.inertia': { paramsTuple?: []; params?: {} }
    'maps.index': { paramsTuple?: []; params?: {} }
    'supply_depot.index': { paramsTuple?: []; params?: {} }
    'easy_setup.index': { paramsTuple?: []; params?: {} }
    'easy_setup.complete': { paramsTuple?: []; params?: {} }
    'easy_setup.list_curated_categories': { paramsTuple?: []; params?: {} }
    'easy_setup.refresh_manifests': { paramsTuple?: []; params?: {} }
    'collection_updates.check_for_updates': { paramsTuple?: []; params?: {} }
    'collection_updates.apply_update': { paramsTuple?: []; params?: {} }
    'collection_updates.apply_all_updates': { paramsTuple?: []; params?: {} }
    'settings.system': { paramsTuple?: []; params?: {} }
    'settings.legal': { paramsTuple?: []; params?: {} }
    'settings.maps': { paramsTuple?: []; params?: {} }
    'settings.models': { paramsTuple?: []; params?: {} }
    'settings.update': { paramsTuple?: []; params?: {} }
    'settings.zim': { paramsTuple?: []; params?: {} }
    'settings.zim_remote': { paramsTuple?: []; params?: {} }
    'settings.creator_packs': { paramsTuple?: []; params?: {} }
    'settings.benchmark': { paramsTuple?: []; params?: {} }
    'settings.support': { paramsTuple?: []; params?: {} }
    'settings.advanced': { paramsTuple?: []; params?: {} }
    'docs.show': { paramsTuple: [ParamValue]; params: {'slug': ParamValue} }
    'maps.list_regions': { paramsTuple?: []; params?: {} }
    'maps.styles': { paramsTuple?: []; params?: {} }
    'maps.list_curated_collections': { paramsTuple?: []; params?: {} }
    'maps.fetch_latest_collections': { paramsTuple?: []; params?: {} }
    'maps.download_base_assets': { paramsTuple?: []; params?: {} }
    'maps.setup_world_basemap': { paramsTuple?: []; params?: {} }
    'maps.download_remote': { paramsTuple?: []; params?: {} }
    'maps.download_remote_preflight': { paramsTuple?: []; params?: {} }
    'maps.download_collection': { paramsTuple?: []; params?: {} }
    'maps.global_map_info': { paramsTuple?: []; params?: {} }
    'maps.download_global_map': { paramsTuple?: []; params?: {} }
    'maps.list_countries': { paramsTuple?: []; params?: {} }
    'maps.list_country_groups': { paramsTuple?: []; params?: {} }
    'maps.extract_preflight': { paramsTuple?: []; params?: {} }
    'maps.extract_region': { paramsTuple?: []; params?: {} }
    'maps.list_markers': { paramsTuple?: []; params?: {} }
    'maps.create_marker': { paramsTuple?: []; params?: {} }
    'maps.update_marker': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'maps.delete_marker': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'maps.delete': { paramsTuple: [ParamValue]; params: {'filename': ParamValue} }
    'docs.list': { paramsTuple?: []; params?: {} }
    'downloads.index': { paramsTuple?: []; params?: {} }
    'downloads.filetype': { paramsTuple: [ParamValue]; params: {'filetype': ParamValue} }
    'downloads.remove_job': { paramsTuple: [ParamValue]; params: {'jobId': ParamValue} }
    'downloads.cancel_job': { paramsTuple: [ParamValue]; params: {'jobId': ParamValue} }
    'downloads.retry_job': { paramsTuple: [ParamValue]; params: {'jobId': ParamValue} }
    'open_api.spec': { paramsTuple?: []; params?: {} }
    'open_api.reference': { paramsTuple?: []; params?: {} }
    'open_api.standalone': { paramsTuple?: []; params?: {} }
    'ollama.chat': { paramsTuple?: []; params?: {} }
    'ollama.available_models': { paramsTuple?: []; params?: {} }
    'ollama.dispatch_model_download': { paramsTuple?: []; params?: {} }
    'ollama.delete_model': { paramsTuple?: []; params?: {} }
    'ollama.installed_models': { paramsTuple?: []; params?: {} }
    'ollama.unload_chat_models': { paramsTuple?: []; params?: {} }
    'ollama.configure_remote': { paramsTuple?: []; params?: {} }
    'ollama.remote_status': { paramsTuple?: []; params?: {} }
    'nomad_md.show': { paramsTuple?: []; params?: {} }
    'nomad_md.update': { paramsTuple?: []; params?: {} }
    'chats.index': { paramsTuple?: []; params?: {} }
    'chats.store': { paramsTuple?: []; params?: {} }
    'chats.destroy_all': { paramsTuple?: []; params?: {} }
    'chats.show': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'chats.update': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'chats.destroy': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'chats.add_message': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'chats.suggestions': { paramsTuple?: []; params?: {} }
    'rag.upload': { paramsTuple?: []; params?: {} }
    'rag.get_stored_files': { paramsTuple?: []; params?: {} }
    'rag.get_file_warnings': { paramsTuple?: []; params?: {} }
    'rag.delete_file': { paramsTuple?: []; params?: {} }
    'rag.embed_file': { paramsTuple?: []; params?: {} }
    'rag.get_file_content': { paramsTuple?: []; params?: {} }
    'rag.download_file': { paramsTuple?: []; params?: {} }
    'rag.get_active_jobs': { paramsTuple?: []; params?: {} }
    'rag.get_failed_jobs': { paramsTuple?: []; params?: {} }
    'rag.cleanup_failed_jobs': { paramsTuple?: []; params?: {} }
    'rag.cancel_all_jobs': { paramsTuple?: []; params?: {} }
    'rag.get_job_status': { paramsTuple?: []; params?: {} }
    'rag.scan_and_sync': { paramsTuple?: []; params?: {} }
    'rag.reembed_all': { paramsTuple?: []; params?: {} }
    'rag.reset_and_rebuild': { paramsTuple?: []; params?: {} }
    'rag.estimate_batch': { paramsTuple?: []; params?: {} }
    'rag.policy_prompt_state': { paramsTuple?: []; params?: {} }
    'rag.health': { paramsTuple?: []; params?: {} }
    'rag.get_knowledge_collections': { paramsTuple?: []; params?: {} }
    'rag.update_file_collection': { paramsTuple?: []; params?: {} }
    'rag.set_file_active': { paramsTuple?: []; params?: {} }
    'rag.rename_knowledge_collection': { paramsTuple?: []; params?: {} }
    'rag.delete_knowledge_collection': { paramsTuple?: []; params?: {} }
    'rag.set_knowledge_collection_active': { paramsTuple?: []; params?: {} }
    'system.get_debug_info': { paramsTuple?: []; params?: {} }
    'system.get_system_info': { paramsTuple?: []; params?: {} }
    'system.get_internet_status': { paramsTuple?: []; params?: {} }
    'system.get_services': { paramsTuple?: []; params?: {} }
    'system.affect_service': { paramsTuple?: []; params?: {} }
    'system.install_service': { paramsTuple?: []; params?: {} }
    'system.force_reinstall_service': { paramsTuple?: []; params?: {} }
    'system.uninstall_service': { paramsTuple?: []; params?: {} }
    'system.check_service_updates': { paramsTuple?: []; params?: {} }
    'system.preflight_check': { paramsTuple?: []; params?: {} }
    'system.suggest_custom_port': { paramsTuple?: []; params?: {} }
    'system.preflight_custom_app': { paramsTuple?: []; params?: {} }
    'system.create_custom_app': { paramsTuple?: []; params?: {} }
    'system.update_custom_app': { paramsTuple?: []; params?: {} }
    'system.update_custom_app_pull_latest': { paramsTuple?: []; params?: {} }
    'system.delete_custom_app': { paramsTuple?: []; params?: {} }
    'system.get_custom_app': { paramsTuple: [ParamValue]; params: {'name': ParamValue} }
    'system.create_link_tile': { paramsTuple?: []; params?: {} }
    'system.update_link_tile': { paramsTuple?: []; params?: {} }
    'system.delete_link_tile': { paramsTuple?: []; params?: {} }
    'system.set_service_custom_url': { paramsTuple?: []; params?: {} }
    'system.get_service_logs': { paramsTuple: [ParamValue]; params: {'name': ParamValue} }
    'system.get_service_stats': { paramsTuple: [ParamValue]; params: {'name': ParamValue} }
    'system.get_available_versions': { paramsTuple: [ParamValue]; params: {'name': ParamValue} }
    'system.update_service': { paramsTuple?: []; params?: {} }
    'system.set_service_auto_update': { paramsTuple?: []; params?: {} }
    'system.get_app_auto_update_status': { paramsTuple?: []; params?: {} }
    'system.get_content_auto_update_status': { paramsTuple?: []; params?: {} }
    'system.subscribe_to_release_notes': { paramsTuple?: []; params?: {} }
    'system.check_latest_version': { paramsTuple?: []; params?: {} }
    'system.request_system_update': { paramsTuple?: []; params?: {} }
    'system.get_system_update_status': { paramsTuple?: []; params?: {} }
    'system.get_system_update_logs': { paramsTuple?: []; params?: {} }
    'system.get_auto_update_status': { paramsTuple?: []; params?: {} }
    'settings.get_setting': { paramsTuple?: []; params?: {} }
    'settings.update_setting': { paramsTuple?: []; params?: {} }
    'zim.list': { paramsTuple?: []; params?: {} }
    'zim.list_remote': { paramsTuple?: []; params?: {} }
    'zim.list_catalog_languages': { paramsTuple?: []; params?: {} }
    'zim.list_curated_categories': { paramsTuple?: []; params?: {} }
    'zim.download_remote': { paramsTuple?: []; params?: {} }
    'zim.download_category_tier': { paramsTuple?: []; params?: {} }
    'zim.upload': { paramsTuple?: []; params?: {} }
    'zim.get_wikipedia_state': { paramsTuple?: []; params?: {} }
    'zim.select_wikipedia': { paramsTuple?: []; params?: {} }
    'zim.list_custom_libraries': { paramsTuple?: []; params?: {} }
    'zim.add_custom_library': { paramsTuple?: []; params?: {} }
    'zim.remove_custom_library': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'zim.browse_library': { paramsTuple?: []; params?: {} }
    'zim.rescan_library': { paramsTuple?: []; params?: {} }
    'zim.delete': { paramsTuple: [ParamValue]; params: {'filename': ParamValue} }
    'creator_packs.index': { paramsTuple?: []; params?: {} }
    'creator_packs.install': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'creator_packs.uninstall': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'benchmark.run': { paramsTuple?: []; params?: {} }
    'benchmark.run_system': { paramsTuple?: []; params?: {} }
    'benchmark.run_ai': { paramsTuple?: []; params?: {} }
    'benchmark.results': { paramsTuple?: []; params?: {} }
    'benchmark.latest': { paramsTuple?: []; params?: {} }
    'benchmark.show': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'benchmark.submit': { paramsTuple?: []; params?: {} }
    'benchmark.update_builder_tag': { paramsTuple?: []; params?: {} }
    'benchmark.comparison': { paramsTuple?: []; params?: {} }
    'benchmark.status': { paramsTuple?: []; params?: {} }
    'benchmark.rerun_banner': { paramsTuple?: []; params?: {} }
    'benchmark.settings': { paramsTuple?: []; params?: {} }
    'benchmark.update_settings': { paramsTuple?: []; params?: {} }
    'drug_reference.index': { paramsTuple?: []; params?: {} }
    'drug_reference.interactions': { paramsTuple?: []; params?: {} }
    'drug_reference.show': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'drug_reference.search': { paramsTuple?: []; params?: {} }
    'drug_reference.status': { paramsTuple?: []; params?: {} }
    'drug_reference.interactions_api': { paramsTuple?: []; params?: {} }
    'drug_reference.download': { paramsTuple?: []; params?: {} }
    'drug_reference.ingest': { paramsTuple?: []; params?: {} }
    'drug_reference.reset_ingest': { paramsTuple?: []; params?: {} }
    'drug_reference.uninstall': { paramsTuple?: []; params?: {} }
    'drug_reference.ingest_log': { paramsTuple?: []; params?: {} }
    'conditions.index': { paramsTuple?: []; params?: {} }
    'conditions.show': { paramsTuple: [ParamValue]; params: {'slug': ParamValue} }
    'conditions.drugs_api': { paramsTuple?: []; params?: {} }
  }
  GET: {
    'event_stream': { paramsTuple?: []; params?: {} }
    'home.index': { paramsTuple?: []; params?: {} }
    'home.home': { paramsTuple?: []; params?: {} }
    'chats.inertia': { paramsTuple?: []; params?: {} }
    'maps.index': { paramsTuple?: []; params?: {} }
    'supply_depot.index': { paramsTuple?: []; params?: {} }
    'easy_setup.index': { paramsTuple?: []; params?: {} }
    'easy_setup.complete': { paramsTuple?: []; params?: {} }
    'easy_setup.list_curated_categories': { paramsTuple?: []; params?: {} }
    'settings.system': { paramsTuple?: []; params?: {} }
    'settings.legal': { paramsTuple?: []; params?: {} }
    'settings.maps': { paramsTuple?: []; params?: {} }
    'settings.models': { paramsTuple?: []; params?: {} }
    'settings.update': { paramsTuple?: []; params?: {} }
    'settings.zim': { paramsTuple?: []; params?: {} }
    'settings.zim_remote': { paramsTuple?: []; params?: {} }
    'settings.creator_packs': { paramsTuple?: []; params?: {} }
    'settings.benchmark': { paramsTuple?: []; params?: {} }
    'settings.support': { paramsTuple?: []; params?: {} }
    'settings.advanced': { paramsTuple?: []; params?: {} }
    'docs.show': { paramsTuple: [ParamValue]; params: {'slug': ParamValue} }
    'maps.list_regions': { paramsTuple?: []; params?: {} }
    'maps.styles': { paramsTuple?: []; params?: {} }
    'maps.list_curated_collections': { paramsTuple?: []; params?: {} }
    'maps.global_map_info': { paramsTuple?: []; params?: {} }
    'maps.list_countries': { paramsTuple?: []; params?: {} }
    'maps.list_country_groups': { paramsTuple?: []; params?: {} }
    'maps.list_markers': { paramsTuple?: []; params?: {} }
    'docs.list': { paramsTuple?: []; params?: {} }
    'downloads.index': { paramsTuple?: []; params?: {} }
    'downloads.filetype': { paramsTuple: [ParamValue]; params: {'filetype': ParamValue} }
    'open_api.spec': { paramsTuple?: []; params?: {} }
    'open_api.reference': { paramsTuple?: []; params?: {} }
    'open_api.standalone': { paramsTuple?: []; params?: {} }
    'ollama.available_models': { paramsTuple?: []; params?: {} }
    'ollama.installed_models': { paramsTuple?: []; params?: {} }
    'ollama.remote_status': { paramsTuple?: []; params?: {} }
    'nomad_md.show': { paramsTuple?: []; params?: {} }
    'chats.index': { paramsTuple?: []; params?: {} }
    'chats.show': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'chats.suggestions': { paramsTuple?: []; params?: {} }
    'rag.get_stored_files': { paramsTuple?: []; params?: {} }
    'rag.get_file_warnings': { paramsTuple?: []; params?: {} }
    'rag.get_file_content': { paramsTuple?: []; params?: {} }
    'rag.download_file': { paramsTuple?: []; params?: {} }
    'rag.get_active_jobs': { paramsTuple?: []; params?: {} }
    'rag.get_failed_jobs': { paramsTuple?: []; params?: {} }
    'rag.get_job_status': { paramsTuple?: []; params?: {} }
    'rag.policy_prompt_state': { paramsTuple?: []; params?: {} }
    'rag.health': { paramsTuple?: []; params?: {} }
    'rag.get_knowledge_collections': { paramsTuple?: []; params?: {} }
    'system.get_debug_info': { paramsTuple?: []; params?: {} }
    'system.get_system_info': { paramsTuple?: []; params?: {} }
    'system.get_internet_status': { paramsTuple?: []; params?: {} }
    'system.get_services': { paramsTuple?: []; params?: {} }
    'system.preflight_check': { paramsTuple?: []; params?: {} }
    'system.suggest_custom_port': { paramsTuple?: []; params?: {} }
    'system.get_custom_app': { paramsTuple: [ParamValue]; params: {'name': ParamValue} }
    'system.get_service_logs': { paramsTuple: [ParamValue]; params: {'name': ParamValue} }
    'system.get_service_stats': { paramsTuple: [ParamValue]; params: {'name': ParamValue} }
    'system.get_available_versions': { paramsTuple: [ParamValue]; params: {'name': ParamValue} }
    'system.get_app_auto_update_status': { paramsTuple?: []; params?: {} }
    'system.get_content_auto_update_status': { paramsTuple?: []; params?: {} }
    'system.check_latest_version': { paramsTuple?: []; params?: {} }
    'system.get_system_update_status': { paramsTuple?: []; params?: {} }
    'system.get_system_update_logs': { paramsTuple?: []; params?: {} }
    'system.get_auto_update_status': { paramsTuple?: []; params?: {} }
    'settings.get_setting': { paramsTuple?: []; params?: {} }
    'zim.list': { paramsTuple?: []; params?: {} }
    'zim.list_remote': { paramsTuple?: []; params?: {} }
    'zim.list_catalog_languages': { paramsTuple?: []; params?: {} }
    'zim.list_curated_categories': { paramsTuple?: []; params?: {} }
    'zim.get_wikipedia_state': { paramsTuple?: []; params?: {} }
    'zim.list_custom_libraries': { paramsTuple?: []; params?: {} }
    'zim.browse_library': { paramsTuple?: []; params?: {} }
    'creator_packs.index': { paramsTuple?: []; params?: {} }
    'benchmark.results': { paramsTuple?: []; params?: {} }
    'benchmark.latest': { paramsTuple?: []; params?: {} }
    'benchmark.show': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'benchmark.comparison': { paramsTuple?: []; params?: {} }
    'benchmark.status': { paramsTuple?: []; params?: {} }
    'benchmark.rerun_banner': { paramsTuple?: []; params?: {} }
    'benchmark.settings': { paramsTuple?: []; params?: {} }
    'drug_reference.index': { paramsTuple?: []; params?: {} }
    'drug_reference.interactions': { paramsTuple?: []; params?: {} }
    'drug_reference.show': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'drug_reference.search': { paramsTuple?: []; params?: {} }
    'drug_reference.status': { paramsTuple?: []; params?: {} }
    'drug_reference.interactions_api': { paramsTuple?: []; params?: {} }
    'drug_reference.ingest_log': { paramsTuple?: []; params?: {} }
    'conditions.index': { paramsTuple?: []; params?: {} }
    'conditions.show': { paramsTuple: [ParamValue]; params: {'slug': ParamValue} }
    'conditions.drugs_api': { paramsTuple?: []; params?: {} }
  }
  HEAD: {
    'event_stream': { paramsTuple?: []; params?: {} }
    'home.index': { paramsTuple?: []; params?: {} }
    'home.home': { paramsTuple?: []; params?: {} }
    'chats.inertia': { paramsTuple?: []; params?: {} }
    'maps.index': { paramsTuple?: []; params?: {} }
    'supply_depot.index': { paramsTuple?: []; params?: {} }
    'easy_setup.index': { paramsTuple?: []; params?: {} }
    'easy_setup.complete': { paramsTuple?: []; params?: {} }
    'easy_setup.list_curated_categories': { paramsTuple?: []; params?: {} }
    'settings.system': { paramsTuple?: []; params?: {} }
    'settings.legal': { paramsTuple?: []; params?: {} }
    'settings.maps': { paramsTuple?: []; params?: {} }
    'settings.models': { paramsTuple?: []; params?: {} }
    'settings.update': { paramsTuple?: []; params?: {} }
    'settings.zim': { paramsTuple?: []; params?: {} }
    'settings.zim_remote': { paramsTuple?: []; params?: {} }
    'settings.creator_packs': { paramsTuple?: []; params?: {} }
    'settings.benchmark': { paramsTuple?: []; params?: {} }
    'settings.support': { paramsTuple?: []; params?: {} }
    'settings.advanced': { paramsTuple?: []; params?: {} }
    'docs.show': { paramsTuple: [ParamValue]; params: {'slug': ParamValue} }
    'maps.list_regions': { paramsTuple?: []; params?: {} }
    'maps.styles': { paramsTuple?: []; params?: {} }
    'maps.list_curated_collections': { paramsTuple?: []; params?: {} }
    'maps.global_map_info': { paramsTuple?: []; params?: {} }
    'maps.list_countries': { paramsTuple?: []; params?: {} }
    'maps.list_country_groups': { paramsTuple?: []; params?: {} }
    'maps.list_markers': { paramsTuple?: []; params?: {} }
    'docs.list': { paramsTuple?: []; params?: {} }
    'downloads.index': { paramsTuple?: []; params?: {} }
    'downloads.filetype': { paramsTuple: [ParamValue]; params: {'filetype': ParamValue} }
    'open_api.spec': { paramsTuple?: []; params?: {} }
    'open_api.reference': { paramsTuple?: []; params?: {} }
    'open_api.standalone': { paramsTuple?: []; params?: {} }
    'ollama.available_models': { paramsTuple?: []; params?: {} }
    'ollama.installed_models': { paramsTuple?: []; params?: {} }
    'ollama.remote_status': { paramsTuple?: []; params?: {} }
    'nomad_md.show': { paramsTuple?: []; params?: {} }
    'chats.index': { paramsTuple?: []; params?: {} }
    'chats.show': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'chats.suggestions': { paramsTuple?: []; params?: {} }
    'rag.get_stored_files': { paramsTuple?: []; params?: {} }
    'rag.get_file_warnings': { paramsTuple?: []; params?: {} }
    'rag.get_file_content': { paramsTuple?: []; params?: {} }
    'rag.download_file': { paramsTuple?: []; params?: {} }
    'rag.get_active_jobs': { paramsTuple?: []; params?: {} }
    'rag.get_failed_jobs': { paramsTuple?: []; params?: {} }
    'rag.get_job_status': { paramsTuple?: []; params?: {} }
    'rag.policy_prompt_state': { paramsTuple?: []; params?: {} }
    'rag.health': { paramsTuple?: []; params?: {} }
    'rag.get_knowledge_collections': { paramsTuple?: []; params?: {} }
    'system.get_debug_info': { paramsTuple?: []; params?: {} }
    'system.get_system_info': { paramsTuple?: []; params?: {} }
    'system.get_internet_status': { paramsTuple?: []; params?: {} }
    'system.get_services': { paramsTuple?: []; params?: {} }
    'system.preflight_check': { paramsTuple?: []; params?: {} }
    'system.suggest_custom_port': { paramsTuple?: []; params?: {} }
    'system.get_custom_app': { paramsTuple: [ParamValue]; params: {'name': ParamValue} }
    'system.get_service_logs': { paramsTuple: [ParamValue]; params: {'name': ParamValue} }
    'system.get_service_stats': { paramsTuple: [ParamValue]; params: {'name': ParamValue} }
    'system.get_available_versions': { paramsTuple: [ParamValue]; params: {'name': ParamValue} }
    'system.get_app_auto_update_status': { paramsTuple?: []; params?: {} }
    'system.get_content_auto_update_status': { paramsTuple?: []; params?: {} }
    'system.check_latest_version': { paramsTuple?: []; params?: {} }
    'system.get_system_update_status': { paramsTuple?: []; params?: {} }
    'system.get_system_update_logs': { paramsTuple?: []; params?: {} }
    'system.get_auto_update_status': { paramsTuple?: []; params?: {} }
    'settings.get_setting': { paramsTuple?: []; params?: {} }
    'zim.list': { paramsTuple?: []; params?: {} }
    'zim.list_remote': { paramsTuple?: []; params?: {} }
    'zim.list_catalog_languages': { paramsTuple?: []; params?: {} }
    'zim.list_curated_categories': { paramsTuple?: []; params?: {} }
    'zim.get_wikipedia_state': { paramsTuple?: []; params?: {} }
    'zim.list_custom_libraries': { paramsTuple?: []; params?: {} }
    'zim.browse_library': { paramsTuple?: []; params?: {} }
    'creator_packs.index': { paramsTuple?: []; params?: {} }
    'benchmark.results': { paramsTuple?: []; params?: {} }
    'benchmark.latest': { paramsTuple?: []; params?: {} }
    'benchmark.show': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'benchmark.comparison': { paramsTuple?: []; params?: {} }
    'benchmark.status': { paramsTuple?: []; params?: {} }
    'benchmark.rerun_banner': { paramsTuple?: []; params?: {} }
    'benchmark.settings': { paramsTuple?: []; params?: {} }
    'drug_reference.index': { paramsTuple?: []; params?: {} }
    'drug_reference.interactions': { paramsTuple?: []; params?: {} }
    'drug_reference.show': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'drug_reference.search': { paramsTuple?: []; params?: {} }
    'drug_reference.status': { paramsTuple?: []; params?: {} }
    'drug_reference.interactions_api': { paramsTuple?: []; params?: {} }
    'drug_reference.ingest_log': { paramsTuple?: []; params?: {} }
    'conditions.index': { paramsTuple?: []; params?: {} }
    'conditions.show': { paramsTuple: [ParamValue]; params: {'slug': ParamValue} }
    'conditions.drugs_api': { paramsTuple?: []; params?: {} }
  }
  POST: {
    'subscribe': { paramsTuple?: []; params?: {} }
    'unsubscribe': { paramsTuple?: []; params?: {} }
    'easy_setup.refresh_manifests': { paramsTuple?: []; params?: {} }
    'collection_updates.check_for_updates': { paramsTuple?: []; params?: {} }
    'collection_updates.apply_update': { paramsTuple?: []; params?: {} }
    'collection_updates.apply_all_updates': { paramsTuple?: []; params?: {} }
    'maps.fetch_latest_collections': { paramsTuple?: []; params?: {} }
    'maps.download_base_assets': { paramsTuple?: []; params?: {} }
    'maps.setup_world_basemap': { paramsTuple?: []; params?: {} }
    'maps.download_remote': { paramsTuple?: []; params?: {} }
    'maps.download_remote_preflight': { paramsTuple?: []; params?: {} }
    'maps.download_collection': { paramsTuple?: []; params?: {} }
    'maps.download_global_map': { paramsTuple?: []; params?: {} }
    'maps.extract_preflight': { paramsTuple?: []; params?: {} }
    'maps.extract_region': { paramsTuple?: []; params?: {} }
    'maps.create_marker': { paramsTuple?: []; params?: {} }
    'downloads.cancel_job': { paramsTuple: [ParamValue]; params: {'jobId': ParamValue} }
    'downloads.retry_job': { paramsTuple: [ParamValue]; params: {'jobId': ParamValue} }
    'ollama.chat': { paramsTuple?: []; params?: {} }
    'ollama.dispatch_model_download': { paramsTuple?: []; params?: {} }
    'ollama.unload_chat_models': { paramsTuple?: []; params?: {} }
    'ollama.configure_remote': { paramsTuple?: []; params?: {} }
    'chats.store': { paramsTuple?: []; params?: {} }
    'chats.add_message': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'rag.upload': { paramsTuple?: []; params?: {} }
    'rag.embed_file': { paramsTuple?: []; params?: {} }
    'rag.scan_and_sync': { paramsTuple?: []; params?: {} }
    'rag.reembed_all': { paramsTuple?: []; params?: {} }
    'rag.reset_and_rebuild': { paramsTuple?: []; params?: {} }
    'rag.estimate_batch': { paramsTuple?: []; params?: {} }
    'rag.update_file_collection': { paramsTuple?: []; params?: {} }
    'rag.set_file_active': { paramsTuple?: []; params?: {} }
    'rag.rename_knowledge_collection': { paramsTuple?: []; params?: {} }
    'rag.delete_knowledge_collection': { paramsTuple?: []; params?: {} }
    'rag.set_knowledge_collection_active': { paramsTuple?: []; params?: {} }
    'system.affect_service': { paramsTuple?: []; params?: {} }
    'system.install_service': { paramsTuple?: []; params?: {} }
    'system.force_reinstall_service': { paramsTuple?: []; params?: {} }
    'system.uninstall_service': { paramsTuple?: []; params?: {} }
    'system.check_service_updates': { paramsTuple?: []; params?: {} }
    'system.preflight_custom_app': { paramsTuple?: []; params?: {} }
    'system.create_custom_app': { paramsTuple?: []; params?: {} }
    'system.update_custom_app_pull_latest': { paramsTuple?: []; params?: {} }
    'system.create_link_tile': { paramsTuple?: []; params?: {} }
    'system.update_service': { paramsTuple?: []; params?: {} }
    'system.set_service_auto_update': { paramsTuple?: []; params?: {} }
    'system.subscribe_to_release_notes': { paramsTuple?: []; params?: {} }
    'system.request_system_update': { paramsTuple?: []; params?: {} }
    'zim.download_remote': { paramsTuple?: []; params?: {} }
    'zim.download_category_tier': { paramsTuple?: []; params?: {} }
    'zim.upload': { paramsTuple?: []; params?: {} }
    'zim.select_wikipedia': { paramsTuple?: []; params?: {} }
    'zim.add_custom_library': { paramsTuple?: []; params?: {} }
    'zim.rescan_library': { paramsTuple?: []; params?: {} }
    'creator_packs.install': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'benchmark.run': { paramsTuple?: []; params?: {} }
    'benchmark.run_system': { paramsTuple?: []; params?: {} }
    'benchmark.run_ai': { paramsTuple?: []; params?: {} }
    'benchmark.submit': { paramsTuple?: []; params?: {} }
    'benchmark.update_builder_tag': { paramsTuple?: []; params?: {} }
    'benchmark.update_settings': { paramsTuple?: []; params?: {} }
    'drug_reference.download': { paramsTuple?: []; params?: {} }
    'drug_reference.ingest': { paramsTuple?: []; params?: {} }
    'drug_reference.reset_ingest': { paramsTuple?: []; params?: {} }
    'drug_reference.uninstall': { paramsTuple?: []; params?: {} }
  }
  PATCH: {
    'maps.update_marker': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'settings.update_setting': { paramsTuple?: []; params?: {} }
  }
  DELETE: {
    'maps.delete_marker': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'maps.delete': { paramsTuple: [ParamValue]; params: {'filename': ParamValue} }
    'downloads.remove_job': { paramsTuple: [ParamValue]; params: {'jobId': ParamValue} }
    'ollama.delete_model': { paramsTuple?: []; params?: {} }
    'chats.destroy_all': { paramsTuple?: []; params?: {} }
    'chats.destroy': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'rag.delete_file': { paramsTuple?: []; params?: {} }
    'rag.cleanup_failed_jobs': { paramsTuple?: []; params?: {} }
    'rag.cancel_all_jobs': { paramsTuple?: []; params?: {} }
    'system.delete_custom_app': { paramsTuple?: []; params?: {} }
    'system.delete_link_tile': { paramsTuple?: []; params?: {} }
    'zim.remove_custom_library': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'zim.delete': { paramsTuple: [ParamValue]; params: {'filename': ParamValue} }
    'creator_packs.uninstall': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
  }
  PUT: {
    'nomad_md.update': { paramsTuple?: []; params?: {} }
    'chats.update': { paramsTuple: [ParamValue]; params: {'id': ParamValue} }
    'system.update_custom_app': { paramsTuple?: []; params?: {} }
    'system.update_link_tile': { paramsTuple?: []; params?: {} }
    'system.set_service_custom_url': { paramsTuple?: []; params?: {} }
  }
}
declare module '@adonisjs/core/types/http' {
  export interface RoutesList extends ScannedRoutes {}
}