/**
 * auth.js — Gestion de l'authentification et redirection par rôle
 */

const authService = {
    async login(email, password) {
        try {
            const data = await apiClient.post("/auth/login", { email, password });
            if (data && data.access_token) {
                apiClient.setToken(data.access_token);
                localStorage.setItem("rh_user", JSON.stringify(data.user));
                // Aussi stocker avec la clé utilisée par le portail candidat
                localStorage.setItem("access_token", data.access_token);
                localStorage.setItem("user", JSON.stringify(data.user));
                this.redirectByRole(data.user.role);
                return data;
            }
        } catch (error) {
            alert("Erreur de connexion: " + error.message);
        }
    },

    redirectByRole(role) {
        const urlParams = new URLSearchParams(window.location.search);
        const customRedirect = urlParams.get('redirect');
        
        if (customRedirect) {
            window.location.href = customRedirect;
            return;
        }

        const rolePaths = {
            "super_admin": "/static/dashboards/super_admin/index.html",
            "directeur_rh": "/static/dashboards/directeur_rh/index.html",
            "directeur_hierarchique": "/static/dashboards/directeur_hierarchique/index.html",
            "directeur_fonctionnel": "/static/dashboards/directeur_fonctionnel/index.html",
            "directeur_general": "/static/dashboards/directeur_general/index.html",
            "candidat": "/static/portal/dashboard.html",
            "employe": "/static/portal/employee-dashboard.html"
        };
        
        window.location.href = rolePaths[role] || "/";
    },


    logout() {
        apiClient.clearToken();
        localStorage.removeItem("rh_user");
        window.location.href = "/static/auth/login.html";
    },

    getCurrentUser() {
        const user = localStorage.getItem("rh_user");
        return user ? JSON.parse(user) : null;
    },

    checkAuth() {
        if (!apiClient.getToken()) {
            const path = window.location.pathname;
            if (!path.includes("/login.html") && 
                !path.includes("/register.html") &&
                !path.includes("/portal/")) {
                window.location.href = "/static/auth/login.html";
            }
        }
    }

};

window.authService = authService;
document.addEventListener("DOMContentLoaded", () => authService.checkAuth());
