// Placeholder for local dev (`npm run dev` / `npm run preview`) -- the
// production container overwrites this at startup via docker-entrypoint.sh,
// injecting the real API_URL from the runtime environment. Left empty here
// so config.ts falls through to VITE_API_URL, then a localhost default.
window.__ENV__ = {};
