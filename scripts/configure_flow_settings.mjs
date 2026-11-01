import { spawn } from 'node:child_process';

const profileId = process.argv[2] || '731e6d16-b95b-480f-a245-cb443411400d';
const tabId = Number(process.argv[3] || 612097030);

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

// Stop recursion at nested interactive/radio elements so each radio only gets its own direct text!
const ownTexts = (n, root = true) => {
  if (!n) return [];
  if (!root && (n.role === 'radio' || n.role === 'button' || n.role === 'menuitem' || n.role === 'link')) {
    return [];
  }
  const out = [];
  if (n.text) out.push(n.text.trim());
  for (const c of n.children || []) {
    out.push(...ownTexts(c, false));
  }
  return out.filter(Boolean);
};

await req('initialize', {
  protocolVersion: '2024-11-05',
  capabilities: {},
  clientInfo: { name: 'configure-flow', version: '1.0.0' },
});
proc.stdin.write(
  JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized', params: {} }) + '\n'
);

try {
  await call('browser_claim_tab', { profileId, tabId });
  let snap = await call('browser_observe_page', { profileId, tabId });
  let nodes = flat(snap.frames?.[0]?.tree);
  if (!nodes.some((n) => n.role === 'radio')) {
    const settingsBtn = nodes.find(
      (n) => n.ref && n.role === 'button' && n.name === 'Settings trigger'
    );
    if (settingsBtn) {
      await call('browser_click', { profileId, tabId, ref: settingsBtn.ref });
      await new Promise((r) => setTimeout(r, 900));
    }
  }

  const clickRadio = async (matchText) => {
    const s = await call('browser_observe_page', { profileId, tabId });
    const ns = flat(s.frames?.[0]?.tree);
    const radios = ns.filter((n) => n.ref && n.role === 'radio');
    for (const r of radios) {
      console.log(`  radio [${r.ref}] own=${JSON.stringify(ownTexts(r))}`);
    }
    const target = radios.find((r) => ownTexts(r).includes(matchText));
    if (target) {
      console.log(`Clicking radio [${target.ref}] for "${matchText}"`);
      await call('browser_click', { profileId, tabId, ref: target.ref });
      await new Promise((res) => setTimeout(res, 800));
    }
  };

  await clickRadio('Video');
  await clickRadio('9:16');
  await clickRadio('720p');
  await clickRadio('8s');
  await clickRadio('x1');

  snap = await call('browser_observe_page', { profileId, tabId });
  nodes = flat(snap.frames?.[0]?.tree);
  const modelBtn = nodes.find((n) => n.ref && n.role === 'button' && n.name === 'Select model family');
  if (modelBtn) {
    console.log('Clicking Select model family:', modelBtn.ref, ownTexts(modelBtn));
    await call('browser_click', { profileId, tabId, ref: modelBtn.ref });
    await new Promise((r) => setTimeout(r, 900));
    const sm = await call('browser_observe_page', { profileId, tabId });
    const mns = flat(sm.frames?.[0]?.tree);
    for (const n of mns.slice(70)) {
      if (n.ref && (n.interactive || n.role === 'menuitem' || n.role === 'option')) {
        console.log(`  model opt [${n.ref}] role=${n.role} name=${JSON.stringify(n.name)} own=${JSON.stringify(ownTexts(n))}`);
      }
    }
    const veoFast = mns.find(
      (n) =>
        n.ref &&
        (n.role === 'menuitem' || n.role === 'option' || n.interactive) &&
        ownTexts(n).some((t) => /Veo 3\.1\s*-\s*Fast/i.test(t))
    );
    if (veoFast) {
      console.log('Clicking Veo 3.1 - Fast:', veoFast.ref, ownTexts(veoFast));
      await call('browser_click', { profileId, tabId, ref: veoFast.ref });
      await new Promise((r) => setTimeout(r, 900));
    }
  }

  await call('browser_press_key', { profileId, tabId, key: 'Escape' });
  await new Promise((r) => setTimeout(r, 600));
  const finalSnap = await call('browser_observe_page', { profileId, tabId });
  const finalNodes = flat(finalSnap.frames?.[0]?.tree);
  for (const n of finalNodes.slice(50)) {
    if (n.ref && n.interactive) {
      console.log(`  final [${n.ref}] role=${n.role} name=${JSON.stringify(n.name)} own=${JSON.stringify(ownTexts(n))}`);
    }
  }
} finally {
  try {
    await call('browser_release_tab', { profileId, tabId });
  } catch {}
  proc.kill();
}
