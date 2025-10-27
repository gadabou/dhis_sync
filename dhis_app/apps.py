from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class DhisAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dhis_app'

    def ready(self):
        """
        Cette méthode est appelée au démarrage de Django.
        Elle démarre automatiquement la synchronisation automatique.
        """
        # Importer ici pour éviter les imports circulaires
        import sys

        # Ne pas exécuter lors des migrations ou autres commandes de gestion
        # Uniquement lors du démarrage du serveur
        if 'runserver' in sys.argv or 'gunicorn' in sys.argv[0]:
            try:
                # Import delayed pour éviter les problèmes au démarrage
                from django.core.cache import cache
                from .services.auto_sync.scheduler import start_auto_sync

                # Vérifier si on a déjà démarré (pour éviter le double démarrage avec le reloader)
                cache_key = 'auto_sync_started'
                if not cache.get(cache_key):
                    cache.set(cache_key, True, timeout=300)  # 5 minutes

                    # Attendre un peu que Django soit complètement démarré
                    import threading
                    import time

                    def delayed_start():
                        """Démarre l'auto-sync après un court délai"""
                        time.sleep(5)  # Attendre 5 secondes
                        try:
                            logger.info("🚀 Démarrage automatique de la synchronisation...")
                            start_auto_sync()  # Démarre toutes les configs actives
                            logger.info("✅ Synchronisation automatique démarrée avec succès")
                        except Exception as e:
                            logger.error(f"❌ Erreur lors du démarrage automatique: {e}", exc_info=True)

                    # Lancer dans un thread séparé pour ne pas bloquer le démarrage
                    thread = threading.Thread(target=delayed_start, daemon=True)
                    thread.start()

            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation de l'auto-sync: {e}", exc_info=True)
