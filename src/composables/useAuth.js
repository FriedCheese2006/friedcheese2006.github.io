import { ref, readonly, computed } from 'vue';

const backendEnabled = import.meta.env.VITE_BACKEND_ENABLED === 'true';

// Module-level singleton so all components share the same auth state
const _user = ref(null);
const _ssoEnabled = ref(false);
const _isLoading = ref(false);
let _initialized = false;

export function useAuth() {
    const isLoggedIn = computed(() => !!_user.value);

    async function fetchUser() {
        _isLoading.value = true;
        try {
            const response = await fetch('/auth/me', { credentials: 'same-origin' });
            _user.value = response.ok ? await response.json() : null;
        } catch {
            _user.value = null;
        } finally {
            _isLoading.value = false;
        }
    }

    async function fetchConfig() {
        try {
            const response = await fetch('/auth/config', { credentials: 'same-origin' });
            if (response.ok) {
                const data = await response.json();
                _ssoEnabled.value = data.sso_enabled ?? false;
            }
        } catch {
            // Backend not reachable (pure Vite dev mode) — SSO stays disabled
            _ssoEnabled.value = false;
        }
    }

    async function init() {
        if (_initialized) return;
        _initialized = true;
        if (!backendEnabled) return;

        await fetchConfig();
        if (_ssoEnabled.value) await fetchUser();
    }

    function login() {
        window.location.href = '/auth/login';
    }

    function logout() {
        window.location.href = '/auth/logout';
    }

    return {
        user: readonly(_user),
        isLoggedIn,
        ssoEnabled: readonly(_ssoEnabled),
        isLoading: readonly(_isLoading),
        init,
        fetchUser,
        login,
        logout,
    };
}
