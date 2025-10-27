# 🚀 Démarrage rapide - DHIS2 Sync

## Méthode 1: Script simple (Recommandé pour développement)

```bash
./start_simple.sh
```

Lance uniquement Django avec synchronisation automatique (pas besoin de Redis/Celery).

## Méthode 2: Script complet (Production)

```bash
./start.sh
```

Lance Django + Celery + Synchronisation automatique (nécessite Redis).

## Méthode 3: Commande Django standard

```bash
python manage.py runserver
```

La synchronisation automatique se lance automatiquement après 5 secondes.

---

## 📊 Accès rapide

- **Application:** http://localhost:8000
- **Dashboard Auto-Sync:** http://localhost:8000/auto-sync/dashboard/
- **Logs:** `tail -f logs/auto_sync.log`

## 📖 Documentation complète

Consultez [STARTUP_GUIDE.md](STARTUP_GUIDE.md) pour plus de détails.

## 🛠️ Commandes utiles

```bash
# Lister les configurations auto-sync
python manage.py start_auto_sync --list

# Voir le statut des threads
python manage.py start_auto_sync --status

# Démarrer manuellement
python manage.py start_auto_sync

# Arrêter
python manage.py stop_auto_sync
```