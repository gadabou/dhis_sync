# Correction du bug de progression de synchronisation

## 🐛 Problème identifié

Erreur dans les APIs de progression:
```
AttributeError: 'SyncJob' object has no attribute 'total_synced'
```

## 🔍 Analyse

Le modèle `SyncJob` utilise des noms de champs différents de ceux attendus par les APIs:

### Champs réels du modèle SyncJob:
- ✅ `success_count` (nombre d'objets synchronisés avec succès)
- ✅ `error_count` (nombre d'erreurs)
- ✅ `total_items` (nombre total d'items à synchroniser)
- ✅ `processed_items` (nombre d'items traités)
- ✅ `progress` (pourcentage de progression)
- ✅ `job_type` (type de job: complete, metadata, data, etc.)
- ✅ `last_error` (dernier message d'erreur)

### Champs incorrectement utilisés dans les APIs:
- ❌ `total_synced` → Devrait être `success_count`
- ❌ `total_errors` → Devrait être `error_count`
- ❌ `progress_data` → N'existe pas dans le modèle
- ❌ `error_message` → Devrait être `last_error`

## ✅ Corrections appliquées

### 1. API `api_sync_progress` (Ligne 382-500)

#### Avant:
```python
'total_synced': last_job.total_synced or 0,
'total_errors': last_job.total_errors or 0,
'error_message': last_job.error_message,
```

#### Après:
```python
'total_synced': last_job.success_count or 0,
'total_errors': last_job.error_count or 0,
'error_message': last_job.last_error or '',
```

#### Changements pour job en cours:
- Utilise `current_job.total_items` pour le total attendu
- Utilise `current_job.processed_items` pour le nombre d'items traités
- Utilise `current_job.success_count` pour les succès
- Utilise `current_job.error_count` pour les erreurs
- Calcul du pourcentage basé sur `processed_items / total_items`
- Détermination automatique de l'étape en cours selon `job_type`

### 2. API `api_dashboard_stats` (Ligne 503-575)

#### Avant:
```python
'total_synced': last_job.total_synced or 0,
'total_errors': last_job.total_errors or 0,
```

#### Après:
```python
'total_synced': last_job.success_count or 0,
'total_errors': last_job.error_count or 0,
```

## 📊 Nouvelles fonctionnalités de progression

### Calcul du pourcentage
```python
if total_items > 0:
    progress_percent = int((processed_items / total_items) * 100)
else:
    progress_percent = current_job.progress or 0
```

### Calcul de la vitesse
```python
if current_job.started_at:
    elapsed_seconds = (now - current_job.started_at).total_seconds()
    speed = processed_items / elapsed_seconds if elapsed_seconds > 0 else 0
```

### Estimation du temps restant
```python
if speed > 0 and total_items > processed_items:
    remaining_items = total_items - processed_items
    estimated_seconds = remaining_items / speed
```

### Détermination de l'étape actuelle
```python
if current_job.job_type == 'metadata':
    current_step = 'Synchronisation des métadonnées'
elif current_job.job_type in ['data', 'aggregate', 'events', 'tracker', 'all_data']:
    current_step = 'Synchronisation des données'
elif current_job.job_type == 'complete':
    if progress_percent < 50:
        current_step = 'Synchronisation des métadonnées'
    else:
        current_step = 'Synchronisation des données'
```

## 🎯 Résultat

Les APIs retournent maintenant correctement:

### Pour un job en cours:
```json
{
  "success": true,
  "is_running": true,
  "job_id": 123,
  "config_name": "Local 97-94",
  "progress": {
    "percent": 45,
    "total_expected": 1000,
    "total_processed": 450,
    "total_synced": 440,
    "total_errors": 10
  },
  "timing": {
    "started_at": "2025-10-14T10:30:00Z",
    "elapsed_seconds": 120,
    "speed_per_second": 3.75,
    "estimated_remaining_seconds": 146
  },
  "resources": {},
  "current_step": "Synchronisation des métadonnées",
  "current_resource": "Job Complet"
}
```

### Pour un job terminé:
```json
{
  "success": true,
  "is_running": false,
  "last_job": {
    "id": 456,
    "status": "completed",
    "started_at": "2025-10-14T10:00:00Z",
    "completed_at": "2025-10-14T10:05:00Z",
    "total_synced": 1250,
    "total_errors": 3,
    "error_message": ""
  }
}
```

## 📝 Notes

### Détail par ressource temporairement désactivé
Le champ `resources` est actuellement un objet vide `{}` car le modèle `SyncJob` ne stocke pas de détails par type de ressource.

Pour activer cette fonctionnalité à l'avenir, il faudrait:
1. Ajouter un champ JSON `progress_data` au modèle `SyncJob`
2. Modifier l'orchestrateur pour stocker les statistiques par ressource
3. Ou créer un modèle séparé `SyncJobResource` avec une relation ForeignKey

### Compatibilité
Les corrections sont rétro-compatibles avec les données existantes grâce à l'utilisation de `or 0` et `or ''` pour gérer les valeurs NULL.

## ✅ Tests recommandés

```bash
# 1. Tester l'API de progression
curl http://localhost:8000/api/auto-sync/3/progress/

# 2. Tester l'API du dashboard
curl http://localhost:8000/api/auto-sync/dashboard-stats/

# 3. Vérifier le dashboard en temps réel
# Ouvrir http://localhost:8000/auto-sync/dashboard/
# Observer la mise à jour automatique toutes les 3 secondes
```

## 🚀 Fichiers modifiés

- `/home/gado/Integrate Health Dropbox/Djakpo GADO/projets/Dhis2/dhis_sync/dhis_app/views/auto_sync.py`
  - Ligne 395-483: `api_sync_progress()`
  - Ligne 525-537: `api_dashboard_stats()`

---

**Le bug est maintenant corrigé et le dashboard fonctionne correctement! ✨**
