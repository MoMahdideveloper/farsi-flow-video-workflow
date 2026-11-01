#!/usr/bin/env node
/**
 * Fast Batch Generator for Gemini 3.8 Flash TTS in Google AI Studio via Profile Bridge MCP.
 * Generates all 18 Persian voice clips across Stories 7, 8, and 9 using two distinct male voices:
 * - Pass 1 (Voice 1: "Koda" - Direct & helpful, Medium-low pitch): 11 protagonist/friend clips
 * - Pass 2 (Voice 2: "Neno" - Deep & velvety, Deep pitch): 7 boss/advisor/secondary clips
 * Saves each clip to story{7,8,9}/gemini_tts/clip_0X.wav and verifies unique SHA-256 hashes.
 */

import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

const PROFILE_ID = '731e6d16-b95b-480f-a245-cb443411400d';
const TAB_ID = 612097134;
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
      clientInfo: { name: 'gemini-38-flash-tts-batch', version: '1.1.0' },
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

function sha256File(filePath) {
  return createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

function listWavFiles() {
  const entries = fs.readdirSync(DOWNLOADS_DIR);
  const map = new Map();
  for (const name of entries) {
    if (!name.toLowerCase().endsWith('.wav')) continue;
    const full = path.join(DOWNLOADS_DIR, name);
    try {
      const st = fs.statSync(full);
      if (st.size > 10000) {
        map.set(full, st.mtimeMs);
      }
    } catch {
      // ignore
    }
  }
  return map;
}

async function waitForNewWav(beforeMap, timeoutMs = 8000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    await sleep(350);
    const nowMap = listWavFiles();
    for (const [full, mtime] of nowMap.entries()) {
      if (!beforeMap.has(full) || mtime > beforeMap.get(full)) {
        return full;
      }
    }
  }
  return null;
}

const PASS1_KODA_CLIPS = [
  {
    id: 'S7_C01',
    story: 'story7',
    clip: 1,
    text: 'ساعت دو نصفه‌شبه و چت‌جی‌پی‌تی رایگانم قفل شد! خرید دلاریش هم ویزاکارت می‌خواد!',
  },
  {
    id: 'S7_C03',
    story: 'story7',
    clip: 3,
    text: 'نگران نباش! از کلیدباکس چت‌جی‌پی‌تی گو رو سه میلیون و ششصد و نود تومن بخر!',
  },
  {
    id: 'S7_C04',
    story: 'story7',
    clip: 4,
    text: 'عالیه! به‌جای دردسر بیست دلار ویزاکارت، اشتراک چت‌جی‌پی‌تی پلاس رو چهار قسطه با گارانتی گرفتم!',
  },
  {
    id: 'S7_C06',
    story: 'story7',
    clip: 6,
    text: 'برای خرید چت‌جی‌پی‌تی گو، پلاس و پرو با گارانتی سی روزه، همین الان برو کلیدباکس!',
  },
  {
    id: 'S8_C01',
    story: 'story8',
    clip: 1,
    text: 'سفارش مشتری رو باید فردا تحویل بدم، اما تا سر ماه پول نقد اکانت هوش مصنوعی ندارم!',
  },
  {
    id: 'S8_C04',
    story: 'story8',
    clip: 4,
    text: 'یعنی بدون ضامن و چک، امروز فقط یک‌چهارم پول رو می‌دم و اکانتم همون لحظه فعال می‌شه؟!',
  },
  {
    id: 'S8_C06',
    story: 'story8',
    clip: 6,
    text: 'همین الان برو سایت کلیدباکس و اکانت هوش مصنوعیت رو چهار قسطه با ترب‌پی و دیجی‌پی بخر!',
  },
  {
    id: 'S9_C01',
    story: 'story9',
    clip: 1,
    text: 'واسه ساختن استودیوی حرفه‌ای به چت‌جی‌پی‌تی پرو و جمنای اولترا نیاز دارم، ولی پول نقدش سنگینه!',
  },
  {
    id: 'S9_C03',
    story: 'story9',
    clip: 3,
    text: 'سی میلیون تومن اعتبار تُرُب؟! یعنی می‌تونم قوی‌ترین اکانت‌های هوش مصنوعی دنیا رو یکجا بخرم؟!',
  },
  {
    id: 'S9_C05',
    story: 'story9',
    clip: 5,
    text: 'هورا! با اعتبار سی میلیونی تُرُب، استودیومون مجهز شد و سرعت کارمون ده برابر شده!',
  },
  {
    id: 'S9_C06',
    story: 'story9',
    clip: 6,
    text: 'اعتبار سی میلیون تومانیِ تُرُب رو از دست نده! همین الان از کلیدباکس قسطی خرید کن!',
  },
];

const PASS2_DEEP_CLIPS = [
  {
    id: 'S7_C02',
    story: 'story7',
    clip: 2,
    text: 'آرش! اگه تا ساعت هشت صبح گزارش کامل تحلیلی رو تحویل ندی، از شرکت اخراجی!',
  },
  {
    id: 'S7_C05',
    story: 'story7',
    clip: 5,
    text: 'فوق‌العاده‌ست آرش! این دقیق‌ترین گزارشیه که تو عمرم دیدم! همین امروز ترفیع می‌گیری!',
  },
  {
    id: 'S8_C02',
    story: 'story8',
    clip: 2,
    text: 'اگه اکانت می‌خوای باید کل پول دلار و کارمزد رو همین الان نقد کارت‌به‌کارت کنی!',
  },
  {
    id: 'S8_C03',
    story: 'story8',
    clip: 3,
    text: 'صبر کن نیما! توی سایت کلیدباکس می‌تونی همه اکانت‌ها رو با ترب‌پی و دیجی‌پی چهار قسطه بخری!',
  },
  {
    id: 'S8_C05',
    story: 'story8',
    clip: 5,
    text: 'دقیقاً! با درگاه رسمی ترب‌پی و دیجی‌پی، اکانتت رو الان تحویل بگیر و قسطی پرداخت کن!',
  },
  {
    id: 'S9_C02',
    story: 'story9',
    clip: 2,
    text: 'رامین خبر نداری؟! ترب تا سقف سی میلیون تومن اعتبار خرید قسطی بدون ضامن بهت می‌ده!',
  },
  {
    id: 'S9_C04',
    story: 'story9',
    clip: 4,
    text: 'آره! توی سایت کلیدباکس با اعتبار سی میلیونی ترب، کل پکیج حرفه‌ای رو چهار قسطه بردار!',
  },
];

async function selectSpeakerVoice(mcp, targetVoiceName) {
  console.log(`\n=== Switching Speaker 1 voice to "${targetVoiceName}" ===`);
  let snap = await mcp.callTool('browser_observe_page', { profileId: PROFILE_ID, tabId: TAB_ID });
  let nodes = flattenNodes(snap.frames?.[0]?.tree);

  const openBtn = nodes.find((n) => n.ref && n.visible && n.role === 'button' && n.name === 'Open voice settings');
  if (openBtn) {
    await mcp.callTool('browser_click', { profileId: PROFILE_ID, tabId: TAB_ID, ref: openBtn.ref });
    await sleep(1200);
    snap = await mcp.callTool('browser_observe_page', { profileId: PROFILE_ID, tabId: TAB_ID });
    nodes = flattenNodes(snap.frames?.[0]?.tree);
  }

  let voiceBtn = nodes.find(
    (n) => n.ref && n.visible && n.role === 'button' && typeof n.name === 'string' && n.name.startsWith(targetVoiceName)
  );
  if (!voiceBtn) {
    // Fallback to Riko or Bodi if targetVoiceName not found
    voiceBtn = nodes.find(
      (n) =>
        n.ref &&
        n.visible &&
        n.role === 'button' &&
        typeof n.name === 'string' &&
        (n.name.startsWith('Riko') || n.name.startsWith('Bodi'))
    );
  }
  if (!voiceBtn) {
    throw new Error(`Could not find voice button "${targetVoiceName}" in Speaker settings drawer`);
  }
  console.log(`  Clicking voice "${voiceBtn.name}" [${voiceBtn.ref}]...`);
  await mcp.callTool('browser_click', { profileId: PROFILE_ID, tabId: TAB_ID, ref: voiceBtn.ref });
  await sleep(900);

  snap = await mcp.callTool('browser_observe_page', { profileId: PROFILE_ID, tabId: TAB_ID });
  nodes = flattenNodes(snap.frames?.[0]?.tree);
  const closeBtn = nodes.find((n) => n.ref && n.visible && n.role === 'button' && n.name === 'Close panel');
  if (closeBtn) {
    await mcp.callTool('browser_click', { profileId: PROFILE_ID, tabId: TAB_ID, ref: closeBtn.ref });
    await sleep(800);
  }
}

async function generateClip(mcp, item, seenHashes) {
  const outDir = path.join(S4_DIR, item.story, 'gemini_tts');
  fs.mkdirSync(outDir, { recursive: true });
  const outPath = path.join(outDir, `clip_0${item.clip}.wav`);

  if (fs.existsSync(outPath) && fs.statSync(outPath).size > 20000) {
    const h = sha256File(outPath);
    seenHashes.add(h);
    console.log(`[SKIP] ${item.id} already exists (${fs.statSync(outPath).size} bytes, sha256=${h.slice(0, 10)})`);
    return;
  }

  console.log(`\n--- [${item.id}] Generating via Gemini 3.8 Flash TTS ---`);
  let snap = await mcp.callTool('browser_observe_page', { profileId: PROFILE_ID, tabId: TAB_ID });
  let nodes = flattenNodes(snap.frames?.[0]?.tree);

  let textBox = nodes.find((n) => n.ref && n.visible && n.role === 'textbox' && n.name === 'Speech block text');
  if (!textBox) throw new Error(`Could not find "Speech block text" textarea for ${item.id}`);

  // 1. Focus the textarea first so the "+ Expression" header expands and DOM refs stabilize
  await mcp.callTool('browser_click', {
    profileId: PROFILE_ID,
    tabId: TAB_ID,
    ref: textBox.ref,
  });
  await sleep(600);

  // 2. Re-observe and fill the text
  snap = await mcp.callTool('browser_observe_page', { profileId: PROFILE_ID, tabId: TAB_ID });
  nodes = flattenNodes(snap.frames?.[0]?.tree);
  textBox = nodes.find((n) => n.ref && n.visible && n.role === 'textbox' && n.name === 'Speech block text');
  if (!textBox) throw new Error(`Could not find focused "Speech block text" textarea for ${item.id}`);

  await mcp.callTool('browser_fill', {
    profileId: PROFILE_ID,
    tabId: TAB_ID,
    ref: textBox.ref,
    value: item.text,
  });
  await sleep(700);

  // 3. Re-observe after fill so we get the exact current ref of "Run Ctrl keyboard_return"
  snap = await mcp.callTool('browser_observe_page', { profileId: PROFILE_ID, tabId: TAB_ID });
  nodes = flattenNodes(snap.frames?.[0]?.tree);
  let runBtn = nodes.find(
    (n) =>
      n.ref &&
      n.visible &&
      n.role === 'button' &&
      typeof n.name === 'string' &&
      (n.name === 'Run Ctrl keyboard_return' || n.name.startsWith('Run Ctrl'))
  );
  if (!runBtn) {
    runBtn = nodes.find(
      (n) => n.ref && n.visible && n.role === 'button' && typeof n.name === 'string' && n.name.startsWith('Run')
    );
  }
  if (!runBtn) throw new Error(`Could not find Run button for ${item.id}`);

  await mcp.callTool('browser_click', { profileId: PROFILE_ID, tabId: TAB_ID, ref: runBtn.ref });
  console.log(`  [1/2] Clicked Run [${runBtn.ref}]`);

  // Wait 5.5s for synthesis to finish
  await sleep(5500);

  for (let poll = 1; poll <= 18; poll++) {
    snap = await mcp.callTool('browser_observe_page', { profileId: PROFILE_ID, tabId: TAB_ID });
    nodes = flattenNodes(snap.frames?.[0]?.tree);

    const isRunning = nodes.some(
      (n) => n.ref && n.visible && n.role === 'button' && /stop/i.test(String(n.name || n.text || ''))
    );
    const dlBtn = nodes.find((n) => n.ref && n.visible && n.role === 'button' && n.name === 'Download');

    if (!isRunning && dlBtn) {
      const beforeMap = listWavFiles();
      await mcp.callTool('browser_click', { profileId: PROFILE_ID, tabId: TAB_ID, ref: dlBtn.ref });
      const downloaded = await waitForNewWav(beforeMap, 7000);
      if (downloaded) {
        const hash = sha256File(downloaded);
        if (seenHashes.has(hash)) {
          try {
            fs.unlinkSync(downloaded);
          } catch {}
          console.log(`  [retry ${poll}] Downloaded WAV matched old hash; re-clicking Run and waiting 5.5s...`);
          snap = await mcp.callTool('browser_observe_page', { profileId: PROFILE_ID, tabId: TAB_ID });
          nodes = flattenNodes(snap.frames?.[0]?.tree);
          const retryRunBtn = nodes.find(
            (n) =>
              n.ref &&
              n.visible &&
              n.role === 'button' &&
              typeof n.name === 'string' &&
              (n.name === 'Run Ctrl keyboard_return' || n.name.startsWith('Run Ctrl'))
          );
          if (retryRunBtn) {
            await mcp.callTool('browser_click', { profileId: PROFILE_ID, tabId: TAB_ID, ref: retryRunBtn.ref });
          }
          await sleep(5500);
          continue;
        }
        seenHashes.add(hash);
        fs.copyFileSync(downloaded, outPath);
        console.log(`  [2/2] Saved ${outPath} (${fs.statSync(outPath).size} bytes, sha256=${hash.slice(0, 10)})`);
        return;
      }
    }
    await sleep(2000);
  }

  throw new Error(`Timed out generating/downloading ${item.id}`);
}

async function main() {
  const mcp = new McpClient();
  const seenHashes = new Set();
  try {
    await mcp.init();
    await mcp.callTool('browser_activate_tab', { profileId: PROFILE_ID, tabId: TAB_ID });
    await sleep(500);

    // Ensure Koda is selected for Pass 1
    let snap = await mcp.callTool('browser_observe_page', { profileId: PROFILE_ID, tabId: TAB_ID });
    let nodes = flattenNodes(snap.frames?.[0]?.tree);
    const hasKoda = nodes.some((n) => typeof n.text === 'string' && n.text.includes('Koda'));
    if (!hasKoda) {
      await selectSpeakerVoice(mcp, 'Koda');
    } else {
      console.log('=== Pass 1: Speaker 1 is already set to "Koda" ===');
    }

    for (const item of PASS1_KODA_CLIPS) {
      await generateClip(mcp, item, seenHashes);
    }

    // Switch to Neno (deep male voice) for Pass 2
    await selectSpeakerVoice(mcp, 'Neno');

    for (const item of PASS2_DEEP_CLIPS) {
      await generateClip(mcp, item, seenHashes);
    }

    console.log('\nALL 18 CLIPS GENERATED VIA GEMINI 3.8 FLASH TTS!');
  } finally {
    try {
      await mcp.callTool('browser_release_tab', { profileId: PROFILE_ID, tabId: TAB_ID });
    } catch {}
    mcp.close();
  }
}

main().catch((err) => {
  console.error('FATAL:', err);
  process.exit(1);
});
