/**
 * Authentication utility functions for the frontend
 */

class AuthManager {
    constructor() {
        this.token = localStorage.getItem('authToken');
        this.user = JSON.parse(localStorage.getItem('user') || 'null');
    }

    /**
     * Check if user is logged in
     */
    isLoggedIn() {
        return !!this.token;
    }

    /**
     * Get stored authentication token
     */
    getToken() {
        return this.token;
    }

    /**
     * Get stored user data
     */
    getUser() {
        return this.user;
    }

    /**
     * Store authentication data
     */
    setAuth(token, user) {
        this.token = token;
        this.user = user;
        localStorage.setItem('authToken', token);
        localStorage.setItem('user', JSON.stringify(user));
    }

    /**
     * Clear authentication data (logout)
     */
    clearAuth() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('authToken');
        localStorage.removeItem('user');
    }

    /**
     * Make authenticated API request
     */
    async request(endpoint, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        const response = await fetch(endpoint, {
            ...options,
            headers
        });

        if (response.status === 401) {
            // Unauthorized - clear auth and redirect to login
            this.clearAuth();
            window.location.href = 'home_page.html';
        }

        return response;
    }

    /**
     * Redirect to login if not authenticated
     */
    requireAuth() {
        if (!this.isLoggedIn()) {
            window.location.href = 'home_page.html';
        }
    }
}

// Create global auth manager instance
const auth = new AuthManager();

/**
 * Quick function to get headers with auth token
 */
function getAuthHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    if (auth.token) {
        headers['Authorization'] = `Bearer ${auth.token}`;
    }
    return headers;
}

/**
 * Logout helper function
 */
async function logout() {
    try {
        await fetch('/api/auth/logout', {
            method: 'POST',
            headers: getAuthHeaders()
        });
    } catch (error) {
        console.error('Logout error:', error);
    } finally {
        auth.clearAuth();
        window.location.href = 'home_page.html';
    }
}
