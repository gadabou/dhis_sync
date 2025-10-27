/**
 * DHIS2 Sync - Main JavaScript
 * Fonctionnalités globales de l'application
 */

(function() {
    'use strict';

    // =================================
    // UTILITAIRES GLOBAUX
    // =================================

    /**
     * Affiche l'overlay de chargement
     */
    window.showLoading = function(message = 'Chargement...') {
        const overlay = document.getElementById('loading-overlay');
        const messageElement = overlay.querySelector('span');

        if (messageElement) {
            messageElement.textContent = message;
        }

        overlay.classList.remove('hidden');
        overlay.classList.add('flex');
    };

    /**
     * Masque l'overlay de chargement
     */
    window.hideLoading = function() {
        const overlay = document.getElementById('loading-overlay');
        overlay.classList.add('hidden');
        overlay.classList.remove('flex');
    };

    /**
     * Affiche une notification toast
     */
    window.showToast = function(message, type = 'info', duration = 5000) {
        const toastContainer = document.getElementById('toast-container') || createToastContainer();

        const toast = document.createElement('div');
        toast.className = `toast max-w-sm rounded-lg shadow-lg overflow-hidden ${getToastClasses(type)}`;
        toast.innerHTML = `
            <div class="p-4">
                <div class="flex items-start">
                    <div class="flex-shrink-0">
                        <i class="${getToastIcon(type)}"></i>
                    </div>
                    <div class="ml-3 flex-1">
                        <p class="text-sm font-medium ${getToastTextClasses(type)}">
                            ${message}
                        </p>
                    </div>
                    <div class="ml-4 flex-shrink-0">
                        <button onclick="this.closest('.toast').remove()"
                                class="${getToastButtonClasses(type)} transition-colors duration-200">
                            <i class="fas fa-times text-sm"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;

        toastContainer.appendChild(toast);

        // Animation d'entrée
        setTimeout(() => toast.classList.add('show'), 100);

        // Auto-suppression
        setTimeout(() => {
            toast.classList.remove('show');
            toast.classList.add('hide');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    };

    /**
     * Crée le conteneur de toasts s'il n'existe pas
     */
    function createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'fixed top-4 right-4 z-50 space-y-2';
        document.body.appendChild(container);
        return container;
    }

    /**
     * Retourne les classes CSS pour les toasts selon le type
     */
    function getToastClasses(type) {
        const classes = {
            'error': 'bg-red-50 border-l-4 border-red-400',
            'warning': 'bg-yellow-50 border-l-4 border-yellow-400',
            'success': 'bg-green-50 border-l-4 border-green-400',
            'info': 'bg-blue-50 border-l-4 border-blue-400'
        };
        return classes[type] || classes.info;
    }

    /**
     * Retourne l'icône pour les toasts selon le type
     */
    function getToastIcon(type) {
        const icons = {
            'error': 'fas fa-exclamation-circle text-red-400',
            'warning': 'fas fa-exclamation-triangle text-yellow-400',
            'success': 'fas fa-check-circle text-green-400',
            'info': 'fas fa-info-circle text-blue-400'
        };
        return icons[type] || icons.info;
    }

    /**
     * Retourne les classes de texte pour les toasts selon le type
     */
    function getToastTextClasses(type) {
        const classes = {
            'error': 'text-red-800',
            'warning': 'text-yellow-800',
            'success': 'text-green-800',
            'info': 'text-blue-800'
        };
        return classes[type] || classes.info;
    }

    /**
     * Retourne les classes de bouton pour les toasts selon le type
     */
    function getToastButtonClasses(type) {
        const classes = {
            'error': 'text-red-400 hover:text-red-600',
            'warning': 'text-yellow-400 hover:text-yellow-600',
            'success': 'text-green-400 hover:text-green-600',
            'info': 'text-blue-400 hover:text-blue-600'
        };
        return classes[type] || classes.info;
    }

    // =================================
    // GESTION DES FORMULAIRES
    // =================================

    /**
     * Initialise la gestion des formulaires AJAX
     */
    function initAjaxForms() {
        document.addEventListener('submit', function(e) {
            if (!e.target.hasAttribute('data-ajax')) return;

            e.preventDefault();
            showLoading();

            const form = e.target;
            const formData = new FormData(form);
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');

            const headers = {
                'X-Requested-With': 'XMLHttpRequest'
            };

            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken.value;
            }

            fetch(form.action, {
                method: form.method,
                body: formData,
                headers: headers
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                hideLoading();

                if (data.success) {
                    if (data.message) {
                        showToast(data.message, 'success');
                    }

                    if (data.redirect) {
                        setTimeout(() => window.location.href = data.redirect, 1000);
                    } else if (data.reload) {
                        setTimeout(() => window.location.reload(), 1000);
                    }
                } else {
                    showToast(data.message || 'Une erreur est survenue', 'error');
                }
            })
            .catch(error => {
                hideLoading();
                console.error('Erreur AJAX:', error);
                showToast('Une erreur de connexion est survenue', 'error');
            });
        });
    }

    // =================================
    // CONFIRMATIONS
    // =================================

    /**
     * Initialise les confirmations pour les actions dangereuses
     */
    function initConfirmations() {
        document.addEventListener('click', function(e) {
            const element = e.target.closest('[data-confirm]');
            if (!element) return;

            const message = element.getAttribute('data-confirm');
            if (!confirm(message)) {
                e.preventDefault();
                return false;
            }
        });
    }

    // =================================
    // TOOLTIPS ET POPOVERS
    // =================================

    /**
     * Initialise les tooltips
     */
    function initTooltips() {
        const tooltipElements = document.querySelectorAll('[data-tooltip]');

        tooltipElements.forEach(element => {
            element.addEventListener('mouseenter', showTooltip);
            element.addEventListener('mouseleave', hideTooltip);
        });
    }

    function showTooltip(e) {
        const element = e.target;
        const text = element.getAttribute('data-tooltip');

        const tooltip = document.createElement('div');
        tooltip.id = 'tooltip';
        tooltip.className = 'absolute z-50 px-2 py-1 text-sm text-white bg-gray-900 rounded shadow-lg';
        tooltip.textContent = text;

        document.body.appendChild(tooltip);

        const rect = element.getBoundingClientRect();
        tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
        tooltip.style.top = rect.top - tooltip.offsetHeight - 5 + 'px';
    }

    function hideTooltip() {
        const tooltip = document.getElementById('tooltip');
        if (tooltip) {
            tooltip.remove();
        }
    }

    // =================================
    // GESTION DES MESSAGES FLASH
    // =================================

    /**
     * Auto-dismiss des messages flash après 5 secondes
     */
    function initFlashMessages() {
        setTimeout(function() {
            const alerts = document.querySelectorAll('.alert');
            alerts.forEach(function(alert) {
                alert.classList.add('dismissing');
                setTimeout(function() {
                    alert.remove();
                }, 300);
            });
        }, 5000);
    }

    // =================================
    // NAVIGATION MOBILE
    // =================================

    /**
     * Gère la fermeture automatique du menu mobile lors du scroll
     */
    function initMobileNav() {
        let lastScrollTop = 0;

        window.addEventListener('scroll', function() {
            const st = window.pageYOffset || document.documentElement.scrollTop;

            // Fermer le menu mobile lors du scroll vers le bas
            if (st > lastScrollTop && st > 100) {
                const mobileMenus = document.querySelectorAll('[x-data*="mobileMenuOpen"]');
                mobileMenus.forEach(menu => {
                    // Déclencher la fermeture via Alpine.js
                    menu.__x && menu.__x.$data && (menu.__x.$data.mobileMenuOpen = false);
                });
            }

            lastScrollTop = st <= 0 ? 0 : st;
        });
    }

    // =================================
    // UTILITAIRES DE VALIDATION
    // =================================

    /**
     * Validation en temps réel des formulaires
     */
    function initFormValidation() {
        const inputs = document.querySelectorAll('input[required], textarea[required], select[required]');

        inputs.forEach(input => {
            input.addEventListener('blur', validateField);
            input.addEventListener('input', clearValidationState);
        });
    }

    function validateField(e) {
        const field = e.target;
        const isValid = field.checkValidity();

        field.classList.remove('is-valid', 'is-invalid');

        if (field.value.trim() !== '') {
            field.classList.add(isValid ? 'is-valid' : 'is-invalid');
        }
    }

    function clearValidationState(e) {
        const field = e.target;
        field.classList.remove('is-valid', 'is-invalid');
    }

    // =================================
    // GESTION DES TABLEAUX
    // =================================

    /**
     * Initialise le tri des tableaux
     */
    function initTableSorting() {
        const sortableHeaders = document.querySelectorAll('[data-sort]');

        sortableHeaders.forEach(header => {
            header.style.cursor = 'pointer';
            header.addEventListener('click', sortTable);
        });
    }

    function sortTable(e) {
        const header = e.target.closest('[data-sort]');
        const table = header.closest('table');
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const column = header.getAttribute('data-sort');
        const isNumeric = header.hasAttribute('data-sort-numeric');

        // Déterminer la direction du tri
        const currentDir = header.getAttribute('data-sort-dir') || 'asc';
        const newDir = currentDir === 'asc' ? 'desc' : 'asc';

        // Réinitialiser tous les headers
        sortableHeaders.forEach(h => h.removeAttribute('data-sort-dir'));
        header.setAttribute('data-sort-dir', newDir);

        // Trier les lignes
        rows.sort((a, b) => {
            const aVal = a.querySelector(`[data-value="${column}"]`)?.textContent ||
                        a.cells[parseInt(column)]?.textContent || '';
            const bVal = b.querySelector(`[data-value="${column}"]`)?.textContent ||
                        b.cells[parseInt(column)]?.textContent || '';

            let comparison = 0;

            if (isNumeric) {
                comparison = parseFloat(aVal) - parseFloat(bVal);
            } else {
                comparison = aVal.localeCompare(bVal);
            }

            return newDir === 'asc' ? comparison : -comparison;
        });

        // Réinsérer les lignes triées
        rows.forEach(row => tbody.appendChild(row));
    }

    // =================================
    // INITIALISATION
    // =================================

    /**
     * Initialise tous les modules au chargement de la page
     */
    function init() {
        initAjaxForms();
        initConfirmations();
        initTooltips();
        initFlashMessages();
        initMobileNav();
        initFormValidation();
        initTableSorting();

        // Event personnalisé pour signaler que l'app est prête
        document.dispatchEvent(new CustomEvent('dhis2sync:ready'));
    }

    // Initialiser quand le DOM est prêt
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // =================================
    // API PUBLIQUE
    // =================================

    // Exposer les fonctions utilitaires globalement
    window.DHIS2Sync = {
        showLoading,
        hideLoading,
        showToast,
        utils: {
            validateField: function(field) {
                const isValid = field.checkValidity();
                field.classList.remove('is-valid', 'is-invalid');
                if (field.value.trim() !== '') {
                    field.classList.add(isValid ? 'is-valid' : 'is-invalid');
                }
            },
            sortTable
        }
    };

})();