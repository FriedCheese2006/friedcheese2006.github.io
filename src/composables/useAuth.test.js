import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const loadAuth = async (backendEnabled) => {
    vi.stubEnv('VITE_BACKEND_ENABLED', backendEnabled ? 'true' : 'false');
    vi.resetModules();
    return (await import('./useAuth')).useAuth();
};

describe('useAuth initialization', () => {
    beforeEach(() => {
        vi.stubGlobal('fetch', vi.fn());
    });

    afterEach(() => {
        vi.unstubAllEnvs();
        vi.unstubAllGlobals();
    });

    it('does not request auth endpoints in standalone builds', async () => {
        const auth = await loadAuth(false);

        await auth.init();

        expect(fetch).not.toHaveBeenCalled();
        expect(auth.ssoEnabled.value).toBe(false);
        expect(auth.isLoggedIn.value).toBe(false);
    });

    it('does not request the current user when container SSO is disabled', async () => {
        fetch.mockResolvedValueOnce({ ok: true, json: async () => ({ sso_enabled: false }) });
        const auth = await loadAuth(true);

        await auth.init();

        expect(fetch).toHaveBeenCalledOnce();
        expect(fetch).toHaveBeenCalledWith('/auth/config', { credentials: 'same-origin' });
    });

    it('requests the current user when container SSO is enabled', async () => {
        fetch
            .mockResolvedValueOnce({ ok: true, json: async () => ({ sso_enabled: true }) })
            .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 'user-1' }) });
        const auth = await loadAuth(true);

        await auth.init();

        expect(fetch).toHaveBeenNthCalledWith(1, '/auth/config', { credentials: 'same-origin' });
        expect(fetch).toHaveBeenNthCalledWith(2, '/auth/me', { credentials: 'same-origin' });
        expect(auth.isLoggedIn.value).toBe(true);
    });
});