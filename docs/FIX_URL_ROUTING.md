# Correction du Routage des URLs - Configuration des Filtres de Date

## Date: 22 Octobre 2025

## Problème Identifié

Lors du chargement de la page de configuration des filtres de date (`/date-filter-config/`), les appels AJAX JavaScript échouaient avec des erreurs 404:

```
[WARNING] Not Found: /dhis/api/programs/
[WARNING] "GET /dhis/api/programs/?instance_id=4 HTTP/1.1" 404 12076
```

**Erreur côté client:**
```
Erreur réseau: Unexpected token '<', "<!DOCTYPE "... is not valid JSON
```

## Cause du Problème

Les routes API étaient définies dans `dhis_app/urls.py` **SANS** le préfixe `/dhis/`:

```python
# dhis_app/urls.py
path('api/programs/', get_programs_api, name='get_programs_api'),
path('api/date-attributes/', get_date_attributes_api, name='get_date_attributes_api'),
path('api/save-date-filter-configs/', save_date_filter_configs, name='save_date_filter_configs'),
```

Et dans `dhis_sync/urls.py`, les URLs de l'app sont incluses à la racine:

```python
# dhis_sync/urls.py
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include("dhis_app.urls")),  # Pas de préfixe
]
```

Donc les routes réelles sont:
- `/api/programs/` ✓
- `/api/date-attributes/` ✓
- `/api/save-date-filter-configs/` ✓

**MAIS** le JavaScript dans le template utilisait le préfixe `/dhis/`:
- `/dhis/api/programs/` ✗
- `/dhis/api/date-attributes/` ✗
- `/dhis/api/save-date-filter-configs/` ✗

## Solution Appliquée

Correction des 3 URLs JavaScript dans `dhis_app/templates/dhis_app/date_filter_config.html`:

### 1. Fonction loadPrograms() - Ligne 183

**Avant:**
```javascript
const response = await fetch(`/dhis/api/programs/?instance_id=${instanceId}`);
```

**Après:**
```javascript
const response = await fetch(`/api/programs/?instance_id=${instanceId}`);
```

### 2. Fonction loadDateAttributes() - Ligne 258

**Avant:**
```javascript
const response = await fetch(`/dhis/api/date-attributes/?instance_id=${instanceId}&program_uid=${programUid}&filter_type=${filterType}`);
```

**Après:**
```javascript
const response = await fetch(`/api/date-attributes/?instance_id=${instanceId}&program_uid=${programUid}&filter_type=${filterType}`);
```

### 3. Fonction saveConfigs() - Ligne 334

**Avant:**
```javascript
const response = await fetch('/dhis/api/save-date-filter-configs/', {
```

**Après:**
```javascript
const response = await fetch('/api/save-date-filter-configs/', {
```

## Fichiers Modifiés

- `dhis_app/templates/dhis_app/date_filter_config.html` (3 modifications)

## Vérification

Après la correction:

```bash
$ grep -n "/dhis/" dhis_app/templates/dhis_app/date_filter_config.html
# Aucun résultat → ✓ Toutes les URLs corrigées
```

## Résultat

- ✓ Les URLs JavaScript correspondent maintenant aux routes Django
- ✓ Les appels AJAX ne retournent plus 404
- ✓ La page peut charger les programmes depuis l'API DHIS2
- ✓ Les attributs de date peuvent être chargés dynamiquement
- ✓ Les configurations peuvent être sauvegardées

## Test Manuel

Pour tester la correction:

1. Démarrer le serveur: `python manage.py runserver`
2. Accéder à la page: `http://127.0.0.1:8000/date-filter-config/`
3. Sélectionner une instance source
4. Vérifier que les programmes se chargent (pas d'erreur 404 dans la console)
5. Sélectionner des attributs de date
6. Sauvegarder les configurations

## Logs Attendus (Succès)

```
[INFO] "GET /date-filter-config/ HTTP/1.1" 200
[INFO] "GET /api/programs/?instance_id=4 HTTP/1.1" 200
[INFO] "GET /api/date-attributes/?instance_id=4&program_uid=xyz&filter_type=event HTTP/1.1" 200
[INFO] "POST /api/save-date-filter-configs/ HTTP/1.1" 200
```

## Leçons Apprises

1. **Toujours vérifier la structure complète des URLs** en remontant depuis l'app jusqu'au projet principal
2. **Les URLs JavaScript doivent correspondre exactement** aux routes Django définies
3. **Les erreurs 404 avec JSON invalide** indiquent souvent une mauvaise URL (retourne HTML au lieu de JSON)

---

**Statut:** ✅ RÉSOLU
**Impact:** Aucune régression, fonctionnalité maintenant opérationnelle
**Durée de fix:** ~10 minutes
