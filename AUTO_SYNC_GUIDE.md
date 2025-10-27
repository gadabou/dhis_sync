# Guide de la Synchronisation Automatique DHIS2

## Résumé de l'implémentation

J'ai créé une fonctionnalité complète de synchronisation automatique pour votre application DHIS2. Voici ce qui a été implémenté :

## 🏗️ Architecture créée

### 1. Services dans `dhis_app/services/auto_sync/`

#### **change_detector.py**
- Détecte les changements sur l'instance DHIS2 source
- Surveille les métadonnées (organisationUnits, dataElements, programs, etc.)
- Surveille les données (aggregate, events, tracker)
- Utilise l'API DHIS2 avec filtre `lastUpdated`
- Stocke les timestamps de dernière vérification en cache

#### **lifecycle_manager.py**
- Gère le cycle de vie des synchronisations
- **Premier lancement** : Métadonnées puis Données (ordre respecté)
- **Synchronisations suivantes** : Uniquement les changements détectés
- Gestion des erreurs avec cooldown automatique
- Throttling (limite de synchronisations par heure)

#### **scheduler.py**
- Scheduler singleton pour gérer toutes les configurations
- Un thread par configuration active
- Monitoring périodique selon l'intervalle configuré
- Démarrage/arrêt dynamique via l'interface web

#### **tasks.py**
- Tâches asynchrones pour exécution en arrière-plan
- Support threading natif Python (actuel)
- Code Celery prêt (commenté, à activer si besoin)

### 2. Vues dans `dhis_app/views/auto_sync.py`

- **auto_sync_settings** : Configuration des paramètres
- **start_auto_sync** : Démarrer la synchronisation automatique
- **stop_auto_sync** : Arrêter la synchronisation
- **restart_auto_sync** : Redémarrer
- **trigger_sync_now** : Déclencher une synchronisation immédiate
- **auto_sync_dashboard** : Dashboard de monitoring
- **API endpoints** : Statut et contrôle via REST

### 3. URLs ajoutées dans `dhis_app/urls.py`

```python
# Interface web
/auto-sync/dashboard/                          # Dashboard global
/configurations/<id>/auto-sync/settings/       # Paramètres
/configurations/<id>/auto-sync/start/          # Démarrer
/configurations/<id>/auto-sync/stop/           # Arrêter
/configurations/<id>/auto-sync/restart/        # Redémarrer
/configurations/<id>/auto-sync/trigger/        # Sync immédiate

# API REST
/api/auto-sync/<id>/status/                    # Statut d'une config
/api/auto-sync/status/                         # Statut de toutes
/api/auto-sync/cleanup/                        # Nettoyer threads morts
```

### 4. Templates HTML créés

- `templates/dhis_app/auto_sync/settings.html` : Page de configuration
- `templates/dhis_app/auto_sync/dashboard.html` : Dashboard de monitoring

## 🚀 Comment utiliser

### Méthode 1 : Via l'interface web

1. **Créer une configuration de synchronisation** avec `execution_mode='automatic'`

2. **Accéder aux paramètres Auto-Sync** :
   - Depuis la page de détail de la configuration
   - Ou directement via `/configurations/<id>/auto-sync/settings/`

3. **Configurer les paramètres** :
   - Activer la synchronisation automatique
   - Définir l'intervalle de vérification (ex: 300 secondes = 5 minutes)
   - Choisir les ressources à surveiller (métadonnées, données)
   - Configurer les limites de sécurité

4. **Démarrer** :
   - Cliquer sur "Démarrer" dans les contrôles
   - Le système démarre un thread de monitoring

5. **Monitoring** :
   - Accéder au dashboard : `/auto-sync/dashboard/`
   - Voir l'état de toutes les configurations
   - Contrôler chaque configuration individuellement

### Méthode 2 : Via code Python

```python
from dhis_app.services.auto_sync import start_auto_sync, stop_auto_sync

# Démarrer pour une configuration spécifique
start_auto_sync(sync_config_id=1)

# Démarrer pour toutes les configs en mode automatique
start_auto_sync()

# Arrêter
stop_auto_sync(sync_config_id=1)
```

## 📋 Fonctionnement détaillé

### Premier lancement (après création de la configuration)

1. Le système détecte que c'est le premier lancement
2. **Étape 1** : Synchronisation complète des métadonnées
3. **Étape 2** : Synchronisation complète des données
4. L'état est marqué comme "initial sync done"

### Synchronisations automatiques suivantes

1. **Monitoring périodique** :
   - Le scheduler vérifie les changements selon l'intervalle
   - Exemple : toutes les 5 minutes

2. **Détection de changements** :
   - Utilise l'API DHIS2 avec `lastUpdated` filter
   - Compare avec la dernière vérification

3. **Synchronisation ciblée** :
   - Si métadonnées modifiées → sync métadonnées
   - Si données modifiées → sync données
   - Respecte l'ordre si nécessaire

4. **Mise à jour des timestamps** :
   - Après succès, enregistre le timestamp de vérification

## ⚙️ Paramètres configurables

### Paramètres de base (model `AutoSyncSettings`)

```python
is_enabled = True/False                    # Activer/désactiver
check_interval = 300                       # Intervalle en secondes (min: 60)
immediate_sync = True/False                # Sync immédiate ou attendre delay
delay_before_sync = 30                     # Délai avant sync (secondes)
```

### Surveillance

```python
monitor_metadata = True/False              # Surveiller les métadonnées
monitor_data_values = True/False           # Surveiller les données
metadata_resources = []                    # Ressources spécifiques à surveiller
exclude_resources = []                     # Ressources à exclure
```

### Sécurité

```python
max_sync_per_hour = 10                     # Limite de syncs par heure
cooldown_after_error = 1800                # Cooldown après erreur (secondes)
```

### Notifications

```python
notify_on_change = True/False              # Notifier lors de détection
notify_on_sync_complete = True/False       # Notifier fin de sync
```

## 🔧 Configuration recommandée

### Pour environnement de développement

```python
check_interval = 300          # 5 minutes
immediate_sync = True
max_sync_per_hour = 20
cooldown_after_error = 300    # 5 minutes
```

### Pour environnement de production

```python
check_interval = 600          # 10 minutes
immediate_sync = False        # Attendre un délai
delay_before_sync = 60        # 1 minute
max_sync_per_hour = 10
cooldown_after_error = 1800   # 30 minutes
```

## 🎯 Cas d'usage

### Cas 1 : Synchronisation en temps quasi-réel

```python
# Configuration
check_interval = 60           # Vérifier toutes les minutes
immediate_sync = True         # Sync immédiate
monitor_metadata = True
monitor_data_values = True
```

**Usage** : Environnement où les données doivent être synchronisées rapidement

### Cas 2 : Synchronisation périodique légère

```python
# Configuration
check_interval = 3600         # Vérifier toutes les heures
immediate_sync = False
delay_before_sync = 300       # Attendre 5 minutes
```

**Usage** : Environnement avec modifications peu fréquentes

### Cas 3 : Synchronisation des métadonnées uniquement

```python
# Configuration
monitor_metadata = True
monitor_data_values = False
check_interval = 1800         # 30 minutes
```

**Usage** : Quand seules les métadonnées changent (configuration, structure)

## 📊 Dashboard et Monitoring

### Dashboard Auto-Sync (`/auto-sync/dashboard/`)

Affiche :
- Nombre total de configurations automatiques
- Nombre de configurations actives
- Nombre de threads actifs
- Liste de toutes les configurations avec leur état
- Contrôles rapides (démarrer/arrêter/synchroniser)
- Auto-refresh toutes les 10 secondes

### Indicateurs

- 🟢 **Actif** : Le thread de monitoring est en cours
- 🔴 **Arrêté** : Le monitoring est arrêté
- 🔵 **Activé** : La configuration auto-sync est activée
- ⚠️ **Désactivé** : La configuration existe mais est désactivée
- ❌ **Non configuré** : Pas de paramètres auto-sync

## 🛡️ Gestion des erreurs

### Cooldown automatique

Lorsqu'une synchronisation échoue :
1. Le système entre en "cooldown"
2. Aucune nouvelle sync pendant la durée configurée
3. Après le cooldown, reprend normalement

### Throttling

Pour éviter la surcharge :
- Maximum de X syncs par heure (configurable)
- Au-delà, les nouvelles syncs attendent
- Compteur se réinitialise toutes les heures

### Logs détaillés

Tous les événements sont loggés :
```python
logger = logging.getLogger('dhis_app.services.auto_sync')
```

Niveaux :
- **INFO** : Démarrage, arrêt, syncs réussies
- **WARNING** : Throttling, ressources non disponibles
- **ERROR** : Échecs de sync, erreurs de connexion
- **DEBUG** : Détails de détection de changements

## 🔌 Intégration existante

Le système utilise les services existants :
- `SyncOrchestrator` : Pour orchestrer les synchronisations
- `MetadataSyncService` : Pour synchroniser les métadonnées
- `TrackerDataService`, `EventsDataService`, `AggregateDataService` : Pour les données
- Modèles existants : `SyncConfiguration`, `SyncJob`, `AutoSyncSettings`

## 📝 Prochaines étapes

1. **Tester la fonctionnalité** :
   ```bash
   python manage.py runserver
   ```
   Puis accéder à `/auto-sync/dashboard/`

2. **Créer une configuration automatique** :
   - Créer une `SyncConfiguration` avec `execution_mode='automatic'`
   - Configurer les paramètres auto-sync
   - Démarrer

3. **Observer les logs** :
   ```bash
   # Voir les logs en temps réel
   tail -f logs/dhis2_sync.log
   ```

4. **Optionnel - Migrer vers Celery** :
   - Décommenter les tâches Celery dans `tasks.py`
   - Configurer Celery et Celery Beat
   - Plus robuste pour la production

## 🚨 Points importants

1. **Le modèle `AutoSyncSettings` existe déjà** dans vos models
2. **Premier lancement** : Métadonnées PUIS Données (ordre automatique)
3. **Lancements suivants** : Uniquement les changements
4. **Thread-safe** : Utilise un scheduler singleton
5. **Cache Django** : Pour stocker les timestamps et états
6. **Pas de modification BDD** : Utilise les models existants

## 📞 Support

- Documentation complète : `dhis_app/services/auto_sync/README.md`
- Logs : `logger = logging.getLogger('dhis_app.services.auto_sync')`
- Dashboard : `/auto-sync/dashboard/`
- API statut : `/api/auto-sync/status/`

---

**Voilà ! Votre système de synchronisation automatique est prêt à être utilisé ! 🎉**
