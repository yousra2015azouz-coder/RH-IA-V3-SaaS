/**
 * api.js — Client API centralisé pour SaaS RH V3
 */

const API_BASE_URL = window.location.origin + "/api/v1";

const apiClient = {
    getToken: () => localStorage.getItem("rh_token"),
    
    setToken: (token) => localStorage.setItem("rh_token", token),
    
    clearToken: () => localStorage.removeItem("rh_token"),

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
                // Token expiré ou invalide
                this.clearToken();
                if (!window.location.pathname.includes("/login.html")) {
                    window.location.href = "/static/auth/login.html";
                }
                return null;
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
                this.clearToken();
                if (!window.location.pathname.includes("/login.html")) {
                    window.location.href = "/static/auth/login.html";
                }
                return null;
            }

            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || "Erreur upload");
            return data;
        } catch (error) {
            console.error(`Upload Error [${endpoint}]:`, error);
            throw error;
        }
    }

};

window.apiClient = apiClient;
