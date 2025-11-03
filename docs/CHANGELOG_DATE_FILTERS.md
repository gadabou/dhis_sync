# Changelog - Configuration des Filtres de Date

## Version 2.0 - Refactorisation Complète

### Date : 22 Octobre 2025

### 🎯 Objectif

Remplacer le système de configuration codé en dur par une interface web moderne permettant de configurer dynamiquement les attributs de filtre de date pour chaque programme DHIS2.

### ✨ Nouvelles Fonctionnalités

#### 1. Interface Web de Configuration
- **URL** : `/dhis/date-filter-config/`
- **Accès** : Depuis la page de détail d'une instance source
- **Fonctionnalités** :
  - Sélection d'instance source via dropdown
  - Chargement automatique de tous les programmes DHIS2
  - Détection automatique du type (Event/Tracker) depuis DHIS2
  - Chargement automatique des attributs/dataElements de type date
  - Configuration en lot (toutes les configurations en une seule sauvegarde)
  - Interface responsive Bootstrap 5

#### 2. APIs RESTful

**`GET /dhis/api/programs/`**
- Récupère tous les programmes d'une instance
- Détermine automatiquement le type (event/tracker)
- Paramètre : `instance_id`

**`GET /dhis/api/date-attributes/`**
- Récupère les attributs/dataElements de type date d'un programme
- Paramètres : `instance_id`, `program_uid`, `filter_type`
- Filtre les types : DATE, DATETIME, TIME

**`POST /dhis/api/save-date-filter-configs/`**
- Sauvegarde toutes les configurations en une transaction
- Supprime les anciennes configurations avant de créer les nouvelles
- Format JSON avec validation côté serveur

#### 3. Lien dans Page de Détail Instance

Ajout d'une carte "Filtres de Date" dans la page de détail d'une instance source :
- Visible uniquement pour les instances sources (`is_source=True`)
- Lien direct vers la page de configuration avec l'instance pré-sélectionnée
- Design cohérent avec les autres cartes (Test de Connexion, Métadonnées)

### 🔄 Modifications du Modèle

#### Modèle `DateFilterAttribute`

**Ajouts** :
- `limit_choices_to={'is_source': True}` sur `dhis2_instance`
- Validation pour s'assurer que l'instance est source

**Suppressions** :
- Champ `is_active` (toutes les configurations sont maintenant actives)
- Index sur `is_active`

**Contraintes maintenues** :
- Unicité sur `(dhis2_instance, filter_type, program_uid)`
- Indexes sur `dhis2_instance`, `filter_type`, `program_uid`

### 📁 Fichiers Modifiés/Créés/Supprimés

#### Créés
- `/dhis_app/views/date_filter_config.py` - 4 vues (1 page + 3 APIs)
- `/dhis_app/templates/dhis_app/date_filter_config.html` - Interface web complète
- `/docs/DATE_FILTER_ATTRIBUTES_CONFIG.md` - Documentation utilisateur
- `/docs/CHANGELOG_DATE_FILTERS.md` - Ce fichier

#### Modifiés
- `/dhis_app/models.py` :
  - `DateFilterAttribute.dhis2_instance` : ajout de `limit_choices_to`
  - `DateFilterAttribute.clean()` : validation instance source
  - `DHIS2Instance.get_date_filter_attribute()` : suppression filtre `is_active`
- `/dhis_app/urls.py` : 4 nouvelles routes
- `/dhis_app/admin.py` : simplification admin (suppression actions is_active)
- `/templates/dhis_app/dhis2_instance/detail.html` : ajout carte "Filtres de Date"

#### Supprimés
- `/dhis_app/management/commands/setup_date_filter_attributes.py`
- `/docs/DATE_FILTER_ATTRIBUTES.md` (remplacé par CONFIG.md)

### 📊 Migrations

**Migration 0006** : `alter_datefilterattribute_dhis2_instance`
- Modification du champ `dhis2_instance` pour limiter aux instances sources
- Pas de perte de données

### 🎨 Design

#### Interface Utilisateur
- Framework : Bootstrap 5
- Style : Moderne, responsive
- Couleurs : Gradient violet/bleu pour les boutons principaux
- Icons : Bootstrap Icons
- Composants :
  - Select dropdown pour instance
  - Table dynamique pour les programmes
  - Select dynamique pour les attributs de date
  - Messages de succès/erreur flottants

#### Workflow Utilisateur
```
1. Accès via page détail instance OU URL directe
   ↓
2. Sélection instance source
   ↓
3. Chargement automatique programmes (API)
   ↓
4. Pour chaque programme : chargement attributs date (API)
   ↓
5. Sélection attributs désirés
   ↓
6. Sauvegarde en lot (API)
   ↓
7. Confirmation + Redirection possible
```

### 🔧 Intégration

Les méthodes suivantes utilisent automatiquement les configurations :

#### `DHIS2Instance.get_events()`
```python
# Récupère automatiquement l'attribut configuré
dateAttributFilter = self.get_date_filter_attribute(program_uid=program, filter_type='event')

params = {
    "filter": [
        dateAttributFilter + ':GE:' + startDate,
        dateAttributFilter + ':LE:' + endDate
    ]
}
```

#### `DHIS2Instance.get_tracked_entity_instances()`
```python
# Support ajouté avec startDate/endDate
if startDate or endDate:
    dateAttributeUid = self.get_date_filter_attribute(program_uid=program, filter_type='tracker')

    if dateAttributeUid and dateAttributeUid != 'created':
        params["filter"] = [
            f"{dateAttributeUid}:GE:{startDate}",
            f"{dateAttributeUid}:LE:{endDate}"
        ]
```

### 📝 Migration depuis Ancien Système

L'ancien système utilisait une liste codée en dur :
```python
config = [
    {
        "programId": 'siupB4uk4O2',
        "programName": 'Fiche récapitulative des visites des ASC',
        "reportDate": 'RlquY86kI66'
    }
]
```

**Migration automatique effectuée** :
- 2 configurations créées (Local 87 et IH PROD)
- Programme : siupB4uk4O2
- Attribut : RlquY86kI66 (Date de rapport)

### 🚀 Avantages de la Nouvelle Version

| Avant | Après |
|-------|-------|
| Configuration codée en dur | Interface web intuitive |
| Modification du code requise | Configuration sans code |
| Redémarrage nécessaire | Changements immédiats |
| Commande CLI | Page web accessible |
| Type manuel | Type auto-détecté |
| Configuration par programme | Configuration en lot |
| Toutes instances | Instances sources uniquement |

### ✅ Tests Effectués

- ✅ Chargement des programmes depuis DHIS2
- ✅ Détection automatique du type (event/tracker)
- ✅ Chargement des attributs de date par programme
- ✅ Sauvegarde des configurations en lot
- ✅ Utilisation dans `get_events()`
- ✅ Utilisation dans `get_tracked_entity_instances()`
- ✅ Lien depuis page détail instance
- ✅ Migrations appliquées sans erreur
- ✅ Admin Django fonctionnel

### 🐛 Problèmes Résolus

1. **Import error** : Correction de l'import des vues depuis le package
2. **Champ is_active** : Supprimé comme demandé
3. **Migration incorrecte** : Recréée sans perte de données
4. **Grid layout** : Ajusté dynamiquement selon le type d'instance

### 📚 Documentation

- **Guide utilisateur** : `/docs/DATE_FILTER_ATTRIBUTES_CONFIG.md`
- **Changelog** : `/docs/CHANGELOG_DATE_FILTERS.md` (ce fichier)
- **Code documentation** : Docstrings dans tous les fichiers

### 🔮 Améliorations Futures Possibles

1. Export/Import des configurations
2. Historique des modifications
3. Validation des attributs (vérifier qu'ils existent dans DHIS2)
4. Prévisualisation des données avec le filtre
5. Clonage de configurations entre instances
6. Notifications de changements
7. API REST complète pour intégration externe

### 👥 Impact Utilisateur

**Administrateurs** :
- Configuration plus rapide et intuitive
- Pas besoin de connaissances en code
- Visualisation claire de toutes les configurations

**Développeurs** :
- Code plus propre et maintenable
- APIs bien documentées
- Séparation des responsabilités

**Système** :
- Performances identiques
- Pas de régression
- Meilleure traçabilité (created_at, updated_at)

### 📞 Support

En cas de problème :
1. Vérifier les logs Django
2. Consulter la documentation : `/docs/DATE_FILTER_ATTRIBUTES_CONFIG.md`
3. Vérifier l'admin Django : `/admin/dhis_app/datefilterattribute/`
4. Tester la connexion à l'instance DHIS2

---

**Développé par** : Claude Code
**Date de version** : 22 Octobre 2025
**Version** : 2.0.0
