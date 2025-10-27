#!/bin/bash

echo "Démarrage des conteneurs DHIS2..."

# Démarrer le conteneur dhis2_2_40_7_cible5
echo "Démarrage de dhis2 87"
cd ~/Applications/Dhis2/dhis2_20
docker-compose down
docker-compose up -d

# Démarrer le conteneur dhis292
echo "Démarrage de dhis2 92..."
cd ~/Applications/Dhis2/dhis2_21
docker-compose down
docker-compose up -d

# Démarrer le conteneur dhis293
echo "Démarrage de dhis2 93..."
cd ~/Applications/Dhis2/dhis2_22
docker-compose down
docker-compose up -d



echo "Tous les conteneurs DHIS2 ont été démarrés."

