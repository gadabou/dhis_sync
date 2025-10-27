#!/bin/bash

echo "Démarrage des conteneurs DHIS2..."

# Démarrer le conteneur dhis2_20
echo "Démarrage de dhis2 20"
cd ~/Applications/dhis2/dhis2_20
docker compose down
docker compose up -d

# Démarrer le conteneur dhis2_21
# echo "Démarrage de dhis2 21..."
# cd ~/Applications/Dhis2/dhis2_21
# docker compose down
# docker compose up -d

# Démarrer le conteneur dhis2_22
# echo "Démarrage de dhis2 22..."
# cd ~/Applications/Dhis2/dhis2_22
# docker compose down
# docker compose up -d

# echo "Tous les conteneurs DHIS2 ont été démarrés."

