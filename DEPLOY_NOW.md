# Déploiement Final - DHIS2 Sync

## Tout est prêt! Il ne reste que quelques commandes à exécuter.

### Étape 1: Vérifier la configuration

Vérifiez et ajustez le fichier `.env` selon vos besoins:

```bash
nano .env
```

**Important:** Modifiez au minimum:
- `ALLOWED_HOSTS` - Ajoutez votre nom de domaine si nécessaire
- Configurations email si vous souhaitez recevoir des rapports

### Étape 2: Créer un superutilisateur (optionnel mais recommandé)

```bash
cd "/home/gado/Integrate Health Dropbox/Djakpo GADO/projets/Dhis2/dhis_sync"
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=dhis_sync.settings_production
python manage.py createsuperuser
```

### Étape 3: Déployer avec Apache2 (UNE SEULE COMMANDE)

```bash
cd "/home/gado/Integrate Health Dropbox/Djakpo GADO/projets/Dhis2/dhis_sync"
sudo bash deploy_apache.sh
```

Ce script va automatiquement:
- Activer les modules Apache2 nécessaires
- Configurer le VirtualHost
- Installer le service systemd pour Gunicorn
- Démarrer tous les services
- Vérifier que tout fonctionne

### Étape 4: Vérifier que tout fonctionne

```bash
# Vérifier le statut de Gunicorn
sudo systemctl status dhis2-sync-gunicorn

# Vérifier le statut d'Apache2
sudo systemctl status apache2

# Tester l'accès à l'application
curl -I http://localhost/
```

### Étape 5: Accéder à l'application

Ouvrez votre navigateur et accédez à:
- **Application:** http://localhost/
- **Admin:** http://localhost/admin/
- **Dashboard Auto-Sync:** http://localhost/auto-sync/dashboard/

---

## En cas de problème

### Les logs à consulter:

```bash
# Logs Gunicorn
sudo journalctl -u dhis2-sync-gunicorn -f

# Logs Apache2
sudo tail -f /var/log/apache2/dhis2-sync-error.log

# Logs Django
tail -f logs/django.log
```

### Commandes de redémarrage:

```bash
# Redémarrer Gunicorn
sudo systemctl restart dhis2-sync-gunicorn

# Redémarrer Apache2
sudo systemctl restart apache2
```

---

## Documentation complète

Pour plus de détails, consultez:
- `DEPLOYMENT_GUIDE.md` - Guide de déploiement complet avec toutes les difficultés rencontrées
- `TROUBLESHOOTING.md` - Guide de dépannage
- `AUTO_SYNC_GUIDE.md` - Guide de configuration de la synchronisation

---

## Résumé de l'architecture déployée

```
Internet/LAN → Apache2:80 → Gunicorn:8000 → Django → SQLite/Redis
```

- **Apache2:** Serveur web, proxy inverse, fichiers statiques
- **Gunicorn:** Serveur d'application WSGI (3 workers)
- **Django:** Application DHIS2 Sync
- **SQLite:** Base de données
- **Redis:** Cache et broker Celery

---

## Prochaines étapes recommandées

1. Configurer HTTPS avec Let's Encrypt
2. Configurer vos instances DHIS2 dans l'interface admin
3. Mettre en place des sauvegardes automatiques
4. Configurer les tâches Celery si nécessaire

---

**Tout est prêt pour le déploiement!**

Exécutez simplement: `sudo bash deploy_apache.sh`
