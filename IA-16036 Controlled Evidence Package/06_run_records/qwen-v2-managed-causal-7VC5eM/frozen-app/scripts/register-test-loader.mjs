// Node-only test adapter for the app's existing Vite aliases and ?raw prompts.
// Production modules are imported unchanged; no provider is substituted here.
import { registerHooks } from 'node:module';
import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
const root = new URL('../', import.meta.url);
registerHooks({
  resolve(specifier, context, nextResolve) {
    if (specifier === 'cloudflare:workers') return { url: specifier, shortCircuit: true };
    let url;
    if (specifier.startsWith('@/')) url = new URL(specifier.slice(2), root);
    else if (specifier.startsWith('.') && context.parentURL?.startsWith('file:')) url = new URL(specifier, context.parentURL);
    if (url) {
      if (url.search === '?raw') return { url: url.href, shortCircuit: true };
      const base = fileURLToPath(url);
      for (const suffix of ['.ts', '/index.ts']) {
        if (existsSync(base + suffix)) return { url: pathToFileURL(base + suffix).href, shortCircuit: true };
      }
    }
    return nextResolve(specifier, context);
  },
  load(url, context, nextLoad) {
    if (url === 'cloudflare:workers') return {
      format: 'module', source: 'export const env = new Proxy({}, {get(){throw new Error("Tests must not access a real Cloudflare binding");}});', shortCircuit: true,
    };
    if (url.startsWith('file:') && url.endsWith('?raw')) return {
      format: 'module', source: `export default ${JSON.stringify(readFileSync(new URL(url), 'utf8'))};`, shortCircuit: true,
    };
    return nextLoad(url, context);
  },
});
