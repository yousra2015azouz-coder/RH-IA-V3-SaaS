/**
 * branding.js — Injection dynamique de l'identité visuelle
 */
const brandingService = {
    async apply() {
        try {
            // Récupérer le branding depuis l'API (Public)
            const response = await fetch('/api/v1/branding/');
            const data = await response.json();

            if (data && !data.error) {
                // 1. Appliquer les couleurs via variables CSS
                if (data.primary_color) {
                    document.documentElement.style.setProperty('--primary', data.primary_color);
                    // Générer une version "light" auto (pour les hovers)
                    document.documentElement.style.setProperty('--primary-light', data.primary_color + 'CC'); 
                }
                if (data.secondary_color) {
                    document.documentElement.style.setProperty('--secondary', data.secondary_color);
                }

                // 2. Mettre à jour le logo (partout où la classe .app-logo est présente)
                if (data.logo_url) {
                    const logos = document.querySelectorAll('.app-logo');
                    logos.forEach(img => {
                        img.src = data.logo_url;
                        img.style.display = 'block';
                    });
                    const logoTexts = document.querySelectorAll('.logo-text');
                    logoTexts.forEach(el => el.style.display = 'none');
                }

                // 3. Mettre à jour le nom de l'application (titre de l'onglet)
                if (data.name) {
                    document.title = `${document.title.split('|')[0]} | ${data.name}`;
                    const appNames = document.querySelectorAll('.app-name');
                    appNames.forEach(el => el.textContent = data.name);
                }

                // 4. Mettre à jour les textes Hero (uniquement sur la page publique)
                const heroTitle = document.getElementById('hero-title');
                if (heroTitle && data.hero_title) heroTitle.textContent = data.hero_title;
                
                const heroSubtitle = document.getElementById('hero-subtitle');
                if (heroSubtitle && data.hero_subtitle) heroSubtitle.textContent = data.hero_subtitle;

                const footerText = document.getElementById('footer-text');
                if (footerText && data.footer_text) footerText.textContent = data.footer_text;
            }
        } catch (error) {
            console.error("Erreur branding:", error);
        }
    }
};

// Exécuter au chargement de la page
document.addEventListener('DOMContentLoaded', () => brandingService.apply());
