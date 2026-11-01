import { spawn } from 'node:child_process';

const profileId = process.argv[2] || 'ba220a18-ed4b-443c-a1af-70cf5fd45db1';
const tabId = Number(process.argv[3] || 612096971);

const proc = spawn(
  'C:\\Program Files\\nodejs\\node.exe',
  ['C:\\Users\\LifeCycle\\AppData\\Local\\ProfileBridge\\mcp-adapter.js'],
  {
    env: {
      ...process.env,
      PB_BROKER_ENTRY: 'C:\\Users\\LifeCycle\\AppData\\Local\\ProfileBridge\\broker.js',
    },
    stdio: ['pipe', 'pipe', 'inherit'],
  }
);

let nextId = 1;
let buf = '';
const pending = new Map();
proc.stdout.setEncoding('utf8');
proc.stdout.on('data', (c) => {
  buf += c;
  let i;
  while ((i = buf.indexOf('\n')) !== -1) {
    const line = buf.slice(0, i).trim();
    buf = buf.slice(i + 1);
    if (!line) continue;
    try {
      const m = JSON.parse(line);
      if (m.id && pending.has(m.id)) {
        const { resolve, reject } = pending.get(m.id);
        pending.delete(m.id);
        m.error ? reject(new Error(JSON.stringify(m.error))) : resolve(m.result);
      }
    } catch {}
  }
});

const req = (method, params = {}) =>
  new Promise((resolve, reject) => {
    const id = nextId++;
    pending.set(id, { resolve, reject });
    proc.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n');
  });

const call = async (name, args) => {
  const r = await req('tools/call', { name, arguments: args });
  if (r?.isError) throw new Error(r?.content?.[0]?.text || JSON.stringify(r));
  return r?.content?.[0]?.text ? JSON.parse(r.content[0].text) : r;
};

const flat = (n, out = []) => {
  if (!n) return out;
  out.push(n);
  for (const c of n.children || []) flat(c, out);
  return out;
};

await req('initialize', {
  protocolVersion: '2024-11-05',
  capabilities: {},
  clientInfo: { name: 'open-flow-project', version: '1.0.0' },
});
proc.stdin.write(
  JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized', params: {} }) + '\n'
);

try {
  await call('browser_activate_tab', { profileId, tabId });
  await call('browser_claim_tab', { profileId, tabId });
  const snap = await call('browser_observe_page', { profileId, tabId });
  const nodes = flat(snap.frames?.[0]?.tree);
  const dismiss = nodes.find(
    (n) => n.ref && n.role === 'button' && (n.name === 'Dismiss banner' || n.name === 'بستن برنما')
  );
  if (dismiss) {
    console.log('Dismissing banner:', dismiss.ref);
    await call('browser_click', { profileId, tabId, ref: dismiss.ref });
    await new Promise((r) => setTimeout(r, 800));
  }
  const snap2 = await call('browser_observe_page', { profileId, tabId });
  const nodes2 = flat(snap2.frames?.[0]?.tree);
  const target =
    nodes2.find(
      (n) =>
        n.ref &&
        n.role === 'button' &&
        typeof n.name === 'string' &&
        (n.name.includes('New project') || n.name.includes('پروژه جدید'))
    ) ||
    nodes2.find(
      (n) =>
        n.ref &&
        n.role === 'link' &&
        (n.name === 'Open project' || n.name === 'باز کردن پروژه')
    );
  console.log('Clicking target:', target?.ref, target?.name);
  if (target) {
    await call('browser_click', { profileId, tabId, ref: target.ref });
    await new Promise((r) => setTimeout(r, 5000));
  }
  const snap3 = await call('browser_observe_page', { profileId, tabId });
  console.log('Final URL:', snap3.url);
  const nodes3 = flat(snap3.frames?.[0]?.tree);
  for (const n of nodes3) {
    if (n.ref && n.interactive) {
      console.log(`  [${n.ref}] ${n.role} name=${JSON.stringify(n.name)} text=${JSON.stringify(n.text)}`);
    }
  }
} finally {
  try {
    await call('browser_release_tab', { profileId, tabId });
  } catch {}
  proc.kill();
}
