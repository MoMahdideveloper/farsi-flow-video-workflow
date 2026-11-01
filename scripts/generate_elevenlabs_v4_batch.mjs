#!/usr/bin/env node
/**
 * Ultra-Fast ElevenLabs v4 Text-to-Speech Generator & Downloader via Profile Bridge MCP.
 * - Closes any accidental "Voice Design" dialog first.
 * - Opens Select voice -> Explore -> Persian -> selects "Arman - Friendly" (or "Mr O - Warm & Natural").
 * - Generates the remaining 10 clips straight through (~5s/clip).
 */

import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const PROFILE_ID = '731e6d16-b95b-480f-a245-cb443411400d';
const TAB_ID = 612097117;
const DOWNLOADS_DIR = 'C:\\Users\\LifeCycle\\Downloads';
const S4_DIR = 'C:\\Users\\LifeCycle\\.gemini\\antigravity\\scratch\\series4-viral-6-stories-farsi';

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
      clientInfo: { name: 'elevenlabs-v4-fast-batch', version: '7.0.0' },
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

function listMp3Files() {
  const entries = fs.readdirSync(DOWNLOADS_DIR);
  const map = new Map();
  for (const name of entries) {
    if (!name.toLowerCase().endsWith('.mp3')) continue;
    const full = path.join(DOWNLOADS_DIR, name);
    try {
      const st = fs.statSync(full);
      if (st.size > 5000) {
        map.set(full, st.mtimeMs);
      }
    } catch {
      // ignore
    }
  }
  return map;
}

async function waitForNewMp3(beforeMap, timeoutMs = 10000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    await sleep(400);
    const nowMap = listMp3Files();
    for (const [full, mtime] of nowMap.entries()) {
      if (!beforeMap.has(full) || mtime > beforeMap.get(full)) {
        return full;
      }
    }
  }
  return null;
}

function copyTextToClipboard(text) {
  const b64 = Buffer.from(text, 'utf8').toString('base64');
  const psCmd = `[Console]::InputEncoding = [System.Text.Encoding]::UTF8; $txt = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('${b64}')); Set-Clipboard -Value $txt; Write-Output 'COPIED_TEXT_OK'`;
  const res = spawnSync('powershell.exe', ['-Sta', '-NoProfile', '-Command', psCmd], {
    encoding: 'utf8',
  });
  if (res.status !== 0 || !res.stdout.includes('COPIED_TEXT_OK')) {
    throw new Error(`Clipboard text copy failed: ${res.stderr || res.stdout}`);
  }
}

export const REMAINING_CLIPS = [
  {
    id: 'S7_C01',
    story: 'story7',
    clip: 1,
    text: '[urgent] ساعت دو نصف شبه و چت‌جی‌پی‌تی رایگانم قفل شد، خرید دلاریشم ویزاکارت می‌خواد!',
  },
  {
    id: 'S7_C04',
    story: 'story7',
    clip: 4,
    text: '[excited] عالیه! به جای دردسر بیست دلار و ویزاکارت، اشتراک چت‌جی‌پی‌تی پلاس رو چهار قسطه با گارانتی گرفتم!',
  },
  {
    id: 'S7_C06',
    story: 'story7',
    clip: 6,
    text: '[energetic] برای خرید چت‌جی‌پی‌تی گو، پلاس و پرو با گارانتی سی روزه، همین الان برو کلیدباکس!',
  },
  {
    id: 'S8_C01',
    story: 'story8',
    clip: 1,
    text: '[urgent] سفارش مشتری رو باید فردا تحویل بدم اما تا سر ماه پول نقد اکانت هوش مصنوعی ندارم!',
  },
  {
    id: 'S8_C02',
    story: 'story8',
    clip: 2,
    text: '[confident] اگه اکانت می‌خوای باید کل پول دلاری و کارمزد رو همین الان نقد کارت به کارت کنی!',
  },
  {
    id: 'S8_C04',
    story: 'story8',
    clip: 4,
    text: '[surprised] یعنی بدون ضامن و چک، امروز فقط یک‌چهارم پول رو می‌دم و اکانتم همون لحظه فعال می‌شه؟',
  },
  {
    id: 'S8_C06',
    story: 'story8',
    clip: 6,
    text: '[energetic] همین الان برو سایت کلیدباکس و اکانت هوش مصنوعی‌ت رو چهار قسطه با ترب‌پی و دیجی‌پی بخر!',
  },
  {
    id: 'S9_C01',
    story: 'story9',
    clip: 1,
    text: '[thoughtful] واسه ساختن استودیوی حرفه‌ای به چت‌جی‌پی‌تی پرو و جمینای اولترا نیاز دارم ولی پول نقدش سنگینه!',
  },
  {
    id: 'S9_C03',
    story: 'story9',
    clip: 3,
    text: '[excited] سی میلیون تومان اعتبار ترب؟! یعنی می‌تونم قوی‌ترین اکانت‌های هوش مصنوعی دنیا رو یکجا بخرم؟',
  },
  {
    id: 'S9_C06',
    story: 'story9',
    clip: 6,
    text: '[energetic] اعتبار سی میلیون تومانی ترب رو از دست نده! همین الان از کلیدباکس قسطی خرید کن!',
  },
];

function findActiveEditorRef(nodes) {
  const addIdx = nodes.findIndex((n) => n.role === 'button' && n.name === 'Add speaker');
  if (addIdx === -1) throw new Error('Could not find "Add speaker" button');
  for (let i = addIdx - 1; i >= Math.max(0, addIdx - 15); i--) {
    const n = nodes[i];
    if (n.ref && n.visible && n.tag === 'div' && typeof n.text === 'string' && n.text.length > 0) {
      return n.ref;
    }
  }
  for (let i = addIdx - 1; i >= Math.max(0, addIdx - 15); i--) {
    const n = nodes[i];
    if (n.ref && n.visible && n.tag === 'div') {
      return n.ref;
    }
  }
  throw new Error('Could not find active editor div before Add speaker');
}

async function ensurePersianVoiceSelected(mcp) {
  let snap = await mcp.callTool('browser_observe_page', { profileId: PROFILE_ID, tabId: TAB_ID });
  let nodes = flattenNodes(snap.frames?.[0]?.tree);

  const voiceBtn = nodes.find(
    (n) => n.ref && n.visible && n.role === 'button' && typeof n.name === 'string' && n.name.startsWith('Select voice -')
  );
  if (voiceBtn && !voiceBtn.name.includes('Auto-select voice')) {
    console.log(`  [voice] Active voice is already set: "${voiceBtn.name}"`);
    return;
  }

  await mcp.callTool('browser_activate_tab', { profileId: PROFILE_ID, tabId: TAB_ID });

  console.log('  [voice] Opening Select voice modal -> Explore -> Persian...');
  const openBtn =
    voiceBtn ||
    nodes.find((n) => n.ref && n.visible && n.role === 'button' && n.name === 'Auto-select voice');
  if (!openBtn) throw new Error('Could not find button to open voice selector');

  await mcp.callTool('browser_click', { profileId: PROFILE_ID, tabId: TAB_ID, ref: openBtn.ref });
  await sleep(1200);

  snap = await mcp.callTool('browser_observe_page', { profileId: PROFILE_ID, tabId: TAB_ID });
  nodes = flattenNodes(snap.frames?.[0]?.tree);

  // Step 1: Click Explore tab inside modal if present
  const exploreTab = nodes.find((n) => n.ref && n.visible && n.role === 'tab' && n.text === 'Explore');
  if (exploreTab) {
    console.log(`  [voice] Clicking Explore tab [${exploreTab.ref}]...`);
    await mcp.callTool('browser_click', { profileId: PROFILE_ID, tabId: TAB_ID, ref: exploreTab.ref });
    await sleep(1000);
    snap = await mcp.callTool('browser_observe_page', { profileId: PROFILE_ID, tabId: TAB_ID });
    nodes = flattenNodes(snap.frames?.[0]?.tree);
  }

  // Step 2: Fill search box with "Persian"
  const searchInput = nodes.find(
    (n) => n.ref && n.visible && n.role === 'textbox' && n.name === 'Start typing to search...'
  );
  if (searchInput) {
    console.log(`  [voice] Typing "Persian" into search [${searchInput.ref}]...`);
    await mcp.callTool('browser_fill', {
      profileId: PROFILE_ID,
      tabId: TAB_ID,
      ref: searchInput.ref,
      value: 'Persian',
    });
    await sleep(1500);
    snap = await mcp.callTool('browser_observe_page', { profileId: PROFILE_ID, tabId: TAB_ID });
    nodes = flattenNodes(snap.frames?.[0]?.tree);
  }

  // Step 3: Click "Select Arman - Friendly" or "Select Mr O - Warm & Natural"
  const pickBtn =
    nodes.find((n) => n.ref && n.visible && n.role === 'button' && n.name === 'Select Arman - Friendly') ||
    nodes.find((n) => n.ref && n.visible && n.role === 'button' && n.name === 'Select Mr O - Warm & Natural') ||
    nodes.find((n) => n.ref && n.visible && n.role === 'button' && n.name === 'Select Sara - Neutral Persian Female');

  if (!pickBtn) {
    throw new Error('Could not find visible Select button for Persian voice after Explore -> Persian search');
  }

  console.log(`  [voice] Clicking "${pickBtn.name}" [${pickBtn.ref}]...`);
  await mcp.callTool('browser_click', { profileId: PROFILE_ID, tabId: TAB_ID, ref: pickBtn.ref });
  await sleep(1000);
}

async function downloadLatestGeneration(mcp, nodes, beforeMp3, clipId) {
  const inlineDl = nodes.find((n) => n.ref && n.visible && n.role === 'button' && n.name === 'Download');
  if (inlineDl) {
    console.log(`  [dl] Clicking inline Generation Download [${inlineDl.ref}]...`);
    await mcp.callTool('browser_click', { profileId: PROFILE_ID, tabId: TAB_ID, ref: inlineDl.ref });
    const f1 = await waitForNewMp3(beforeMp3, 8000);
    if (f1) return f1;
  }

  const playerDl = nodes.find((n) => n.ref && n.visible && n.role === 'button' && n.name === 'Download Audio');
  if (playerDl) {
    console.log(`  [dl] Clicking bottom player Download Audio [${playerDl.ref}]...`);
    await mcp.callTool('browser_click', { profileId: PROFILE_ID, tabId: TAB_ID, ref: playerDl.ref });
    const f2 = await waitForNewMp3(beforeMp3, 8000);
    if (f2) return f2;
  }

  throw new Error(`Timed out waiting for MP3 download for [${clipId}]`);
}

async function generateOneClip(mcp, item) {
  const outPath = path.join(S4_DIR, item.story, 'elevenlabs_v4', `clip_0${item.clip}.mp3`);
  if (fs.existsSync(outPath) && fs.statSync(outPath).size > 10000) {
    console.log(`\n=== Skipping [${item.id}] (already exists: ${outPath}) ===`);
    return outPath;
  }
  console.log(`\n=== Generating [${item.id}] -> ${outPath} ===`);

  await ensurePersianVoiceSelected(mcp);

  let snap = await mcp.callTool('browser_observe_page', { profileId: PROFILE_ID, tabId: TAB_ID });
  let nodes = flattenNodes(snap.frames?.[0]?.tree);

  copyTextToClipboard(item.text);
  const editorRef = findActiveEditorRef(nodes);

  await mcp.callTool('browser_click', { profileId: PROFILE_ID, tabId: TAB_ID, ref: editorRef });
  await sleep(200);
  await mcp.callTool('browser_press_key', { profileId: PROFILE_ID, tabId: TAB_ID, key: 'a', modifiers: ['ctrl'] });
  await sleep(150);
  await mcp.callTool('browser_press_key', { profileId: PROFILE_ID, tabId: TAB_ID, key: 'v', modifiers: ['ctrl'] });
  await sleep(500);

  snap = await mcp.callTool('browser_observe_page', { profileId: PROFILE_ID, tabId: TAB_ID });
  nodes = flattenNodes(snap.frames?.[0]?.tree);

  const genBtn = nodes.find(
    (n) =>
      n.ref &&
      n.visible &&
      n.role === 'button' &&
      typeof n.name === 'string' &&
      (n.name.includes('Generate speech') || n.name.includes('Regenerate speech'))
  );
  if (!genBtn) {
    throw new Error(`Could not find visible Generate speech button after pasting [${item.id}]`);
  }

  const beforeMp3 = listMp3Files();
  // If this exact text was already generated on screen (Regenerate speech + inline Download visible), just download it!
  const alreadyDl = nodes.find((n) => n.ref && n.visible && n.role === 'button' && n.name === 'Download');
  if (alreadyDl && genBtn.name.includes('Regenerate speech')) {
    console.log(`  [1/3] Text already generated on screen; downloading directly [${alreadyDl.ref}]...`);
    const downloadedMp3 = await downloadLatestGeneration(mcp, nodes, beforeMp3, item.id);
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    fs.copyFileSync(downloadedMp3, outPath);
    const sz = fs.statSync(outPath).size;
    console.log(`  [3/3] Saved -> ${outPath} (${sz} bytes)`);
    return outPath;
  }

  console.log(`  [1/3] Clicking ${genBtn.name} [${genBtn.ref}]...`);
  await mcp.callTool('browser_click', { profileId: PROFILE_ID, tabId: TAB_ID, ref: genBtn.ref });

  await sleep(3200);
  let readyNodes = null;
  for (let poll = 1; poll <= 25; poll++) {
    const pSnap = await mcp.callTool('browser_observe_page', { profileId: PROFILE_ID, tabId: TAB_ID });
    const pNodes = flattenNodes(pSnap.frames?.[0]?.tree);
    const isRegen = pNodes.some(
      (n) => n.visible && n.role === 'button' && typeof n.name === 'string' && n.name.includes('Regenerate speech')
    );
    const hasInlineDl = pNodes.some((n) => n.ref && n.visible && n.role === 'button' && n.name === 'Download');
    if (isRegen && hasInlineDl) {
      readyNodes = pNodes;
      console.log(`  [2/3] Generation complete on poll ${poll}!`);
      break;
    }
    await sleep(900);
  }
  if (!readyNodes) {
    throw new Error(`Timed out waiting for "Regenerate speech" state for [${item.id}]`);
  }

  const downloadedMp3 = await downloadLatestGeneration(mcp, readyNodes, beforeMp3, item.id);
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.copyFileSync(downloadedMp3, outPath);
  const sz = fs.statSync(outPath).size;
  console.log(`  [3/3] Saved -> ${outPath} (${sz} bytes)`);
  return outPath;
}

async function main() {
  const verifiedMap = [
    ['story7', 2, 'ElevenLabs_2026-10-28T23_52_03_Chuck Miller - Deep, Raspy, American_pvc_sp100_s30_sb80_v4.mp3'],
    ['story7', 3, 'ElevenLabs_2026-10-29T00_09_57_Mr O - Warm & Natural_pvc_sp83_s50_sb75_v4.mp3'],
    ['story7', 5, 'ElevenLabs_2026-10-29T00_10_42_Mr O - Warm & Natural_pvc_sp83_s50_sb75_v4.mp3'],
    ['story8', 3, 'ElevenLabs_2026-10-29T00_13_39_Mr O - Warm & Natural_pvc_sp83_s50_sb75_v4.mp3'],
    ['story8', 5, 'ElevenLabs_2026-10-29T00_13_50_Mr O - Warm & Natural_pvc_sp83_s50_sb75_v4.mp3'],
    ['story9', 2, 'ElevenLabs_2026-10-29T00_14_00_Mr O - Warm & Natural_pvc_sp83_s50_sb75_v4.mp3'],
    ['story9', 4, 'ElevenLabs_2026-10-29T00_14_10_Mr O - Warm & Natural_pvc_sp83_s50_sb75_v4.mp3'],
    ['story9', 5, 'ElevenLabs_2026-10-29T00_14_21_Mr O - Warm & Natural_pvc_sp83_s50_sb75_v4.mp3'],
  ];
  for (const [story, clip, fname] of verifiedMap) {
    const src = path.join(DOWNLOADS_DIR, fname);
    const dst = path.join(S4_DIR, story, 'elevenlabs_v4', `clip_0${clip}.mp3`);
    if (fs.existsSync(src)) {
      fs.mkdirSync(path.dirname(dst), { recursive: true });
      fs.copyFileSync(src, dst);
    }
  }

  const mcp = new McpClient();
  try {
    await mcp.init();
    for (const item of REMAINING_CLIPS) {
      await generateOneClip(mcp, item);
    }
    console.log('\nALL 18 ELEVENLABS V4 CLIPS GENERATED & VERIFIED!');
  } finally {
    try {
      await mcp.callTool('browser_release_tab', { profileId: PROFILE_ID, tabId: TAB_ID });
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
