#!/usr/bin/env node
/**
 * shellion MCP driver — a tiny stdio MCP client for testing the server
 * without an AI agent. It spawns server.py, performs the MCP handshake,
 * then lists tools or calls one over SSH.
 *
 * Usage:
 *   node tools/mcp_driver.js list
 *   node tools/mcp_driver.js run "uptime"
 *   node tools/mcp_driver.js run --device server "uptime"
 *   node tools/mcp_driver.js upload ./file.txt /tmp/file.txt
 *   node tools/mcp_driver.js download /tmp/file.txt ./file.txt
 *
 * Environment overrides:
 *   SHELLION_PYTHON         Python interpreter (default: .venv in this repo)
 *   SHELLION_SERVER         server.py path     (default: server.py in this repo)
 *   SSH_CREDENTIALS_FILE    passed through to the server; a Documents-level
 *                           ssh_credential.json is used when it exists
 */
const { spawn } = require('child_process');
const path = require('path');
const os = require('os');
const fs = require('fs');

const REPO = path.resolve(__dirname, '..');
const PY = process.env.SHELLION_PYTHON
  || path.join(REPO, '.venv', process.platform === 'win32' ? 'Scripts' : 'bin',
              process.platform === 'win32' ? 'python.exe' : 'python');
const SERVER = process.env.SHELLION_SERVER || path.join(REPO, 'server.py');
const CRED = process.env.SSH_CREDENTIALS_FILE
  || [path.join(os.homedir(), 'Documents', 'ssh_credential.json')].find(p => fs.existsSync(p))
  || undefined;

const argv = process.argv.slice(2);
const action = argv[0] || 'list';

// pull --key value / --flag options out of the argument list
const opts = {};
const rest = [];
for (let i = 1; i < argv.length; i++) {
  const a = argv[i];
  if (a.startsWith('--')) {
    const key = a.slice(2);
    if (i + 1 < argv.length && !argv[i + 1].startsWith('--')) { opts[key] = argv[++i]; }
    else opts[key] = true;
  } else rest.push(a);
}

const child = spawn(PY, [SERVER], {
  env: { ...process.env, PYTHONUNBUFFERED: '1', ...(CRED ? { SSH_CREDENTIALS_FILE: CRED } : {}) },
  stdio: ['pipe', 'pipe', 'pipe'],
});

let buf = '';
const pending = new Map();
const log = (...a) => process.stderr.write(a.join(' ') + '\n');

child.stdout.on('data', d => {
  buf += d.toString('utf8');
  let i;
  while ((i = buf.indexOf('\n')) >= 0) {
    const line = buf.slice(0, i).trim();
    buf = buf.slice(i + 1);
    if (!line) continue;
    let msg;
    try { msg = JSON.parse(line); } catch { log('non-json stdout line:', line.slice(0, 200)); continue; }
    if (msg.id !== undefined && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) reject(new Error(JSON.stringify(msg.error))); else resolve(msg.result);
    } else {
      log('server note:', JSON.stringify(msg).slice(0, 300));
    }
  }
});
child.stderr.on('data', d => log('[server-stderr]', d.toString().trim()));
child.on('error', e => { log('failed to start server:', e.message, '(try SHELLION_PYTHON=...)'); process.exit(1); });
child.on('exit', c => { if (c) { log('server exited with code', c); process.exit(1); } });

const send = obj => child.stdin.write(JSON.stringify(obj) + '\n');
function request(id, method, params) {
  return new Promise((resolve, reject) => {
    // clear the timer on settle, otherwise node stays alive for 90s
    const timer = setTimeout(() => {
      if (pending.has(id)) { pending.delete(id); reject(new Error('timeout waiting for ' + method)); }
    }, 90000);
    const settle = fn => value => { clearTimeout(timer); fn(value); };
    pending.set(id, { resolve: settle(resolve), reject: settle(reject) });
    send({ jsonrpc: '2.0', id, method, params });
  });
}

// device/host/port/username apply to every tool call
function overrides(extra) {
  const args = { ...extra };
  if (opts.device) args.device = opts.device;
  if (opts.host) args.host = opts.host;
  if (opts.port) args.port = Number(opts.port);
  if (opts.username) args.username = opts.username;
  return args;
}

(async () => {
  const init = await request(1, 'initialize', {
    protocolVersion: '2024-11-05',
    capabilities: {},
    clientInfo: { name: 'shellion-driver', version: '1.0' },
  });
  log(`connected: ${init.serverInfo.name} (protocol ${init.protocolVersion})`);
  send({ jsonrpc: '2.0', method: 'notifications/initialized' });

  if (action === 'list') {
    const tools = await request(2, 'tools/list', {});
    console.log('available tools:');
    for (const t of tools.tools) console.log(`- ${t.name}: ${String(t.description).trim().split('\n')[0]}`);
  } else {
    const calls = {
      run: ['run_command', () => overrides({ command: rest.join(' ') })],
      upload: ['upload_file', () => overrides({ local_path: rest[0], remote_path: rest[1] })],
      download: ['download_file', () => overrides({ remote_path: rest[0], local_path: rest[1] })],
    }[action];
    if (!calls) throw new Error('unknown action "' + action + '" (use list | run | upload | download)');
    if (action !== 'list' && rest.length === 0) throw new Error('missing arguments for ' + action);
    const [name, buildArgs] = calls;
    const args = buildArgs();
    log(`calling ${name}: ${JSON.stringify(args)}`);
    const res = await request(3, 'tools/call', { name, arguments: args });
    for (const c of (res.content || [])) console.log(c.text !== undefined ? c.text : JSON.stringify(c));
    if (res.isError) process.exitCode = 1;
  }

  child.kill();
})().catch(e => { console.error('DRIVER ERROR:', e.message); child.kill(); process.exit(1); });
