import { spawn } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { loadEnv } from 'vite';
const root = fileURLToPath(new URL('../', import.meta.url));
const configured={...loadEnv('development',root,''),...process.env};
const port = configured.RCA_PORT || '3015';
const env = { ...configured, RCA_PORT: port, RCA_WORKER_TOKEN: configured.RCA_WORKER_TOKEN || randomBytes(32).toString('hex'),
  WRANGLER_WRITE_LOGS: 'false', WRANGLER_LOG_PATH: '.wrangler/logs', MINIFLARE_REGISTRY_PATH: '.wrangler/registry' };
const executable = name => fileURLToPath(new URL(`../node_modules/.bin/${name}`, import.meta.url));
async function command(binary, args) {
  const child = spawn(binary, args, { cwd: root, env, stdio: 'inherit' });
  await new Promise((resolve, reject) => { child.once('error', reject); child.once('exit', code => code === 0 ? resolve() : reject(new Error(`${binary} exited ${code}`))); });
}
await command(executable('wrangler'), ['d1','migrations','apply','DB','--local','--config','wrangler.local.json','--persist-to','.wrangler/state']);
// D1/R2 require the local Cloudflare runtime. vinext's Node production server
// does not supply those bindings; deployment is intentionally out of scope.
const server = spawn(executable('vinext'), ['dev', '--hostname','127.0.0.1','--port',port], { cwd: root, env, stdio: 'inherit' });
const worker = spawn(process.execPath, [fileURLToPath(new URL('./task-worker.mjs', import.meta.url))], { cwd: root, env, stdio: 'inherit' });
let stopping = false;
function stop(code = 0) { if (stopping) return; stopping = true; worker.kill('SIGTERM'); server.kill('SIGTERM'); process.exitCode = code; }
process.on('SIGINT', () => stop()); process.on('SIGTERM', () => stop());
server.on('error', e => { console.error(e); stop(1); }); worker.on('error', e => { console.error(e); stop(1); });
server.on('exit', code => stop(code || 0)); worker.on('exit', code => { if (!stopping) stop(code || 1); });
