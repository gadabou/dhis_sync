# Guide de dépannage - DHIS2 Sync Auto-Sync

## 🔴 Erreur: "No auto-sync settings configured"

### Symptômes
```bash
$ python manage.py start_auto_sync
Skipping "Local 97-94": No auto-sync settings configured
No configurations with enabled auto-sync found.
```

### Cause
La configuration existe et est en mode `automatic`, mais il manque l'objet `AutoSyncSettings` associé.

### Solution

#### Option 1: Via commande setup (Recommandé)
```bash
# Configurer avec des paramètres par défaut
python manage.py setup_auto_sync 3

# Avec options personnalisées
python manage.py setup_auto_sync 3 \
  --interval 600 \
  --no-immediate \
  --delay 60 \
  --max-per-hour 20
```

#### Option 2: Via interface web
1. Accédez à: http://localhost:8000/configurations/3/auto-sync/settings/
2. Configurez les paramètres
3. Activez la synchronisation automatique

#### Option 3: Via shell Django
```bash
python manage.py shell
```

```python
from dhis_app.models import SyncConfiguration, AutoSyncSettings

# Récupérer la configuration (remplacer 3 par votre ID)
config = SyncConfiguration.objects.get(id=3)

# Créer les paramètres auto-sync
AutoSyncSettings.objects.create(
    sync_config=config,
    is_enabled=True,
    check_interval=300,  # 5 minutes
    immediate_sync=True,
    monitor_metadata=True,
    monitor_data_values=True
)
```

### Vérification

Après configuration, vérifiez:

```bash
# Lister les configurations
python manage.py start_auto_sync --list

# Démarrer
python manage.py start_auto_sync

# Vérifier le statut
python manage.py start_auto_sync --status
```

---

## 🔴 Erreur: Configuration pas en mode "automatic"

### Symptômes
```bash
Configuration "Local 97-94" is not in automatic mode. Current mode: manual
```

### Solution

```python
from dhis_app.models import SyncConfiguration

config = SyncConfiguration.objects.get(id=3)
config.execution_mode = 'automatic'
config.save()
```

Ou via l'interface web en éditant la configuration.

---

## 🔴 Auto-sync ne démarre pas au démarrage de Django

### Vérifications

1. **Vérifier que la configuration est en mode automatic:**
```bash
python manage.py start_auto_sync --list
```

2. **Vérifier les logs:**
```bash
tail -f logs/dhis2_sync.log
```

Vous devriez voir:
```
🚀 Démarrage automatique de la synchronisation...
✓ Synchronisation automatique démarrée avec succès
```

3. **Vérifier que vous utilisez runserver:**
Le démarrage automatique ne fonctionne qu'avec:
- `python manage.py runserver`
- `gunicorn`

Pas avec:
- `python manage.py migrate`
- `python manage.py shell`
- Autres commandes de gestion

---

## 🔴 Threads ne s'arrêtent pas

### Solution

```bash
# Arrêter tous les threads
python manage.py stop_auto_sync

# Ou nettoyer via l'API
curl http://localhost:8000/api/auto-sync/cleanup/
```

Via Python:
```python
from dhis_app.services.auto_sync.scheduler import AutoSyncScheduler

scheduler = AutoSyncScheduler.get_instance()
scheduler.stop()  # Arrête tous les threads
```

---

## 🔴 Erreur: "Configuration is not active"

### Solution

```python
from dhis_app.models import SyncConfiguration

config = SyncConfiguration.objects.get(id=3)
config.is_active = True
config.save()
```

---

## 🔴 Redis/Celery ne se connecte pas

### Vérifications

1. **Redis est-il démarré?**
```bash
redis-cli ping
# Doit retourner: PONG
```

2. **Démarrer Redis:**
```bash
# Ubuntu/Debian
sudo systemctl start redis

# macOS
brew services start redis
```

3. **Utiliser le mode sans Celery:**
Le système fonctionne parfaitement sans Redis/Celery en utilisant des threads Python natifs:
```bash
./start_simple.sh
# ou
python manage.py runserver
```

---

## 🔴 Double démarrage des threads (reloader Django)

### Symptômes
Voir deux fois le message de démarrage dans les logs.

### Solution
C'est normal en développement avec `runserver`. Le système utilise un cache pour éviter de démarrer deux threads identiques.

Pas de problème, le deuxième démarrage est ignoré.

---

## 🔴 Les synchronisations ne se déclenchent pas

### Vérifications

1. **Le thread est-il actif?**
```bash
python manage.py start_auto_sync --status
```

2. **Y a-t-il des changements à synchroniser?**
Vérifiez les logs:
```bash
tail -f logs/auto_sync.log
```

Vous devriez voir:
```
[DEBUG] Détection des changements pour Local 97-94
[INFO] Aucun changement détecté
```

3. **La source DHIS2 est-elle accessible?**
Testez la connexion dans l'interface web.

4. **Vérifier les paramètres:**
```bash
python manage.py shell
```

```python
from dhis_app.models import AutoSyncSettings

settings = AutoSyncSettings.objects.get(sync_config_id=3)
print(f"Enabled: {settings.is_enabled}")
print(f"Interval: {settings.check_interval}s")
print(f"Monitor metadata: {settings.monitor_metadata}")
print(f"Monitor data: {settings.monitor_data_values}")
```

---

## 🔴 Erreur lors de la synchronisation

### Vérifications

1. **Consulter les logs détaillés:**
```bash
tail -f logs/dhis2_sync.log
tail -f logs/auto_sync.log
```

2. **Vérifier le cooldown:**
Après une erreur, le système entre en cooldown (par défaut 30 minutes).

Vérifier:
```python
from django.core.cache import cache
cooldown = cache.get('auto_sync_cooldown_3')  # 3 = config ID
print(f"Cooldown actif: {cooldown}")
```

Forcer la fin du cooldown:
```python
from django.core.cache import cache
cache.delete('auto_sync_cooldown_3')
```

3. **Throttling:**
Vérifier le nombre de syncs:
```python
from django.core.cache import cache
count = cache.get('auto_sync_count_3')  # 3 = config ID
print(f"Syncs cette heure: {count}")
```

---

## 📊 Commandes de diagnostic

```bash
# Lister toutes les configurations
python manage.py start_auto_sync --list

# Voir le statut des threads
python manage.py start_auto_sync --status

# Voir les logs en temps réel
tail -f logs/auto_sync.log

# Vérifier les configurations en base
python manage.py shell -c "
from dhis_app.models import SyncConfiguration, AutoSyncSettings
for c in SyncConfiguration.objects.all():
    print(f'{c.id}: {c.name} - {c.execution_mode}')
    try:
        s = c.auto_sync_settings
        print(f'  AutoSync: enabled={s.is_enabled}, interval={s.check_interval}s')
    except: print('  AutoSync: NOT CONFIGURED')
"
```

---

## 🆘 Support

Si le problème persiste:

1. **Collectez les informations:**
   - Logs: `logs/dhis2_sync.log` et `logs/auto_sync.log`
   - Configuration: `python manage.py start_auto_sync --list`
   - Statut: `python manage.py start_auto_sync --status`

2. **Consultez la documentation:**
   - [AUTO_SYNC_GUIDE.md](AUTO_SYNC_GUIDE.md)
   - [STARTUP_GUIDE.md](STARTUP_GUIDE.md)

3. **Redémarrez complètement:**
   ```bash
   python manage.py stop_auto_sync
   # Attendre 5 secondes
   python manage.py start_auto_sync
   ```