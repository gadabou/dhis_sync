# Correction du problème CSRF (403 Forbidden)

## Problème rencontré

Après le déploiement Docker réussi, l'erreur suivante apparaissait lors de l'accès à l'application:

```
Forbidden (403)
CSRF verification failed. Request aborted.
```

## Cause du problème

Django 4.0+ a introduit une nouvelle vérification de sécurité appelée `CSRF_TRUSTED_ORIGINS`.

**Pourquoi ce problème?**

1. **Port non-standard (4999)**: Django doit explicitement faire confiance aux requêtes provenant de `http://localhost:4999`
2. **Mode production** (`DEBUG=False`): Django est plus strict avec la validation CSRF
3. **Configuration manquante**: `CSRF_TRUSTED_ORIGINS` n'était pas défini dans `settings_production.py`

## Solution appliquée

### Modification de settings_production.py

Ajout de la configuration `CSRF_TRUSTED_ORIGINS` dans le fichier `/dhis_sync/settings_production.py`:

```python
# CSRF Configuration
# Django 4+ requires explicit trusted origins for CSRF protection
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:4999',
    'http://127.0.0.1:4999',
    'http://localhost',
    'http://127.0.0.1',
]

# Add custom domain if configured
CUSTOM_DOMAIN = config('CUSTOM_DOMAIN', default=None)
if CUSTOM_DOMAIN:
    CSRF_TRUSTED_ORIGINS.append(f'http://{CUSTOM_DOMAIN}')
    CSRF_TRUSTED_ORIGINS.append(f'https://{CUSTOM_DOMAIN}')
```

### Application des changements

```bash
# Redémarrer le conteneur web
docker-compose restart web

# Vérifier les logs
docker-compose logs web
```

## Vérification

Après le redémarrage, l'application devrait fonctionner correctement:

```bash
# Test de l'application
curl -I http://localhost:4999/

# Devrait retourner 302 Found (redirection vers /login/)
# Au lieu de 403 Forbidden
```

## Configuration pour production avec domaine personnalisé

Si vous utilisez un domaine personnalisé, ajoutez-le dans le fichier `.env`:

```bash
# .env
CUSTOM_DOMAIN=your-domain.com
```

Le code ajoutera automatiquement:
- `http://your-domain.com`
- `https://your-domain.com`

à la liste des origines de confiance.

## Pour HTTPS (production)

Quand vous configurez SSL/TLS, les origines HTTPS seront automatiquement ajoutées si vous définissez `CUSTOM_DOMAIN`.

Pour un domaine spécifique:

```python
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:4999',
    'http://127.0.0.1:4999',
    'https://your-domain.com',  # Votre domaine en HTTPS
]
```

## Ports alternatifs

Si vous changez le port HTTP (par exemple 8080), ajoutez-le aux origines:

```python
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8080',  # Port personnalisé
    'http://127.0.0.1:8080',
]
```

## Notes importantes

1. **Toujours inclure le protocole**: `http://` ou `https://`
2. **Inclure le port si non-standard**: `:4999`, `:8080`, etc.
3. **Redémarrer l'application après modifications**: `docker-compose restart web`

## Dépannage

### L'erreur persiste?

**1. Vérifier que les changements sont pris en compte:**
```bash
docker-compose exec web python -c "from dhis_sync import settings_production; print(settings_production.CSRF_TRUSTED_ORIGINS)"
```

**2. Vider le cache du navigateur:**
- Ctrl+Shift+Delete (Chrome/Firefox)
- Ou utiliser le mode navigation privée

**3. Vérifier les logs:**
```bash
docker-compose logs web | grep CSRF
```

**4. Redémarrer complètement:**
```bash
docker-compose down
docker-compose up -d
```

### Mode debug temporaire

**Pour diagnostiquer le problème (DÉVELOPPEMENT UNIQUEMENT):**

Dans `.env`:
```bash
DEBUG=True
```

Puis redémarrer:
```bash
docker-compose restart web
```

**⚠️ IMPORTANT:** Remettez `DEBUG=False` après le diagnostic!

## Pourquoi CSRF?

CSRF (Cross-Site Request Forgery) est une protection de sécurité qui empêche des sites malveillants d'exécuter des actions non autorisées sur votre application.

Django valide que:
1. Les requêtes proviennent d'une origine de confiance
2. Un token CSRF valide est inclus dans les formulaires
3. Les headers HTTP correspondent aux attentes

## Documentation officielle

- [Django CSRF Protection](https://docs.djangoproject.com/en/5.0/ref/csrf/)
- [CSRF_TRUSTED_ORIGINS](https://docs.djangoproject.com/en/5.0/ref/settings/#csrf-trusted-origins)

---

## Résumé

**Problème:** `403 Forbidden - CSRF verification failed`

**Cause:** Configuration manquante `CSRF_TRUSTED_ORIGINS` pour Django 4+

**Solution:** Ajout de la liste des origines de confiance dans `settings_production.py`

**Résultat:** ✅ Application fonctionnelle

**Commande de redémarrage:** `docker-compose restart web`

---

**Date de résolution:** 20 octobre 2025
**Version Django:** 5.2.4
**Port HTTP:** 4999
