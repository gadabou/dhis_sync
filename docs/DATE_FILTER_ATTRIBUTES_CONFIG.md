# Configuration des Filtres de Date - Guide Complet

## Vue d'ensemble

La fonctionnalité de configuration des filtres de date permet de gérer dynamiquement les attributs utilisés pour filtrer les données DHIS2 par date, sans modifier le code source. Cette configuration se fait via une interface web intuitive.

## Accès à la Page de Configuration

URL: `/dhis/date-filter-config/`

## Fonctionnement

### 1. Sélection de l'Instance Source

1. Accédez à la page de configuration
2. Sélectionnez une instance DHIS2 source dans la liste déroulante
3. Cliquez sur "Charger les Programmes"

### 2. Configuration des Programmes

Une fois l'instance sélectionnée, le système :

1. **Charge automatiquement tous les programmes** de l'instance DHIS2
2. **Détermine le type de chaque programme** :
   - `Event` : pour les programmes sans inscription (programType = WITHOUT_REGISTRATION)
   - `Tracker` : pour les programmes avec inscription (programType = WITH_REGISTRATION)
3. **Charge les attributs/dataElements de type date** disponibles pour chaque programme

### 3. Sélection des Attributs

Pour chaque programme :

- **Option par défaut** : `created` (date de création de l'entité)
- **Attributs personnalisés** : Liste des dataElements/attributs de type DATE, DATETIME ou TIME du programme

### 4. Sauvegarde

Cliquez sur "Sauvegarder les Configurations" pour enregistrer toutes les configurations en une seule fois.

## Architecture Technique

### API Endpoints

#### 1. GET `/dhis/api/programs/`

Récupère la liste des programmes d'une instance DHIS2.

**Paramètres** :
- `instance_id` : ID de l'instance DHIS2 source

**Réponse** :
```json
{
  "success": true,
  "programs": [
    {
      "uid": "siupB4uk4O2",
      "name": "Fiche récapitulative des visites des ASC",
      "programType": "WITHOUT_REGISTRATION",
      "filter_type": "event"
    }
  ]
}
```

#### 2. GET `/dhis/api/date-attributes/`

Récupère les attributs/dataElements de type date d'un programme.

**Paramètres** :
- `instance_id` : ID de l'instance DHIS2 source
- `program_uid` : UID du programme
- `filter_type` : Type de filtre ('event' ou 'tracker')

**Réponse** :
```json
{
  "success": true,
  "attributes": [
    {
      "uid": "RlquY86kI66",
      "name": "Date de rapport",
      "valueType": "DATE"
    }
  ]
}
```

#### 3. POST `/dhis/api/save-date-filter-configs/`

Sauvegarde les configurations des filtres de date.

**Paramètres** :
```json
{
  "instance_id": 1,
  "configs": [
    {
      "program_uid": "siupB4uk4O2",
      "program_name": "Fiche récapitulative des visites des ASC",
      "filter_type": "event",
      "date_attribute_uid": "RlquY86kI66",
      "date_attribute_name": "Date de rapport"
    }
  ]
}
```

**Réponse** :
```json
{
  "success": true,
  "message": "2 configuration(s) sauvegardée(s) avec succès"
}
```

### Modèle de Données

```python
class DateFilterAttribute(models.Model):
    dhis2_instance = ForeignKey(DHIS2Instance, limit_choices_to={'is_source': True})
    filter_type = CharField(choices=[('event', 'Événement'), ('tracker', 'Entité suivie')])
    program_uid = CharField(max_length=11)
    program_name = CharField(max_length=255, blank=True, null=True)
    date_attribute_uid = CharField(max_length=11)
    date_attribute_name = CharField(max_length=255, blank=True, null=True)
    default_to_created = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

### Contraintes

- **Unicité** : `(dhis2_instance, filter_type, program_uid)` doit être unique
- **Instance Source uniquement** : Seules les instances marquées comme `is_source=True` peuvent être configurées

## Utilisation Programmatique

### Méthode `get_date_filter_attribute`

```python
from dhis_app.models import DHIS2Instance

instance = DHIS2Instance.objects.get(name="IH PROD")

# Pour un programme event
date_attr = instance.get_date_filter_attribute(
    program_uid='siupB4uk4O2',
    filter_type='event'
)
# Retourne: 'RlquY86kI66' ou 'created' si non configuré

# Pour un programme tracker
date_attr = instance.get_date_filter_attribute(
    program_uid='IpHINAT79UW',
    filter_type='tracker'
)
```

### Intégration dans `get_events`

```python
# Récupération automatique de l'attribut configuré
dateAttributFilter = self.get_date_filter_attribute(program_uid=program, filter_type='event')

params = {
    "program": program,
    "orgUnit": orgUnit,
    "filter": [
        dateAttributFilter + ':GE:' + startDate,
        dateAttributFilter + ':LE:' + endDate
    ]
}
```

### Intégration dans `get_tracked_entity_instances`

```python
# Si startDate et endDate sont fournis
if startDate or endDate:
    dateAttributeUid = self.get_date_filter_attribute(program_uid=program, filter_type='tracker')

    # Appliquer les filtres sur l'attribut configuré
    if dateAttributeUid and dateAttributeUid != 'created':
        params["filter"] = [
            f"{dateAttributeUid}:GE:{startDate}",
            f"{dateAttributeUid}:LE:{endDate}"
        ]
```

## Cas d'Usage

### Cas 1 : Programme Event avec Date de Rapport Personnalisée

**Programme** : Fiche récapitulative des visites des ASC
**Type** : Event
**Attribut de date** : RlquY86kI66 (Date de rapport)

**Configuration** :
- Sélectionner l'instance
- Trouver le programme dans la liste
- Sélectionner "Date de rapport (DATE)" dans la liste déroulante
- Sauvegarder

**Résultat** : Les données seront filtrées sur la date de rapport au lieu de la date de création.

### Cas 2 : Programme Tracker avec Date de Naissance

**Programme** : Child Programme
**Type** : Tracker
**Attribut de date** : A03MvHHogjR (Birth date)

**Configuration** :
- Sélectionner l'instance
- Trouver le programme "Child Programme"
- Sélectionner "Birth date (DATE)" dans la liste déroulante
- Sauvegarder

**Résultat** : Les entités seront filtrées sur la date de naissance.

### Cas 3 : Utiliser la Date de Création par Défaut

**Programme** : N'importe quel programme
**Configuration** :
- Sélectionner "created (Par défaut)" dans la liste déroulante
- OU ne rien sélectionner (laisse vide)

**Résultat** : Utilisation de la date de création système.

## Migration depuis l'Ancien Système

L'ancien système utilisait une configuration codée en dur :

```python
# Ancien code (supprimé)
config = [
    {
        "programId": 'siupB4uk4O2',
        "programName": 'Fiche récapitulative des visites des ASC',
        "reportDate": 'RlquY86kI66'
    }
]
```

Cette configuration a été automatiquement migrée vers la base de données et peut maintenant être gérée via l'interface web.

## Administration Django

Les configurations peuvent également être gérées via l'interface d'administration Django :

URL: `/admin/dhis_app/datefilterattribute/`

**Fonctionnalités** :
- Créer/Modifier/Supprimer des configurations
- Filtrer par instance, type, date de création
- Exporter en CSV/JSON
- Rechercher par nom de programme, UID, attribut

## Dépannage

### Erreur : "Aucun programme trouvé"

**Cause** : L'instance DHIS2 ne répond pas ou n'a pas de programmes

**Solution** :
1. Vérifier la connectivité avec l'instance
2. Vérifier que l'instance a des programmes configurés
3. Vérifier les logs : `/dhis/logs/`

### Erreur : "Aucun attribut de date trouvé"

**Cause** : Le programme n'a pas de dataElements/attributs de type date

**Solution** :
1. Vérifier la configuration du programme dans DHIS2
2. Ajouter des dataElements de type DATE au programme
3. Utiliser "created" par défaut

### Les données ne sont pas filtrées correctement

**Cause** : L'attribut configuré n'est pas rempli dans les données

**Solution** :
1. Vérifier que les données ont l'attribut configuré
2. Tester avec un autre attribut
3. Revenir à "created" temporairement

## Bonnes Pratiques

1. **Toujours tester** après configuration avec une petite période
2. **Documenter** les choix d'attributs dans les noms des configurations
3. **Vérifier les données** avant de configurer des filtres personnalisés
4. **Utiliser `created` par défaut** si aucun attribut de date spécifique n'est pertinent
5. **Sauvegarder régulièrement** pour ne pas perdre les configurations

## Avantages

✅ **Interface intuitive** : Configuration via interface web, pas de code
✅ **Chargement automatique** : Tous les programmes et attributs sont récupérés automatiquement
✅ **Type auto-détecté** : Le système détermine automatiquement event vs tracker
✅ **Configuration par instance** : Chaque instance peut avoir sa propre configuration
✅ **Sauvegarde en lot** : Toutes les configurations sont sauvegardées en une seule fois
✅ **Pas de redémarrage** : Les modifications sont prises en compte immédiatement

## Support

Pour toute question ou problème :
- Consulter les logs : `/dhis/logs/`
- Vérifier l'admin Django : `/admin/dhis_app/datefilterattribute/`
- Contacter l'équipe technique
