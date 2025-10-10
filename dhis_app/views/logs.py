"""
Vues pour la consultation des logs en temps réel
"""

import os
import logging
from pathlib import Path
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def logs_viewer(request):
    """
    Page de visualisation des logs

    Affiche les différents fichiers de logs disponibles
    """
    logs_dir = settings.BASE_DIR / 'logs'

    # Liste des fichiers de logs disponibles
    log_files = []
    if logs_dir.exists():
        for log_file in logs_dir.glob('*.log'):
            file_stat = log_file.stat()
            log_files.append({
                'name': log_file.name,
                'path': str(log_file),
                'size': file_stat.st_size,
                'size_mb': round(file_stat.st_size / (1024 * 1024), 2),
                'modified': file_stat.st_mtime,
            })

    # Trier par date de modification (plus récent en premier)
    log_files.sort(key=lambda x: x['modified'], reverse=True)

    context = {
        'log_files': log_files,
        'logs_dir': str(logs_dir),
    }

    return render(request, 'dhis_app/logs/viewer.html', context)


@login_required
@require_http_methods(["GET"])
def view_log_file(request, log_filename):
    """
    Affiche le contenu d'un fichier de log

    Args:
        log_filename: Nom du fichier de log
    """
    logs_dir = settings.BASE_DIR / 'logs'
    log_file_path = logs_dir / log_filename

    # Sécurité: vérifier que le fichier est bien dans le répertoire logs
    try:
        log_file_path = log_file_path.resolve()
        if not str(log_file_path).startswith(str(logs_dir.resolve())):
            return JsonResponse({'error': 'Accès non autorisé'}, status=403)
    except Exception:
        return JsonResponse({'error': 'Fichier invalide'}, status=400)

    if not log_file_path.exists():
        return JsonResponse({'error': 'Fichier introuvable'}, status=404)

    # Paramètres de pagination
    lines = int(request.GET.get('lines', 100))  # Nombre de lignes
    offset = int(request.GET.get('offset', 0))  # Offset
    tail = request.GET.get('tail', 'true') == 'true'  # Lire depuis la fin

    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            if tail:
                # Lire les dernières lignes
                content_lines = f.readlines()
                total_lines = len(content_lines)

                if offset > 0:
                    # Pour tail mode, offset signifie "skip les N dernières"
                    end = total_lines - offset
                    start = max(0, end - lines)
                else:
                    start = max(0, total_lines - lines)
                    end = total_lines

                content = ''.join(content_lines[start:end])
            else:
                # Lire depuis le début
                content_lines = f.readlines()
                total_lines = len(content_lines)
                start = offset
                end = min(total_lines, offset + lines)
                content = ''.join(content_lines[start:end])

        return JsonResponse({
            'success': True,
            'filename': log_filename,
            'content': content,
            'total_lines': total_lines,
            'returned_lines': end - start,
            'start': start,
            'end': end,
        })

    except Exception as e:
        logger.error(f"Erreur lors de la lecture du fichier {log_filename}: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def stream_log_file(request, log_filename):
    """
    Stream le contenu d'un fichier de log en temps réel (tail -f)

    Args:
        log_filename: Nom du fichier de log
    """
    logs_dir = settings.BASE_DIR / 'logs'
    log_file_path = logs_dir / log_filename

    # Sécurité
    try:
        log_file_path = log_file_path.resolve()
        if not str(log_file_path).startswith(str(logs_dir.resolve())):
            return JsonResponse({'error': 'Accès non autorisé'}, status=403)
    except Exception:
        return JsonResponse({'error': 'Fichier invalide'}, status=400)

    if not log_file_path.exists():
        return JsonResponse({'error': 'Fichier introuvable'}, status=404)

    def generate():
        """Générateur pour streamer les lignes du fichier"""
        import time

        with open(log_file_path, 'r', encoding='utf-8') as f:
            # Aller à la fin du fichier
            f.seek(0, 2)

            while True:
                line = f.readline()
                if line:
                    yield f"data: {line}\n\n"
                else:
                    time.sleep(0.5)  # Attendre avant de réessayer

    response = StreamingHttpResponse(generate(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@login_required
@require_http_methods(["GET"])
def auto_sync_logs(request):
    """
    Affiche les logs spécifiques à la synchronisation automatique

    Combines les logs de:
    - auto_sync.log
    - changes_detected.log
    - sync_jobs.log
    """
    logs_dir = settings.BASE_DIR / 'logs'

    # Fichiers de logs auto-sync
    auto_sync_files = [
        'auto_sync.log',
        'changes_detected.log',
        'sync_jobs.log',
    ]

    # Lire les logs
    logs_content = {}
    for filename in auto_sync_files:
        file_path = logs_dir / filename
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    # Lire les 100 dernières lignes
                    lines = f.readlines()
                    logs_content[filename] = ''.join(lines[-100:])
            except Exception as e:
                logs_content[filename] = f"Erreur: {str(e)}"
        else:
            logs_content[filename] = "Fichier non trouvé"

    context = {
        'logs_content': logs_content,
        'auto_sync_files': auto_sync_files,
    }

    return render(request, 'dhis_app/logs/auto_sync_logs.html', context)


@login_required
@require_http_methods(["POST"])
def clear_log_file(request, log_filename):
    """
    Vide le contenu d'un fichier de log

    Args:
        log_filename: Nom du fichier de log
    """
    logs_dir = settings.BASE_DIR / 'logs'
    log_file_path = logs_dir / log_filename

    # Sécurité
    try:
        log_file_path = log_file_path.resolve()
        if not str(log_file_path).startswith(str(logs_dir.resolve())):
            return JsonResponse({'error': 'Accès non autorisé'}, status=403)
    except Exception:
        return JsonResponse({'error': 'Fichier invalide'}, status=400)

    if not log_file_path.exists():
        return JsonResponse({'error': 'Fichier introuvable'}, status=404)

    try:
        # Vider le fichier
        with open(log_file_path, 'w', encoding='utf-8') as f:
            f.write('')

        logger.info(f"Fichier de log {log_filename} vidé par {request.user.username}")

        return JsonResponse({
            'success': True,
            'message': f'Fichier {log_filename} vidé avec succès'
        })

    except Exception as e:
        logger.error(f"Erreur lors du vidage du fichier {log_filename}: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def download_log_file(request, log_filename):
    """
    Télécharge un fichier de log

    Args:
        log_filename: Nom du fichier de log
    """
    logs_dir = settings.BASE_DIR / 'logs'
    log_file_path = logs_dir / log_filename

    # Sécurité
    try:
        log_file_path = log_file_path.resolve()
        if not str(log_file_path).startswith(str(logs_dir.resolve())):
            return JsonResponse({'error': 'Accès non autorisé'}, status=403)
    except Exception:
        return JsonResponse({'error': 'Fichier invalide'}, status=400)

    if not log_file_path.exists():
        return JsonResponse({'error': 'Fichier introuvable'}, status=404)

    try:
        with open(log_file_path, 'rb') as f:
            response = StreamingHttpResponse(f, content_type='text/plain')
            response['Content-Disposition'] = f'attachment; filename="{log_filename}"'
            return response

    except Exception as e:
        logger.error(f"Erreur lors du téléchargement du fichier {log_filename}: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def search_logs(request):
    """
    Recherche dans les logs

    Query params:
        - query: Terme de recherche
        - files: Liste des fichiers à rechercher (séparés par des virgules)
        - case_sensitive: Recherche sensible à la casse (true/false)
    """
    query = request.GET.get('query', '')
    files = request.GET.get('files', '').split(',')
    case_sensitive = request.GET.get('case_sensitive', 'false') == 'true'

    if not query:
        return JsonResponse({'error': 'Query requis'}, status=400)

    logs_dir = settings.BASE_DIR / 'logs'
    results = []

    for filename in files:
        if not filename:
            continue

        file_path = logs_dir / filename

        # Sécurité
        try:
            file_path = file_path.resolve()
            if not str(file_path).startswith(str(logs_dir.resolve())):
                continue
        except Exception:
            continue

        if not file_path.exists():
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    # Recherche
                    if case_sensitive:
                        if query in line:
                            results.append({
                                'file': filename,
                                'line_num': line_num,
                                'content': line.strip()
                            })
                    else:
                        if query.lower() in line.lower():
                            results.append({
                                'file': filename,
                                'line_num': line_num,
                                'content': line.strip()
                            })
        except Exception as e:
            logger.error(f"Erreur lors de la recherche dans {filename}: {e}")

    return JsonResponse({
        'success': True,
        'query': query,
        'total_results': len(results),
        'results': results[:500]  # Limiter à 500 résultats
    })
