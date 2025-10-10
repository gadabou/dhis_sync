# Synchronisation Automatique DHIS2

## Vue d'ensemble

Le système de synchronisation automatique permet de détecter automatiquement les changements sur une instance DHIS2 source et de déclencher une synchronisation vers l'instance de destination sans intervention manuelle.

## Architecture

Le système est composé de plusieurs modules:

### 1. **change_detector.py** - Détection des changements
Surveille l'instance source pour détecter les modifications:
- Métadonnées (organisationUnits, dataElements, programs, etc.)
- Données agrégées (dataValues)
- Événements (events)
- Données tracker (trackedEntityInstances)

### 2. **lifecycle_manager.py** - Gestion du cycle de vie
Gère l'orchestration des synchronisations:
- **Premier lancement**: Métadonnées → Données (ordre respecté)
- **Synchronisations suivantes**: Uniquement les ressources modifiées
- Gestion des erreurs avec cooldown
- Throttling (limite de syncs par heure)

### 3. **scheduler.py** - Planification
Scheduler singleton qui gère l'exécution périodique:
- Un thread par configuration active
- Monitoring continu à intervalle configurable
- Démarrage/arrêt dynamique

### 4. **tasks.py** - Tâches asynchrones
Fonctions pour exécuter les synchronisations en arrière-plan:
- Déclenchement asynchrone de synchronisations
- Nettoyage des threads morts
- Support Celery (commenté, à activer si besoin)

## Utilisation

### Configuration initiale

1. **Créer une configuration de synchronisation** avec `execution_mode='automatic'`

2. **Configurer les paramètres de synchronisation automatique**:
   ```python
   from dhis_app.models import AutoSyncSettings

   auto_settings = AutoSyncSettings.objects.create(
       sync_config=ma_config,
       is_enabled=True,
       check_interval=300,  # 5 minutes
       monitor_metadata=True,
       monitor_data_values=True,
       max_sync_per_hour=10,
       cooldown_after_error=1800  # 30 minutes
   )
   ```

### Démarrage via l'interface web

1. Accéder aux **Paramètres Auto-Sync** d'une configuration
2. Activer la synchronisation automatique
3. Configurer les paramètres (intervalle, ressources surveillées, etc.)
4. Cliquer sur "Démarrer"

### Démarrage programmatique

```python
from dhis_app.services.auto_sync import start_auto_sync, stop_auto_sync

# Démarrer pour une configuration spécifique
start_auto_sync(sync_config_id=1)

# Démarrer pour toutes les configs actives
start_auto_sync()

# Arrêter une configuration
stop_auto_sync(sync_config_id=1)
```

### Dashboard

Le dashboard auto-sync (`/auto-sync/dashboard/`) affiche:
- Nombre total de configurations
- Configurations actives
- Threads actifs
- État de chaque configuration
- Contrôles rapides (démarrer/arrêter)

## Fonctionnement détaillé

### Premier lancement

Lors du premier lancement pour une nouvelle configuration:

1. **Détection de l'état initial**: Le système détecte qu'aucune synchronisation n'a eu lieu
2. **Synchronisation des métadonnées**:
   - Tous les types de métadonnées configurés sont synchronisés
   - L'ordre de dépendance est respecté
3. **Synchronisation des données**:
   - Après succès des métadonnées
   - Types de données selon la configuration (tracker, events, aggregate)
4. **Marquage de l'état**: Le système marque que la synchronisation initiale est complète

### Synchronisations suivantes

Pour les synchronisations suivantes:

1. **Monitoring périodique**:
   - Le scheduler vérifie les changements selon l'intervalle configuré
   - Utilise les timestamps `lastUpdated` de DHIS2

2. **Détection de changements**:
   - Compare avec la dernière vérification (stockée en cache)
   - Identifie les ressources modifiées

3. **Synchronisation ciblée**:
   - Synchronise uniquement les ressources modifiées
   - Métadonnées si nécessaire
   - Données modifiées (aggregate/events/tracker)

4. **Mise à jour des timestamps**:
   - Après succès, met à jour les timestamps de dernière vérification

## Paramètres de configuration

### Surveillance

- **check_interval**: Intervalle entre les vérifications (minimum 60s)
- **delay_before_sync**: Délai avant de démarrer une sync après détection
- **immediate_sync**: Démarrer immédiatement (ignore delay_before_sync)

### Ressources surveillées

- **monitor_metadata**: Surveiller les métadonnées
- **monitor_data_values**: Surveiller les données
- **metadata_resources**: Liste des ressources métadonnées spécifiques
- **exclude_resources**: Ressources à exclure

### Limites de sécurité

- **max_sync_per_hour**: Limite de synchronisations par heure (protection)
- **cooldown_after_error**: Temps d'attente après une erreur (en secondes)

### Notifications

- **notify_on_change**: Notifier lors de la détection de changements
- **notify_on_sync_complete**: Notifier à la fin de la synchronisation

## API REST

### Obtenir le statut

```bash
# Statut d'une configuration
GET /api/auto-sync/<config_id>/status/

# Statut de toutes les configurations
GET /api/auto-sync/status/
```

### Nettoyage des tâches

```bash
# Nettoyer les threads morts et redémarrer
POST /api/auto-sync/cleanup/
```

## Gestion des erreurs

### Cooldown après erreur

Lorsqu'une synchronisation échoue:
1. Le système entre en mode "cooldown"
2. Aucune nouvelle synchronisation n'est tentée pendant la durée configurée
3. Après le cooldown, les synchronisations reprennent normalement

### Throttling

Pour éviter une surcharge:
- Maximum de `max_sync_per_hour` synchronisations par heure
- Au-delà, les nouvelles synchronisations sont mises en attente
- Le compteur se réinitialise toutes les heures

### Retry automatique

Le `lifecycle_manager` gère automatiquement:
- Les erreurs temporaires (réseau, timeout)
- Le backoff exponentiel (via les jobs)
- La reprise après erreur

## Monitoring et logs

### Logs

Les logs sont écrits dans le logger Django:
```python
import logging
logger = logging.getLogger('dhis_app.services.auto_sync')
```

Niveaux de logs:
- **INFO**: Démarrage/arrêt, synchronisations réussies
- **WARNING**: Erreurs non critiques, throttling
- **ERROR**: Échecs de synchronisation, erreurs fatales
- **DEBUG**: Détails de la détection de changements

### Cache

Le système utilise le cache Django pour stocker:
- Timestamps de dernière vérification
- État du cycle de vie
- Compteurs de throttling
- État running/cooldown

Clés de cache: `dhis2_change_detector:*`, `auto_sync_lifecycle:*`

## Déploiement en production

### Recommandations

1. **Utiliser Celery pour la production**:
   - Décommenter les tâches Celery dans `tasks.py`
   - Configurer Celery Beat pour les tâches périodiques
   - Plus robuste que les threads Python

2. **Configurer un cache persistant**:
   - Redis recommandé (au lieu de cache mémoire)
   - Évite la perte d'état au redémarrage

3. **Monitoring externe**:
   - Vérifier que les threads sont actifs
   - Alertes si synchronisations échouent
   - Dashboard de métriques (Grafana, etc.)

4. **Ajuster les intervalles**:
   - `check_interval`: Selon la fréquence de modifications
   - `max_sync_per_hour`: Selon la charge serveur
   - `cooldown_after_error`: Selon les patterns d'erreur

### Démarrage automatique au boot

Créer un management command Django:

```python
# dhis_app/management/commands/start_auto_sync.py
from django.core.management.base import BaseCommand
from dhis_app.services.auto_sync import start_auto_sync

class Command(BaseCommand):
    help = 'Démarre la synchronisation automatique'

    def handle(self, *args, **options):
        start_auto_sync()  # Démarre toutes les configs actives
        self.stdout.write(self.style.SUCCESS('Auto-sync démarré'))
```

Puis dans systemd ou supervisord:
```bash
python manage.py start_auto_sync
```

## Dépannage

### Les synchronisations ne se déclenchent pas

1. Vérifier que `execution_mode='automatic'`
2. Vérifier que `auto_settings.is_enabled=True`
3. Vérifier les logs pour les erreurs
4. Vérifier le statut via le dashboard

### Threads morts

Si des threads sont "morts" mais toujours listés:
- Utiliser l'endpoint `/api/auto-sync/cleanup/`
- Ou redémarrer manuellement via le dashboard

### Synchronisations trop fréquentes

- Augmenter `check_interval`
- Réduire `max_sync_per_hour`
- Vérifier que les changements sont réels (pas de faux positifs)

### Erreurs de connexion

- Vérifier la connexion à l'instance source
- Augmenter `cooldown_after_error`
- Vérifier les credentials DHIS2

## Support

Pour toute question ou problème:
1. Consulter les logs Django
2. Vérifier le dashboard auto-sync
3. Tester manuellement via "Synchroniser maintenant"
4. Contacter le support technique

## Évolutions futures possibles

- [ ] Support webhooks DHIS2 (au lieu de polling)
- [ ] Notifications email/Slack
- [ ] Métriques détaillées (Prometheus)
- [ ] Interface de configuration avancée
- [ ] Historique des détections de changements
- [ ] Synchronisation différentielle optimisée
