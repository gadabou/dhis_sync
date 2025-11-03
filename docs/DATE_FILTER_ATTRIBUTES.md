# Configuration des Attributs de Filtre de Date

## Vue d'ensemble

Le système de configuration des attributs de filtre de date permet de spécifier, pour chaque programme DHIS2, quel attribut ou dataElement doit être utilisé pour filtrer les données par date lors de la récupération via les API DHIS2.

## Problématique résolue

Avant cette fonctionnalité, le filtre de date était codé en dur dans le code pour chaque programme. Cela nécessitait de modifier le code à chaque fois qu'on voulait ajouter ou modifier la configuration d'un programme.

Maintenant, la configuration est stockée en base de données et peut être gérée via l'interface d'administration Django.

## Modèle de données

### DateFilterAttribute

Le modèle `DateFilterAttribute` contient les champs suivants :

- **dhis2_instance** : Instance DHIS2 concernée (ForeignKey vers DHIS2Instance)
- **filter_type** : Type de filtre ('event' ou 'tracker')
- **program_uid** : UID du programme DHIS2 (pour events) ou du trackedEntityType (pour tracker)
- **program_name** : Nom du programme (optionnel, pour information)
- **date_attribute_uid** : UID de l'attribut/dataElement à utiliser pour filtrer par date
- **date_attribute_name** : Nom de l'attribut (optionnel, pour information)
- **default_to_created** : Utiliser 'created' comme valeur par défaut si l'attribut n'est pas disponible
- **is_active** : Configuration active/inactive

## Utilisation

### 1. Via l'interface d'administration Django

Accédez à `/admin/dhis_app/datefilterattribute/` pour gérer les configurations.

#### Créer une nouvelle configuration :

1. Cliquez sur "Ajouter Attribut de filtre de date"
2. Sélectionnez l'instance DHIS2
3. Choisissez le type de filtre (event ou tracker)
4. Entrez l'UID du programme
5. Entrez l'UID de l'attribut/dataElement à utiliser pour le filtre de date
6. Optionnellement, ajoutez les noms pour faciliter l'identification
7. Sauvegardez

### 2. Via la commande de management

#### Lister toutes les configurations :

```bash
python manage.py setup_date_filter_attributes --list
```

#### Migrer la configuration existante dans le code :

```bash
python manage.py setup_date_filter_attributes --migrate-existing
```

Cette commande migre automatiquement la configuration codée en dur dans `get_events` vers la base de données.

#### Créer une nouvelle configuration :

```bash
python manage.py setup_date_filter_attributes \
    --instance "IH PROD" \
    --program-uid "siupB4uk4O2" \
    --program-name "Fiche récapitulative des visites des ASC" \
    --attribute-uid "RlquY86kI66" \
    --attribute-name "Date de rapport" \
    --filter-type event
```

Si l'option `--instance` est omise, la configuration sera créée pour toutes les instances sources.

### 3. Via le code Python

```python
from dhis_app.models import DHIS2Instance, DateFilterAttribute

# Récupérer une instance
instance = DHIS2Instance.objects.get(name="IH PROD")

# Créer une configuration pour un programme event
DateFilterAttribute.objects.create(
    dhis2_instance=instance,
    filter_type='event',
    program_uid='siupB4uk4O2',
    program_name='Fiche récapitulative des visites des ASC',
    date_attribute_uid='RlquY86kI66',
    date_attribute_name='Date de rapport',
    default_to_created=True,
    is_active=True
)

# Créer une configuration pour un programme tracker
DateFilterAttribute.objects.create(
    dhis2_instance=instance,
    filter_type='tracker',
    program_uid='IpHINAT79UW',
    program_name='Child Programme',
    date_attribute_uid='A03MvHHogjR',
    date_attribute_name='Birth date',
    default_to_created=True,
    is_active=True
)
```

## Fonctionnement technique

### Méthode `get_date_filter_attribute`

La méthode `DHIS2Instance.get_date_filter_attribute(program_uid, filter_type)` est utilisée par `get_events` et `get_tracked_entity_instances` pour récupérer l'attribut de filtre configuré.

```python
# Exemple d'utilisation dans get_events
dateAttributFilter = self.get_date_filter_attribute(program_uid=program, filter_type='event')
```

### Comportement par défaut

Si aucune configuration n'est trouvée pour un programme :
- Pour `get_events` : utilise 'created' par défaut
- Pour `get_tracked_entity_instances` : si l'attribut retourné est 'created', utilise `lastUpdatedStartDate`/`lastUpdatedEndDate` comme fallback

### Méthodes refactorisées

#### `get_events`

Avant :
```python
config = [
    {
        "programId": 'siupB4uk4O2',
        "programName": 'Fiche récapitulative des visites des ASC',
        "reportDate": 'RlquY86kI66'
    }
]
selected = next((c for c in config if c["programId"] == program), None)
rDate = selected["reportDate"] if selected else 'created'
dateAttributFilter = rDate if (rDate != None and rDate != '') else 'created'
```

Après :
```python
# Récupérer l'attribut de filtre de date configuré pour ce programme
dateAttributFilter = self.get_date_filter_attribute(program_uid=program, filter_type='event')
```

#### `get_tracked_entity_instances`

Ajout de paramètres `startDate` et `endDate` pour permettre le filtrage par date personnalisé :

```python
def get_tracked_entity_instances(
    self,
    *,
    program: str,
    orgUnit: str,
    startDate: Optional[str] = None,  # Nouveau
    endDate: Optional[str] = None,    # Nouveau
    ...
)
```

## Exemples de configurations

### Programme Event

```python
DateFilterAttribute(
    dhis2_instance=instance,
    filter_type='event',
    program_uid='siupB4uk4O2',
    program_name='Fiche récapitulative des visites des ASC',
    date_attribute_uid='RlquY86kI66',
    date_attribute_name='Date de rapport'
)
```

Résultat dans l'API :
```python
params = {
    "filter": [
        "RlquY86kI66:GE:2024-01-01",
        "RlquY86kI66:LE:2024-12-31"
    ]
}
```

### Programme Tracker

```python
DateFilterAttribute(
    dhis2_instance=instance,
    filter_type='tracker',
    program_uid='IpHINAT79UW',
    program_name='Child Programme',
    date_attribute_uid='A03MvHHogjR',
    date_attribute_name='Birth date'
)
```

Résultat dans l'API :
```python
params = {
    "filter": [
        "A03MvHHogjR:GE:2024-01-01",
        "A03MvHHogjR:LE:2024-12-31"
    ]
}
```

## Migration depuis l'ancien système

Pour migrer la configuration existante codée en dur vers la base de données :

```bash
python manage.py setup_date_filter_attributes --migrate-existing
```

Cette commande :
1. Lit la configuration existante dans le code
2. Crée les entrées correspondantes dans la base de données pour toutes les instances sources
3. Active automatiquement les configurations créées

## Bonnes pratiques

1. **Nommer clairement les configurations** : Utilisez les champs `program_name` et `date_attribute_name` pour faciliter l'identification
2. **Tester avant d'activer** : Créez d'abord la configuration avec `is_active=False`, testez, puis activez
3. **Une configuration par programme** : Ne créez qu'une seule configuration active par combinaison (instance, program_uid, filter_type)
4. **Documenter les attributs** : Ajoutez des commentaires ou notes pour expliquer pourquoi un attribut spécifique est utilisé

## Dépannage

### Aucune donnée retournée après configuration

Vérifiez que :
1. L'UID de l'attribut est correct
2. L'attribut existe dans le programme DHIS2
3. Les données ont effectivement cet attribut rempli
4. La configuration est active (`is_active=True`)

### L'ancien comportement est toujours actif

Assurez-vous que :
1. Les migrations ont été appliquées : `python manage.py migrate`
2. La configuration a été créée pour la bonne instance
3. Le serveur a été redémarré après la création de la configuration

### Vérifier quelle configuration est utilisée

Activez les logs de débogage et cherchez les messages de `get_date_filter_attribute` :

```python
import logging
logging.getLogger('dhis_app.models').setLevel(logging.DEBUG)
```

Vous verrez des messages comme :
```
INFO: Aucune configuration de filtre de date trouvée pour le programme siupB4uk4O2 (type: event). Utilisation de 'created' par défaut.
```
