import { readdir, stat } from 'node:fs/promises';
import path, { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Hono } from 'hono';
import type { Handler } from 'hono/types';
import updatedFetch from '../src/__create/fetch';
import { pathToFileURL } from 'node:url';


const API_BASENAME = '/api';
const api = new Hono();

// Fix fetch for Node runtime
if (globalThis.fetch) {
  globalThis.fetch = updatedFetch;
}

// Resolve API directory
const __dirname = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '../src/app/api'
);

// Cache loaded route modules
const routeCache = new Map<string, any>();

// Recursively find all route.js files
async function findRouteFiles(dir: string): Promise<string[]> {
  const files = await readdir(dir);
  let routes: string[] = [];

  for (const file of files) {
    const filePath = join(dir, file);
    const stats = await stat(filePath);

    if (stats.isDirectory()) {
      routes = routes.concat(await findRouteFiles(filePath));
    } else if (file === 'route.js') {
      routes.push(filePath);
    }
  }

  return routes;
}

// Convert file path → Hono route path
function getHonoPath(routeFile: string): string {
  const relative = routeFile.replace(__dirname, '');
  const parts = relative
    .split(/[\\/]/)        // Windows-safe
    .filter(Boolean)
    .slice(0, -1);         // remove route.js

  if (parts.length === 0) return '/';

  return (
    '/' +
    parts
      .map((segment) => {
        const match = segment.match(/^\[(\.{3})?([^\]]+)\]$/);
        if (!match) return segment;
        const [, dots, param] = match;
        return dots ? `:${param}{.+}` : `:${param}`;
      })
      .join('/')
  );
}

// Load module with cache
async function loadRoute(routeFile: string) {
  if (!routeCache.has(routeFile)) {
    const mod = await import(
  /* @vite-ignore */ pathToFileURL(routeFile).href
  );

    routeCache.set(routeFile, mod);
  }
  return routeCache.get(routeFile);
}

// Register routes
async function registerRoutes() {
  const routeFiles = (await findRouteFiles(__dirname)).sort(
    (a, b) => b.length - a.length
  );

  // Reset router safely
  api.router = new Hono().router;

  for (const routeFile of routeFiles) {
    try {
      const route = await loadRoute(routeFile);
      const honoPath = getHonoPath(routeFile);

      for (const method of ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']) {
        if (!route[method]) continue;

        const handler: Handler = async (c) => {
          return route[method](c.req.raw, { params: c.req.param() });
        };

        switch (method) {
          case 'GET':
            api.get(honoPath, handler);
            break;
          case 'POST':
            api.post(honoPath, handler);
            break;
          case 'PUT':
            api.put(honoPath, handler);
            break;
          case 'DELETE':
            api.delete(honoPath, handler);
            break;
          case 'PATCH':
            api.patch(honoPath, handler);
            break;
        }
      }
    } catch (err) {
      console.error(`Failed to load route: ${routeFile}`, err);
    }
  }
}

// Initial load
await registerRoutes();

// Dev reload support (SAFE)
if (import.meta.env.DEV && import.meta.hot) {
  import.meta.hot.accept(() => {
    routeCache.clear();
    registerRoutes().catch((err) =>
      console.error('Failed to reload routes', err)
    );
  });
}

export { api, API_BASENAME };
