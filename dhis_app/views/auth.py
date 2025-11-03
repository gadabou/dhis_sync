"""
Vues pour l'authentification
"""
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse


def login_view(request):
    """
    Vue de connexion
    """
    # Si l'utilisateur est déjà connecté, rediriger vers le dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        next_url = request.POST.get('next', 'dashboard')

        # Authentifier l'utilisateur
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Connexion réussie
            login(request, user)
            messages.success(request, f'Bienvenue {user.username} !')

            # Rediriger vers la page demandée ou le dashboard
            return redirect(next_url if next_url else 'dashboard')
        else:
            # Authentification échouée
            messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect.')

    # GET request ou échec d'authentification
    next_url = request.GET.get('next', '')
    return render(request, 'registration/login.html', {'next': next_url})


@login_required
def logout_view(request):
    """
    Vue de déconnexion
    """
    username = request.user.username
    logout(request)
    messages.info(request, f'Au revoir {username} ! Vous avez été déconnecté.')
    return redirect('login')