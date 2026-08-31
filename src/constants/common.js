export const LOCAL_STORAGE_PREFIX = 'icarusCalculator';

const configuredGameAssetsUrl = import.meta.env.VITE_GAME_ASSETS_URL?.trim();
export const GAME_ASSETS_URL = configuredGameAssetsUrl?.replace(/\/+$/, '') || '/icarus-game';
