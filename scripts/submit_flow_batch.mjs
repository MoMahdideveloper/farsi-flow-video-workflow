#!/usr/bin/env node
/**
 * Automated Google Flow Keyframe + Native Farsi Prompt Batch Submitter via Profile Bridge MCP.
 *
 * Usage:
 *   node scripts/submit_flow_batch.mjs --part part1 [--clip 1]
 *   node scripts/submit_flow_batch.mjs --part part2 [--clip 1]
 */

import { spawn, spawnSync } from 'node:child_process';

const PROFILE_ID = process.env.FLOW_PROFILE_ID || '731e6d16-b95b-480f-a245-cb443411400d';
const TAB_ID = Number(process.env.FLOW_TAB_ID || 612095035);
const KF_DIR = 'C:\\Users\\LifeCycle\\.gemini\\antigravity\\scratch\\series1-whats-her-number-farsi\\02_keyframes\\flow_kfs';

const BATCHES = {
  part1: [
    {
      clip: 1,
      kf: `${KF_DIR}\\ep4_kf_01.jpg`,
      prompt:
        '3D Pixar animation, static medium two-shot keeping both characters in frame the entire time (no camera cuts), in a cozy warm living room the arrogant golden pineapple man in a white polo shirt holds up a black smartphone for a selfie beside the cute red strawberry girl with curly brown hair, big crooked buck teeth, and a yellow cardigan. First the pineapple man speaks in native Persian (Farsi) with an arrogant young male voice: «عزیزم، میشه برای عکس با دهن بسته لبخند بزنی؟» Then the red strawberry girl replies in native Persian (Farsi) with a hurt young female voice: «چطوری با دهن بسته لبخند بزنم؟ خودت می‌دونی دندونام بسته نمیشه!» Zero on-screen subtitles.',
    },
    {
      clip: 2,
      kf: `${KF_DIR}\\ep4_kf_02.jpg`,
      prompt:
        '3D Pixar animation, static medium shot keeping both characters in frame the entire time (no camera cuts), the arrogant golden pineapple man sits on the living room sofa laughing into his smartphone while the red strawberry girl peeks from the hallway doorway in shock. First the pineapple man speaks into his phone in native Persian (Farsi) with a mocking male voice: «جرئت ندارم با دختری که دندوناش به دوازده جهت کج شده ازدواج کنم!» Then the red strawberry girl whispers in native Persian (Farsi) with a heartbroken female voice: «پس تمام این مدت اصلاً دوستم نداشته...» Zero on-screen subtitles.',
    },
    {
      clip: 3,
      kf: `${KF_DIR}\\ep4_kf_03.jpg`,
      prompt:
        '3D Pixar animation, static medium two-shot keeping both characters in frame the entire time (no camera cuts), inside a bright dental clinic the red strawberry girl in a yellow cardigan sits in the dental chair talking to the kind red cherry female dentist with glasses and a white coat holding a dental mirror. First the strawberry girl speaks in native Persian (Farsi) with a sad female voice: «خانم دکتر، کلی وقته منتظرم دندونام درست بشه!» Then the red cherry female dentist replies in native Persian (Farsi) with a kind professional female voice: «مشکل اینجاست که تکون نمی‌خورن عزیزم، باید اساسی درستشون کنیم!» Zero on-screen subtitles.',
    },
    {
      clip: 4,
      kf: `${KF_DIR}\\ep4_kf_04.jpg`,
      prompt:
        '3D Pixar animation, static medium shot keeping the character in frame the entire time (no camera cuts), the arrogant golden pineapple man in a white polo shirt sits on the living room sofa talking on his smartphone with a smug grin and gesturing with his hand. He speaks in native Persian (Farsi) with an arrogant male voice: «خیالت راحت، توت‌فرنگی به هیچی شک نکرده! فقط به خاطر پولش باهاش موندم!» Zero on-screen subtitles.',
    },
    {
      clip: 5,
      kf: `${KF_DIR}\\ep4_kf_05.jpg`,
      prompt:
        '3D Pixar animation, static medium close-up keeping the characters in frame the entire time (no camera cuts), in the foreground the red strawberry girl with curly brown hair hides behind the doorway wall with a fierce angry expression while the pineapple man sits on the sofa in the background. The strawberry girl speaks in native Persian (Farsi) with a fierce angry female voice: «آها، پس فقط به خاطر پولم باهامی؟ کاری می‌کنم از روز تولدت پشیمون بشی!» Zero on-screen subtitles.',
    },
    {
      clip: 6,
      kf: `${KF_DIR}\\ep4_kf_06.jpg`,
      prompt:
        '3D Pixar animation, static medium two-shot keeping both characters in frame the entire time (no camera cuts), in a bright dental clinic the red strawberry girl sits in the green dental chair looking hopeful while the kind red cherry female dentist in a white coat and glasses stands beside her. First the strawberry girl speaks in native Persian (Farsi) with an excited determined female voice: «خانم دکتر، یه لبخند می‌خوام که چشماش از تعجب چهار تا بشه!» Then the red cherry female dentist replies in native Persian (Farsi) with an enthusiastic female voice: «بحث انتقام خالصه! یه شاهکار برات می‌سازم دختر!» Zero on-screen subtitles.',
    },
  ],
  part2: [
    {
      clip: 1,
      kf: `${KF_DIR}\\ep3_kf_01.jpg`,
      prompt:
        '3D Pixar animation, static medium close-up keeping the character in frame the entire time (no camera cuts), the cute red strawberry girl with curly brown hair and brand-new straight sparkling white teeth smiles happily in the dental chair. She speaks in native Persian (Farsi) with a joyful young female voice: «آخیش! بالاخره دندونام صاف و سفید شد! مرسی خانم دکتر که سر قولتون موندید!» Zero on-screen subtitles.',
    },
    {
      clip: 2,
      kf: `${KF_DIR}\\ep3_kf_02.jpg`,
      prompt:
        '3D Pixar animation, static medium shot keeping the characters in frame the entire time (no camera cuts), in a luxury hair salon a stylish green apple male hairstylist in a black apron stands behind the red strawberry girl gesturing with his hands. The green apple male hairstylist speaks in native Persian (Farsi) with an energetic stylish male voice: «دیگه هیچی نگو! بذار با یه مدل موی جدید تبدیلت کنم به یه ملکه جذاب!» Zero on-screen subtitles.',
    },
    {
      clip: 3,
      kf: `${KF_DIR}\\ep3_kf_03.jpg`,
      prompt:
        '3D Pixar animation, static medium two-shot keeping both characters in frame the entire time (no camera cuts), in a bright dressing room with vanity mirror lights the red cherry female doctor in a white coat and glasses smiles and gestures proudly toward the transformed strawberry girl with long straight dark hair. First the red cherry female doctor speaks in native Persian (Farsi) with an excited female voice: «دختر ترکوندی! با این موهای صاف و استایل جدید واقعاً خیره‌کننده شدی!» Then the strawberry girl replies in native Persian (Farsi) with a confident female voice: «عاشقشم! حالا وقت روبه‌رو شدن با آناناسه!» Zero on-screen subtitles.',
    },
    {
      clip: 4,
      kf: `${KF_DIR}\\ep3_kf_04.jpg`,
      prompt:
        '3D Pixar animation, static medium shot keeping the character in frame the entire time (no camera cuts), the arrogant golden pineapple man in a white polo shirt sits on the sofa talking into his smartphone with a greedy laugh. He speaks in native Persian (Farsi) with a greedy arrogant male voice: «حاضر شو ببرمت خرید عشقم! توت‌فرنگی خونه نیست، با پولاش کلی خوش می‌گذرونیم!» Zero on-screen subtitles.',
    },
    {
      clip: 5,
      kf: `${KF_DIR}\\ep3_kf_05.jpg`,
      prompt:
        '3D Pixar animation, static medium shot keeping the character in frame the entire time (no camera cuts), the glamorous transformed red strawberry girl with sleek long straight dark hair, sparkling straight white teeth, gold heart necklace, and black top stands confidently with her hand on her hip in the living room. She speaks in native Persian (Farsi) with a powerful confident female voice: «منم توت‌فرنگی! همون دختری که به دندوناش می‌خندیدی! همین الان چمدوناتو جمع کن و گمشو بیرون!» Zero on-screen subtitles.',
    },
    {
      clip: 6,
      kf: `${KF_DIR}\\ep3_kf_06.jpg`,
      prompt:
        '3D Pixar animation, static medium shot keeping the character in frame the entire time (no camera cuts), the red cherry female dentist in a white coat and round glasses sits at her clinic desk with an open medical book, holding her chin thoughtfully. She speaks in native Persian (Farsi) with a dramatic worried female voice: «امیدوارم اثر درمان توت‌فرنگی بعد از بیست و چهار ساعت نپره... وگرنه دندوناش از قبل هم بزرگ‌تر می‌شه!» Zero on-screen subtitles.',
    },
  ],
};

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
          // ignore non-json
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
      clientInfo: { name: 'flow-batch-submitter', version: '1.0.0' },
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

function findNode(snapshot, predicate) {
  for (const frame of snapshot?.frames || []) {
    const nodes = flattenNodes(frame.tree);
    const found = nodes.find(predicate);
    if (found) return found;
  }
  return null;
}

function copyImageToClipboard(imagePath) {
  const psCmd = `Add-Type -AssemblyName System.Windows.Forms,System.Drawing; $img = [System.Drawing.Image]::FromFile('${imagePath}'); [System.Windows.Forms.Clipboard]::SetImage($img); $img.Dispose(); Write-Output 'COPIED_OK'`;
  const res = spawnSync('powershell.exe', ['-Sta', '-NoProfile', '-Command', psCmd], {
    encoding: 'utf8',
  });
  if (res.status !== 0 || !res.stdout.includes('COPIED_OK')) {
    throw new Error(`Clipboard copy failed for ${imagePath}: ${res.stderr || res.stdout}`);
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function submitSingleClip(mcp, item) {
  console.log(`\n=== Submitting Clip ${item.clip}: ${item.kf} ===`);
  copyImageToClipboard(item.kf);
  console.log(`  [1/5] Copied image to clipboard: ${item.kf}`);

  // Ensure prompt box is 100% empty before pasting a new image
  let snap = null;
  for (let clearTry = 1; clearTry <= 4; clearTry++) {
    snap = await mcp.callTool('browser_observe_page', {
      profileId: PROFILE_ID,
      tabId: TAB_ID,
    });
    const leftoverClear = findNode(
      snap,
      (n) => n.role === 'button' && n.name === 'Clear prompt'
    );
    if (!leftoverClear) break;
    console.log(`  [!] Clearing leftover prompt (try ${clearTry}, ${leftoverClear.ref})...`);
    await mcp.callTool('browser_click', {
      profileId: PROFILE_ID,
      tabId: TAB_ID,
      ref: leftoverClear.ref,
    });
    await sleep(1200);
  }

  // Try up to 3 paste attempts in case a background grid render stole focus
  let uploadedSnap = null;
  for (let pasteTry = 1; pasteTry <= 3 && !uploadedSnap; pasteTry++) {
    snap = await mcp.callTool('browser_observe_page', {
      profileId: PROFILE_ID,
      tabId: TAB_ID,
    });
    const promptBox = findNode(
      snap,
      (n) => n.role === 'textbox' && n.name === 'What do you want to create?'
    );
    if (!promptBox) {
      throw new Error('Could not find prompt textbox ("What do you want to create?")');
    }

    await mcp.callTool('browser_click', {
      profileId: PROFILE_ID,
      tabId: TAB_ID,
      ref: promptBox.ref,
    });
    await sleep(600);

    await mcp.callTool('browser_press_key', {
      profileId: PROFILE_ID,
      tabId: TAB_ID,
      key: 'v',
      modifiers: ['ctrl'],
    });
    console.log(
      `  [2/5] Pressed Ctrl+V (try ${pasteTry}) on prompt textbox (${promptBox.ref}), waiting for upload...`
    );

    for (let attempt = 1; attempt <= 6; attempt++) {
      await sleep(1500);
      const s = await mcp.callTool('browser_observe_page', {
        profileId: PROFILE_ID,
        tabId: TAB_ID,
      });
      const clearBtn = findNode(s, (n) => n.role === 'button' && n.name === 'Clear prompt');
      const cancelIcon = findNode(s, (n) => n.tag === 'mat-icon' && n.text === 'cancel');
      if (clearBtn || cancelIcon) {
        uploadedSnap = s;
        console.log(`  [3/5] Image upload confirmed on attempt ${attempt} (try ${pasteTry})!`);
        break;
      }
    }
  }
  if (!uploadedSnap) {
    throw new Error(`Timed out waiting for keyframe image to upload for Clip ${item.clip}`);
  }

  let readySnap = null;
  for (let typeTry = 1; typeTry <= 3; typeTry++) {
    const snapBeforeType =
      typeTry === 1
        ? uploadedSnap
        : await mcp.callTool('browser_observe_page', {
            profileId: PROFILE_ID,
            tabId: TAB_ID,
          });
    const updatedPromptBox = findNode(
      snapBeforeType,
      (n) => n.role === 'textbox' && n.name === 'What do you want to create?'
    );
    if (!updatedPromptBox) {
      throw new Error('Could not find prompt textbox after image upload');
    }

    await mcp.callTool('browser_type', {
      profileId: PROFILE_ID,
      tabId: TAB_ID,
      ref: updatedPromptBox.ref,
      text: item.prompt,
    });
    console.log(
      `  [4/5] Typed prompt (${item.prompt.length} chars, try ${typeTry}) into ${updatedPromptBox.ref}`
    );
    await sleep(1000);

    const checkSnap = await mcp.callTool('browser_observe_page', {
      profileId: PROFILE_ID,
      tabId: TAB_ID,
    });
    const promptPrefix = item.prompt.slice(0, 45);
    const hasPromptText = findNode(
      checkSnap,
      (n) => typeof n.text === 'string' && n.text.includes(promptPrefix)
    );
    if (hasPromptText) {
      readySnap = checkSnap;
      break;
    }
    console.log(`  [!] Prompt text not yet detected in textbox, retrying type...`);
  }
  if (!readySnap) {
    throw new Error(`Failed to verify typed prompt text for Clip ${item.clip}`);
  }

  const startBtn = findNode(
    readySnap,
    (n) => n.role === 'button' && n.name === 'Start generation'
  );
  if (!startBtn) {
    throw new Error('Could not find "Start generation" button');
  }

  await mcp.callTool('browser_click', {
    profileId: PROFILE_ID,
    tabId: TAB_ID,
    ref: startBtn.ref,
  });
  console.log(`  [5/5] Clicked "Start generation" (${startBtn.ref})!`);

  // Wait for prompt box to clear confirming submission
  await sleep(4500);
}

async function main() {
  const argv = process.argv.slice(2);
  let part = 'part1';
  let clipFilter = null;
  let startClip = 1;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--part' && argv[i + 1]) part = argv[++i];
    else if (argv[i] === '--clip' && argv[i + 1]) clipFilter = Number(argv[++i]);
    else if (argv[i] === '--start-clip' && argv[i + 1]) startClip = Number(argv[++i]);
  }

  const batch = BATCHES[part];
  if (!batch) throw new Error(`Unknown --part ${part}`);
  const items = clipFilter
    ? batch.filter((x) => x.clip === clipFilter)
    : batch.filter((x) => x.clip >= startClip);

  const mcp = new McpClient();
  try {
    await mcp.init();
    for (const item of items) {
      await submitSingleClip(mcp, item);
    }
    console.log(`\nALL ${items.length} CLIPS FOR ${part} SUBMITTED SUCCESSFULLY!`);
  } finally {
    try {
      await mcp.callTool('browser_release_tab', {
        profileId: PROFILE_ID,
        tabId: TAB_ID,
      });
    } catch {
      // ignore release errors
    }
    mcp.close();
  }
}

main().catch((err) => {
  console.error('FATAL:', err);
  process.exit(1);
});
