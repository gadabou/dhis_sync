#!/bin/bash

echo "Démarrage des conteneurs DHIS2..."

# Démarrer le conteneur dhis2_2_40_7_cible5
echo "Démarrage de dhis2 87"
cd ~/Applications/dhis2/dhis2_2_40_7_cible5
docker-compose down
docker-compose up -d

# Démarrer le conteneur dhis292
echo "Démarrage de dhis2 92..."
cd ~/Applications/dhis2/dhis292
docker-compose down
docker-compose up -d

# Démarrer le conteneur dhis293
echo "Démarrage de dhis2 93..."
cd ~/Applications/dhis2/dhis293
docker-compose down
docker-compose up -d


# Démarrer le conteneur dhis293
echo "Démarrage de dhis2 94..."
cd ~/Applications/dhis2/dhis294
docker-compose down
docker-compose up -d


echo "Tous les conteneurs DHIS2 ont été démarrés."


# Démarrer le conteneur dhis231
echo "Démarrage de dhis2 31..."
cd ~/Applications/dhis2/2_31/dhis231
docker-compose down
docker-compose up -d


echo "Tous les conteneurs DHIS2 ont été démarrés."
