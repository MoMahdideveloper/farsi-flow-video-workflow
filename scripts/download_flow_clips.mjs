#!/usr/bin/env node
/**
 * Automated Google Flow Video Downloader via Profile Bridge MCP.
 * Supports both Row View (direct "Download" button) and Grid View ("More options" / "گزینه‌های بیشتر" -> "Download" / "بارگیری" -> "720p" / "۷۲۰ پیکسل").
 *
 * Usage:
 *   node scripts/download_flow_clips.mjs --profile <id> --tab <id> --match "Banana man spraying" --out "C:\\...\\clip_01.mp4"
 */

import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const DOWNLOADS_DIR = 'C:\\Users\\LifeCycle\\Downloads';

class McpClient {
  constructor() {
    this.proc = spawn(
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
    this.nextId = 1;
    this.pending = new Map();
    this.buffer = '';

    this.proc.stdout.setEncoding('utf8');
    this.proc.stdout.on('data', (chunk) => {
      this.buffer += chunk;
      let idx;
      while ((idx = this.buffer.indexOf('\n')) !== -1) {
        const line = this.buffer.slice(0, idx).trim();
        this.buffer = this.buffer.slice(idx + 1);
        if (!line) continue;
        try {
          const msg = JSON.parse(line);
          if (msg.id && this.pending.has(msg.id)) {
            const { resolve, reject } = this.pending.get(msg.id);
            this.pending.delete(msg.id);
            if (msg.error) reject(new Error(JSON.stringify(msg.error)));
            else resolve(msg.result);
          }
        } catch {
          // ignore
        }
      }
    });
  }

  request(method, params = {}) {
    const id = this.nextId++;
    const payload = JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n';
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.proc.stdin.write(payload);
    });
  }

  async init() {
    await this.request('initialize', {
      protocolVersion: '2024-11-05',
      capabilities: {},
      clientInfo: { name: 'flow-downloader', version: '1.0.0' },
    });
    this.proc.stdin.write(
      JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized', params: {} }) + '\n'
    );
  }

  async callTool(name, args) {
    const res = await this.request('tools/call', { name, arguments: args });
    if (res?.isError) {
      const txt = res?.content?.[0]?.text || JSON.stringify(res);
      throw new Error(`Tool ${name} failed: ${txt}`);
    }
    const txt = res?.content?.[0]?.text;
    return txt ? JSON.parse(txt) : res;
  }

  close() {
    this.proc.kill();
  }
}

function flattenNodes(node, out = []) {
  if (!node || typeof node !== 'object') return out;
  out.push(node);
  if (Array.isArray(node.children)) {
    for (const child of node.children) flattenNodes(child, out);
  }
  return out;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function listMp4Files() {
  const entries = fs.readdirSync(DOWNLOADS_DIR);
  const map = new Map();
  for (const name of entries) {
    if (!name.toLowerCase().endsWith('.mp4')) continue;
    const full = path.join(DOWNLOADS_DIR, name);
    try {
      const st = fs.statSync(full);
      if (st.size > 100000) {
        map.set(full, st.mtimeMs);
      }
    } catch {
      // ignore
    }
  }
  return map;
}

async function waitForNewMp4(beforeMap, timeoutMs = 20000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    await sleep(1000);
    const nowMap = listMp4Files();
    for (const [full, mtime] of nowMap.entries()) {
      if (!beforeMap.has(full) || mtime > beforeMap.get(full)) {
        return full;
      }
    }
  }
  return null;
}

async function cleanFailedTiles(mcp, profileId, tabId) {
  for (let round = 0; round < 6; round++) {
    const snap = await mcp.callTool('browser_observe_page', { profileId, tabId });
    const nodes = flattenNodes(snap.frames?.[0]?.tree);
    const delBtn = nodes.find(
      (n) => n.ref && n.role === 'button' && (n.name === 'Delete' || n.name === 'حذف')
    );
    if (!delBtn) break;
    console.log(`  [clean] Deleting failed tile [${delBtn.ref}] (${delBtn.name})...`);
    await mcp.callTool('browser_click', { profileId, tabId, ref: delBtn.ref });
    await sleep(1000);
  }
}

async function downloadOne(mcp, profileId, tabId, matchSubstr, outPath) {
  console.log(`\n=== Looking for tile matching "${matchSubstr}" -> ${outPath} ===`);
  let snap = null;
  let interactive = [];
  let idx = -1;
  for (let scrollTry = 0; scrollTry < 5; scrollTry++) {
    snap = await mcp.callTool('browser_observe_page', { profileId, tabId });
    const nodes = flattenNodes(snap.frames?.[0]?.tree);
    interactive = nodes.filter((n) => n.ref && n.interactive);
    idx = interactive.findIndex(
      (n) =>
        n.role === 'button' &&
        typeof n.name === 'string' &&
        n.name.toLowerCase().includes(matchSubstr.toLowerCase())
    );
    if (idx !== -1) break;
    console.log(`  [scroll ${scrollTry + 1}] Tile not in current viewport, pressing PageDown...`);
    await mcp.callTool('browser_press_key', {
      profileId,
      tabId,
      key: 'PageDown',
    });
    await sleep(1200);
  }
  if (idx === -1) {
    console.log('  [!] Tile not found! Available video tiles:');
    for (const n of interactive) {
      if (n.role === 'button' && n.name) {
        console.log(`      - [${n.ref}] ${n.name}`);
      }
    }
    throw new Error(`Could not find tile matching "${matchSubstr}"`);
  }

  const tile = interactive[idx];
  console.log(`  [1/3] Found tile [${tile.ref}] "${tile.name}"`);
  const beforeMap = listMp4Files();

  // Check if one of the next interactive buttons is direct "Download" or "بارگیری" (Row view)
  const nextBtn = interactive
    .slice(idx + 1, idx + 4)
    .find((b) => b && (b.name === 'Download' || b.name === 'بارگیری'));
  const prevBtn = interactive[idx - 1];
  if (nextBtn) {
    console.log(`  [2/3] Clicking direct Download button [${nextBtn.ref}]...`);
    await mcp.callTool('browser_click', { profileId, tabId, ref: nextBtn.ref });
  } else if (prevBtn && (prevBtn.name === 'More options' || prevBtn.name === 'گزینه‌های بیشتر')) {
    console.log(`  [2/3] Clicking More options [${prevBtn.ref}]...`);
    await mcp.callTool('browser_click', { profileId, tabId, ref: prevBtn.ref });
    await sleep(1000);
    const menuSnap = await mcp.callTool('browser_observe_page', { profileId, tabId });
    const allMenuNodes = flattenNodes(menuSnap.frames?.[0]?.tree);
    const dlMenuItem = allMenuNodes.find(
      (n) =>
        n.role === 'menuitem' &&
        flattenNodes(n).some((c) => c.text === 'Download' || c.text === 'بارگیری' || c.text === 'download')
    );
    if (!dlMenuItem) throw new Error('Could not find Download menuitem');
    console.log(`  [2b/3] Clicking Download menuitem [${dlMenuItem.ref}]...`);
    await mcp.callTool('browser_click', { profileId, tabId, ref: dlMenuItem.ref });
    await sleep(1100);
    const subSnap = await mcp.callTool('browser_observe_page', { profileId, tabId });
    const allSubNodes = flattenNodes(subSnap.frames?.[0]?.tree);
    const res720 = [...allSubNodes].reverse().find(
      (n) =>
        n.role === 'menuitem' &&
        flattenNodes(n).some(
          (c) => typeof c.text === 'string' && (c.text.includes('720') || c.text.includes('۷۲۰'))
        )
    );
    if (res720) {
      console.log(`  [2c/3] Clicking 720p option [${res720.ref}]...`);
      await mcp.callTool('browser_click', { profileId, tabId, ref: res720.ref });
    }
  } else {
    throw new Error(`Neither direct Download nor More options found adjacent to [${tile.ref}]`);
  }

  const downloadedFile = await waitForNewMp4(beforeMap, 25000);
  if (!downloadedFile) {
    throw new Error(`Timed out waiting for MP4 download for "${tile.name}"`);
  }
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.copyFileSync(downloadedFile, outPath);
  const sz = fs.statSync(outPath).size;
  console.log(`  [3/3] Saved ${downloadedFile} -> ${outPath} (${sz} bytes)`);
}

async function main() {
  const argv = process.argv.slice(2);
  let profileId = '731e6d16-b95b-480f-a245-cb443411400d';
  let tabId = 612095035;
  let listOnly = false;
  const pairs = [];
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--profile' && argv[i + 1]) profileId = argv[++i];
    else if (argv[i] === '--tab' && argv[i + 1]) tabId = Number(argv[++i]);
    else if (argv[i] === '--list') listOnly = true;
    else if (argv[i] === '--match' && argv[i + 1]) {
      const match = argv[++i];
      if (argv[i + 1] === '--out' && argv[i + 2]) {
        const out = argv[i + 2];
        i += 2;
        pairs.push({ match, out });
      }
    } else if (argv[i] === '--ref' && argv[i + 1]) {
      const ref = argv[++i];
      if (argv[i + 1] === '--out' && argv[i + 2]) {
        const out = argv[i + 2];
        i += 2;
        pairs.push({ ref, out });
      }
    }
  }

  const mcp = new McpClient();
  try {
    await mcp.init();
    const initSnap = await mcp.callTool('browser_observe_page', { profileId, tabId });
    const initNodes = flattenNodes(initSnap.frames?.[0]?.tree);
    const videosTab = initNodes.find(
      (n) =>
        n.role === 'button' &&
        typeof n.name === 'string' &&
        (n.name.includes('videocam Videos') || n.name.includes('videocam ویدیوها'))
    );
    if (videosTab) {
      await mcp.callTool('browser_click', { profileId, tabId, ref: videosTab.ref });
      await sleep(1200);
    }
    await cleanFailedTiles(mcp, profileId, tabId);
    if (listOnly) {
      const snap = await mcp.callTool('browser_observe_page', { profileId, tabId });
      const nodes = flattenNodes(snap.frames?.[0]?.tree);
      for (const n of nodes) {
        if (n.ref && (n.interactive || (typeof n.text === 'string' && n.text.length > 15))) {
          console.log(`[${n.ref}] role=${n.role} name=${JSON.stringify(n.name)} text=${JSON.stringify(n.text)}`);
        }
      }
      return;
    }
    for (const p of pairs) {
      if (p.ref) {
        const beforeMap = listMp4Files();
        console.log(`\n=== Clicking direct ref [${p.ref}] -> ${p.out} ===`);
        await mcp.callTool('browser_click', { profileId, tabId, ref: p.ref });
        const downloadedFile = await waitForNewMp4(beforeMap, 25000);
        if (!downloadedFile) throw new Error(`Timed out waiting for MP4 download from ref ${p.ref}`);
        fs.mkdirSync(path.dirname(p.out), { recursive: true });
        fs.copyFileSync(downloadedFile, p.out);
        console.log(`  Saved ${downloadedFile} -> ${p.out} (${fs.statSync(p.out).size} bytes)`);
      } else {
        await downloadOne(mcp, profileId, tabId, p.match, p.out);
      }
    }
  } finally {
    try {
      await mcp.callTool('browser_release_tab', { profileId, tabId });
    } catch {
      // ignore
    }
    mcp.close();
  }
}

main().catch((err) => {
  console.error('FATAL:', err);
  process.exit(1);
});
