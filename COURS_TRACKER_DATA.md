# Cours Complet sur les Données Tracker dans DHIS2

## Table des matières
1. [Introduction aux données Tracker](#1-introduction-aux-données-tracker)
2. [Architecture des données Tracker](#2-architecture-des-données-tracker)
3. [Composants principaux](#3-composants-principaux)
4. [Modèle de données Tracker](#4-modèle-de-données-tracker)
5. [API Tracker](#5-api-tracker)
6. [Synchronisation des données Tracker](#6-synchronisation-des-données-tracker)
7. [Cas d'usage pratiques](#7-cas-dusage-pratiques)
8. [Bonnes pratiques](#8-bonnes-pratiques)
9. [Exercices pratiques](#9-exercices-pratiques)

---

## 1. Introduction aux données Tracker

### 1.1 Qu'est-ce que les données Tracker?

Les **données Tracker** (ou données de suivi individuel) dans DHIS2 sont un type de données qui permettent de suivre des entités individuelles (personnes, animaux, équipements, etc.) dans le temps et à travers différents services ou événements.

**Différence avec les données agrégées:**

| Aspect | Données Agrégées | Données Tracker |
|--------|------------------|-----------------|
| **Granularité** | Résumé statistique | Niveau individuel |
| **Exemple** | "100 patients traités" | "Patient ID-123 traité le 15/10/2025" |
| **Anonymat** | Anonyme par nature | Identifiable (avec gestion de confidentialité) |
| **Suivi temporel** | Périodes fixes (mois, trimestre) | Chronologie événementielle |
| **Cas d'usage** | Rapports statistiques, indicateurs | Dossiers médicaux, suivi de cohorte |

### 1.2 Quand utiliser les données Tracker?

Utilisez les données Tracker pour:
- **Suivi longitudinal** de patients (VIH, tuberculose, maternité)
- **Gestion de cas** individuels
- **Programmes de vaccination** avec historique
- **Suivi d'équipements** ou de ressources
- **Gestion de la chaîne d'approvisionnement** au niveau unitaire
- **Registres** (naissances, décès, maladies à déclaration obligatoire)

### 1.3 Exemples concrets

**Exemple 1: Programme de suivi de grossesse**
- Entité: Une femme enceinte
- Inscription: Au programme de maternité
- Événements: Consultations prénatales (CPN1, CPN2, CPN3, accouchement, postnatal)

**Exemple 2: Gestion du VIH**
- Entité: Patient séropositif
- Inscription: Programme de prise en charge VIH
- Événements: Tests CD4, retraits ARV, consultations médicales

---

## 2. Architecture des données Tracker

### 2.1 Hiérarchie conceptuelle

```
Tracked Entity Type (Type d'entité suivie)
    └── Tracked Entity Instance (TEI) - Instance individuelle
        └── Enrollment (Inscription) - Inscription à un programme
            └── Program Stage (Étape de programme)
                └── Event (Événement) - Événement spécifique
                    └── Data Values (Valeurs de données)
```

### 2.2 Schéma visuel

```
┌─────────────────────────────────────────────────────────┐
│ Tracked Entity Type: "Personne"                         │
│  - Attributs: Nom, Date de naissance, Sexe, Adresse     │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ TEI #1: Marie Dupont (UID: AbCdEfGhIjK)                 │
│  - Nom: Marie Dupont                                    │
│  - Date naissance: 15/03/1990                           │
│  - Sexe: Féminin                                        │
└─────────────────────────────────────────────────────────┘
                    │
                    ├────────────────┬────────────────┐
                    ▼                ▼                ▼
        ┌───────────────────┐  ┌──────────────┐  ┌─────────────┐
        │ Enrollment 1      │  │ Enrollment 2 │  │ Enrollment 3│
        │ Programme: VIH    │  │ Programme:TB │  │ Programme:  │
        │ Date: 01/01/2024  │  │ Date: ...    │  │ Maternité   │
        └───────────────────┘  └──────────────┘  └─────────────┘
                    │
                    ▼
        ┌─────────────────────────────────┐
        │ Program Stage: "Consultation"   │
        └─────────────────────────────────┘
                    │
                    ├──────────┬──────────┬──────────┐
                    ▼          ▼          ▼          ▼
              ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
              │Event 1  │ │Event 2  │ │Event 3  │ │Event 4  │
              │15/01/24 │ │15/02/24 │ │15/03/24 │ │15/04/24 │
              └─────────┘ └─────────┘ └─────────┘ └─────────┘
                    │
                    ▼
              ┌───────────────────────┐
              │ Data Values           │
              │ - Poids: 65 kg        │
              │ - Tension: 120/80     │
              │ - CD4: 450            │
              └───────────────────────┘
```

---

## 3. Composants principaux

### 3.1 Tracked Entity Type (Type d'entité suivie)

**Définition:** Catégorie générique d'objets à suivre.

**Exemples:**
- Personne
- Animal (pour programmes vétérinaires)
- Équipement médical
- Véhicule

**Configuration dans DHIS2:**
```json
{
  "id": "nEenWmSyUEp",
  "name": "Personne",
  "description": "Individu suivi dans le système de santé",
  "allowAuditLog": true,
  "minAttributesRequiredToSearch": 1,
  "maxTeiCountToReturn": 50
}
```

### 3.2 Tracked Entity Attributes (Attributs)

**Définition:** Caractéristiques descriptives d'une entité suivie.

**Types d'attributs:**
- **Identifiants:** Numéro d'identification national, numéro de carte de santé
- **Démographiques:** Nom, prénom, date de naissance, sexe
- **Localisation:** Adresse, village, district
- **Contact:** Numéro de téléphone, email

**Exemple de configuration:**
```json
{
  "id": "w75KJ2mc4zz",
  "name": "Prénom",
  "valueType": "TEXT",
  "unique": false,
  "mandatory": true,
  "orgunitScope": false,
  "generated": false
}
```

**Types de valeurs (valueType):**
- `TEXT` - Texte libre
- `LONG_TEXT` - Texte long
- `NUMBER` - Nombre
- `INTEGER` - Entier
- `POSITIVE_INTEGER` - Entier positif
- `DATE` - Date
- `BOOLEAN` - Vrai/Faux
- `TRUE_ONLY` - Case à cocher
- `EMAIL` - Email
- `PHONE_NUMBER` - Numéro de téléphone
- `USERNAME` - Nom d'utilisateur
- `OPTION_SET` - Liste de choix prédéfinis
- `IMAGE` - Image
- `FILE_RESOURCE` - Fichier

### 3.3 Tracked Entity Instance (TEI)

**Définition:** Instance concrète d'une entité suivie (ex: un patient spécifique).

**Structure:**
```json
{
  "trackedEntityInstance": "AbCdEfGhIjK",
  "trackedEntityType": "nEenWmSyUEp",
  "orgUnit": "DiszpKrYNg8",
  "attributes": [
    {
      "attribute": "w75KJ2mc4zz",
      "value": "Marie"
    },
    {
      "attribute": "zDhUuAYrxNC",
      "value": "Dupont"
    },
    {
      "attribute": "NI0QRzJvQ0k",
      "value": "1990-03-15"
    }
  ],
  "enrollments": [...]
}
```

### 3.4 Program (Programme)

**Définition:** Cadre structuré pour le suivi d'entités dans un contexte spécifique.

**Types de programmes:**

1. **Programme WITH registration (avec inscription)**
   - Suivi longitudinal
   - Événements répétés
   - Exemple: Programme VIH, Maternité

2. **Programme WITHOUT registration (sans inscription)**
   - Événements isolés
   - Pas de suivi dans le temps
   - Exemple: Consultation externe unique, Vaccination ponctuelle

**Configuration:**
```json
{
  "id": "IpHINAT79UW",
  "name": "Programme de suivi VIH",
  "programType": "WITH_REGISTRATION",
  "trackedEntityType": "nEenWmSyUEp",
  "categoryCombo": "bjDvmb4bfuf",
  "version": 1,
  "enrollmentDateLabel": "Date de diagnostic",
  "incidentDateLabel": "Date d'infection présumée",
  "displayIncidentDate": true,
  "onlyEnrollOnce": true,
  "selectEnrollmentDatesInFuture": false,
  "selectIncidentDatesInFuture": false
}
```

### 3.5 Enrollment (Inscription)

**Définition:** Lien entre une TEI et un programme à une date donnée.

**Caractéristiques:**
- **enrollmentDate:** Date d'inscription au programme
- **incidentDate:** Date de l'événement déclencheur (ex: date de diagnostic)
- **status:** ACTIVE, COMPLETED, CANCELLED

**Exemple:**
```json
{
  "enrollment": "MnOoPqQrRsS",
  "trackedEntityInstance": "AbCdEfGhIjK",
  "program": "IpHINAT79UW",
  "orgUnit": "DiszpKrYNg8",
  "enrollmentDate": "2024-01-15",
  "incidentDate": "2024-01-10",
  "status": "ACTIVE",
  "events": [...]
}
```

### 3.6 Program Stage (Étape de programme)

**Définition:** Phase ou type d'événement dans un programme.

**Caractéristiques:**
- **repeatable:** Peut être répété (ex: consultations)
- **generatedByEnrollmentDate:** Généré automatiquement à l'inscription
- **autoGenerateEvent:** Créer automatiquement un événement
- **reportDateToUse:** Date à utiliser pour le rapport

**Exemple:**
```json
{
  "id": "A03MvHHogjR",
  "name": "Consultation de suivi",
  "description": "Consultation médicale de routine",
  "repeatable": true,
  "minDaysFromStart": 0,
  "standardInterval": 30,
  "programStageDataElements": [...]
}
```

### 3.7 Event (Événement)

**Définition:** Occurrence concrète d'une étape de programme.

**Statuts possibles:**
- `ACTIVE` - En cours
- `COMPLETED` - Terminé
- `VISITED` - Visité
- `SCHEDULE` - Planifié
- `OVERDUE` - En retard
- `SKIPPED` - Ignoré

**Structure:**
```json
{
  "event": "XyZ123456",
  "program": "IpHINAT79UW",
  "programStage": "A03MvHHogjR",
  "enrollment": "MnOoPqQrRsS",
  "orgUnit": "DiszpKrYNg8",
  "eventDate": "2024-02-15",
  "status": "COMPLETED",
  "completedDate": "2024-02-15",
  "dataValues": [
    {
      "dataElement": "qrur9Dvnyt5",
      "value": "65"
    },
    {
      "dataElement": "oZg33kd9taw",
      "value": "120/80"
    }
  ]
}
```

---

## 4. Modèle de données Tracker

### 4.1 Relations entre entités

```sql
-- Schéma relationnel simplifié

TrackedEntityType
    ├── TrackedEntityInstance (n)
    │       └── Enrollment (n)
    │               └── Event (n)
    │                       └── DataValue (n)
    │
    └── TrackedEntityAttribute (n)

Program
    ├── ProgramStage (n)
    │       └── ProgramStageDataElement (n)
    │
    ├── ProgramTrackedEntityAttribute (n)
    └── ProgramIndicator (n)
```

### 4.2 Exemple de données complètes

**Scénario:** Suivi d'une femme enceinte dans un programme de maternité

```json
{
  "trackedEntityInstances": [
    {
      "trackedEntityInstance": "TEI_001",
      "trackedEntityType": "Person",
      "orgUnit": "Centre_Sante_A",
      "attributes": [
        {
          "attribute": "first_name",
          "value": "Amina"
        },
        {
          "attribute": "last_name",
          "value": "Koné"
        },
        {
          "attribute": "date_of_birth",
          "value": "1995-06-10"
        },
        {
          "attribute": "phone_number",
          "value": "+22912345678"
        },
        {
          "attribute": "national_id",
          "value": "BJ199506101234"
        }
      ],
      "enrollments": [
        {
          "enrollment": "ENR_001",
          "program": "Maternite",
          "enrollmentDate": "2024-10-01",
          "incidentDate": "2024-09-25",
          "status": "ACTIVE",
          "events": [
            {
              "event": "EVT_001",
              "programStage": "CPN1",
              "eventDate": "2024-10-01",
              "status": "COMPLETED",
              "dataValues": [
                {
                  "dataElement": "poids",
                  "value": "62"
                },
                {
                  "dataElement": "tension_arterielle",
                  "value": "110/70"
                },
                {
                  "dataElement": "hemoglobine",
                  "value": "11.5"
                },
                {
                  "dataElement": "age_gestationnel",
                  "value": "12"
                }
              ]
            },
            {
              "event": "EVT_002",
              "programStage": "CPN2",
              "eventDate": "2024-11-15",
              "status": "COMPLETED",
              "dataValues": [
                {
                  "dataElement": "poids",
                  "value": "65"
                },
                {
                  "dataElement": "tension_arterielle",
                  "value": "115/75"
                },
                {
                  "dataElement": "hauteur_uterine",
                  "value": "22"
                },
                {
                  "dataElement": "age_gestationnel",
                  "value": "18"
                }
              ]
            },
            {
              "event": "EVT_003",
              "programStage": "CPN3",
              "eventDate": "2025-01-10",
              "status": "SCHEDULED"
            }
          ]
        }
      ]
    }
  ]
}
```

---

## 5. API Tracker

### 5.1 Endpoints principaux

#### 5.1.1 Récupération de TEI

**Endpoint moderne (DHIS2 >= 2.36):**
```
GET /api/trackedEntityInstances
```

**Paramètres principaux:**
- `trackedEntityType` - Type d'entité
- `ou` - Unité d'organisation
- `ouMode` - Mode de sélection (SELECTED, DESCENDANTS, CHILDREN, ACCESSIBLE)
- `program` - Filtre par programme
- `programStatus` - ACTIVE, COMPLETED, CANCELLED
- `followUp` - Suivi marqué (true/false)
- `lastUpdatedStartDate` - Date de mise à jour minimale
- `lastUpdatedEndDate` - Date de mise à jour maximale
- `fields` - Champs à retourner
- `page` - Numéro de page
- `pageSize` - Taille de page

**Exemple de requête:**
```bash
curl -u admin:district \
  "https://play.dhis2.org/demo/api/trackedEntityInstances?\
trackedEntityType=nEenWmSyUEp&\
ou=DiszpKrYNg8&\
ouMode=DESCENDANTS&\
program=IpHINAT79UW&\
programStatus=ACTIVE&\
fields=*&\
pageSize=50"
```

**Filtrage par attributs:**
```bash
# Recherche par nom
curl -u admin:district \
  "https://play.dhis2.org/demo/api/trackedEntityInstances?\
ou=DiszpKrYNg8&\
attribute=w75KJ2mc4zz:LIKE:Marie"

# Filtre multiple
curl -u admin:district \
  "https://play.dhis2.org/demo/api/trackedEntityInstances?\
ou=DiszpKrYNg8&\
attribute=w75KJ2mc4zz:EQ:Marie&\
attribute=zDhUuAYrxNC:EQ:Dupont"
```

**Opérateurs de filtrage:**
- `EQ` - Égal
- `LIKE` - Contient (insensible à la casse)
- `GT` - Supérieur à
- `GE` - Supérieur ou égal
- `LT` - Inférieur à
- `LE` - Inférieur ou égal
- `NE` - Différent de
- `IN` - Dans une liste (séparé par ;)

#### 5.1.2 Récupération d'events

**Endpoint:**
```
GET /api/events
```

**Paramètres:**
- `program` - UID du programme
- `programStage` - UID de l'étape
- `orgUnit` - Unité d'organisation
- `ouMode` - Mode organisationnel
- `startDate` - Date de début (format: YYYY-MM-DD)
- `endDate` - Date de fin
- `status` - Statut de l'événement
- `trackedEntityInstance` - UID de la TEI

**Exemple:**
```bash
curl -u admin:district \
  "https://play.dhis2.org/demo/api/events?\
program=IpHINAT79UW&\
orgUnit=DiszpKrYNg8&\
startDate=2024-01-01&\
endDate=2024-12-31&\
status=COMPLETED"
```

#### 5.1.3 Import de données Tracker (DHIS2 >= 2.36)

**Endpoint moderne:**
```
POST /api/tracker
```

**Payload:**
```json
{
  "trackedEntities": [...],
  "enrollments": [...],
  "events": [...],
  "relationships": [...]
}
```

**Paramètres d'import:**
- `importStrategy` - CREATE | UPDATE | CREATE_AND_UPDATE | DELETE
- `atomicMode` - ALL | OBJECT | NONE
- `async` - true | false (import asynchrone)
- `validationMode` - STRICT | SOFT (selon version)

**Exemple d'import avec Python (dhis2.py):**
```python
from dhis2 import Api

api = Api('https://play.dhis2.org/demo', 'admin', 'district')

# Import de TEI avec enrollments et events
bundle = {
    "trackedEntities": [
        {
            "trackedEntity": "new_tei_uid",
            "trackedEntityType": "nEenWmSyUEp",
            "orgUnit": "DiszpKrYNg8",
            "attributes": [
                {
                    "attribute": "w75KJ2mc4zz",
                    "value": "Marie"
                }
            ]
        }
    ],
    "enrollments": [
        {
            "enrollment": "new_enr_uid",
            "trackedEntity": "new_tei_uid",
            "program": "IpHINAT79UW",
            "orgUnit": "DiszpKrYNg8",
            "enrollmentDate": "2024-10-15",
            "incidentDate": "2024-10-10",
            "status": "ACTIVE"
        }
    ],
    "events": [
        {
            "event": "new_evt_uid",
            "enrollment": "new_enr_uid",
            "programStage": "A03MvHHogjR",
            "orgUnit": "DiszpKrYNg8",
            "eventDate": "2024-10-15",
            "status": "COMPLETED",
            "dataValues": [
                {
                    "dataElement": "qrur9Dvnyt5",
                    "value": "65"
                }
            ]
        }
    ]
}

response = api.post('tracker', data=bundle, params={
    'importStrategy': 'CREATE_AND_UPDATE',
    'atomicMode': 'NONE',
    'async': 'false'
})

print(response.json())
```

**Endpoint legacy (DHIS2 < 2.36):**
```
POST /api/trackedEntityInstances
POST /api/enrollments
POST /api/events
```

### 5.2 Exemple complet d'utilisation avec Python

**Fichier: `models.py` (extrait)**
```python
# Voir /home/gado/.../dhis_sync/dhis_app/models.py:320-354

def get_tracked_entity_instances(
    self,
    *,
    program: str,
    orgUnit: str,
    ouMode: str = "DESCENDANTS",
    paging: str = "false",
    lastUpdatedStartDate: Optional[str] = None,
    lastUpdatedEndDate: Optional[str] = None,
    trackedEntityType: Optional[str] = None,
    **attribute_filters
) -> Dict[str, Any]:
    """
    Récupère des TEI via /api/trackedEntityInstances.
    Requis: program, orgUnit
    """
    api = self.get_api_client()

    params = {
        "program": program,
        "orgUnit": orgUnit,
        "ouMode": ouMode,
        "paging": paging,
    }
    if lastUpdatedStartDate:
        params["lastUpdatedStartDate"] = lastUpdatedStartDate
    if lastUpdatedEndDate:
        params["lastUpdatedEndDate"] = lastUpdatedEndDate
    if trackedEntityType:
        params["trackedEntityType"] = trackedEntityType

    # Pass-through (ex: attribute=uid:EQ:value, etc.)
    params.update(attribute_filters or {})

    r = api.get("trackedEntityInstances", params=params)
    r.raise_for_status()
    return r.json()
```

**Utilisation:**
```python
from dhis_app.models import DHIS2Instance

# Récupérer instance source
source = DHIS2Instance.objects.get(name="Source DHIS2")

# Récupérer TEI pour un programme
result = source.get_tracked_entity_instances(
    program="IpHINAT79UW",
    orgUnit="DiszpKrYNg8",
    ouMode="DESCENDANTS",
    lastUpdatedStartDate="2024-01-01",
    paging="false"
)

teis = result.get('trackedEntityInstances', [])
print(f"Nombre de TEI: {len(teis)}")

for tei in teis:
    print(f"TEI: {tei['trackedEntityInstance']}")
    for enrollment in tei.get('enrollments', []):
        print(f"  Enrollment: {enrollment['enrollment']}")
        for event in enrollment.get('events', []):
            print(f"    Event: {event['event']} - {event['eventDate']}")
```

---

## 6. Synchronisation des données Tracker

### 6.1 Stratégie de synchronisation

**Approche recommandée:**

1. **Synchroniser les métadonnées d'abord**
   - Tracked Entity Types
   - Attributes
   - Programs
   - Program Stages
   - Data Elements

2. **Synchroniser les données Tracker**
   - Tracked Entity Instances
   - Enrollments
   - Events

### 6.2 Gestion des dépendances

**Ordre de synchronisation:**

```
1. TrackedEntityTypes
2. TrackedEntityAttributes
3. Programs
4. ProgramStages
5. ProgramStageDataElements
6. TrackedEntityInstances (données)
7. Enrollments (données)
8. Events (données)
```

### 6.3 Implémentation dans le projet

**Fichier: `models.py:522-640`**

```python
def import_tracker_bundle(
    self,
    *,
    tracked_entities: list[dict] | None = None,
    enrollments: list[dict] | None = None,
    events: list[dict] | None = None,
    relationships: list[dict] | None = None,
    strategy: str = "CREATE_AND_UPDATE",
    atomic_mode: str = "NONE",
    async_import: bool = False,
    validation_mode: str | None = None,
    **extra_params,
):
    """
    Importe un bundle tracker (TEI/Enrollments/Events/Relationships).

    Endpoint recommandé (DHIS2 >= 2.39/2.40): POST /api/tracker
    """
    api = self.get_api_client()

    # Construire le bundle
    bundle = {}
    if tracked_entities:
        bundle["trackedEntities"] = tracked_entities
    if enrollments:
        bundle["enrollments"] = enrollments
    if events:
        bundle["events"] = events
    if relationships:
        bundle["relationships"] = relationships

    params = {
        "importStrategy": strategy,
        "atomicMode": atomic_mode,
    }
    if async_import:
        params["async"] = "true"
    if validation_mode:
        params["validationMode"] = validation_mode
    params.update(extra_params or {})

    # Essayer endpoint moderne /tracker
    try:
        r = api.post("tracker", data=bundle, params=params)
        r.raise_for_status()
        return r.json()
    except Exception as primary_err:
        # Fallback legacy si /tracker indisponible
        logging.warning(f"/api/tracker indisponible, fallback legacy")
        # ... (voir code complet dans models.py)
```

### 6.4 Exemple d'utilisation

```python
from dhis_app.models import DHIS2Instance

# Instances source et destination
source = DHIS2Instance.objects.get(name="Source")
destination = DHIS2Instance.objects.get(name="Destination")

# 1. Récupérer données de la source
source_data = source.get_tracked_entity_instances(
    program="IpHINAT79UW",
    orgUnit="DiszpKrYNg8",
    lastUpdatedStartDate="2024-10-01",
    paging="false"
)

# 2. Préparer le bundle
teis = source_data.get('trackedEntityInstances', [])

tracked_entities = []
enrollments = []
events = []

for tei in teis:
    # Ajouter TEI
    tracked_entities.append({
        "trackedEntity": tei['trackedEntityInstance'],
        "trackedEntityType": tei['trackedEntityType'],
        "orgUnit": tei['orgUnit'],
        "attributes": tei.get('attributes', [])
    })

    # Ajouter enrollments et events
    for enr in tei.get('enrollments', []):
        enrollments.append({
            "enrollment": enr['enrollment'],
            "trackedEntity": tei['trackedEntityInstance'],
            "program": enr['program'],
            "orgUnit": enr['orgUnit'],
            "enrollmentDate": enr['enrollmentDate'],
            "incidentDate": enr.get('incidentDate'),
            "status": enr['status']
        })

        for evt in enr.get('events', []):
            events.append({
                "event": evt['event'],
                "enrollment": enr['enrollment'],
                "programStage": evt['programStage'],
                "orgUnit": evt['orgUnit'],
                "eventDate": evt['eventDate'],
                "status": evt['status'],
                "dataValues": evt.get('dataValues', [])
            })

# 3. Importer vers la destination
result = destination.import_tracker_bundle(
    tracked_entities=tracked_entities,
    enrollments=enrollments,
    events=events,
    strategy="CREATE_AND_UPDATE",
    atomic_mode="NONE"
)

# 4. Analyser le résultat
print(f"Status: {result.get('status')}")
if 'response' in result:
    stats = result['response'].get('importSummaries', {})
    print(f"Imported: {stats.get('imported', 0)}")
    print(f"Updated: {stats.get('updated', 0)}")
    print(f"Ignored: {stats.get('ignored', 0)}")
```

### 6.5 Gestion des erreurs et conflits

**Types d'erreurs courantes:**

1. **Erreurs de validation**
   - Attributs obligatoires manquants
   - Format de valeur incorrect
   - Valeurs hors plage

2. **Conflits d'unicité**
   - UID déjà existant
   - Attribut unique dupliqué

3. **Erreurs de référence**
   - Référence à un programme inexistant
   - Unité d'organisation invalide

**Stratégies de résolution:**

```python
def sync_with_error_handling(source, destination, program, org_unit):
    """Synchronisation avec gestion d'erreurs"""

    # Récupérer données
    data = source.get_tracked_entity_instances(
        program=program,
        orgUnit=org_unit,
        paging="false"
    )

    teis = data.get('trackedEntityInstances', [])

    success_count = 0
    error_count = 0
    errors = []

    # Importer par lots
    batch_size = 50
    for i in range(0, len(teis), batch_size):
        batch = teis[i:i+batch_size]

        try:
            # Préparer bundle (voir code précédent)
            tracked_entities, enrollments, events = prepare_bundle(batch)

            # Importer
            result = destination.import_tracker_bundle(
                tracked_entities=tracked_entities,
                enrollments=enrollments,
                events=events,
                strategy="CREATE_AND_UPDATE",
                atomic_mode="NONE"  # Permet import partiel
            )

            # Analyser résultat
            if result.get('status') == 'OK':
                success_count += len(batch)
            else:
                # Analyser conflits
                conflicts = result.get('response', {}).get('conflicts', [])
                for conflict in conflicts:
                    errors.append({
                        'object': conflict.get('object'),
                        'value': conflict.get('value'),
                        'message': conflict.get('errorMessage')
                    })
                error_count += len(conflicts)

        except Exception as e:
            logging.error(f"Erreur batch {i}: {e}")
            error_count += len(batch)
            errors.append({
                'batch': i,
                'message': str(e)
            })

    return {
        'success': success_count,
        'errors': error_count,
        'error_details': errors
    }
```

---

## 7. Cas d'usage pratiques

### 7.1 Cas 1: Suivi de patients VIH

**Contexte:**
- Programme de prise en charge VIH
- Suivi longitudinal des patients
- Événements: Consultations, tests CD4, retraits ARV

**Configuration:**

```json
{
  "program": {
    "name": "Programme VIH",
    "programType": "WITH_REGISTRATION",
    "trackedEntityType": "Personne",
    "programStages": [
      {
        "name": "Inscription",
        "repeatable": false,
        "generatedByEnrollmentDate": true
      },
      {
        "name": "Consultation médicale",
        "repeatable": true,
        "standardInterval": 30
      },
      {
        "name": "Test CD4",
        "repeatable": true,
        "standardInterval": 90
      },
      {
        "name": "Retrait ARV",
        "repeatable": true,
        "standardInterval": 30
      }
    ]
  }
}
```

**Éléments de données:**
- Poids
- Taille
- Tension artérielle
- CD4 count
- Charge virale
- Nombre de comprimés ARV
- Observance traitement

### 7.2 Cas 2: Registre de maternité

**Contexte:**
- Suivi de grossesse (CPN)
- Accouchement
- Suivi postnatal

**Étapes du programme:**

1. **Inscription** (CPN1)
   - Date de dernières règles
   - Date présumée d'accouchement
   - Antécédents médicaux
   - Groupe sanguin

2. **CPN2, CPN3, CPN4** (répétables)
   - Âge gestationnel
   - Poids
   - Tension artérielle
   - Hauteur utérine
   - Mouvements fœtaux
   - Examens biologiques

3. **Accouchement**
   - Date et heure
   - Type d'accouchement
   - Complications
   - Poids du nouveau-né
   - Score APGAR

4. **Suivi postnatal** (répétable)
   - Allaitement
   - Contrôle de la mère
   - Vaccination du bébé

### 7.3 Cas 3: Surveillance épidémiologique

**Contexte:**
- Déclaration de cas de maladie à déclaration obligatoire
- Traçabilité des cas contacts
- Suivi de l'évolution

**Programme:** Surveillance COVID-19

**Étapes:**
1. **Déclaration initiale**
   - Symptômes
   - Date d'apparition
   - Facteurs de risque

2. **Tests** (répétable)
   - Type de test
   - Résultat
   - Date du test

3. **Suivi clinique** (répétable)
   - Évolution des symptômes
   - Hospitalisation
   - Complications

4. **Clôture du cas**
   - Date de guérison/décès
   - Issue du cas

### 7.4 Cas 4: Gestion de la vaccination

**Programme:** Vaccination infantile

**Tracked Entity:** Enfant

**Attributs:**
- Nom, prénom
- Date de naissance
- Numéro de carnet de santé
- Mère/tuteur

**Events (répétables par type de vaccin):**
- BCG (à la naissance)
- Polio 0, 1, 2, 3
- Pentavalent 1, 2, 3
- Rougeole
- Fièvre jaune

**Données collectées par event:**
- Date de vaccination
- Lot du vaccin
- Site d'injection
- Effets indésirables

---

## 8. Bonnes pratiques

### 8.1 Conception de programmes Tracker

**1. Définir clairement le cas d'usage**
- Quel est l'objectif du suivi?
- Qui sont les utilisateurs finaux?
- Quelles décisions seront prises avec ces données?

**2. Minimiser les données collectées**
- Collecter uniquement ce qui est nécessaire
- Éviter la surcharge des agents de saisie
- Privilégier la qualité sur la quantité

**3. Utiliser des listes d'options (Option Sets)**
- Standardiser les réponses
- Faciliter l'analyse
- Réduire les erreurs de saisie

**4. Planifier les Program Rules**
- Validation automatique
- Masquage/affichage conditionnel
- Calculs automatiques
- Messages d'avertissement

**5. Définir les Program Indicators**
- Calculer des indicateurs à partir des données individuelles
- Faciliter l'analyse et le reporting

### 8.2 Performance et optimisation

**1. Pagination**
```python
# Toujours utiliser la pagination pour grands volumes
result = api.get("trackedEntityInstances", params={
    "program": "xyz",
    "orgUnit": "abc",
    "page": 1,
    "pageSize": 50,
    "totalPages": "true"
})
```

**2. Filtrage côté serveur**
```python
# Filtrer côté serveur plutôt que côté client
# BON
result = api.get("trackedEntityInstances", params={
    "lastUpdatedStartDate": "2024-10-01",
    "programStatus": "ACTIVE"
})

# MAUVAIS
all_teis = api.get("trackedEntityInstances")
filtered = [t for t in all_teis if t['status'] == 'ACTIVE']
```

**3. Utilisation des fields**
```python
# Demander uniquement les champs nécessaires
result = api.get("trackedEntityInstances", params={
    "fields": "trackedEntityInstance,attributes,enrollments[enrollment,program]"
})
```

**4. Import par lots (batching)**
```python
# Importer par lots de 50-100 TEI
batch_size = 50
for i in range(0, len(teis), batch_size):
    batch = teis[i:i+batch_size]
    api.post("tracker", data={"trackedEntities": batch})
```

**5. Mode asynchrone pour gros volumes**
```python
# Import asynchrone
response = api.post("tracker", data=bundle, params={
    "async": "true"
})

# Récupérer l'ID de la tâche
task_id = response.json()['response']['id']

# Vérifier le statut
status = api.get(f"system/tasks/{task_id}")
```

### 8.3 Sécurité et confidentialité

**1. Gestion des droits d'accès**
- Utiliser les sharing settings
- Définir des Program Access Levels
- Limiter l'accès aux données sensibles

**2. Audit trail**
```json
{
  "trackedEntityType": {
    "allowAuditLog": true
  }
}
```

**3. Anonymisation**
- Utiliser des identifiants générés
- Éviter les attributs trop identifiants
- Mettre en place des politiques de rétention

**4. Chiffrement**
- HTTPS pour toutes les communications
- Chiffrement des données sensibles en base

### 8.4 Qualité des données

**1. Validation côté client et serveur**
```json
{
  "programRules": [
    {
      "name": "Age valide",
      "condition": "d2:yearsBetween(#{date_of_birth}, V{current_date}) <= 120",
      "programRuleActions": [
        {
          "programRuleActionType": "SHOWERROR",
          "content": "L'âge ne peut pas dépasser 120 ans"
        }
      ]
    }
  ]
}
```

**2. Indicateurs de complétude**
- Taux de remplissage
- Événements manquants
- Pertes de vue

**3. Nettoyage régulier**
- Supprimer les doublons
- Fusionner les enregistrements
- Archiver les données anciennes

---

## 9. Exercices pratiques

### Exercice 1: Création d'un programme simple

**Objectif:** Créer un programme de vaccination infantile

**Étapes:**
1. Créer un Tracked Entity Type "Enfant"
2. Définir les attributs:
   - Nom
   - Prénom
   - Date de naissance
   - Numéro de carnet de santé (unique)
3. Créer le programme "Vaccination infantile"
4. Ajouter une étape de programme "Vaccination" (répétable)
5. Ajouter les data elements:
   - Type de vaccin (option set)
   - Date de vaccination
   - Lot du vaccin
   - Effets indésirables (yes/no)

**Solution (via API):**

```python
from dhis2 import Api

api = Api('https://play.dhis2.org/demo', 'admin', 'district')

# 1. Créer Tracked Entity Type
tet = {
    "id": "tet_enfant",
    "name": "Enfant",
    "description": "Enfant à vacciner"
}
api.post('metadata', data={"trackedEntityTypes": [tet]})

# 2. Créer Attributes
attributes = [
    {
        "id": "attr_nom",
        "name": "Nom",
        "valueType": "TEXT",
        "aggregationType": "NONE"
    },
    {
        "id": "attr_prenom",
        "name": "Prénom",
        "valueType": "TEXT",
        "aggregationType": "NONE"
    },
    {
        "id": "attr_dob",
        "name": "Date de naissance",
        "valueType": "DATE",
        "aggregationType": "NONE"
    },
    {
        "id": "attr_carnet",
        "name": "Numéro de carnet",
        "valueType": "TEXT",
        "unique": True,
        "aggregationType": "NONE"
    }
]
api.post('metadata', data={"trackedEntityAttributes": attributes})

# 3. Créer Option Set pour vaccins
option_set = {
    "id": "os_vaccins",
    "name": "Types de vaccins",
    "valueType": "TEXT",
    "options": [
        {"id": "opt_bcg", "name": "BCG", "code": "BCG"},
        {"id": "opt_polio", "name": "Polio", "code": "POLIO"},
        {"id": "opt_penta", "name": "Pentavalent", "code": "PENTA"},
        {"id": "opt_rougeole", "name": "Rougeole", "code": "ROUGEOLE"}
    ]
}
api.post('metadata', data={"optionSets": [option_set]})

# 4. Créer Data Elements
data_elements = [
    {
        "id": "de_type_vaccin",
        "name": "Type de vaccin",
        "valueType": "TEXT",
        "domainType": "TRACKER",
        "aggregationType": "NONE",
        "optionSet": {"id": "os_vaccins"}
    },
    {
        "id": "de_date_vacc",
        "name": "Date de vaccination",
        "valueType": "DATE",
        "domainType": "TRACKER",
        "aggregationType": "NONE"
    },
    {
        "id": "de_lot",
        "name": "Lot du vaccin",
        "valueType": "TEXT",
        "domainType": "TRACKER",
        "aggregationType": "NONE"
    },
    {
        "id": "de_effets",
        "name": "Effets indésirables",
        "valueType": "BOOLEAN",
        "domainType": "TRACKER",
        "aggregationType": "NONE"
    }
]
api.post('metadata', data={"dataElements": data_elements})

# 5. Créer Program Stage
program_stage = {
    "id": "ps_vaccination",
    "name": "Vaccination",
    "repeatable": True,
    "programStageDataElements": [
        {"dataElement": {"id": "de_type_vaccin"}, "compulsory": True},
        {"dataElement": {"id": "de_date_vacc"}, "compulsory": True},
        {"dataElement": {"id": "de_lot"}, "compulsory": False},
        {"dataElement": {"id": "de_effets"}, "compulsory": False}
    ]
}

# 6. Créer Program
program = {
    "id": "prog_vaccination",
    "name": "Programme de vaccination infantile",
    "programType": "WITH_REGISTRATION",
    "trackedEntityType": {"id": "tet_enfant"},
    "programStages": [program_stage],
    "programTrackedEntityAttributes": [
        {"trackedEntityAttribute": {"id": "attr_nom"}, "mandatory": True, "searchable": True},
        {"trackedEntityAttribute": {"id": "attr_prenom"}, "mandatory": True, "searchable": True},
        {"trackedEntityAttribute": {"id": "attr_dob"}, "mandatory": True, "searchable": False},
        {"trackedEntityAttribute": {"id": "attr_carnet"}, "mandatory": True, "searchable": True}
    ]
}
api.post('metadata', data={"programs": [program]})

print("Programme de vaccination créé avec succès!")
```

### Exercice 2: Import de données Tracker

**Objectif:** Importer 3 enfants avec leurs vaccinations

**Solution:**

```python
bundle = {
    "trackedEntities": [
        {
            "trackedEntity": "tei_001",
            "trackedEntityType": "tet_enfant",
            "orgUnit": "votre_org_unit_id",
            "attributes": [
                {"attribute": "attr_nom", "value": "Koné"},
                {"attribute": "attr_prenom", "value": "Amina"},
                {"attribute": "attr_dob", "value": "2024-01-15"},
                {"attribute": "attr_carnet", "value": "VAC2024001"}
            ]
        },
        {
            "trackedEntity": "tei_002",
            "trackedEntityType": "tet_enfant",
            "orgUnit": "votre_org_unit_id",
            "attributes": [
                {"attribute": "attr_nom", "value": "Diallo"},
                {"attribute": "attr_prenom", "value": "Moussa"},
                {"attribute": "attr_dob", "value": "2024-02-20"},
                {"attribute": "attr_carnet", "value": "VAC2024002"}
            ]
        }
    ],
    "enrollments": [
        {
            "enrollment": "enr_001",
            "trackedEntity": "tei_001",
            "program": "prog_vaccination",
            "orgUnit": "votre_org_unit_id",
            "enrollmentDate": "2024-01-15",
            "status": "ACTIVE"
        },
        {
            "enrollment": "enr_002",
            "trackedEntity": "tei_002",
            "program": "prog_vaccination",
            "orgUnit": "votre_org_unit_id",
            "enrollmentDate": "2024-02-20",
            "status": "ACTIVE"
        }
    ],
    "events": [
        {
            "event": "evt_001",
            "enrollment": "enr_001",
            "programStage": "ps_vaccination",
            "orgUnit": "votre_org_unit_id",
            "eventDate": "2024-01-15",
            "status": "COMPLETED",
            "dataValues": [
                {"dataElement": "de_type_vaccin", "value": "BCG"},
                {"dataElement": "de_date_vacc", "value": "2024-01-15"},
                {"dataElement": "de_lot", "value": "LOT123"},
                {"dataElement": "de_effets", "value": "false"}
            ]
        },
        {
            "event": "evt_002",
            "enrollment": "enr_001",
            "programStage": "ps_vaccination",
            "orgUnit": "votre_org_unit_id",
            "eventDate": "2024-03-15",
            "status": "COMPLETED",
            "dataValues": [
                {"dataElement": "de_type_vaccin", "value": "POLIO"},
                {"dataElement": "de_date_vacc", "value": "2024-03-15"},
                {"dataElement": "de_lot", "value": "LOT456"},
                {"dataElement": "de_effets", "value": "false"}
            ]
        }
    ]
}

# Import
result = api.post('tracker', data=bundle, params={
    'importStrategy': 'CREATE_AND_UPDATE'
})

print(result.json())
```

### Exercice 3: Synchronisation avec filtrage

**Objectif:** Synchroniser uniquement les TEI mis à jour la semaine dernière

**Solution:**

```python
from datetime import datetime, timedelta

# Calculer dates
end_date = datetime.now()
start_date = end_date - timedelta(days=7)

# Récupérer de la source
source = DHIS2Instance.objects.get(name="Source")
data = source.get_tracked_entity_instances(
    program="prog_vaccination",
    orgUnit="org_unit_id",
    lastUpdatedStartDate=start_date.strftime("%Y-%m-%d"),
    lastUpdatedEndDate=end_date.strftime("%Y-%m-%d"),
    paging="false"
)

teis = data.get('trackedEntityInstances', [])
print(f"TEI à synchroniser: {len(teis)}")

# Préparer et importer vers destination
destination = DHIS2Instance.objects.get(name="Destination")
# ... (voir exemples précédents pour préparation du bundle)
```

---

## Conclusion

Ce cours vous a fourni une compréhension complète des **données Tracker dans DHIS2**, de leur architecture aux techniques de synchronisation. Les points clés à retenir sont:

1. **Architecture hiérarchique:** TEI → Enrollment → Events
2. **Flexibilité:** Adaptable à de nombreux cas d'usage (santé, logistique, etc.)
3. **API puissante:** Endpoints modernes et legacy pour tous besoins
4. **Synchronisation:** Respecter l'ordre des dépendances (métadonnées puis données)
5. **Performance:** Pagination, batching, filtrage côté serveur
6. **Qualité:** Validation, Program Rules, audit trail

**Ressources complémentaires:**
- [Documentation officielle DHIS2](https://docs.dhis2.org)
- [DHIS2 Community](https://community.dhis2.org)
- [GitHub dhis2.py](https://github.com/dhis2/dhis2.py)

**Votre projet:**
- Modèles: `/home/gado/.../dhis_sync/dhis_app/models.py`
- Services Tracker: `/home/gado/.../dhis_sync/dhis_app/services/data/tracker.py`

Bonne pratique et bonne synchronisation!