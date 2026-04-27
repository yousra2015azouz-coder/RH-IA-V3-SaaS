/**
 * api.js — Client API centralisé pour SaaS RH V3
 */

const API_BASE_URL = window.location.origin + "/api/v1";

const apiClient = {
    getToken: () => {
        return localStorage.getItem("rh_token") || 
               localStorage.getItem("access_token") || 
               localStorage.getItem("token");
    },
    
    setToken: (token) => localStorage.setItem("rh_token", token),
    
    clearToken: () => {
        localStorage.removeItem("rh_token");
        localStorage.removeItem("access_token");
        localStorage.removeItem("user");
        localStorage.removeItem("rh_user");
    },

    async request(endpoint, options = {}) {
        const token = this.getToken();
        const headers = {
            "Content-Type": "application/json",
            ...(token && { "Authorization": `Bearer ${token}` }),
            ...options.headers
        };

        const config = {
            ...options,
            headers
        };

        try {
            const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
            
            if (response.status === 401) {
                // Si ce n'est pas une tentative de connexion, c'est que le token a expiré
                if (!endpoint.includes("/auth/login")) {
                    this.clearToken();
                    if (!window.location.pathname.includes("/login.html")) {
                        window.location.href = "/static/auth/login.html";
                    }
                    return null;
                }
            }

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Erreur serveur");
            }
            return data;
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    },

    get: (endpoint) => apiClient.request(endpoint, { method: "GET" }),
    
    post: (endpoint, body) => apiClient.request(endpoint, {
        method: "POST",
        body: JSON.stringify(body)
    }),
    
    put: (endpoint, body) => apiClient.request(endpoint, {
        method: "PUT",
        body: JSON.stringify(body)
    }),
    
    patch: (endpoint, body) => apiClient.request(endpoint, {
        method: "PATCH",
        body: JSON.stringify(body)
    }),
    
    delete: (endpoint) => apiClient.request(endpoint, { method: "DELETE" }),

    // Upload spécifique (form-data)
    async upload(endpoint, formData) {
        const token = this.getToken();
        try {
            const response = await fetch(`${API_BASE_URL}${endpoint}`, {
                method: "POST",
                headers: {
                    ...(token && { "Authorization": `Bearer ${token}` })
                },
                body: formData
            });

            if (response.status === 401) {
                // Pour le debug, on ne déconnecte pas tout de suite sur un upload
                console.warn("Erreur 401 sur upload, vérifiez le token.");
                // this.clearToken();
                // window.location.href = "/static/auth/login.html";
            }

            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || "Erreur upload");
            return data;
        } catch (error) {
            console.error(`Upload Error [${endpoint}]:`, error);
            throw error;
        }
    },

    // Visualisation de PDF avec authentification
    async viewPdf(endpoint) {
        const token = this.getToken();
        try {
            const response = await fetch(`${API_BASE_URL}${endpoint}`, {
                method: "GET",
                headers: {
                    ...(token && { "Authorization": `Bearer ${token}` })
                }
            });

            if (!response.ok) throw new Error("Erreur lors de l'ouverture du PDF");

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            window.open(url, '_blank');
        } catch (error) {
            console.error("PDF View Error:", error);
            alert("Impossible d'ouvrir le document. Vérifiez votre connexion.");
        }
    }
};

window.apiClient = apiClient;
