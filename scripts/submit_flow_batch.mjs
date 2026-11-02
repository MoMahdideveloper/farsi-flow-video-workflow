#!/usr/bin/env node
/**
 * Automated Google Flow Keyframe + Native Farsi Prompt Batch Submitter via Profile Bridge MCP.
 *
 * Guarantees: chips===0 before paste, chips===1 after paste and before Start; a clip with `kf`
 *   never falls back to 0-ingredient Text-to-Video; every step -> flow_submission_trace.jsonl
 *   (override with FLOW_TRACE_PATH). Keyframes are read-only (sha256 logged, never modified).
 *
 * Usage:
 *   node scripts/submit_flow_batch.mjs --part fop_part1 [--clip 1] [--start-clip 1] [--profile <id>] [--tab <id>]
 */

import { spawn, spawnSync } from 'node:child_process';
import { appendFileSync, existsSync, readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { checkSpeechBudget, generationTemplate, itemsFromManifest, manifestForBatch, preflightBatch } from './generation_preflight.mjs';

// Every submission step is appended here (one JSON object per line).
const TRACE_PATH = process.env.FLOW_TRACE_PATH || 'flow_submission_trace.jsonl';
let RUN_ID = new Date().toISOString();

let PROFILE_ID = process.env.FLOW_PROFILE_ID || null;
let TAB_ID = Number(process.env.FLOW_TAB_ID || 0);
const KF_DIR = 'C:\\Users\\LifeCycle\\.gemini\\antigravity\\scratch\\series1-whats-her-number-farsi\\02_keyframes\\flow_kfs';
const FOP_DIR = 'C:\\Users\\LifeCycle\\.gemini\\antigravity\\scratch\\series2-fruits-of-power-farsi';

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
  fop_part1: [
    {
      clip: 1,
      kf: `${FOP_DIR}\\part1\\keyframes\\KF_01.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the character in frame the entire time (no camera cuts), anthropomorphic purple eggplant aristocrat (Duke Eggplant with a full 3D glossy purple eggplant head and green calyx crown, strictly NO human face, NO human hair) in a dark purple velvet tuxedo standing in the rain by the mansion pool at night looking up at the sky in heartbreak and speaking in native Persian (Farsi) with a deep emotional male voice: «چرا؟! چطور تونست به من خیانت کنه و قلبمو بشکنه؟!» Zero on-screen subtitles.',
    },
    {
      clip: 2,
      kf: `${FOP_DIR}\\part1\\keyframes\\KF_02.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), glamorous anthropomorphic yellow lemon woman (Lemonella with a full 3D yellow lemon head and green leaf, strictly NO human face, NO human hair) in a gold gown touching her pregnant belly beside a flashy anthropomorphic banana man (full 3D curved yellow banana head with dark sunglasses, strictly NO human face) in a yellow leather jacket leaning against a yellow sports car at night. First Lemonella speaks in native Persian (Farsi) with a dramatic female voice: «من باردارم! ولی هیچ‌کس نباید بفهمه این بچه مال توئه!» Then Banana Man replies in native Persian (Farsi) with an arrogant young male voice: «نگران نباش عزیزم، دوک به هیچی شک نمی‌کنه!» Zero on-screen subtitles.',
    },
    {
      clip: 3,
      kf: `${FOP_DIR}\\part1\\keyframes\\KF_03.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium close-up keeping the character in frame the entire time (no camera cuts), anthropomorphic purple eggplant aristocrat (Duke Eggplant with a full 3D glossy purple eggplant head and green calyx crown, strictly NO human face, NO human hair) in a dark purple velvet tuxedo holding and staring in shock at a glowing smartphone screen showing a suspicious message inside his luxury mansion. Duke Eggplant speaks in native Persian (Farsi) with a shocked heartbroken male voice: «امکان نداره! لمونلا دیشب کجا بوده؟! یعنی به من خیانت کرده؟!» Zero on-screen subtitles.',
    },
    {
      clip: 4,
      kf: `${FOP_DIR}\\part1\\keyframes\\KF_04.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium close-up keeping the character in frame the entire time (no camera cuts), anthropomorphic purple eggplant aristocrat (Duke Eggplant with a full 3D glossy purple eggplant head, strictly NO human face) in a dark purple velvet tuxedo holding a bouquet of dark purple roses with tears streaming down his face in his luxury mansion. Duke Eggplant speaks in native Persian (Farsi) with an emotional weeping male voice: «من این گل‌ها رو با عشق براش خریده بودم... چطور تونست با قلب من این کار رو بکنه؟!» Zero on-screen subtitles.',
    },
    {
      clip: 5,
      kf: `${FOP_DIR}\\part1\\keyframes\\KF_05.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the character in frame the entire time (no camera cuts), flashy anthropomorphic banana man (full 3D yellow banana head wearing dark sunglasses, strictly NO human face) in a yellow leather jacket and gold chain necklace sitting in a yellow sports car at night in the rain. Banana Man speaks in native Persian (Farsi) with a smug arrogant male voice: «بارون رو ببین... حالا تمام دارایی و زندگیت مال منه، دوک!» Zero on-screen subtitles.',
    },
    {
      clip: 6,
      kf: `${FOP_DIR}\\part1\\keyframes\\KF_06.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the character in frame the entire time (no camera cuts), anthropomorphic purple eggplant aristocrat (Duke Eggplant with a full 3D glossy purple eggplant head and green calyx crown, strictly NO human face) in a dark purple velvet tuxedo standing on his mansion balcony at night in the rain, gripping the stone railing in heartbreak looking down toward the courtyard fountain. Duke Eggplant speaks in native Persian (Farsi) with a broken weeping male voice: «چرا من؟! خدایا چرا؟! دیگه طاقت دیدن این خیانت رو ندارم!» Zero on-screen subtitles.',
    },
  ],
  fop_part2: [
    {
      clip: 1,
      kf: `${FOP_DIR}\\part2\\keyframes\\KF_01.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the character in frame the entire time (no camera cuts), flashy anthropomorphic banana man (full 3D yellow banana head with sunglasses, strictly NO human face) in a yellow leather jacket celebrating in a luxury VIP lounge at night. Banana Man speaks in native Persian (Farsi) with an excited arrogant male voice: «بزن بریم! امشب شبِ ماست! با پول‌های دوک کل شهر رو می‌خریم!» Zero on-screen subtitles.',
    },
    {
      clip: 2,
      kf: `${FOP_DIR}\\part2\\keyframes\\KF_02.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium close-up keeping the character in frame the entire time (no camera cuts), anthropomorphic purple eggplant aristocrat (Duke Eggplant with a full 3D glossy purple eggplant head, strictly NO human face) in a dark purple velvet tuxedo sitting alone holding a crystal glass in his dark rainy mansion. Duke Eggplant speaks in native Persian (Farsi) with a deep sorrowful male voice: «همه فکر می‌کنن من همه‌چیز دارم... ولی توی تنهایی خودم دارم می‌سوزم!» Zero on-screen subtitles.',
    },
    {
      clip: 3,
      kf: `${FOP_DIR}\\part2\\keyframes\\KF_03.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), elegant anthropomorphic red strawberry woman (Countess Strawberry with a full 3D red seeded strawberry head and green leaf crown, strictly NO human face, NO human hair) in a crimson evening gown comforting Duke Eggplant (full 3D purple eggplant head) at a candlelit table. Countess Strawberry speaks in native Persian (Farsi) with a warm gentle female voice: «دوک عزیزم، اون لیاقت عشق تو رو نداشت... بذار من مرهم قلبت باشم.» Zero on-screen subtitles.',
    },
    {
      clip: 4,
      kf: `${FOP_DIR}\\part2\\keyframes\\KF_04.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium close-up keeping the character in frame the entire time (no camera cuts), glamorous anthropomorphic yellow lemon woman (Lemonella with a full 3D yellow lemon head and green leaf, strictly NO human face, NO human hair) in a gold gown gasping in burning jealousy while looking at a photo on her smartphone screen inside a luxury room. Lemonella speaks in native Persian (Farsi) with a shocked jealous female voice: «نه... امکان نداره دوک با کنتس توت‌فرنگی دیده شده باشه!» Zero on-screen subtitles.',
    },
    {
      clip: 5,
      kf: `${FOP_DIR}\\part2\\keyframes\\KF_05.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), flashy anthropomorphic banana man (full 3D yellow banana head with sunglasses, strictly NO human face) in a yellow leather jacket and glamorous anthropomorphic yellow lemon woman (Lemonella with a full 3D yellow lemon head, strictly NO human face, NO human hair) in a gold gown holding an opened medical DNA test envelope and paper in a luxury hallway. First Banana Man speaks in native Persian (Farsi) with a serious male voice: «چی شده؟ توی اون پاکت آزمایش چی نوشته؟» Then Lemonella replies in native Persian (Farsi) with an emotional female voice: «چطور روت میشه حقیقت رو انکار کنی؟! این برگه همه‌چیز رو ثابت می‌کنه!» Zero on-screen subtitles.',
    },
    {
      clip: 6,
      kf: `${FOP_DIR}\\part2\\keyframes\\KF_06.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), glamorous anthropomorphic yellow lemon woman (Lemonella with a full 3D yellow lemon head, strictly NO human face) holding a medical DNA test result paper in total shock while Banana Man and Duke Eggplant stand behind her. Lemonella speaks in native Persian (Farsi) with a terrified shocked female voice: «وای خدای من، نه... امکان نداره نتیجه آزمایش دی‌ان‌ای این باشه!» Zero on-screen subtitles.',
    },
  ],
  fop_part3: [
    {
      clip: 1,
      kf: `${FOP_DIR}\\part3\\keyframes\\KF_01.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium close-up keeping the character in frame the entire time (no camera cuts), glamorous anthropomorphic yellow lemon woman (Lemonella with a full 3D yellow lemon head, strictly NO human face, NO human hair) crying emotionally in a luxury marble room. Lemonella speaks in native Persian (Farsi) with a tearful emotional female voice: «باورم نمیشه... بچه‌مون پسره! ای کاش بقیه حقیقت رو می‌دونستن...» Zero on-screen subtitles.',
    },
    {
      clip: 2,
      kf: `${FOP_DIR}\\part3\\keyframes\\KF_02.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), flashy anthropomorphic banana man (full 3D yellow banana head with dark sunglasses, strictly NO human face) in a yellow leather jacket smirking in the foreground while glamorous anthropomorphic yellow lemon woman (Lemonella with a full 3D yellow lemon head, strictly NO human face) in a gold gown holds up the DNA test paper behind him. First Lemonella speaks in native Persian (Farsi) with a serious female voice: «آزمایش همه‌چیز رو ثابت کرد!» Then Banana Man replies in native Persian (Farsi) with a confident laughing male voice: «هاهاها! که چی مثلاً؟!» Zero on-screen subtitles.',
    },
    {
      clip: 3,
      kf: `${FOP_DIR}\\part3\\keyframes\\KF_03.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), anthropomorphic purple eggplant aristocrat (Duke Eggplant with a full 3D purple eggplant head, strictly NO human face) in his velvet tuxedo proudly showing a golden nursery architectural blueprint on a table to Lemonella (full 3D yellow lemon head) in her gold gown. Duke Eggplant speaks in native Persian (Farsi) with a warm proud male voice: «این نقشه رو ببین لمونلا؛ تزئینات طلای خالص و نمای کامل شهر... بهترین‌ها برای وارثمون!» Zero on-screen subtitles.',
    },
    {
      clip: 4,
      kf: `${FOP_DIR}\\part3\\keyframes\\KF_04.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the character in frame the entire time (no camera cuts), anthropomorphic dark black-purple fig mafia boss (Shadow Fig with a full 3D dark textured fig head, strictly NO human face, wearing a dark fedora hat and black mafia trenchcoat over a black suit) standing outside in the rain at night looking toward the illuminated mansion window and speaking in native Persian (Farsi) with a deep menacing mafia boss male voice: «پس فکر کردی می‌تونی از گذشته فرار کنی لمونلا؟ و اونا به هیچ‌چیز شک نکردن؟» Zero on-screen subtitles.',
    },
    {
      clip: 5,
      kf: `${FOP_DIR}\\part3\\keyframes\\KF_05.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium close-up keeping the character in frame the entire time (no camera cuts), glamorous anthropomorphic yellow lemon woman (Lemonella with a full 3D yellow lemon head and green leaf, strictly NO human face, NO human hair) whispering worriedly into her smartphone in a dimly lit mansion hallway at night. Lemonella speaks in native Persian (Farsi) with a panicked whispering female voice: «معلومه که نه... باید قبل از اینکه دوک بویی ببره از اینجا فرار کنم!» Zero on-screen subtitles.',
    },
    {
      clip: 6,
      kf: `${FOP_DIR}\\part3\\keyframes\\KF_06.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium close-up keeping the character in frame the entire time (no camera cuts), anthropomorphic dark black-purple fig mafia boss (Shadow Fig with a full 3D dark textured fig head, strictly NO human face, wearing a black mafia trenchcoat and dark suit) holding a tiny sparkling crystal baby shoe in his black-gloved hand inside a dimly lit luxury room at night and speaking in native Persian (Farsi) with a deep menacing male voice: «فکر کردی می‌تونی واقعیت رو پنهان کنی عزیزم؟ تمام مدارک دست منه!» Zero on-screen subtitles.',
    },
  ],
  fop_part4: [
    {
      clip: 1,
      kf: `${FOP_DIR}\\part4\\keyframes\\KF_01.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), glamorous anthropomorphic yellow lemon woman (Lemonella with a full 3D yellow lemon head, strictly NO human face) in a gold gown crying in the arms of anthropomorphic purple eggplant aristocrat (Duke Eggplant with a full 3D purple eggplant head, strictly NO human face) in a dark purple velvet tuxedo inside a luxury mansion room and speaking in native Persian (Farsi) with a weeping remorseful female voice: «دوک، قسم می‌خورم نمی‌خواستم اینطوری بشه! به اعتمادت خیانت کردم و همه‌چیز رو خراب کردم!» Zero on-screen subtitles.',
    },
    {
      clip: 2,
      kf: `${FOP_DIR}\\part4\\keyframes\\KF_02.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), Duke Eggplant (full 3D purple eggplant head, strictly NO human face) in a dark purple velvet tuxedo holding a signed legal contract folder with a firm expression while Lemonella (full 3D yellow lemon head, strictly NO human face) in a gold gown looks shocked beside him. First Lemonella speaks in native Persian (Farsi) with a shocked tearful female voice: «این دیگه چیه؟ چرا این قرارداد رو امضا کردی؟» Then Duke Eggplant replies in native Persian (Farsi) with a firm serious male voice: «برای اینکه مطمئن بشم دیگه هیچ‌وقت فریب نمی‌خورم!» Zero on-screen subtitles.',
    },
    {
      clip: 3,
      kf: `${FOP_DIR}\\part4\\keyframes\\KF_03.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), elegant anthropomorphic red strawberry woman (Countess Strawberry with a full 3D red seeded strawberry head and green leaf crown, strictly NO human face, NO human hair) in a crimson evening gown leaning warmly toward Duke Eggplant (full 3D purple eggplant head, strictly NO human face) at a candlelit table and speaking in native Persian (Farsi) with a soft gentle female voice: «لازم نیست امشب تنها بمونی دوک عزیزم... تو لیاقتت خیلی بیشتر از این غم و غصه‌ست.» Zero on-screen subtitles.',
    },
    {
      clip: 4,
      kf: `${FOP_DIR}\\part4\\keyframes\\KF_04.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium close-up keeping the character in frame the entire time (no camera cuts), glamorous anthropomorphic yellow lemon woman (Lemonella with a full 3D yellow lemon head and green leaf, strictly NO human face, NO human hair) in a gold gown crying in distress holding an ultrasound photo in front of a luxury vanity mirror and speaking in native Persian (Farsi) with a sad crying female voice: «حالا با این وضعیت و دردسرهای جدید چه خاکی به سرم بریزم؟!» Zero on-screen subtitles.',
    },
    {
      clip: 5,
      kf: `${FOP_DIR}\\part4\\keyframes\\KF_05.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), glamorous anthropomorphic yellow lemon woman (Lemonella with a full 3D yellow lemon head, strictly NO human face) in a gold gown confronting Countess Strawberry (full 3D red strawberry head) and Duke Eggplant (full 3D purple eggplant head) in a luxury hall. Lemonella speaks in native Persian (Farsi) with a loud upset female voice: «به چه حقی به من پشت می‌کنی؟! وقتی باهات حرف می‌زنم تو چشمام نگاه کن!» Zero on-screen subtitles.',
    },
    {
      clip: 6,
      kf: `${FOP_DIR}\\part4\\keyframes\\KF_06.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), anthropomorphic purple eggplant aristocrat (Duke Eggplant with a full 3D purple eggplant head, strictly NO human face) in a dark purple velvet tuxedo shielding and holding Lemonella (full 3D yellow lemon head, strictly NO human face) in a gold gown inside the mansion hall as shadowy attackers approach during a night storm, speaking in native Persian (Farsi) with an urgent protective male voice: «محکم منو بگیر لمونلا! اون‌ها به عمارت رسیدن!» Zero on-screen subtitles.',
    },
  ],
  fop_part5: [
    {
      clip: 1,
      kf: `${FOP_DIR}\\part5\\keyframes\\KF_01.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium close-up keeping the character in frame the entire time (no camera cuts), flashy anthropomorphic banana man (full 3D yellow banana head wearing dark sunglasses, strictly NO human face) in a yellow leather jacket standing in a dark luxury room looking bitter and betrayed and speaking in native Persian (Farsi) with a bitter upset male voice: «پس یعنی منم برات فقط یه اشتباهِ دیگه بودم لمونلا؟!» Zero on-screen subtitles.',
    },
    {
      clip: 2,
      kf: `${FOP_DIR}\\part5\\keyframes\\KF_02.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium close-up keeping the character in frame the entire time (no camera cuts), anthropomorphic purple eggplant aristocrat (Duke Eggplant with a full 3D glossy purple eggplant head and green calyx crown, strictly NO human face) in a dark purple velvet tuxedo looking stunned and heartbroken as he learns about Lemonella’s past with Shadow Fig, speaking in native Persian (Farsi) with a stunned male voice: «تو قبل از من با اون رابطه داشتی؟! چرا این راز رو پنهان کردی؟!» Zero on-screen subtitles.',
    },
    {
      clip: 3,
      kf: `${FOP_DIR}\\part5\\keyframes\\KF_03.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium close-up keeping the character in frame the entire time (no camera cuts), glamorous anthropomorphic yellow lemon woman (Lemonella with a full 3D yellow lemon head and green leaf, strictly NO human face, NO human hair) in a gold gown standing in a dark luxury casino hall with tears in her eyes explaining her past and speaking in native Persian (Farsi) with a tearful emotional female voice: «قبل از دوک، من توی اون شهر غریب تنها بودم و هیچ چاره‌ای نداشتم!» Zero on-screen subtitles.',
    },
    {
      clip: 4,
      kf: `${FOP_DIR}\\part5\\keyframes\\KF_04.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), Duke Eggplant (full 3D purple eggplant head, strictly NO human face) in a dark purple velvet tuxedo embracing the crying Lemonella (full 3D yellow lemon head, strictly NO human face) in a gold gown tenderly in the mansion and speaking in native Persian (Farsi) with a warm forgiving male voice: «برام مهم نیست قبل از من کی توی گذشته‌ت بوده... من از تو و بچه‌مون محافظت می‌کنم!» Zero on-screen subtitles.',
    },
    {
      clip: 5,
      kf: `${FOP_DIR}\\part5\\keyframes\\KF_05.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), Duke Eggplant (full 3D purple eggplant head, strictly NO human face) in a dark purple velvet tuxedo kneeling on the mansion floor holding Lemonella (full 3D yellow lemon head, strictly NO human face) in a gold gown as she collapses in pain, speaking in native Persian (Farsi) with a worried urgent male voice: «تحمل کن عزیزم! سریع زنگ بزنید به اورژانس و بیمارستان!» Zero on-screen subtitles.',
    },
    {
      clip: 6,
      kf: `${FOP_DIR}\\part5\\keyframes\\KF_06.jpg`,
      prompt:
        '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), anthropomorphic green pear doctor (Dr. Pear with a full 3D green pear head and glasses, strictly NO human face) in a white medical coat and stethoscope holding up an ultrasound scan showing three baby fetuses in a hospital room beside Duke Eggplant (full 3D purple eggplant head) and Lemonella (full 3D yellow lemon head), speaking in native Persian (Farsi) with a surprised male doctor voice: «متاسفانه اسکن‌ها یه چیز غیرمنتظره رو نشون میدن... توی شکمت سه تا بچه‌ست! سه‌قلو بارداری!» Zero on-screen subtitles.',
    },
  ],
};

BATCHES.fop_part6 = [
  {
    clip: 1,
    kf: `${FOP_DIR}\\part6\\keyframes\\KF_01.jpg`,
    prompt:
      '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), anthropomorphic green pear doctor (Dr. Pear with a full 3D green pear head and glasses, strictly NO human face) in a white medical coat holding the medical chart in the hospital room beside Duke Eggplant (full 3D purple eggplant head) and Lemonella (full 3D yellow lemon head), as Dr. Pear speaks in native Persian (Farsi) with a shocked serious male doctor voice: «آزمایش نهایی روی سه‌قلوها انجام شد جناب دوک... نتیجه چیزیه که هیچ‌کس باورش نمیشه!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${FOP_DIR}\\part6\\keyframes\\KF_02.jpg`,
    prompt:
      '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium close-up keeping the character in frame the entire time (no camera cuts), flashy anthropomorphic banana man (full 3D yellow banana head wearing dark sunglasses, strictly NO human face) in a yellow leather jacket gesturing greedily and speaking in native Persian (Farsi) with an arrogant excited male voice: «اگه سه‌قلوئه، پس حتماً حداقل یکیشون مال منه و نصف ثروت عمارت سهم منه!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${FOP_DIR}\\part6\\keyframes\\KF_03.jpg`,
    prompt:
      '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium close-up keeping the character in frame the entire time (no camera cuts), mysterious anthropomorphic dark purple-black fig aristocrat (Shadow Fig with a full 3D dark fig head, strictly NO human face) in a tailored black suit holding up a sparkling diamond heirloom in his gloved hand, speaking in native Persian (Farsi) with a deep serious male voice: «زود قضاوت نکنید آقایون! یکی از اون بچه‌ها وارث منه و مدارکش هم توی دستای منه!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${FOP_DIR}\\part6\\keyframes\\KF_04.jpg`,
    prompt:
      '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), Lemonella (full 3D yellow lemon head, strictly NO human face) sitting on the hospital bed gasping in total panic beside Duke Eggplant (full 3D purple eggplant head) and Dr. Pear (full 3D green pear head in white doctor coat), as Lemonella speaks in native Persian (Farsi) with a terrified panicking female voice: «وای نه... یکی شبیه بادمجانه، یکی شبیه موز، و یکی هم کپِ انجیر سیاهه! همه رازهام لو رفت!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${FOP_DIR}\\part6\\keyframes\\KF_05.jpg`,
    prompt:
      '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), Duke Eggplant (full 3D purple eggplant head in a dark purple velvet tuxedo, strictly NO human face) holding up the black leather contract folder firmly in front of crying Lemonella (full 3D yellow lemon head in a gold gown) and speaking in native Persian (Farsi) with a commanding decisive male voice: «طبق قراردادی که امضا کردی لمونلا، به خاطر این خیانت از تمام ثروت عمارت محرومی و من فقط وارث خودم رو نگه می‌دارم!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${FOP_DIR}\\part6\\keyframes\\KF_06.jpg`,
    prompt:
      '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), glamorous anthropomorphic red strawberry aristocrat woman (Countess Strawberry with a full 3D red strawberry head and green leaf crown, strictly NO human face) in a red velvet evening gown sitting warmly beside Duke Eggplant (full 3D purple eggplant head in a dark purple tuxedo) at a candlelit luxury table, speaking in native Persian (Farsi) with a warm triumphant female voice: «دوک عزیزم، بالاخره از دست دروغ‌هاش خلاص شدی! حالا نوبت زندگی جدید ما و وارث واقعیته!» Zero on-screen subtitles.',
  },
];

BATCHES.fop_p6_a = BATCHES.fop_part6.slice(0, 3);
BATCHES.fop_p6_b = BATCHES.fop_part6.slice(3, 6);
BATCHES.fop_p6_rem = [BATCHES.fop_part6[2], BATCHES.fop_part6[4], BATCHES.fop_part6[5]];

BATCHES.fop_part7 = [
  {
    clip: 1,
    kf: `${FOP_DIR}\\part7\\keyframes\\KF_01.jpg`,
    prompt:
      '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), anthropomorphic green pear doctor (Dr. Pear with a full 3D green pear head and glasses, strictly NO human face) in a white medical coat standing beside Duke Eggplant (full 3D purple eggplant head in a purple velvet suit) next to three hospital cradles holding three miniature fruit characters (a small purple eggplant, a small yellow banana, and a small dark fig), as Dr. Pear speaks in native Persian (Farsi) with a warm amazed male doctor voice: «سه‌قلوها به سلامت به دنیا اومدن جناب دوک! خودتون ببینید: یکی بادمجان، یکی موز، و یکی هم انجیر سیاه!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${FOP_DIR}\\part7\\keyframes\\KF_02.jpg`,
    prompt:
      '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), anthropomorphic dark purple-black fig aristocrat (Shadow Fig with a full 3D dark fig head in a black pinstripe suit, strictly NO human face) holding a sleek black carrier containing the miniature dark fig heir while looking coldly over his shoulder at Lemonella (full 3D yellow lemon head) in the hallway and speaking in native Persian (Farsi) with a deep cold decisive male voice: «من فقط وارث خودم رو می‌برم لمونلا! از این لحظه به بعد، دیگه حتی یک سکه هم از من بهت نمی‌رسه!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${FOP_DIR}\\part7\\keyframes\\KF_03.jpg`,
    prompt:
      '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), flashy anthropomorphic banana man (full 3D yellow banana head with dark sunglasses in a yellow leather jacket, strictly NO human face) backing away toward the exit door with both hands raised in refusal while Lemonella (full 3D yellow lemon head) holds the miniature yellow banana character in her arms, as Banana Man speaks in native Persian (Farsi) with a panicked cowardly male voice: «من فقط دنبال ثروت دوک بودم، نه بزرگ کردن بچه! خودت تنهایی بزرگش کن لمونلا، من رفتم خداحافظ!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${FOP_DIR}\\part7\\keyframes\\KF_04.jpg`,
    prompt:
      '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the character in frame the entire time (no camera cuts), anthropomorphic yellow lemon woman (Lemonella with a full 3D yellow lemon head, strictly NO human face) standing in the pouring rain at night outside the locked wrought-iron gates of the mansion beside her suitcase, crying bitterly and speaking in native Persian (Farsi) with a weeping regretful female voice: «به خاطر طمع و خیانت همه‌چیز رو باختم... هم قصر دوک رو از دست دادم و هم زیر بارون بی‌خانمان شدم!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${FOP_DIR}\\part7\\keyframes\\KF_05.jpg`,
    prompt:
      '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), anthropomorphic glossy purple eggplant aristocrat (Duke Eggplant with a full 3D purple eggplant head in a royal purple velvet tuxedo, strictly NO human face) standing proudly in the sunlit golden palace nursery holding the smiling miniature purple eggplant heir in his arms, speaking in native Persian (Farsi) with a warm proud fatherly male voice: «بالاخره اتاق طلاکوب عمارت به وارث واقعیم رسید! پسرم، از امروز تمام این قصر و پادشاهی متعلق به توئه!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${FOP_DIR}\\part7\\keyframes\\KF_06.jpg`,
    prompt:
      '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), glamorous anthropomorphic red strawberry aristocrat woman (Countess Strawberry with a full 3D red strawberry head and green leaf crown in a sparkling ruby-red royal gown, strictly NO human face) standing happily beside Duke Eggplant (full 3D purple eggplant head in a royal purple tuxedo holding the miniature purple eggplant heir) in a grand sunlit palace ballroom with golden confetti, as Countess Strawberry speaks in native Persian (Farsi) with a joyful loving female voice: «عشق واقعی و صداقت همیشه برنده می‌شه دوک عزیزم! حالا خانواده‌مون توی این قصر برای همیشه خوشبخته!» Zero on-screen subtitles.',
  },
];

BATCHES.fop_p7_a = BATCHES.fop_part7.slice(0, 3);
BATCHES.fop_p7_b = BATCHES.fop_part7.slice(3, 6);

const S4_DIR = 'C:\\Users\\LifeCycle\\.gemini\\antigravity\\scratch\\series4-viral-6-stories-farsi';

BATCHES.s4_story1 = [
  {
    clip: 1,
    kf: `${S4_DIR}\\story1\\keyframes\\KF_01.jpg`,
    prompt:
      '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), strict anthropomorphic green pear father (full 3D green pear head with a thick brown mustache and the number 1 on his forehead, strictly NO human face) in a brown sweater vest looking shocked in the living room beside his pink peach daughter (full 3D pink peach head with a purple bow) and three towering ultra-muscular gym-bro fruits (a buff watermelon, a buff pineapple, and a buff orange in tank tops), as Pear Dad speaks in native Persian (Farsi) with a shocked suspicious male father voice: «صبر کن ببینم دخترم! این سه تا غولِ بدنساز کین آوردی خونه؟! واقعاً می‌خوای با اینا درس بخونی؟!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S4_DIR}\\story1\\keyframes\\KF_02.jpg`,
    prompt:
      '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), cute anthropomorphic pink peach daughter (full 3D pink peach head with a purple bow, strictly NO human face) clasping her hands pleadingly toward her skeptical Pear Dad (full 3D green pear head in armchair) while the three muscular gym-bro fruits (watermelon, pineapple, orange in tank tops) smile politely behind her, as Peach Daughter speaks in native Persian (Farsi) with a sweet persuasive young female voice: «بابا جون این بچه‌ها توی زیست‌شناسی عالین! اگه صدای عجیبی هم از بالا اومد نیا تو اتاق، فقط داریم درس می‌خونیم!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S4_DIR}\\story1\\keyframes\\KF_03.jpg`,
    prompt:
      '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), three huge muscular anthropomorphic gym-bro fruits (a buff watermelon in a black tank top, a buff pineapple in a white tank top, and a buff orange in gym shorts, strictly NO human faces) sitting around the pink peach daughter on the bedroom bed holding biology notebooks, as the muscular Watermelon speaks in native Persian (Farsi) with a deep enthusiastic gym-bro male voice: «خب بچه‌ها، درِ اتاق رو ببندید! وقتشه سنگین‌ترین تمرین عملی زیست‌شناسی رو همین الان با هم شروع کنیم!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S4_DIR}\\story1\\keyframes\\KF_04.jpg`,
    prompt:
      '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the character in frame the entire time (no camera cuts), strict anthropomorphic green pear father (full 3D green pear head with a brown mustache and number 1 on his forehead, strictly NO human face) standing at the foot of the wooden stairs looking up at the shaking ceiling chandelier in shock and fury, speaking in native Persian (Farsi) with an angry suspicious male voice: «این دیگه چه سر و صداییه از طبقه بالا میاد؟! سقف خونه داره می‌ریزه، الان می‌رم بالا مچشون رو می‌گیرم!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S4_DIR}\\story1\\keyframes\\KF_05.jpg`,
    prompt:
      '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), three muscular anthropomorphic gym-bro fruits (watermelon, pineapple, and orange in tank tops wiping sweat from their brows, strictly NO human faces) walking down the wooden stairs while strict Pear Dad (full 3D green pear head) confronts them at the bottom, as the muscular Watermelon speaks in native Persian (Farsi) with a breathless cheerful male voice: «نگران نباشید عموجون، درسمون دیگه تموم شد! تمام فصل زیست‌شناسی رو با انرژی کامل مرور کردیم، خداحافظ!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S4_DIR}\\story1\\keyframes\\KF_06.jpg`,
    prompt:
      '3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), strict anthropomorphic green pear father (full 3D green pear head with mustache, strictly NO human face) standing in the open bedroom doorway looking stunned at his pink peach daughter sitting cross-legged on the bed surrounded by open books with the number 3 glowing on her forehead, as Pear Dad speaks in native Persian (Farsi) with a stunned bewildered male voice: «صبر کن ببینم، واقعاً فقط داشتید درس می‌خوندید؟! پس چرا عدد روی پیشونیت یکهو شده سه؟!» Zero on-screen subtitles.',
  },
];

BATCHES.s4_story2 = [
  {
    clip: 1,
    kf: `${S4_DIR}\\story2\\keyframes\\KF_01.jpg`,
    prompt:
      '[S2_C01] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), wealthy 3D anthropomorphic mahogany wooden man (Mr. Ray in a dark winter overcoat and scarf, strictly NO human skin face) beside his black SUV in a snowy hospital parking lot handing a green banknote to a small cute 3D brown wooden log boy (Leo holding a snow brush), as Mr. Ray speaks in native Persian (Farsi) with a warm appreciative male voice: «آفرین پسر، برف ماشینم رو عالی پاک کردی! اسم من ری هست، این صد دلار مال تو!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S4_DIR}\\story2\\keyframes\\KF_02.jpg`,
    prompt:
      '[S2_C02] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the character in frame the entire time (no camera cuts), small cute 3D anthropomorphic wooden log boy (cylindrical brown wood grain body with big expressive cartoon eyes, strictly NO human skin face) holding a snow brush in a snowy hospital parking lot and looking down in shock at a purple velvet diamond ring box on the snow, speaking in native Persian (Farsi) with an urgent surprised young voice: «وای صبر کنید! آقای ری موقع رفتن این جعبه حلقه الماس رو توی برف انداخت!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S4_DIR}\\story2\\keyframes\\KF_03.jpg`,
    prompt:
      '[S2_C03] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), stern 3D anthropomorphic birch-wood receptionist in hospital scrubs and glasses behind the hospital billing counter shaking her head as the small wooden log boy holds up a single green banknote (strictly NO human faces), speaking in native Persian (Farsi) with a firm cold female voice: «پسرجون صد دلار کافی نیست! تا فردا باید کل هزینه عمل مادرت رو نقد بیاری!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S4_DIR}\\story2\\keyframes\\KF_04.jpg`,
    prompt:
      '[S2_C04] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), elderly 3D anthropomorphic wooden log mother character (weathered brown bark texture with gray mossy hair and kind cartoon eyes, strictly NO human skin face) lying in a hospital bed holding the hand of the small wooden log boy beside her, speaking in native Persian (Farsi) with a gentle wise motherly voice: «لئو پسرم، هیچ‌وقت دست به کار خلاف نزن! پول میاد و می‌ره، اما شرافتت خریدنی نیست!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S4_DIR}\\story2\\keyframes\\KF_05.jpg`,
    prompt:
      '[S2_C05] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), 3D anthropomorphic dark oak wood jeweler character wearing a jeweler loupe and vest behind a black marble counter placing stacks of cash beside the open purple velvet diamond ring box in front of the small wooden log character (strictly NO human faces), as the jeweler speaks in native Persian (Farsi) with a slick excited male voice: «این الماس اصله و پنجاه هزار دلار می‌ارزه! همین الان بیست هزار دلار پول نقد بهت می‌دم، بردار و برو!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S4_DIR}\\story2\\keyframes\\KF_06.jpg`,
    prompt:
      '[S2_C06] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the character in frame the entire time (no camera cuts), small cute 3D anthropomorphic wooden log character (cylindrical brown wood grain body with big cartoon eyes, strictly NO human face) at the black marble counter pushing the stack of cash away and holding the purple velvet ring box firmly, speaking in native Persian (Farsi) with a firm honest young voice: «نه آقا، من نمی‌تونم! این حلقه مال من نیست و مامانم بهم یاد داده هیچ‌وقت مال مردم رو برندارم!» Zero on-screen subtitles.',
  },
  {
    clip: 7,
    kf: `${S4_DIR}\\story2\\keyframes\\KF_07.jpg`,
    prompt:
      '[S2_C07] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), small 3D anthropomorphic wooden log character handing the purple velvet diamond ring box up to a 3D anthropomorphic birch-wood nurse character in teal hospital scrubs at the reception desk (strictly NO human faces), as the small wooden character speaks in native Persian (Farsi) with a polite hopeful young voice: «خانم پرستار، آقای ری این حلقه الماس رو توی پارکینگ انداخته بود! لطفاً همین الان به دستش برسونید!» Zero on-screen subtitles.',
  },
  {
    clip: 8,
    kf: `${S4_DIR}\\story2\\keyframes\\KF_08.jpg`,
    prompt:
      '[S2_C08] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), cunning 3D anthropomorphic birch-wood nurse in teal hospital scrubs and glasses behind the reception desk secretly dropping the sparkling diamond ring into her black purse while tall wealthy mahogany wooden man Mr. Ray in a winter coat stands at the counter (strictly NO human faces), as the nurse speaks in native Persian (Farsi) with a deceitful female voice: «پنجاه هزار دلار افتاد تو کیفم! نه آقای ری، امروز هیچ بچه‌ای هیچ جعبه‌ای اینجا نیاورده!» Zero on-screen subtitles.',
  },
];

BATCHES.s4_story3 = [
  {
    clip: 1,
    kf: `${S4_DIR}\\story3\\keyframes\\KF_01.jpg`,
    prompt:
      '[S3_C01] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), elderly 3D anthropomorphic female gorilla wearing glasses and a cardigan scolding a muscular 3D anthropomorphic silverback gorilla (Salvatore in a cream knit sweater, strictly NO human faces) sitting at a warm kitchen dinner table with plates of spaghetti, as Mama Gorilla speaks in native Persian (Farsi) with an angry scolding older female voice: «خجالت بکش سالواتوره! دیگه ازت خسته شدم، تو با این کارات به هیچ جا نمی‌رسی!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S4_DIR}\\story3\\keyframes\\KF_02.jpg`,
    prompt:
      '[S3_C02] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), elderly 3D anthropomorphic Mama Gorilla angrily sweeping a bundle of cash off the wooden spaghetti dinner table while Salvatore and his gorilla brother Tony sit quietly (strictly NO human faces), as Mama Gorilla speaks in native Persian (Farsi) with a harsh furious female voice: «این پول‌های کثیف رو هم از روی میز شام من جمع کن تا سفره‌م نجس نشده!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S4_DIR}\\story3\\keyframes\\KF_03.jpg`,
    prompt:
      '[S3_C03] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), two muscular 3D anthropomorphic gorilla brothers (Salvatore and Tony wearing dark leather jackets over sweaters, strictly NO human faces) walking side by side on a snowy city street at dusk, as Tony speaks in native Persian (Farsi) with a deep warm brotherly male voice: «از دست مادرت ناراحت نشو برادر... یه روزی دلت برای همین غر زدن‌هاش تنگ می‌شه!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S4_DIR}\\story3\\keyframes\\KF_04.jpg`,
    prompt:
      '[S3_C04] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium close-up keeping the characters in frame the entire time (no camera cuts), muscular 3D anthropomorphic gorilla Tony in a brown leather jacket smiling confidently at his gorilla brother Salvatore as snow falls around them at night (strictly NO human faces), speaking in native Persian (Farsi) with an excited warm male voice: «حالا بیا دنبالم سالواتوره، یه سورپرایز بزرگ برات دارم! امشب زندگی‌مون عوض می‌شه!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S4_DIR}\\story3\\keyframes\\KF_05.jpg`,
    prompt:
      '[S3_C05] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), two muscular 3D anthropomorphic gorilla brothers in leather jackets standing in the falling snow looking up at a grand golden illuminated luxury restaurant entrance at night (strictly NO human faces), as Salvatore speaks in native Persian (Farsi) with an emotional amazed male voice: «باورم نمیشه تونی... این تالار باشکوه واقعاً مالِ ماست؟! چطور هزینه‌ش رو جور کردی؟!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S4_DIR}\\story3\\keyframes\\KF_06.jpg`,
    prompt:
      '[S3_C06] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), muscular 3D anthropomorphic gorilla Tony in a leather jacket placing a proud brotherly hand on Salvatore’s shoulder in front of the glowing golden entrance in the snow (strictly NO human faces), speaking in native Persian (Farsi) with a powerful loyal male voice: «پس‌انداز چند سالم رو گذاشتم وسط! اینجاست آینده ما برادر، با هم قله رو فتح می‌کنیم!» Zero on-screen subtitles.',
  },
];

BATCHES.s4_story4 = [
  {
    clip: 1,
    kf: `${S4_DIR}\\story4\\keyframes\\KF_01.jpg`,
    prompt:
      '[S4_C01] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium close-up keeping the character in frame the entire time (no camera cuts), 3D anthropomorphic dark charcoal sponge character wearing a blue business suit sitting in a car seat holding a small makeup brush to his porous sponge forehead with a sly smirk (strictly NO human face), speaking in native Persian (Farsi) with a sneaky boastful male voice: «امروز بچه‌هامون دنیا میان! با گریم روی پیشونیم می‌نویسم یک میلیون دلار تا نگن فقیرم!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S4_DIR}\\story4\\keyframes\\KF_02.jpg`,
    prompt:
      '[S4_C02] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), 3D anthropomorphic glossy red bell pepper doctor character in glasses and white medical coat standing in a bright hospital nursery beside the dark sponge father in a blue suit and two hospital bassinets holding two miniature porous sponge characters (one bright yellow sponge and one dark charcoal sponge, strictly NO human faces), as Dr. Bell Pepper speaks in native Persian (Farsi) with a professional surprised male doctor voice: «تبریک می‌گم آقا، دوقلو دارید! قلِ زرد پانصد هزار دلاره، اما قلِ تیره پنج دلاره!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S4_DIR}\\story4\\keyframes\\KF_03.jpg`,
    prompt:
      '[S4_C03] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), 3D anthropomorphic dark sponge father in a blue suit standing sternly in a dimly lit brick basement beside a small dark porous sponge character sitting on a wooden cot (strictly NO human faces), as Sponge Dad speaks in native Persian (Farsi) with a harsh threatening male voice: «تو همین پایین توی زیرزمین تاریک می‌مونی! اگه مادرت ببینه پنج دلاری، جفتمون بدبخت می‌شیم!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S4_DIR}\\story4\\keyframes\\KF_04.jpg`,
    prompt:
      '[S4_C04] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), 3D anthropomorphic dark sponge father in a suit and a wealthy purple sponge grandfather in a tuxedo standing on a sunlit luxury mansion terrace proudly holding up a bright yellow sponge boy in a crown (strictly NO human faces), as Sponge Dad speaks in native Persian (Farsi) with an arrogant proud male voice: «ببینید چه تک‌پسر ثروتمندی داریم! پانصد هزار دلاره، توی این عمارت فقط ثروتمندا جا دارن!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S4_DIR}\\story4\\keyframes\\KF_05.jpg`,
    prompt:
      '[S4_C05] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium close-up keeping the character in frame the entire time (no camera cuts), 3D anthropomorphic red bell pepper doctor in glasses and white lab coat holding a phone in front of security monitor screens in a hospital office (strictly NO human faces), speaking in native Persian (Farsi) with an urgent serious male doctor voice: «خانم سندی، فیلم دوربین بیمارستان رو دیدم! شما دوقلو زایمان کردید و شوهرتون یکیشو قایم کرده!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S4_DIR}\\story4\\keyframes\\KF_06.jpg`,
    prompt:
      '[S4_C06] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), wealthy 3D anthropomorphic golden sponge mother wearing a royal blue velvet gown kneeling in the basement doorway and warmly hugging the small dark sponge boy (strictly NO human faces), speaking in native Persian (Farsi) with an emotional loving female voice: «هشت سال بهم دروغ گفت و بچه‌م رو توی زیرزمین حبس کرد! نترس عزیزم، پدرت تاوان می‌ده!» Zero on-screen subtitles.',
  },
];

BATCHES.s4_story5 = [
  {
    clip: 1,
    kf: `${S4_DIR}\\story5\\keyframes\\KF_01.jpg`,
    prompt:
      '[S5_C01] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), 3D anthropomorphic green pear restaurant manager wearing a dark apron and cap standing in a commercial kitchen beside a 3D wooden log character (Tung Tung Sahur) packing round tubs of bright green guacamole (strictly NO human faces), as Pear Manager speaks in native Persian (Farsi) with an excited greedy male voice: «با این سس آووکادوی مخفی که تونگ‌تونگ ساهور پخته، فروش رستورانمون رکورد شهر رو شکسته!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S4_DIR}\\story5\\keyframes\\KF_02.jpg`,
    prompt:
      '[S5_C02] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), two 3D anthropomorphic taco-shell and orange fruit customers sitting at a colorful Mexican restaurant booth happily dipping tortilla chips into a large bowl of glowing green guacamole (strictly NO human faces), as the customer speaks in native Persian (Farsi) with a delighted enthusiastic male voice: «دو پرس ناچو با سس گواکاموله دوبل بدید! وای چه طعم تند و بی‌نظیری داره!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S4_DIR}\\story5\\keyframes\\KF_03.jpg`,
    prompt:
      '[S5_C03] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), two 3D anthropomorphic characters sitting up in bed in a bedroom gasping in horror as their bodies and heads have mutated into bumpy dark-green avocados with green avocado flesh (strictly NO human skin faces), speaking in native Persian (Farsi) with a panicked horrified voice: «وای خدایا چه بلایی سرمون اومده؟! داریم تبدیل به آووکادو می‌شیم! تقصیر غذای اون رستورانه!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S4_DIR}\\story5\\keyframes\\KF_04.jpg`,
    prompt:
      '[S5_C04] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), 3D anthropomorphic green pear manager in a black restaurant uniform and cap sweating in panic at the counter while Cucumber Police officers stand behind him (strictly NO human faces), as Pear Manager speaks in native Persian (Farsi) with a terrified defensive male voice: «به خدا تقصیر من نبود! این سس گواکاموله رو تونگ‌تونگ ساهور توی آشپزخونه پخته بود!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S4_DIR}\\story5\\keyframes\\KF_05.jpg`,
    prompt:
      '[S5_C05] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the character in frame the entire time (no camera cuts), 3D anthropomorphic green cucumber police officer in a dark blue police uniform and cap inspecting the empty restaurant kitchen doorway (strictly NO human face), speaking in native Persian (Farsi) with a serious detective male voice: «انگار تونگ‌تونگ ساهور خیلی زرنگ شده و قبل از رسیدن پلیس از درِ پشتی فرار کرده!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S4_DIR}\\story5\\keyframes\\KF_06.jpg`,
    prompt:
      '[S5_C06] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), tall 3D anthropomorphic wooden log character (Tung Tung Sahur) disguised in a white doctor coat and head mirror standing beside two green avocado patients lying in hospital beds in a bright hospital room (strictly NO human faces), as the wooden doctor speaks in native Persian (Farsi) with a sly bargaining male voice: «من پادزهرش رو دارم و درمانتون می‌کنم... فقط به یک شرط: همین الان شکایتتون رو پس بگیرید!» Zero on-screen subtitles.',
  },
];

BATCHES.s4_story6 = [
  {
    clip: 1,
    kf: `${S4_DIR}\\story6\\keyframes\\KF_01.jpg`,
    prompt:
      '[S6_C01] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), 3D anthropomorphic yellow banana character holding a glass of glowing pink lemonade in front of a sunny outdoor pink lemonade stand where glamorous 3D red strawberry woman (Strawberrina with a full 3D red seeded strawberry head and green leaf crown, strictly NO human face) smiles in a white dress, as Banana Customer speaks in native Persian (Farsi) with an amazed ecstatic male voice: «وای خدای من، این خوشمزه‌ترین لیموناد صورتیه که تو عمرم خوردم! طعمش واقعاً بی‌نظیره!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S4_DIR}\\story6\\keyframes\\KF_02.jpg`,
    prompt:
      '[S6_C02] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the character in frame the entire time (no camera cuts), glamorous 3D anthropomorphic red strawberry woman (Strawberrina with a full 3D red strawberry head and green leaves, strictly NO human face) in a red apron inside a dimly lit kitchen at night grating sparkling pink crystal powder into a large steaming pot of yellow-pink lemonade with a mischievous smirk, speaking in native Persian (Farsi) with a sneaky whispering female voice: «هیچ‌کس نباید بفهمه ماده مخفی این لیموناد چیه! تندتر رنده کن تا شهر رو تیغ بزنیم!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S4_DIR}\\story6\\keyframes\\KF_03.jpg`,
    prompt:
      '[S6_C03] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), 3D anthropomorphic yellow lemon brother in a white shirt standing outside the crowded pink lemonade stall watching fruit customers with a ring light drink pink cups in shock (strictly NO human faces), speaking in native Persian (Farsi) with a stunned suspicious male voice: «باورم نمیشه! لیوانی بیست دلار می‌فروشه و همه جلوی غرفه‌ش صف کشیدن! یه کلکی تو کارشه!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S4_DIR}\\story6\\keyframes\\KF_04.jpg`,
    prompt:
      '[S6_C04] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), glamorous 3D anthropomorphic red strawberry woman (Strawberrina with a full 3D red strawberry head, strictly NO human face) in a pink-and-white apron standing proudly on a red carpet outside her grand pink shop surrounded by cheering apples, pears, and oranges, speaking in native Persian (Farsi) with a joyful charming female voice: «خوش اومدید به افتتاحیه مغازه من! همه می‌پرسن راز این طعم چیه؟ رازش فقط عشق خالصه!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S4_DIR}\\story6\\keyframes\\KF_05.jpg`,
    prompt:
      '[S6_C05] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), 3D anthropomorphic yellow lemon brother and a stern 3D green apple health inspector wearing glasses and a dark suit walking purposefully through the kitchen doorway (strictly NO human faces), as Lemon Brother speaks in native Persian (Farsi) with a determined male voice: «کنار برید، بازرس بهداشت همراه منه! می‌ریم توی آشپزخونه پشتی ببینیم چی تو دیگ می‌ریزه!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S4_DIR}\\story6\\keyframes\\KF_06.jpg`,
    prompt:
      '[S6_C06] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), stern 3D anthropomorphic green apple health inspector in glasses and suit holding a clipboard alongside the yellow lemon brother confronting shocked Strawberrina (full 3D red strawberry head in red apron) beside the steaming pot in the kitchen (strictly NO human faces), as the Green Apple Inspector speaks in native Persian (Farsi) with a stern authoritative male voice: «همون‌جا وایسا خانم توت‌فرنگی! این رنده و پودر مشکوک کنار دیگ چیه؟! مغازه‌ت پلمپ می‌شه!» Zero on-screen subtitles.',
  },
];

BATCHES.s4_story7 = [
  {
    clip: 1,
    kf: `${S4_DIR}\\story7\\keyframes\\KF_01.jpg`,
    prompt:
      '[S7_C01] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the character in frame the entire time (no camera cuts), tired 3D anthropomorphic brown owl engineer (Arash) wearing round glasses and a blue hoodie clutching his feathered head in frustration in front of a glowing red lock icon on his laptop surrounded by tall stacks of paper at night (strictly NO human faces), speaking in native Persian (Farsi) with a stressed exhausted male voice: «ساعت دو نصفه‌شبه و چت‌جی‌پی‌تی رایگانم قفل شد! خرید دلاریش هم ویزاکارت می‌خواد!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S4_DIR}\\story7\\keyframes\\KF_02.jpg`,
    prompt:
      '[S7_C02] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), stern 3D anthropomorphic grizzly bear boss in a dark suit and red tie standing beside brown owl Arash at his desk and pointing angrily at his gold wristwatch (strictly NO human faces), as the Bear Boss speaks in native Persian (Farsi) with a deep angry authoritative male voice: «آرش! اگه تا ساعت هشت صبح گزارش کامل تحلیلی رو تحویل ندی، از شرکت اخراجی!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S4_DIR}\\story7\\keyframes\\KF_03.jpg`,
    prompt:
      '[S7_C03] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), smart 3D anthropomorphic orange fox friend (Sina) wearing a sleek green tech vest smiling confidently beside brown owl Arash and holding up a glowing emerald-and-gold key box (strictly NO human faces), as the Fox speaks in native Persian (Farsi) with a warm energetic friendly male voice: «نگران نباش! از کلیدباکس چت‌جی‌پی‌تی گو رو سه میلیون و ششصد و نود تومن بخر!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S4_DIR}\\story7\\keyframes\\KF_04.jpg`,
    prompt:
      '[S7_C04] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the character in frame the entire time (no camera cuts), happy 3D anthropomorphic brown owl engineer (Arash) in round glasses and blue hoodie beaming with excitement as glowing emerald 3D holographic charts and neat golden report pages swirl magically above his laptop (strictly NO human faces), speaking in native Persian (Farsi) with an amazed joyful male voice: «عالیه! به‌جای دردسر بیست دلار ویزاکارت، اشتراک چت‌جی‌پی‌تی پلاس رو چهار قسطه با گارانتی گرفتم!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S4_DIR}\\story7\\keyframes\\KF_05.jpg`,
    prompt:
      '[S7_C05] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), in a sunny modern boardroom the 3D anthropomorphic grizzly bear boss in a suit claps his paws in amazement before a floating 3D holographic chart projection while brown owl Arash smiles proudly (strictly NO human faces), as the Bear Boss speaks in native Persian (Farsi) with an impressed enthusiastic male voice: «فوق‌العاده‌ست آرش! این دقیق‌ترین گزارشیه که تو عمرم دیدم! همین امروز ترفیع می‌گیری!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S4_DIR}\\story7\\keyframes\\KF_06.jpg`,
    prompt:
      '[S7_C06] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), 3D anthropomorphic brown owl Arash and orange fox Sina high-fiving joyfully in a bright modern office beside a glowing golden key emblem on the desk (strictly NO human faces), as Fox Sina speaks in native Persian (Farsi) with an upbeat confident male voice: «برای خرید چت‌جی‌پی‌تی گو، پلاس و پرو با گارانتی سی روزه، همین الان برو کلیدباکس!» Zero on-screen subtitles.',
  },
];

BATCHES.s4_story8 = [
  {
    clip: 1,
    kf: `${S4_DIR}\\story8\\keyframes\\KF_01.jpg`,
    prompt:
      '[S8_C01] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the character in frame the entire time (no camera cuts), creative 3D anthropomorphic ginger cat designer (Nima) wearing a yellow beanie and blue denim jacket looking sadly into his empty brown leather wallet beside a dark computer monitor in a cozy studio (strictly NO human faces), speaking in native Persian (Farsi) with a worried young male voice: «سفارش مشتری رو باید فردا تحویل بدم، اما تا سر ماه پول نقد اکانت هوش مصنوعی ندارم!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S4_DIR}\\story8\\keyframes\\KF_02.jpg`,
    prompt:
      '[S8_C02] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), in a shadowy neon alley a sneaky 3D anthropomorphic black crow seller in a dark trench coat holds a long paper scroll and gestures greedily at worried ginger cat Nima (strictly NO human faces), as the Crow speaks in native Persian (Farsi) with a harsh greedy male voice: «اگه اکانت می‌خوای باید کل پول دلار و کارمزد رو همین الان نقد کارت‌به‌کارت کنی!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S4_DIR}\\story8\\keyframes\\KF_03.jpg`,
    prompt:
      '[S8_C03] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), inside a bright warm futuristic shop a friendly 3D anthropomorphic golden lion shopkeeper (Dana) in a clean blue blazer welcomes ginger cat Nima and points to four equal glowing golden coins floating above a glass counter (strictly NO human faces), as the Lion speaks in native Persian (Farsi) with a warm reassuring male voice: «صبر کن نیما! توی سایت کلیدباکس می‌تونی همه اکانت‌ها رو با ترب‌پی و دیجی‌پی چهار قسطه بخری!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S4_DIR}\\story8\\keyframes\\KF_04.jpg`,
    prompt:
      '[S8_C04] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the character in frame the entire time (no camera cuts), 3D anthropomorphic ginger cat Nima in a yellow beanie and denim jacket smiling with sparkling eyes as he places just one small glowing golden coin on the glass counter while three other glowing coins float gently in crystal orbs (strictly NO human faces), speaking in native Persian (Farsi) with an excited amazed male voice: «یعنی بدون ضامن و چک، امروز فقط یک‌چهارم پول رو می‌دم و اکانتم همون لحظه فعال می‌شه؟!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S4_DIR}\\story8\\keyframes\\KF_05.jpg`,
    prompt:
      '[S8_C05] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), friendly 3D anthropomorphic golden lion Dana in a blue blazer handing ginger cat Nima a radiant golden key box as colorful 3D design holograms bloom around them (strictly NO human faces), as the Lion speaks in native Persian (Farsi) with a confident warm male voice: «دقیقاً! با درگاه رسمی ترب‌پی و دیجی‌پی، اکانتت رو الان تحویل بگیر و قسطی پرداخت کن!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S4_DIR}\\story8\\keyframes\\KF_06.jpg`,
    prompt:
      '[S8_C06] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the character in frame the entire time (no camera cuts), happy 3D anthropomorphic ginger cat designer Nima in his yellow beanie celebrating with a thumbs-up in front of glowing dual monitors filled with vibrant 3D art in his sunny studio (strictly NO human faces), speaking in native Persian (Farsi) with an energetic cheerful male voice: «همین الان برو سایت کلیدباکس و اکانت هوش مصنوعیت رو چهار قسطه با ترب‌پی و دیجی‌پی بخر!» Zero on-screen subtitles.',
  },
];

BATCHES.s4_story9 = [
  {
    clip: 1,
    kf: `${S4_DIR}\\story9\\keyframes\\KF_01.jpg`,
    prompt:
      '[S9_C01] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the character in frame the entire time (no camera cuts), ambitious 3D anthropomorphic red panda director (Ramin) wearing a burgundy vest and headset looking wistfully at five glowing golden crystal orbs inside a glass display case in a small studio (strictly NO human faces), speaking in native Persian (Farsi) with a thoughtful longing male voice: «واسه ساختن استودیوی حرفه‌ای به چت‌جی‌پی‌تی پرو و جمنای اولترا نیاز دارم، ولی پول نقدش سنگینه!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S4_DIR}\\story9\\keyframes\\KF_02.jpg`,
    prompt:
      '[S9_C02] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), heroic 3D anthropomorphic golden eagle advisor (Parsa) in a sleek green-and-gold jacket standing beside red panda Ramin and holding a radiant golden treasure shield that illuminates the room (strictly NO human faces), as the Eagle speaks in native Persian (Farsi) with a powerful exciting male voice: «رامین خبر نداری؟! ترب تا سقف سی میلیون تومن اعتبار خرید قسطی بدون ضامن بهت می‌ده!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S4_DIR}\\story9\\keyframes\\KF_03.jpg`,
    prompt:
      '[S9_C03] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the character in frame the entire time (no camera cuts), 3D anthropomorphic red panda Ramin in a burgundy vest gasping in pure excitement with starry eyes as warm golden light from the treasure shield reflects on his fur (strictly NO human faces), speaking in native Persian (Farsi) with an astonished thrilled male voice: «سی میلیون تومن اعتبار ترب؟! یعنی می‌تونم قوی‌ترین اکانت‌های هوش مصنوعی دنیا رو یکجا بخرم؟!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S4_DIR}\\story9\\keyframes\\KF_04.jpg`,
    prompt:
      '[S9_C04] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), inside a gleaming futuristic vault 3D anthropomorphic golden eagle Parsa unlocks five floating golden energy orbs with a glowing key while red panda Ramin watches in awe (strictly NO human faces), as the Eagle speaks in native Persian (Farsi) with a confident heroic male voice: «آره! توی سایت کلیدباکس با اعتبار سی میلیونی ترب، کل پکیج حرفه‌ای رو چهار قسطه بردار!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S4_DIR}\\story9\\keyframes\\KF_05.jpg`,
    prompt:
      '[S9_C05] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), in a high-tech glowing animation studio a cheerful 3D anthropomorphic brown otter animator in blue overalls and red panda Ramin cheer joyfully before dazzling 3D holographic cinema projections (strictly NO human faces), as the Otter speaks in native Persian (Farsi) with a joyful enthusiastic male voice: «هورا! با اعتبار سی میلیونی ترب، استودیومون مجهز شد و سرعت کارمون ده برابر شده!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S4_DIR}\\story9\\keyframes\\KF_06.jpg`,
    prompt:
      '[S9_C06] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), 3D anthropomorphic red panda Ramin and golden eagle Parsa standing proudly together in the bright upgraded studio holding a glowing golden key box and treasure shield (strictly NO human faces), as Red Panda Ramin speaks in native Persian (Farsi) with a warm energetic male voice: «اعتبار سی میلیون تومانی ترب رو از دست نده! همین الان از کلیدباکس قسطی خرید کن!» Zero on-screen subtitles.',
  },
];

const S6_DIR = 'C:\\Users\\LifeCycle\\.gemini\\antigravity\\scratch\\series6-emotional-groceries-farsi';

BATCHES.eg_part1 = [
  {
    clip: 1,
    kf: `${S6_DIR}\\part1\\keyframes\\KF_01.jpg`,
    prompt:
      '[EG1_C01] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the character in frame the entire time (no camera cuts), greedy 3D anthropomorphic rectangular yellow kitchen sponge father (Babak, porous yellow sponge body with green scrubbing pad top, strictly NO human face) in a brown suit sitting inside his car and using a makeup brush to paint 1,000,000 on his forehead in the rearview mirror, speaking in native Persian (Farsi) with exact vowel pronunciation and a sly nervous male voice: «اِمْرُوز زَنَم زایْمان می‌کُنه! با کِرِم‌پُودْر رُو پیشُونیم می‌نِویسَم یِک میلْیُون، تا نَفَهْمَن فَقیرَم!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S6_DIR}\\part1\\keyframes\\KF_02.jpg`,
    prompt:
      '[EG1_C02] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), 3D anthropomorphic yellow kitchen sponge father (Babak in brown suit with 1,000,000 on his forehead) rushing up to the hospital reception desk where a 3D anthropomorphic glossy red bell pepper doctor in glasses and a white coat points urgently toward Room 407 (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and an urgent male voice: «خانُمَم تُویِ کُدُوم اُتاق داره زایْمان می‌کُنه دُکْتُر؟ بُدُو اُتاقِ چَهارْصَد و هَفْت، بَچّه‌ها مُنْتَظِر نِمی‌مُونَن!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S6_DIR}\\part1\\keyframes\\KF_03.jpg`,
    prompt:
      '[EG1_C03] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), inside hospital room 407 a 3D anthropomorphic red bell pepper doctor in glasses and white medical coat holds two swaddled sponge twin babies (one dark charcoal-black sponge baby with 5 on his forehead and one bright yellow sponge baby with 500,000 on his forehead) in front of shocked yellow sponge father Babak (strictly NO human faces), as the Doctor speaks in native Persian (Farsi) with exact vowel pronunciation and a warm amazed male doctor voice: «تَبْریک می‌گَم آقا، دُوقُلُو دارید! قُلِ سِیاه فَقَط پَنْج دُلاریه، اَمّا قُلِ زَرْد پانْصَد هِزار دُلاریه!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S6_DIR}\\part1\\keyframes\\KF_04.jpg`,
    prompt:
      '[EG1_C04] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), 3D anthropomorphic yellow sponge father Babak grabbing both baby cradles in a hurry while brown squirrel mother Sandy lies unconscious on the hospital bed behind them and the red bell pepper doctor raises a hand in alarm (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a hurried male voice: «هَمین اَلان هَر دُو تا بَچّه رُو می‌بَرَم! صَبْر کُنید آقا، هَمْسَرِتُون هَنُوز بِه هُوش نَیُومَده!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S6_DIR}\\part1\\keyframes\\KF_05.jpg`,
    prompt:
      '[EG1_C05] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the character in frame the entire time (no camera cuts), 3D anthropomorphic yellow sponge father Babak in his brown suit sneaking down dark stone stairs toward the mansion basement at night carrying the swaddled dark charcoal-black sponge baby with 5 on his forehead (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a sneaky scheming male voice: «چِه بِهْتَر کِه سَنْدی بی‌هُوشه! این بَچّه پَنْج دُلاری رُو قایِم می‌کُنَم تا آبِرُوم نَره!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S6_DIR}\\part1\\keyframes\\KF_06.jpg`,
    prompt:
      '[EG1_C06] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human sponge characters in the reference image, static medium shot keeping both characters in frame the entire time (no camera cuts), inside a dark dusty basement under a single dim lightbulb the 3D rectangular bright-yellow porous kitchen sponge father with a flat dark-green scouring-pad top, 1,000,000 on his forehead, large 3D white cartoon eyes, 3D sponge nose, brown suit jacket, white shirt, and red necktie places the crying swaddled 3D rectangular dark charcoal-black porous sponge baby with 5 on his forehead inside a wooden crate and points a stern warning finger (strictly NO human faces, keep the exact rectangular yellow sponge father with green flat top, 1,000,000 forehead, and brown suit from the reference image), speaking in native Persian (Farsi) with exact vowel pronunciation and a cold harsh male voice: «هَمین پایین تُو تاریکی می‌مُونی! اَگه مادَرِت اُون پَنْج دُلارِ پیشُونیت رُو بِبینه، کارِمُون تَمُومه!» Zero on-screen subtitles.',
  },
];

BATCHES.eg_part2 = [
  {
    clip: 1,
    kf: `${S6_DIR}\\part2\\keyframes\\KF_01.jpg`,
    prompt:
      '[EG2_C01] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters in the reference image, static medium two-shot keeping the characters in frame the entire time (no camera cuts), in a sunlit luxury mansion bedroom the 3D brown woodland squirrel mother with perky ears, fluffy tail, and 10,000,000 on her forehead in a pink satin dress and pearl necklace smiles warmly on a velvet sofa while the 3D rectangular bright-yellow porous kitchen sponge father with a flat green scouring-pad top, 1,000,000 on his forehead, large 3D white cartoon eyes, 3D sponge nose, brown suit jacket, white shirt, and red necktie proudly holds their swaddled newborn 3D yellow rectangular sponge baby with 500,000 on his forehead (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a smooth reassuring male voice: «آخ سَرَم، چی شُد؟ اِسْتِراحَت کُن عِشْقَم، بِبین پِسَرِ تَک‌فَرْزَنْدِمُون با پانْصَد هِزار دُلار دُنْیا اُومَده!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S6_DIR}\\part2\\keyframes\\KF_02.jpg`,
    prompt:
      '[EG2_C02] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), eight years later in a golden luxury mansion dining room 3D anthropomorphic yellow sponge father Babak and 8-year-old rich yellow sponge boy Tala (wearing a navy-and-gold blazer with 500,000 glowing on his forehead, strictly NO human faces) toast arrogantly with golden goblets, speaking in native Persian (Farsi) with exact vowel pronunciation and an arrogant proud male voice: «پانْصَد هِزار دُلار رُویِ پیشُونی، یَعْنی اِصالَت و ثِرْوَت! دُرُسْته پِدَر، تُو این خُونه فَقَط پُولْدارها جان!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S6_DIR}\\part2\\keyframes\\KF_03.jpg`,
    prompt:
      '[EG2_C03] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the character in frame the entire time (no camera cuts), down in the dark damp basement 8-year-old poor dark charcoal-black sponge boy Kouchoulou (with 5 on his forehead and big teary eyes, wearing a tattered grey shirt, strictly NO human face) looks up at the locked wooden basement door pleadingly, speaking in native Persian (Farsi) with exact vowel pronunciation and a sad innocent child voice: «بابا جُون، چِرا مَن اِجازه نَدارَم بِیام طَبَقِه بالا؟ کِی می‌تُونَم مادَرَم رُو بِبینَم؟» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S6_DIR}\\part2\\keyframes\\KF_04.jpg`,
    prompt:
      '[EG2_C04] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), 3D anthropomorphic yellow sponge father Babak standing on the dark basement stairs shoving a small bowl of plain white rice toward poor little charcoal-black sponge boy Kouchoulou with 5 on his forehead (strictly NO human faces), as Babak speaks in native Persian (Farsi) with exact vowel pronunciation and an angry dismissive male voice: «با پَنْج دُلار کُدُوم قَبْض رُو می‌شه داد؟ بِرِنْجِت رُو بُخُور و هَمین پایین ساکِت بِمُون!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S6_DIR}\\part2\\keyframes\\KF_05.jpg`,
    prompt:
      '[EG2_C05] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), outside the sunny mansion porch the 3D warm brown woodland squirrel mother with perky ears, fluffy tail, and 10,000,000 on her forehead in a pink satin dress and pearl necklace hugs the 3D rectangular bright-yellow porous kitchen sponge boy with a flat dark-green scouring-pad top, 500,000 on his forehead, wearing his tailored navy-blue luxury blazer with gold trim, crisp white shirt, red necktie, and golden backpack (strictly NO human faces, keep his exact navy-blue blazer and flat green top from the reference image), speaking in native Persian (Farsi) with exact vowel pronunciation and a warm proud voice: «اِمْرُوز تُویِ مَدْرِسه باعِثِ اِفْتِخارَم باش پِسَرَم! نِگَران نَباش مامان، اِمْرُوز کُلِّ مَدْرِسه رُو می‌خَرَم!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S6_DIR}\\part2\\keyframes\\KF_06.jpg`,
    prompt:
      '[EG2_C06] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human rectangular sponge character in the reference image, static medium close-up keeping the character in frame the entire time (no camera cuts), the 3D rectangular dark charcoal-black porous kitchen sponge child with 5 on his forehead and large round teary cartoon eyes directly on his flat porous charcoal sponge block (strictly NO human nose, NO human ears, NO human lips, NO human face) wearing a tattered grey shirt peers through the dusty barred basement window at ground level with tears rolling down his porous sponge face, speaking in native Persian (Farsi) with exact vowel pronunciation and a heartbroken tearful child voice: «مامان چِقَدْر مِهْرَبُونه... اِی کاش می‌دُونِسْت مَنَم زِنْدِه‌اَم و فَقَط یِک‌بار مَنُو بَغَل می‌کَرْد!» Zero on-screen subtitles.',
  },
];

BATCHES.eg_part3 = [
  {
    clip: 1,
    kf: `${S6_DIR}\\part3\\keyframes\\KF_01.jpg`,
    prompt:
      '[EG3_C01] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the character in frame the entire time (no camera cuts), in a hospital security monitor room 3D anthropomorphic red bell pepper doctor in glasses and white coat gasps in shock as he points at an 8-year-old CCTV screen showing yellow sponge father Babak stealing both twin babies (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a shocked urgent male doctor voice: «این فیلْمِ دُورْبینِ مَدارْبَسْته رُو بِبین! بابَک هَر دُو تا نُوزاد رُو دُزْدیده و سَنْدی خَبَر نَداره!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S6_DIR}\\part3\\keyframes\\KF_02.jpg`,
    prompt:
      '[EG3_C02] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the character in frame the entire time (no camera cuts), 3D anthropomorphic red bell pepper doctor in glasses and white medical coat holding his smartphone urgently to his ear in his hospital office with the security footage glowing on his monitor (strictly NO human face), speaking in native Persian (Farsi) with exact vowel pronunciation and an urgent serious male doctor voice: «اَلُو خانُمِ سَنْدی! شُما هَشْت سالِ پیش دُوقُلُو زایْمان کَرْدید، شُوهَرِتُون قُلِ دُوُّم رُو قایِم کَرْده!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S6_DIR}\\part3\\keyframes\\KF_03.jpg`,
    prompt:
      '[EG3_C03] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the character in frame the entire time (no camera cuts), inside the mansion hallway 3D anthropomorphic brown squirrel mother Sandy in her pink luxury dress and pearls clutches her smartphone with fiery tears of fury and storms toward the locked wooden basement door (strictly NO human face), speaking in native Persian (Farsi) with exact vowel pronunciation and a furious emotional female voice: «دُوقُلُو داشْتَم؟! یَعْنی هَشْت سالِ تَمام بِه مَن دُرُوغ گُفْته؟! اِمْرُوز حِسابِش رُو کَفِ دَسْتِش می‌ذارَم!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S6_DIR}\\part3\\keyframes\\KF_04.jpg`,
    prompt:
      '[EG3_C04] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), 3D anthropomorphic brown squirrel mother Sandy throwing open the dark basement door and gasping in shock as she sees trembling little charcoal-black sponge boy Kouchoulou with 5 on his forehead in a tattered grey shirt sitting on the floor (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and an emotional voice: «خُدایِ مَن، تُو کی هَسْتی تُو زیرْزَمینِ مَن؟! بِبَخْشید خانُم، بابام گُفْته اِجازه نَدارَم بِیام بالا!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S6_DIR}\\part3\\keyframes\\KF_05.jpg`,
    prompt:
      '[EG3_C05] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), 3D anthropomorphic brown squirrel mother Sandy kneeling on the basement floor wrapping poor little charcoal-black sponge boy Kouchoulou with 5 on his forehead in a warm tearful motherly embrace as golden sunlight streams down the open stairs (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a weeping loving female mother voice: «گِرْیه نَکُن جِگَرْگُوشِه مَن! مَن مادَرِتَم عَزیزَم، دیگه هیچ‌وَقْت نِمی‌ذارَم تُو تاریکی تَنْها بِمُونی!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S6_DIR}\\part3\\keyframes\\KF_06.jpg`,
    prompt:
      '[EG3_C06] 3D Pixar/Cinema4D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), outside the sunny golden mansion gates 3D anthropomorphic brown squirrel mother Sandy stands proudly holding happy charcoal-black sponge boy Kouchoulou (now wearing a royal blue blazer with 5,000,000 shining on his forehead) while disgraced yellow sponge father Babak with 0 on his forehead walks away crying with his suitcase (strictly NO human faces), as Sandy speaks in native Persian (Farsi) with exact vowel pronunciation and a proud triumphant female voice: «پِدَرِ دُرُوغْگُوت رُو بیرُون کَرْدَم پِسَرَم! اَز اِمْرُوز تَمامِ این عِمارَت و ثِرْوَت مالِ تُوئه!» Zero on-screen subtitles.',
  },
];

const S7_DIR = 'C:\\Users\\LifeCycle\\.gemini\\antigravity\\scratch\\series7-sponge-pizza-billionaire-farsi';

BATCHES.pz_part1 = [
  {
    clip: 1,
    kf: `${S7_DIR}\\part1\\keyframes\\KF_01.jpg`,
    prompt:
      '[PZ1_C01] 3D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), at a warm wooden pizza parlor counter the poor hungry customer in a tattered shirt and backpack pleads earnestly with the kind cashier in a green polo shirt (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a humble pleading male voice: «خانُم، می‌شه فَقَط یِک تِکّه پیتْزا بِه مَن بِدید؟ بِه خُدا دُو رُوزه کِه هیچْ‌چی نَخُورْدَم!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S7_DIR}\\part1\\keyframes\\KF_02.jpg`,
    prompt:
      '[PZ1_C02] 3D stylized cartoon animation matching the reference image style, static medium shot keeping the character in frame the entire time (no camera cuts), behind the pizza counter the kind cashier in a green pizza shirt and white apron opens the warm display case and hands a fresh slice of pepperoni pizza forward with a compassionate smile (strictly NO human face), speaking in native Persian (Farsi) with exact vowel pronunciation and a warm kind female voice: «آخ عَزیزَم، چِقَدْر گُرْسِنه‌ای! بِیا این تِکّه پیتْزایِ گَرْم رُو بُخُور، وَلی فَقَط هَمین یِک‌باره ها!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S7_DIR}\\part1\\keyframes\\KF_03.jpg`,
    prompt:
      '[PZ1_C03] 3D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), the poor customer in the tattered shirt holds the warm pizza slice with grateful tears while the kind cashier in the green shirt whispers for him to hurry before her boss sees (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation: «خِیْلی مَمْنُونَم خانُم، هیچ‌وَقْت این لُطْفِتُون رُو فَرامُوش نِمی‌کُنَم! نُوشِ جان، فَقَط زُود بُرُو تا رَئیسَم نَدیده!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S7_DIR}\\part1\\keyframes\\KF_04.jpg`,
    prompt:
      '[PZ1_C04] 3D stylized cartoon animation matching the reference image style, static medium close-up keeping the character in frame the entire time (no camera cuts), the greedy red restaurant manager in a white short-sleeve dress shirt, black tie, and gold badge glares furiously from the kitchen doorway with his arms crossed (strictly NO human face), speaking in native Persian (Farsi) with exact vowel pronunciation and an angry harsh male voice: «عَجَب! این دُخْتَره هِی داره پیتْزاهایِ مَن رُو مَجّانی می‌ده بِه این گِداها! اَلان حِسابِش رُو می‌رِسَم!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S7_DIR}\\part1\\keyframes\\KF_05.jpg`,
    prompt:
      '[PZ1_C05] 3D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), inside the restaurant office the kind cashier in the green shirt sits nervously at the desk while the angry red manager in a white shirt and tie slams his hand on the desk (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation: «رَئیس، مَن رُو خْواسْته بُودید؟ بَله! کی بِه تُو اِجازه داده پیتْزایِ رِسْتُورانِ مَن رُو مَجّانی بِبَخْشی؟!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S7_DIR}\\part1\\keyframes\\KF_06.jpg`,
    prompt:
      '[PZ1_C06] 3D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), inside the office the angry red restaurant manager in a white shirt and black tie leans over the desk pointing a threatening finger at the worried cashier in the green shirt (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a furious male boss voice: «پُولِ این پیتْزا رُو اَز حُقُوقِت کَم می‌کُنَم! یِک‌بارِ دیگه بَبینَم، هَمین‌جا اِخْراجی! فَهمیدی؟!» Zero on-screen subtitles.',
  },
];

BATCHES.pz_part2 = [
  {
    clip: 1,
    kf: `${S7_DIR}\\part2\\keyframes\\KF_01.jpg`,
    prompt:
      '[PZ2_C01] 3D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), in the tiled restaurant kitchen the kind cashier in a green shirt and white apron cries with her hands on her cheeks while her tall friendly pink coworker listens sympathetically (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a tearful female voice: «هُومَن بَدْبَخْت شُدَم! رَئیس پُولِ پیتْزا رُو اَز حُقُوقَم کَم کَرْد و گُفْت اِخْراجَم می‌کُنه!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S7_DIR}\\part2\\keyframes\\KF_02.jpg`,
    prompt:
      '[PZ2_C02] 3D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), in the restaurant kitchen the tall friendly pink coworker in a green shirt places a comforting hand on the crying cashier shoulder (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a warm supportive male voice: «آرُوم باش آبْجی، غُصّه نَخُور! اُون رَئیسِ طَمَع‌کار اَصْلاً قَلْب تُو سینَش نیسْت!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S7_DIR}\\part2\\keyframes\\KF_03.jpg`,
    prompt:
      '[PZ2_C03] 3D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), at the pizza parlor cash register the poor customer in the tattered shirt smiles gratefully at the kind cashier in the green shirt who looks worriedly toward the office (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation: «خانُم، اُومَدَم دُوباره تَشَکُّر کُنَم، اُون پیتْزا جُونَم رُو نِجات داد! خْواهِش می‌کُنَم، وَلی رَئیسَم بَفَهْمه بَد می‌شه!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S7_DIR}\\part2\\keyframes\\KF_04.jpg`,
    prompt:
      '[PZ2_C04] 3D stylized cartoon animation matching the exact 3D non-human characters in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), at the glass front door of the restaurant the angry 3D red crustacean manager in a white shirt and tie shoves the poor 3D dark charcoal-black porous rectangular sponge character with black dreads in the tattered shirt out onto the sidewalk (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and an angry harsh male voice: «گُمْ‌شُو بیرُون گِدایِ بی‌مَصْرَف! یِک‌بارِ دیگه طَرَفِ رِسْتُورانِ مَن پِیْدات بِشه، پُلیس خَبَر می‌کُنَم!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S7_DIR}\\part2\\keyframes\\KF_05.jpg`,
    prompt:
      '[PZ2_C05] 3D stylized cartoon animation matching the reference image style, static medium two-shot keeping both characters in frame the entire time (no camera cuts), outside in the dim brick alley beside the restaurant the kind cashier in the green shirt hands a warm plate of pizza to the sad customer in the tattered shirt sitting on the curb (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a gentle caring female voice: «بِبَخْشید کِه رَئیسَم باهاتُون بَد رَفْتار کَرْد! بِیا، این پیتْزا رُو با پُولِ خُودَم بَراتُون خَریدَم!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S7_DIR}\\part2\\keyframes\\KF_06.jpg`,
    prompt:
      '[PZ2_C06] 3D stylized cartoon animation matching the reference image style, static medium shot keeping the character in frame the entire time (no camera cuts), inside an ultra-modern high-rise luxury glass penthouse overlooking the sunset city skyline the dark character walks confidently across the marble floor (strictly NO human face), speaking in native Persian (Farsi) with exact vowel pronunciation and a confident determined male voice: «اُون رَئیسِ مَغْرُور نِمی‌دُونه مَن کی هَسْتَم! وَقْتِشه یِک زَنْگ بِزَنَم و صاحِبِ کُلِّ این رِسْتُوران بِشَم!» Zero on-screen subtitles.',
  },
];

BATCHES.pz_part3 = [
  {
    clip: 1,
    kf: `${S7_DIR}\\part3\\keyframes\\KF_01.jpg`,
    prompt:
      '[PZ3_C01] 3D stylized cartoon animation matching the reference image style, static medium shot keeping the character in frame the entire time (no camera cuts), inside a golden luxury walk-in dressing room the billionaire character wears a sharp tailored black tuxedo suit, white shirt, black tie, and dark sunglasses in front of a golden mirror (strictly NO human face), speaking in native Persian (Farsi) with exact vowel pronunciation and a powerful confident male voice: «آزْمایِشِ مَخْفیِ مَن تَمُوم شُد! حالا با لِباسِ اَصْلیم می‌رَم تا جَوابِ خُوبی و بَدی رُو بِدَم!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S7_DIR}\\part3\\keyframes\\KF_02.jpg`,
    prompt:
      '[PZ3_C02] 3D stylized cartoon animation matching the exact 3D non-human characters in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), inside the pizza restaurant dining area the angry 3D red crustacean manager in a white shirt and tie shouts and points furiously at the tearful 3D brown woodland squirrel cashier with perky ears and fluffy tail in the green shirt and white apron (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a furious male boss voice: «مَگه نَگُفْتَم دیگه پیتْزایِ مَجّانی نَده؟! هَمین اَلان پِیْش‌بَنْدِت رُو دَرْبیار و اَز این‌جا بُرُو بیرُون!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S7_DIR}\\part3\\keyframes\\KF_03.jpg`,
    prompt:
      '[PZ3_C03] 3D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), the billionaire character in a sharp black tuxedo suit and dark sunglasses strides confidently into the pizza restaurant while the red manager and cashier look on in shock (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a commanding male voice: «ایْشُون هیچ‌جا نِمی‌ره، وَلی تُو چِرا! مَن هَمین اَلان کُلِّ شُعْبه‌هایِ این رِسْتُوران رُو خَریدَم!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S7_DIR}\\part3\\keyframes\\KF_04.jpg`,
    prompt:
      '[PZ3_C04] 3D stylized cartoon animation matching the exact 3D non-human characters in the reference image, static medium close-up keeping both characters in frame the entire time (no camera cuts), the 3D red crustacean restaurant manager in a white shirt and tie gasps in total disbelief with his jaw dropped while the 3D brown woodland squirrel cashier with perky ears and fluffy tail in the green shirt looks amazed behind him (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a shocked stammering male voice: «چی؟! یَعْنی تُو هَمُون پِسَرِ فَقیر بُودی کِه کُلِّ زَنْجیرِه رِسْتُوران رُو یِکْ‌جا خَریده؟!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S7_DIR}\\part3\\keyframes\\KF_05.jpg`,
    prompt:
      '[PZ3_C05] 3D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), inside the restaurant the billionaire character in a black suit and dark sunglasses points the disgraced red manager toward the front exit while the kind cashier in the green shirt smiles proudly (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a commanding male voice: «اَز اِمْرُوز شُما مُدیرِ جَدیدِ این رِسْتُوران هَسْتید خانُمِ مِهْرَبُون! و تُو، فَوْراً اَز مِلْکِ مَن بُرُو بیرُون!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S7_DIR}\\part3\\keyframes\\KF_06.jpg`,
    prompt:
      '[PZ3_C06] 3D stylized cartoon animation matching the reference image style, static medium shot keeping the characters in frame the entire time (no camera cuts), outside the warm glowing pizza parlor window on a rainy night the fired manager in a rain-soaked coat and tie stands sadly on the wet sidewalk holding a plain brown box (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a regretful defeated male voice: «بِه خاطِرِ یِک تِکّه پیتْزا هَمِه چیم رُو اَز دَسْت دادَم! این کارْمایِ طَمَع‌کاریِ خُودَم بُود!» Zero on-screen subtitles.',
  },
];


const S8_DIR = 'C:\\Users\\LifeCycle\\.gemini\\antigravity\\scratch\\series8-big-sponge-prom-king-farsi';
const S9_DIR = 'C:\\Users\\LifeCycle\\.gemini\\antigravity\\scratch\\series9-sleep-challenge-millionaire-farsi';

BATCHES.bs_part1 = [
  {
    clip: 1,
    kf: `${S8_DIR}\\part1\\keyframes\\KF_01.jpg`,
    prompt:
      '[BS1_C01] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), in a high-school hallway lined with blue lockers the 3D tall coral-pink cone-headed teen jock with short black dread twists in a navy varsity jacket holds up a yellow measuring tape and laughs mockingly at the towering 8-foot-2 3D rectangular bright-yellow porous kitchen sponge teen with golden-yellow dread twists in an oversized grey hoodie, black shorts, and backpack (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a mocking arrogant male voice: «قَدِّ دُو مِتْر و نیمی؟! تُو دانِش‌آمُوز نیسْتی، عِیْنِ تیرِ چِراغ‌بَرْقی هَسْتی کِه کُوله‌پُشْتی اَنْداخْته!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S8_DIR}\\part1\\keyframes\\KF_02.jpg`,
    prompt:
      '[BS1_C02] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), outside in the sunny school courtyard by a stone fountain the 3D warm brown woodland squirrel teen girl with perky ears, fluffy tail, and braided hair in a pink cardigan and black skirt holds out a bouquet of pink lilies pleadingly toward the arrogant 3D coral-pink cone-headed teen jock in a navy varsity jacket (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and an eager pleading young female voice: «این گُل‌ها رُو بَرایِ تُو خَریدَم هُومَن! خْواهِش می‌کُنَم فَقَط یِک فُرْصَت بِه مَن بِده!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S8_DIR}\\part1\\keyframes\\KF_03.jpg`,
    prompt:
      '[BS1_C03] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), in the sunny courtyard by the fountain the 3D coral-pink cone-headed teen jock with black dread twists in a navy varsity jacket crosses his arms with an evil scheming smirk while talking to the 3D brown woodland squirrel girl holding pink flowers (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a fast scheming arrogant male voice: «فُرْصَت می‌خْوای؟ اُون اِسْفَنْجِ غُول‌پِیْکَر رُو عاشِقِ خُودِت کُن و شَبِ جَشْن قَلْبِش رُو بِشْکَن!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S8_DIR}\\part1\\keyframes\\KF_04.jpg`,
    prompt:
      '[BS1_C04] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), under sunny palm trees in the school courtyard the 3D warm brown woodland squirrel teen girl with perky ears and fluffy tail in a pink cardigan and black skirt offers the bouquet of pink flowers with a fake sweet smile to the towering 8-foot-2 3D rectangular bright-yellow porous sponge teen with golden-yellow dread twists in a grey hoodie and backpack (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a sweet flirtatious female voice: «سَلام سُهْراب! مَن هَمیشه فِکْر می‌کَرْدَم خِیْلی جَذّابی، می‌شه با مَن بِیای جَشْنِ مَدْرِسه؟» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S8_DIR}\\part1\\keyframes\\KF_05.jpg`,
    prompt:
      '[BS1_C05] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), under the sunny courtyard palm trees the towering 8-foot-2 3D rectangular bright-yellow porous sponge teen with golden-yellow dread twists in a grey hoodie and backpack holds the pink flowers with tears of pure joy beside the 3D brown woodland squirrel girl (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a shy overjoyed young male voice: «با مَن؟! تا حالا هیچ‌کَس بِه مَن پِیْشْنَهاد نَداده بُود! با کَمالِ مِیْل باهات می‌یام!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S8_DIR}\\part1\\keyframes\\KF_06.jpg`,
    prompt:
      '[BS1_C06] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium shot keeping the characters in frame the entire time (no camera cuts), in the courtyard colonnade the towering 3D rectangular bright-yellow porous sponge teen in a grey hoodie holding yellow sunflowers hides behind a stone pillar in shock as he overhears the 3D brown woodland squirrel girl and the 3D coral-pink cone-headed teen jock laughing wickedly together (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a mocking female voice: «دیدی چِقَدْر ساده تُویِ تَلِه اُفْتاد؟ شَبِ جَشْن جُلُویِ کُلِّ مَدْرِسه مَسْخَرَش می‌کُنیم!» Zero on-screen subtitles.',
  },
];

BATCHES.bs_part2 = [
  {
    clip: 1,
    kf: `${S8_DIR}\\part2\\keyframes\\KF_01.jpg`,
    prompt:
      '[BS2_C01] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human sponge character and outfit in the reference image, static medium shot keeping the character in frame the entire time (no camera cuts), the heartbroken towering 3D rectangular bright-yellow porous kitchen sponge teen with golden-yellow dread twists in a grey hoodie and backpack leans over a marble counter beside crushed yellow sunflowers sobbing bitterly (strictly NO human face), speaking in native Persian (Farsi) with exact vowel pronunciation and a heartbroken crying male voice: «چِقَدْر سادِه بُودَم! یِک لَحْظه فِکْر کَرْدَم واقِعاً دُوسْتَم داره، وَلی بَرایِ اُون‌ها فَقَط یِک غُولِ عَجیبَم!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S8_DIR}\\part2\\keyframes\\KF_02.jpg`,
    prompt:
      '[BS2_C02] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), in a cozy living room the loving 3D bright-red crustacean father with a smooth rounded red head, black beard, and red pincer hands in a navy work shirt kneels beside his crying giant 3D rectangular yellow porous sponge teen son sitting on the sofa holding wilted sunflowers (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation: «پِسَرَم نِگاهَم کُن، کی اَشْکِت رُو دَرآوُرْده؟ گُفْتَن هیچ‌کَس عاشِقَم نِمی‌شه چُون غُول‌پِیْکَرَم!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S8_DIR}\\part2\\keyframes\\KF_03.jpg`,
    prompt:
      '[BS2_C03] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium close-up two-shot keeping both characters in frame the entire time (no camera cuts), in the cozy living room the 3D bright-red crustacean father with a smooth rounded red head, black beard, and red pincer hands in a navy work shirt places his hand firmly on the shoulder of his teary giant 3D rectangular yellow porous sponge son in a grey hoodie (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a warm powerful fatherly male voice: «تُو زیادی بُزُرْگ نیسْتی پِسَرَم! آدَم‌هایِ حَقیر می‌خْوان تُو رُو کُوچیک کُنَن تا خُودِشُون بُزُرْگ بِه نَظَر بِیان!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S8_DIR}\\part2\\keyframes\\KF_04.jpg`,
    prompt:
      '[BS2_C04] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium shot keeping all three characters in frame the entire time (no camera cuts), inside a glittering luxury high-rise fashion boutique at night the 3D red crustacean father in a navy work shirt stands beside his towering 8-foot-2 3D rectangular yellow porous sponge son in a grey hoodie introducing him to the 3D turquoise-green squid master fashion designer in round gold glasses and a black double-breasted suit (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and an earnest fatherly male voice: «بِه پِسَرَم گُفْتَن قَدِّش خِیْلی بُلَنْده و دیگه حَتّی نِمی‌تُونه تُویِ آیْنه بِه خُودِش نِگاه کُنه!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S8_DIR}\\part2\\keyframes\\KF_05.jpg`,
    prompt:
      '[BS2_C05] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium shot keeping the characters in frame the entire time (no camera cuts), inside the luxury fashion boutique the 3D turquoise-green squid master fashion designer with purple-silver dreads, gold glasses, and a black double-breasted suit looks up in artistic admiration at the towering 8-foot-2 3D rectangular yellow porous sponge teen in a grey hoodie while the 3D red crustacean father watches (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and an inspired confident male designer voice: «خِیْلی بُلَنْد؟! پِسَر، با این قَدّ و هِیْکَل، تُو بَرایِ قایِم شُدَن دُنْیا نَیُومَدی، تُو سُلْطانِ اِسْتایْلی!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S8_DIR}\\part2\\keyframes\\KF_06.jpg`,
    prompt:
      '[BS2_C06] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium shot keeping the characters in frame the entire time (no camera cuts), inside the glittering luxury boutique the towering 3D rectangular yellow porous sponge teen in a grey hoodie looks down hopefully at the 3D turquoise-green squid designer in a black suit and the 3D red crustacean father (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation: «مَن؟! یَعْنی با این قَدِّ بُلَنْد می‌تُونَم شیک‌بِپُوشَم؟ اَلان لِباسی بَرات می‌دُوزَم کِه هَمه مات و مَبْهُوت بِمُونَن!» Zero on-screen subtitles.',
  },
];

BATCHES.bs_part3 = [
  {
    clip: 1,
    kf: `${S8_DIR}\\part3\\keyframes\\KF_01.jpg`,
    prompt:
      '[BS3_C01] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium shot keeping the characters in frame the entire time (no camera cuts), inside the luxury boutique the 3D turquoise-green squid fashion designer in gold glasses and a black suit unveils a royal-blue tuxedo suit embroidered with shimmering gold filigree on a stand beside the amazed towering 3D rectangular yellow porous sponge teen in a grey hoodie (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a proud stylish male voice: «این هُودی اُبُهَّتِت رُو پِنْهان کَرْده! این کُت‌وشَلْوارِ سَلْطَنَتی رُو بُپُوش تا تِمْسْخُرِشُون تَبْدیل بِه حَسادَت بِشه!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S8_DIR}\\part3\\keyframes\\KF_02.jpg`,
    prompt:
      '[BS3_C02] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), inside the luxury boutique the towering 3D rectangular yellow porous sponge teen in a grey hoodie touches the gold-embroidered sleeve of the royal-blue tuxedo on the stand while the 3D turquoise-green squid designer in a black suit smiles reassuringly (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation: «اَگه تُویِ جَشْن بِه مَن بِخَنْدَن چی؟ با این اِسْتایْل کِه وارِد بِشی، نَفَسِ هَمَشُون حَبْس می‌شه!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S8_DIR}\\part3\\keyframes\\KF_03.jpg`,
    prompt:
      '[BS3_C03] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium shot keeping the characters in frame the entire time (no camera cuts), inside the luxury boutique the 3D bright-red crustacean father with a smooth rounded red head, black beard, and red pincer hands in a navy work shirt stands proudly beside his towering 3D rectangular yellow porous sponge son and the royal-blue gold suit (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a proud inspiring fatherly male voice: «تَنْها مَوْجُودِ عَجیب کَسیه کِه خْواسْت خُجالَتِت بِده پِسَرَم! با تَرْس اُومَدی، وَلی مِثْلِ پادْشاه بُرُو بیرُون!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S8_DIR}\\part3\\keyframes\\KF_04.jpg`,
    prompt:
      '[BS3_C04] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium shot keeping the characters in frame the entire time (no camera cuts), inside the grand golden chandelier prom ballroom the 3D coral-pink cone-headed teen jock in a dark navy tuxedo turns around in shock as the tall glowing double entrance doors behind him reveal the towering 8-foot-2 silhouette of the giant sponge king (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a shocked gasping male voice: «صَبْر کُن، اُون دیگه کیه دَمِ دَر؟! حَتّی دَرهایِ بُزُرْگِ تالار هَم کِنارِ قَدِّش کُوچیکَن!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S8_DIR}\\part3\\keyframes\\KF_05.jpg`,
    prompt:
      '[BS3_C05] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium shot keeping the characters in frame the entire time (no camera cuts), inside the golden chandelier prom ballroom the towering 8-foot-2 3D rectangular bright-yellow porous sponge teen with golden-yellow dread twists strides forward confidently wearing his royal-blue and gold-filigree embroidered luxury tuxedo suit and bowtie while the 3D coral-pink cone-headed teen jock in a navy tuxedo drops his jaw in disbelief (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a stunned male voice: «اِمْکان نَداره! اُون قَدّ و بالا... یَعْنی اِسْفَنْجِ غُول‌پِیْکَره؟! چِقَدْر خُوش‌تیپ و بااُبُهَّت شُده!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S8_DIR}\\part3\\keyframes\\KF_06.jpg`,
    prompt:
      '[BS3_C06] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), in the center of the golden chandelier prom ballroom the handsome towering 8-foot-2 3D rectangular bright-yellow porous sponge teen in his royal-blue and gold-embroidered luxury tuxedo suit stands like a king while the 3D warm brown woodland squirrel girl in a pink satin prom gown gazes up at him in regretful awe (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and an amazed regretful female voice: «واو، خُودِشه! چِرا هیچ‌کَس تُویِ سالُن نِمی‌تُونه یِک لَحْظه چِشْم اَزَش بَرْداره؟!» Zero on-screen subtitles.',
  },
];

BATCHES.sc_part1 = [
  {
    clip: 1,
    kf: `${S9_DIR}\\part1\\keyframes\\KF_01.jpg`,
    prompt:
      '[SC1_C01] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human sponge characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), inside a bedroom filled with ringing alarm clocks the 3D rectangular dark charcoal-black porous sponge mother in a pink headscarf, pearl necklace, purple dress, and floral apron holds up a long  receipt and yells at the 3D rectangular dark charcoal-black porous sponge boy with black dread twists, pink forehead sleep mask, and yellow smiley-face pajama shirt snoring in bed (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and an angry frustrated mother voice: «شِشْصَد و هَفْتاد دُلار پُولِ ساعَتِ زَنْگ‌دار دادَم، بَعْد تُو هَنُوز خْوابیدی؟!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S9_DIR}\\part1\\keyframes\\KF_02.jpg`,
    prompt:
      '[SC1_C02] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human sponge characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), inside the bedroom surrounded by buzzing clocks the 3D rectangular dark charcoal-black porous sponge mother in a pink headscarf, purple dress, and floral apron rings a giant hanging brass bell right over the bed while the 3D rectangular dark charcoal-black porous sponge boy in yellow smiley pajamas and a pink forehead sleep mask keeps snoring peacefully (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and an exasperated mother voice: «جِدّی می‌گی؟! حَتّی با صِدایِ این زَنْگِ غُول‌پِیْکَر هَم بیدار نِمی‌شی پِسَر؟!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S9_DIR}\\part1\\keyframes\\KF_03.jpg`,
    prompt:
      '[SC1_C03] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium shot keeping the characters in frame the entire time (no camera cuts), on a noisy city sidewalk the 3D rectangular dark charcoal-black porous sponge boy in yellow smiley pajamas and pink forehead sleep mask sleeps soundly on a metal bus-stop bench beside a jackhammer while the 3D tall coral-pink cone-headed bystander in a blue denim jacket holding a coffee cup stares in disbelief (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a shocked male voice: «صَبْر کُن بِبینَم! چِطُوری کِنارِ این دَسْتْگاهِ حَفّاریِ پُرْسَرُوصِدا هَنُوز خْوابیده؟!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S9_DIR}\\part1\\keyframes\\KF_04.jpg`,
    prompt:
      '[SC1_C04] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human sponge character and outfit in the reference image, static medium shot keeping the character in frame the entire time (no camera cuts), sitting on the city street bench the 3D rectangular dark charcoal-black porous sponge boy with black dread twists, pink sleep mask on his forehead, and yellow smiley-face pajama shirt looks up with wide excited cartoon eyes at a giant glowing ,000,000 billboard behind him (strictly NO human face), speaking in native Persian (Farsi) with exact vowel pronunciation and an excited energetic young male voice: «چی؟! یِک میلْیُون دُلار جایْزِه فَقَط بَرایِ خْوابیدَن؟! این مِیْدُونِ مَنه!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S9_DIR}\\part1\\keyframes\\KF_05.jpg`,
    prompt:
      '[SC1_C05] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), at an outdoor registration kiosk the 3D rectangular dark charcoal-black porous sponge boy in yellow smiley pajamas and pink forehead sleep mask speaks eagerly to the 3D turquoise-green squid official in round glasses and a navy suit holding a registration form (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation: «آقا مَن رُو بَرایِ مُسابِقِه خْواب ثَبْت‌نام کُنید! بِبَخْشید پِسَرَم، بَرایِ ثَبْت‌نام حَتْماً اِمْضایِ مادَرِت لازِمه!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S9_DIR}\\part1\\keyframes\\KF_06.jpg`,
    prompt:
      '[SC1_C06] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human sponge characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), inside the living room beside the  alarm clock box the 3D rectangular dark charcoal-black porous sponge boy in yellow smiley pajamas and pink forehead sleep mask holds out the ,000,000 contest paper toward his shocked 3D dark charcoal-black porous sponge mother in a pink headscarf and floral apron on the sofa (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and an excited pleading young male voice: «مامان جُون، این بَرْگه رُو اِمْضا می‌کُنی؟ مُسابِقِه خْوابه و یِک میلْیُون دُلار جایْزه داره!» Zero on-screen subtitles.',
  },
];

BATCHES.sc_part2 = [
  {
    clip: 1,
    kf: `${S9_DIR}\\part2\\keyframes\\KF_01.jpg`,
    prompt:
      '[SC2_C01] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human sponge characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), inside the living room the 3D rectangular dark charcoal-black porous sponge mother in a pink headscarf, purple dress, and floral apron waves her hand in stern refusal while the 3D dark charcoal-black porous sponge boy in yellow smiley pajamas and pink forehead sleep mask holds the form (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a stern angry mother voice: «چی رُو اِمْضا کُنَم؟! نَخِیْر، اَصْلاً اِجازه نِمی‌دَم وارِدِ این مُسابِقِه مَسْخَره بِشی!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S9_DIR}\\part2\\keyframes\\KF_02.jpg`,
    prompt:
      '[SC2_C02] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human sponge characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), inside the living room the 3D rectangular dark charcoal-black porous sponge boy in yellow smiley pajamas and pink forehead sleep mask points at the $670 alarm clock bill on the box while his 3D dark charcoal-black porous sponge mother in a pink headscarf and floral apron sighs and reaches for the pen to sign (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation: «مامان، پُولِ این ساعَت‌ها رُو با جایْزِه یِک میلْیُونی می‌دیم! اَه، بِده بِبینَم کُجا رُو اِمْضا کُنَم!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S9_DIR}\\part2\\keyframes\\KF_03.jpg`,
    prompt:
      '[SC2_C03] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium shot keeping the characters in frame the entire time (no camera cuts), on a grand neon stadium stage in front of a glowing ,000,000 screen and four beds the 3D bright-green single-eyed alien host with two antennae in an emerald-green tuxedo suit speaks excitedly into his microphone while the 3D dark charcoal porous sponge boy in yellow smiley pajamas lies on the leftmost bed (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a booming energetic male TV host voice: «خُوش اُومَدید بِه سَخْت‌ترین مُسابِقِه بیدار کَرْدَنِ جَهان با جایْزِه یِک میلْیُون دُلاری!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S9_DIR}\\part2\\keyframes\\KF_04.jpg`,
    prompt:
      '[SC2_C04] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human sponge character and outfit in the reference image, static medium shot keeping the character in frame the entire time (no camera cuts), sitting in the glowing stadium audience seats the 3D rectangular dark charcoal-black porous sponge mother in a pink headscarf, pearl necklace, purple dress, and floral apron clasps her hands together anxiously watching the stage (strictly NO human face), speaking in native Persian (Farsi) with exact vowel pronunciation and a worried loving mother voice: «وای پِسَرِ قَشَنْگَم، خُودِت رُو تُویِ چِه دَرْدِسَری اَنْداخْتی؟! خُدا بِه خِیْر کُنه!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S9_DIR}\\part2\\keyframes\\KF_05.jpg`,
    prompt:
      '[SC2_C05] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static wide vertical shot keeping the stage in frame the entire time (no camera cuts), on the stadium stage towering speaker walls and 100 brass alarm clocks ring furiously behind four beds where the 3D dark charcoal porous sponge boy in yellow smiley pajamas and three non-human contenders lie while the 3D bright-green single-eyed host in an emerald tuxedo shouts into his microphone (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a loud dramatic male host voice: «مَرْحَلِه اَوَّل، صَد تا ساعَتِ زَنْگ‌دارِ غُول‌پِیْکَر با حَداَکْثَرِ صِدا! شُرُوع کُنید!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S9_DIR}\\part2\\keyframes\\KF_06.jpg`,
    prompt:
      '[SC2_C06] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static wide vertical shot keeping the stage in frame the entire time (no camera cuts), on the stadium stage the two contenders on the right beds jump up covering their ears in panic while on the left two beds the 3D dark charcoal porous sponge boy in yellow smiley pajamas and the muscular green fish contender stay fast asleep as the 3D bright-green single-eyed host in an emerald tuxedo announces into his microphone (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and an excited male host voice: «دُو نَفَر اَز شِرْکَت‌کُنَنْده‌ها بیدار شُدَن و حَذْف شُدَن! فَقَط دُو نَفَر هَنُوز خْوابَن!» Zero on-screen subtitles.',
  },
];

BATCHES.sc_part3 = [
  {
    clip: 1,
    kf: `${S9_DIR}\\part3\\keyframes\\KF_01.jpg`,
    prompt:
      '[SC3_C01] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static vertical shot keeping the stage in frame the entire time (no camera cuts), on the stadium stage a colossal black-and-gold steel ultrasonic horn suspended on heavy chains lowers directly above the beds of the sleeping 3D dark charcoal porous sponge boy in yellow smiley pajamas and the muscular green fish contender while the 3D bright-green single-eyed host in an emerald tuxedo shouts into his microphone (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a dramatic booming male host voice: «مَرْحَلِه دُوُّم، بُوقِ فَراصُوتیِ غُول‌پِیْکَر! هیچ مَوْجُودی نِمی‌تُونه با این صِدا بَخْوابه!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S9_DIR}\\part3\\keyframes\\KF_02.jpg`,
    prompt:
      '[SC3_C02] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static vertical shot keeping the stage in frame the entire time (no camera cuts), on the stadium stage the colossal suspended steel ultrasonic horn blasts a glowing white sonic shockwave down toward the beds while the 3D dark charcoal porous sponge boy in yellow smiley pajamas continues snoring peacefully and the 3D bright-green single-eyed host in an emerald tuxedo watches (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and an intense male host voice: «حَداَکْثَرِ قُدْرَتِ صَوْتی! بِبینیم کُدُوم یِکی اَز این دُو تا دَوام می‌یارَن!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S9_DIR}\\part3\\keyframes\\KF_03.jpg`,
    prompt:
      '[SC3_C03] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static vertical shot keeping the stage in frame the entire time (no camera cuts), on the stadium stage the muscular green fish contender leaps out of his bed covering his ears in agony while on the left bed the 3D dark charcoal porous sponge boy in yellow smiley pajamas and pink forehead sleep mask stays fast asleep and the 3D bright-green single-eyed host in an emerald tuxedo cheers into his microphone (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and an excited male host voice: «گُوشْ‌هام سُوت کِشید! شِرْکَت‌کُنَنْدِه عَضَلانی هَم تَسْلیم شُد و حَذْف شُد!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S9_DIR}\\part3\\keyframes\\KF_04.jpg`,
    prompt:
      '[SC3_C04] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human sponge character and outfit in the reference image, static medium shot keeping the character in frame the entire time (no camera cuts), in the stadium audience stands under falling golden confetti the 3D rectangular dark charcoal-black porous sponge mother in a pink headscarf, pearl necklace, purple dress, and floral apron stands up clapping and cheering joyfully (strictly NO human face), speaking in native Persian (Farsi) with exact vowel pronunciation and a proud cheering mother voice: «این پِسَرِ مَنه! هَمین‌طُوری بَخْواب عَزیزِ دِلَم و اُون یِک میلْیُون دُلار رُو بَرامُون بِیار خُونه!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S9_DIR}\\part3\\keyframes\\KF_05.jpg`,
    prompt:
      '[SC3_C05] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium shot keeping the characters in frame the entire time (no camera cuts), on the spotlight stadium stage under falling gold confetti the 3D bright-green single-eyed host in an emerald tuxedo proudly holds a giant ,000,000 winner check beside the bed where the 3D dark charcoal porous sponge boy in yellow smiley pajamas and pink forehead sleep mask is still fast asleep (strictly NO human faces), speaking in native Persian (Farsi) with exact vowel pronunciation and a triumphant male host voice: «و بَرَنْدِه جایْزِه بُزُرْگِ یِک میلْیُون دُلاری کَسی نیسْت جُز... سُلْطانِ خْوابِ جَهان!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S9_DIR}\\part3\\keyframes\\KF_06.jpg`,
    prompt:
      '[SC3_C06] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human sponge character and outfit in the reference image, static close-up shot keeping the character in frame the entire time (no camera cuts), the 3D rectangular dark charcoal-black porous sponge boy with black dread twists, pink sleep mask on his forehead, and yellow smiley-face pajama shirt snores blissfully on his white pillow with a cartoon sleep bubble while golden confetti rains down around him (strictly NO human face), speaking in his sleep in native Persian (Farsi) with exact vowel pronunciation and a dreamy sleepy young male voice: «آخیش... چِه خْوابِ شِیرین و یِک میلْیُون دُلاری‌ای! بَچّه‌ها شَبْ‌تُون بِخِیْر!» Zero on-screen subtitles.',
  },
];

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
    const found = nodes.find((n) => n.visible !== false && predicate(n));
    if (found) return found;
  }
  return null;
}

/** Check observable settings; hidden values require a recent, target-bound operator review. */
export function verifyLiveSettings(snapshot, expected, attestation, target = {}, now = Date.now()) {
  const fields = ['model', 'duration_sec', 'aspect', 'outputs', 'video_type'];
  if (!expected || fields.some(k => expected[k] === undefined || expected[k] === '')) {
    throw new Error('SETTINGS_UNVERIFIABLE: manifest generation_settings needs model, duration_sec, aspect, outputs and video_type');
  }
  if (expected.resolution) fields.push('resolution');
  const normalized = (key, value) => ['duration_sec', 'outputs'].includes(key) ? Number(value) :
    String(value ?? '').replace(/[–—]/g, '-').replace(/\s+/g, ' ').trim().toLowerCase();
  if (!Number.isFinite(Number(expected.duration_sec)) || Number(expected.duration_sec) <= 0 ||
      !Number.isInteger(Number(expected.outputs)) || Number(expected.outputs) <= 0 ||
      !['frames', 'ingredients'].includes(normalized('video_type', expected.video_type))) {
    throw new Error('SETTINGS_UNVERIFIABLE: invalid duration, output count or video_type in manifest');
  }
  const nodes = (snapshot?.frames || []).flatMap(f => flattenNodes(f.tree)).filter(n => n.visible !== false);
  const label = n => String(n.name || n.text || '').trim();
  const observed = {};
  const set = (key, value) => {
    if (observed[key] !== undefined && normalized(key, observed[key]) !== normalized(key, value)) {
      throw new Error(`SETTINGS_UNVERIFIABLE: ambiguous live ${key}; close extra settings panels and inspect Flow`);
    }
    observed[key] = value;
  };
  // This compact composer summary reflects the active output configuration, unlike menu options.
  for (const n of nodes) {
    const match = label(n).match(/^Video\s*[·•]\s*(\d+p)\s*[·•]\s*(\d+(?:\.\d+)?)s\s*x(\d+)$/i);
    if (match) { set('resolution', match[1]); set('duration_sec', Number(match[2])); set('outputs', Number(match[3])); }
    const checked = n.checked === true || n.selected === true || n.attributes?.['aria-checked'] === 'true';
    if (checked && ['radio', 'option', 'menuitemradio'].includes(n.role)) {
      const name = label(n);
      if (/^(Frames|Ingredients)$/i.test(name)) set('video_type', name);
      if (/^\d+:\d+$/.test(name)) set('aspect', name);
      if (/^(Veo|Omni)\b/i.test(name)) set('model', name);
    }
  }
  if (observed.duration_sec === undefined) throw new Error('SETTINGS_UNVERIFIABLE: active Video duration/output summary missing; inspect Flow settings before submission');
  if (nodes.some(n => n.role === 'button' && ['Start', 'Swap first and last frames'].includes(label(n))) &&
      nodes.some(n => n.role === 'button' && label(n) === 'End')) {
    set('video_type', 'Frames');
  }
  const modelControl = nodes.find(n => n.role === 'button' && label(n) === 'Select model family');
  for (const n of flattenNodes(modelControl)) if (/^(Veo|Omni)\b/i.test(label(n))) set('model', label(n));
  const settingsControl = nodes.find(n => n.role === 'button' && label(n) === 'Settings trigger');
  const aspects = new Set(flattenNodes(settingsControl).filter(n => n.visible !== false).map(label).filter(v => /^crop_\d+_\d+$/.test(v)));
  if (observed.aspect === undefined && aspects.size === 1) set('aspect', [...aspects][0].slice(5).replace('_', ':'));
  for (const key of fields) {
    if (observed[key] !== undefined && normalized(key, observed[key]) !== normalized(key, expected[key])) {
      throw new Error(`SETTINGS_MISMATCH: ${key} mismatch (live ${observed[key]}, reviewed ${expected[key]}); correct Flow settings before submission`);
    }
  }
  const missing = fields.filter(key => observed[key] === undefined);
  if (missing.length) {
    const age = now - Date.parse(attestation?.reviewed_at);
    const valid = attestation?.status === 'pass' && ['reviewer', 'evidence'].every(k => typeof attestation[k] === 'string' && attestation[k].trim()) &&
      /(?:Z|[+-]\d\d:\d\d)$/.test(attestation?.reviewed_at || '') && age >= 0 && age <= 15 * 60 * 1000 &&
      target.profileId && target.tabId && target.manifestSha256 &&
      ['profileId', 'tabId', 'manifestSha256'].every(k => attestation[k] === target[k]) &&
      fields.every(k => normalized(k, attestation.settings?.[k]) === normalized(k, expected[k]));
    if (!valid) throw new Error(`SETTINGS_UNVERIFIABLE: ${missing.join(', ')} unverifiable; inspect settings and record reviews.flow_settings with status pass, actual settings, reviewer, evidence, reviewed_at (within 15 minutes), profileId, tabId and manifestSha256`);
  }
  return {observed, manually_attested: missing};
}

function composerImageButtons(snapshot) {
  return (snapshot?.frames || []).flatMap(frame => {
    const nodes = flattenNodes(frame.tree).filter(n => n.visible !== false);
    const end = nodes.findIndex(n => n.role === 'textbox' &&
      ['What do you want to create?', 'چه چیزی می‌خواهید بسازید؟'].includes(n.name));
    if (end < 0) return [];
    let lastFeed = -1;
    for (let i = 0; i < end; i++) {
      const n = nodes[i], text = String(n.text || '').trim(), name = String(n.name || '').trim();
      if (/^Created |^\d+%$/.test(text) ||
          (n.role === 'button' && /^(Trash batch|Recycle|Reuse prompt|Delete|حذف|image\.png)$/i.test(name))) lastFeed = i;
    }
    return nodes.slice(lastFeed + 1, end).filter(n => n.role === 'button' && /^(Ingredient|Image ingredient|ماده اولیه)$/i.test(String(n.name || '').trim()));
  });
}

function assertFrameUploadVerifiable(snapshot) {
  if (composerImageButtons(snapshot).some(n => /^Image ingredient$/i.test(n.name))) {
    // Flow exposes the same button while its preview is a blank placeholder.
    // Counting a frame is not evidence that its image finished loading.
    throw new Error('UPLOAD_UNVERIFIABLE: Frames image upload readiness unverifiable; inspect the loaded frame preview before manual generation. Automatic submission stopped');
  }
}

/** Verify the full composer, never a matching prefix in a previous job card. */
export function verifyPromptText(snapshot, expected) {
  const box = findNode(snapshot, isPromptTextbox);
  if (!box) throw new Error('PROMPT_UNVERIFIABLE: prompt textbox is missing');
  const normalize = value => String(value).normalize('NFC').replace(/\s+/gu, ' ').trim();
  const childText = node => {
    if (!node || node.role === 'button' || node.tag === 'button' || node.tag === 'mat-icon' || node.role === 'img') return '';
    if (typeof node.text === 'string' && node.text.trim()) return node.text;
    return (node.children || []).map(childText).filter(Boolean).join(' ');
  };
  const actual = normalize(typeof box.value === 'string' && box.value.trim() ? box.value : childText(box));
  const wanted = normalize(expected);
  if (!actual) return false; // Rendering may lag trusted typing; observe again without appending.
  if (actual === wanted || (actual.length >= 150 && wanted.startsWith(actual))) return true;
  if (wanted.startsWith(actual)) {
    throw new Error('PROMPT_UNVERIFIABLE: snapshot exposes only a prompt prefix; inspect the full composer before manual submission');
  }
  throw new Error('PROMPT_MISMATCH: composer differs from reviewed prompt; clear contamination before submission');
}

/**
 * Count image "ingredient" chips currently attached to the Flow composer.
 * A chip is an attached image tile: its remove control is a `cancel` mat-icon
 * (or a button named Remove/Delete image / حذف تصویر), or an <img>/image node
 * inside the composer whose name mentions ingredient/uploaded image.
 * Returns max(#thumbnails, #remove controls) so one chip is counted once.
 */
export function countIngredientChips(snapshot) {
  // Each attached image chip exposes a thumbnail, a remove ("cancel") control,
  // or (in the Oct 2026 Flow UI) a role="button" name="Ingredient"/"Image ingredient" inside the composer
  // (located after all media-feed tile footers like "Created ..." and before the prompt textbox).
  if (!Array.isArray(snapshot?.frames) || snapshot.frames.length === 0 ||
      snapshot.frames.some((f) => !f.tree || typeof f.tree !== 'object')) {
    throw new Error('Cannot count ingredients: missing or malformed page snapshot');
  }
  let imgs = 0;
  let removers = 0;
  const composerIngredientBtns = composerImageButtons(snapshot).length;
  for (const frame of snapshot?.frames || []) {
    const nodes = flattenNodes(frame.tree);
    for (let i = 0; i < nodes.length; i++) {
      const n = nodes[i];
      const name = String(n.name || '');
      const text = String(n.text || '').trim();
      if ((n.role === 'img' || n.tag === 'img') && /ingredient|uploaded image|تصویر بارگذاری/i.test(name)) imgs++;
      else if (
        (n.tag === 'mat-icon' && text === 'cancel') ||
        (n.role === 'button' && /^(remove|delete) (image|ingredient)|حذف (تصویر|عکس)/i.test(name))
      )
        removers++;
    }
  }
  return Math.max(imgs, removers, composerIngredientBtns);
}

function sha256File(path) {
  try {
    return createHash('sha256').update(readFileSync(path)).digest('hex');
  } catch {
    return null;
  }
}

export function trace(event, data = {}, destination = TRACE_PATH) {
  const row = { ts: new Date().toISOString(), run: RUN_ID, event, ...data };
  // An untraceable submission is not safe: fail before spending generation credits.
  appendFileSync(destination, JSON.stringify(row) + '\n', 'utf8');
}

const isPromptTextbox = (n) =>
  n.role === 'textbox' &&
  n.visible !== false &&
  (!n.rect || n.rect.x < 1250) &&
  (n.name === 'What do you want to create?' || n.name === 'چه چیزی می‌خواهید بسازید؟');

const isClearButton = (n) =>
  n.role === 'button' &&
  n.visible !== false &&
  (!n.rect || n.rect.x < 1250) &&
  (n.name === 'Clear prompt' || n.name === 'پاک کردن پیام‌واره');

const isStartButton = (n) =>
  n.role === 'button' &&
  n.visible !== false &&
  (!n.rect || n.rect.x < 1250) &&
  (n.name === 'Start generation' || n.name === 'شروع تولید');

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

async function submitSingleClipImpl(mcp, item, ctx = {}) {
  const record = ctx.trace || trace;
  const pause = ctx.sleep || sleep;
  const copyImage = ctx.copyImage || copyImageToClipboard;
  const base = { part: ctx.part, clip: item.clip, kf: item.kf || null };
  // A clip with a keyframe is NEVER allowed to degrade to 0-ingredient Text-to-Video.
  if (item.kf && item.noImage) {
    record('reject', { ...base, reason: 'item has kf AND noImage; refusing silent Text-to-Video' });
    throw new Error(`Clip ${item.clip}: kf is set but noImage=true — refusing Text-to-Video fallback`);
  }
  const skipImage = !item.kf;
  if (skipImage && !item.allowTextOnly) {
    record('reject', { ...base, reason: 'no kf and allowTextOnly not set' });
    throw new Error(`Clip ${item.clip}: no keyframe; set allowTextOnly:true to submit Text-to-Video on purpose`);
  }
  if (!skipImage) {
    if (!existsSync(item.kf)) {
      record('reject', { ...base, reason: 'keyframe file missing' });
      throw new Error(`Clip ${item.clip}: keyframe not found: ${item.kf}`);
    }
    base.kf_sha256 = sha256File(item.kf); // read-only fingerprint; keyframe is never modified
  }
  checkSpeechBudget(item.prompt, item.duration || 8);
  if (typeof ctx.verifyReview !== 'function') throw new Error('REVIEW_STALE: per-clip reviewed-manifest verification required before submission');
  ctx.verifyReview();
  const assertKeyframeUnchanged = () => {
    if (!skipImage && sha256File(item.kf) !== base.kf_sha256) throw new Error(`REVIEW_STALE: clip ${item.clip} keyframe changed during upload; review again`);
  };
  const verifySettings = snapshot => {
    const result = verifyLiveSettings(snapshot, ctx.generationSettings, ctx.settingsAttestation, {
      profileId: PROFILE_ID, tabId: TAB_ID, manifestSha256: ctx.manifestSha256,
    });
    if (Number(item.duration || 8) !== Number(ctx.generationSettings.duration_sec)) {
      throw new Error('SETTINGS_MISMATCH: clip duration differs from reviewed generation_settings.duration_sec');
    }
    record('settings_verified', { ...base, ...result });
  };
  record('start', { ...base, mode: skipImage ? 'text_to_video_explicit' : 'image_to_video', prompt_chars: item.prompt.length });
  console.log(`\n=== Submitting Clip ${item.clip}: ${skipImage ? '(TEXT-ONLY, explicit)' : item.kf} ===`);
  if (!skipImage) {
    copyImage(item.kf);
    assertKeyframeUnchanged();
    record('clipboard_image', base);
    console.log(`  [1/5] Copied image to clipboard: ${item.kf}`);
  }

  // Ensure the composer is in Video mode (not Agent mode) and 100% empty (no prompt, NO leftover ingredient chips)
  let snap = null;
  let chipsBefore = -1;
  for (let clearTry = 1; clearTry <= 6; clearTry++) {
    snap = await mcp.callTool('browser_observe_page', {
      profileId: PROFILE_ID,
      tabId: TAB_ID,
    });
    const settingsTrigger = findNode(snap, (n) => n.role === 'button' && n.name === 'Settings trigger');
    const agentInstr = findNode(snap, (n) => n.role === 'button' && n.name === 'Agent instructions');
    if (!settingsTrigger || agentInstr) {
      const agentToggle = findNode(snap, (n) => n.role === 'button' && n.name === 'Agent');
      if (agentToggle) {
        console.log(`  [!] Composer is in Agent mode — clicking Agent toggle (${agentToggle.ref}) to restore Video mode...`);
        await mcp.callTool('browser_click', {
          profileId: PROFILE_ID,
          tabId: TAB_ID,
          ref: agentToggle.ref,
        });
        await pause(1000);
        snap = await mcp.callTool('browser_observe_page', {
          profileId: PROFILE_ID,
          tabId: TAB_ID,
        });
      }
    }
    verifySettings(snap);
    chipsBefore = countIngredientChips(snap);
    const leftoverClear = findNode(snap, isClearButton);
    if (!leftoverClear && chipsBefore === 0) break;
    const target =
      leftoverClear ||
      findNode(snap, (n) => n.ref && n.tag === 'mat-icon' && String(n.text || '').trim() === 'cancel');
    if (!target) break;
    console.log(`  [!] Clearing leftover prompt/chips (chips=${chipsBefore}, try ${clearTry}, ${target.ref})...`);
    record('clear_leftover', { ...base, try: clearTry, chips: chipsBefore });
    await mcp.callTool('browser_click', {
      profileId: PROFILE_ID,
      tabId: TAB_ID,
      ref: target.ref,
    });
    await pause(1200);
  }
  record('preflight_chips', { ...base, chips: chipsBefore });
  if (chipsBefore !== 0) {
    throw new Error(
      `Clip ${item.clip}: composer still has ${chipsBefore} ingredient chip(s) before paste (MULTI_INGREDIENT_CONTAMINATION guard)`
    );
  }

  let uploadedSnap = null;
  if (skipImage) {
    uploadedSnap = await mcp.callTool('browser_observe_page', {
      profileId: PROFILE_ID,
      tabId: TAB_ID,
    });
  } else {
    // Try up to 3 paste attempts in case a background grid render stole focus
    for (let pasteTry = 1; pasteTry <= 3 && !uploadedSnap; pasteTry++) {
      snap = await mcp.callTool('browser_observe_page', {
        profileId: PROFILE_ID,
        tabId: TAB_ID,
      });
      const promptBox = findNode(snap, isPromptTextbox);
      if (!promptBox) {
        throw new Error('Could not find prompt textbox');
      }

      await mcp.callTool('browser_click', {
        profileId: PROFILE_ID,
        tabId: TAB_ID,
        ref: promptBox.ref,
      });
      await pause(600);

      const beforePaste = await mcp.callTool('browser_observe_page', {
        profileId: PROFILE_ID, tabId: TAB_ID,
      });
      const beforePasteChips = countIngredientChips(beforePaste);
      record('pre_paste_chips', { ...base, try: pasteTry, chips: beforePasteChips });
      if (beforePasteChips !== 0) {
        throw new Error(`Clip ${item.clip}: need 0 chips immediately before every paste, found ${beforePasteChips}`);
      }

      await mcp.callTool('browser_press_key', {
        profileId: PROFILE_ID,
        tabId: TAB_ID,
        key: 'v',
        modifiers: ['ctrl'],
      });
      console.log(
        `  [2/5] Pressed Ctrl+V (try ${pasteTry}) on prompt textbox (${promptBox.ref}), waiting for upload...`
      );

      const maxUploadAttempts = ctx.sleep ? 10 : 24;
      for (let attempt = 1; attempt <= maxUploadAttempts; attempt++) {
        await pause(1500);
        const s = await mcp.callTool('browser_observe_page', {
          profileId: PROFILE_ID,
          tabId: TAB_ID,
        });
        const clearBtn = findNode(s, isClearButton);
        const cancelIcon = findNode(s, (n) => n.tag === 'mat-icon' && n.text === 'cancel');
        const chips = countIngredientChips(s);
        assertFrameUploadVerifiable(s);
        if ((clearBtn || cancelIcon) && chips >= 1) {
          let curS = s;
          let curChips = chips;
          while (curChips > 1) {
            const cIcon = findNode(curS, (n) => n.ref && n.tag === 'mat-icon' && String(n.text || '').trim() === 'cancel');
            if (!cIcon) break;
            console.log(`  [dedup] Removing duplicate chip after paste (${curChips} -> ${curChips - 1})...`);
            await mcp.callTool('browser_click', { profileId: PROFILE_ID, tabId: TAB_ID, ref: cIcon.ref });
            await pause(1200);
            curS = await mcp.callTool('browser_observe_page', { profileId: PROFILE_ID, tabId: TAB_ID });
            curChips = countIngredientChips(curS);
          }
          record('paste_chips', { ...base, try: pasteTry, attempt, chips: curChips });
          if (curChips !== 1) {
            throw new Error(`Clip ${item.clip}: expected exactly 1 ingredient chip after paste, found ${curChips}`);
          }
          uploadedSnap = curS;
          console.log(`  [3/5] Image upload confirmed on attempt ${attempt} (try ${pasteTry})!`);
          break;
        }
      }
    }
    if (!uploadedSnap) {
      record('fail', { ...base, reason: 'keyframe upload not confirmed (no fallback to Text-to-Video)' });
      throw new Error(`Timed out waiting for keyframe image to upload for Clip ${item.clip}`);
    }
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
    const updatedPromptBox = findNode(snapBeforeType, isPromptTextbox);
    if (!updatedPromptBox) {
      throw new Error('Could not find prompt textbox after image upload');
    }

    if (typeTry === 1) await mcp.callTool('browser_type', {
      profileId: PROFILE_ID,
      tabId: TAB_ID,
      ref: updatedPromptBox.ref,
      text: item.prompt,
    });
    console.log(
      `  [4/5] Typed prompt (${item.prompt.length} chars, try ${typeTry}) into ${updatedPromptBox.ref}`
    );
    await pause(1000);

    const checkSnap = await mcp.callTool('browser_observe_page', {
      profileId: PROFILE_ID,
      tabId: TAB_ID,
    });
    if (verifyPromptText(checkSnap, item.prompt)) {
      readySnap = checkSnap;
      break;
    }
    console.log(`  [wait] Prompt text not yet visible; observing again without retyping...`);
  }
  if (!readySnap) {
    throw new Error(`Failed to verify typed prompt text for Clip ${item.clip}`);
  }

  for (let waitSlot = 1; waitSlot <= 40; waitSlot++) {
    const slotSnap = waitSlot === 1 ? readySnap : await mcp.callTool('browser_observe_page', { profileId: PROFILE_ID, tabId: TAB_ID });
    let activeCount = 0;
    const countActive = (n) => {
      if (!n || typeof n !== 'object') return;
      if (/^\d+%$/.test(String(n.text || '').trim())) activeCount++;
      for (const c of n.children || []) countActive(c);
    };
    for (const f of slotSnap?.frames || []) countActive(f.tree);
    if (activeCount < 4) {
      readySnap = slotSnap;
      break;
    }
    console.log(`  [wait] ${activeCount} jobs currently generating in Flow (limit 4); waiting 6s (poll ${waitSlot}/40)...`);
    await pause(6000);
  }

  for (let submitTry = 1; submitTry <= 6; submitTry++) {
    let curSnap =
      submitTry === 1
        ? readySnap
        : await mcp.callTool('browser_observe_page', {
            profileId: PROFILE_ID,
            tabId: TAB_ID,
          });
    if (submitTry > 1) {
      const box = findNode(curSnap, isPromptTextbox);
      if (box) {
        await mcp.callTool('browser_click', { profileId: PROFILE_ID, tabId: TAB_ID, ref: box.ref });
        await mcp.callTool('browser_press_key', { profileId: PROFILE_ID, tabId: TAB_ID, key: ' ' });
        await pause(3000);
        curSnap = await mcp.callTool('browser_observe_page', {
          profileId: PROFILE_ID,
          tabId: TAB_ID,
        });
      }
    }
    {
      let chipsNow = countIngredientChips(curSnap);
      const requiredChips = skipImage ? 0 : 1;
      while (chipsNow > requiredChips) {
        const cIcon = findNode(curSnap, (n) => n.ref && n.tag === 'mat-icon' && String(n.text || '').trim() === 'cancel');
        if (!cIcon) break;
        console.log(`  [dedup] Removing duplicate chip before Start (${chipsNow} -> ${chipsNow - 1})...`);
        await mcp.callTool('browser_click', { profileId: PROFILE_ID, tabId: TAB_ID, ref: cIcon.ref });
        await pause(1200);
        curSnap = await mcp.callTool('browser_observe_page', { profileId: PROFILE_ID, tabId: TAB_ID });
        chipsNow = countIngredientChips(curSnap);
      }
      record('pre_submit_chips', { ...base, try: submitTry, chips: chipsNow });
      if (chipsNow !== requiredChips) {
        throw new Error(`Clip ${item.clip}: ${chipsNow} ingredient chips right before Start (need exactly ${requiredChips})`);
      }
    }
    const startBtn = findNode(curSnap, isStartButton);
    if (!startBtn) {
      throw new Error('Could not find "Start generation" button');
    }

    assertKeyframeUnchanged();
    if (!verifyPromptText(curSnap, item.prompt)) throw new Error('PROMPT_UNVERIFIABLE: composer is empty before submission');
    assertFrameUploadVerifiable(curSnap);
    ctx.verifyReview();
    verifySettings(curSnap);
    record('submit_attempt', { ...base, try: submitTry });
    await mcp.callTool('browser_click', {
      profileId: PROFILE_ID,
      tabId: TAB_ID,
      ref: startBtn.ref,
    });
    console.log(`  [5/5] Clicked "Start generation" (${startBtn.ref}, try ${submitTry})!`);
    await pause(3500);

    const afterSnap = await mcp.callTool('browser_observe_page', {
      profileId: PROFILE_ID,
      tabId: TAB_ID,
    });
    const stillHasClear = findNode(afterSnap, isClearButton);
    if (!stillHasClear) {
      console.log(`  [OK] Confirmed prompt submitted and cleared!`);
      record('submitted', { ...base, try: submitTry });
      return true;
    }
    throw new Error(`Clip ${item.clip}: submission outcome unknown; inspect the Flow job before any retry`);
  }
  record('fail', { ...base, reason: 'submission not confirmed after 3 tries' });
  throw new Error(`Clip ${item.clip}: submission not confirmed`);
}

export async function submitSingleClip(mcp, item, ctx = {}) {
  const maxClipTries = ctx.sleep ? 1 : 3;
  let submissionAttempted = false;
  const guardedContext = { ...ctx, trace: (event, data) => {
    if (event === 'submit_attempt') submissionAttempted = true;
    (ctx.trace || trace)(event, data);
  }};
  for (let clipTry = 1; clipTry <= maxClipTries; clipTry++) {
    try {
      return await submitSingleClipImpl(mcp, item, guardedContext);
    } catch (error) {
      console.warn(`  [!] Clip ${item.clip} attempt ${clipTry}/3 failed: ${error.message}`);
      if (submissionAttempted || /OUTCOME_UNKNOWN|SITE_BLOCKED|PERMISSION|QUARANTIN|REVIEW_STALE|SETTINGS_|UPLOAD_UNVERIFIABLE|PROMPT_/i.test(error.message) || clipTry === maxClipTries) {
        (ctx.trace || trace)('fail', { part: ctx.part, clip: item.clip, reason: error.message });
        throw error;
      }
      await new Promise((r) => setTimeout(r, 3000));
    }
  }
}

async function main() {
  const argv = process.argv.slice(2);
  let part = null;
  let clipSet = null;
  let startClip = 1;
  let endClip = 999;
  let manifestPath = null, reviewsPath = null, templatePath = null;
  let preflightOnly = false;
  for (let i = 0; i < argv.length; i++) {
    if ((argv[i] === '--part' || argv[i] === '--batch') && argv[i + 1]) part = argv[++i];
    else if ((argv[i] === '--clip' || argv[i] === '--clips') && argv[i + 1]) {
      clipSet = new Set(String(argv[++i]).split(',').map((s) => Number(s.trim())).filter(Boolean));
    }
    else if (argv[i] === '--start-clip' && argv[i + 1]) startClip = Number(argv[++i]);
    else if (argv[i] === '--end-clip' && argv[i + 1]) endClip = Number(argv[++i]);
    else if (argv[i] === '--profile' && argv[i + 1]) PROFILE_ID = argv[++i];
    else if (argv[i] === '--tab' && argv[i + 1]) TAB_ID = Number(argv[++i]);
    else if (argv[i] === '--manifest' && argv[i + 1]) manifestPath = argv[++i];
    else if (argv[i] === '--reviews' && argv[i + 1]) reviewsPath = argv[++i];
    else if (argv[i] === '--review-template' && argv[i + 1]) templatePath = argv[++i];
    else if (argv[i] === '--preflight-only') preflightOnly = true;
    else throw new Error(`Unknown or incomplete argument: ${argv[i]}`);
  }

  if (!part && !manifestPath) throw new Error('Specify --manifest <path> or --batch <batch_name>');
  const batch = manifestPath ? itemsFromManifest(manifestPath) : BATCHES[part];
  if (!batch) throw new Error(`Unknown --part ${part}`);
  manifestPath ||= manifestForBatch(part);
  part ||= 'manifest';
  const items = clipSet
    ? batch.filter((x) => clipSet.has(x.clip))
    : batch.filter((x) => x.clip >= startClip && x.clip <= endClip);

  if (clipSet && items.length !== clipSet.size) throw new Error('Selected clip IDs absent from manifest/batch');
  if (templatePath) {
    const template = generationTemplate(manifestPath, items);
    template.flow_settings = {status: 'pending', profileId: PROFILE_ID, tabId: TAB_ID,
      manifestSha256: template.manifest_sha256, settings: {}, reviewer: '', evidence: '', reviewed_at: ''};
    writeFileSync(templatePath, JSON.stringify(template, null, 2), { flag: 'wx' });
    console.log(`Pending generation review template: ${templatePath}`);
    return;
  }
  const reviews = reviewsPath ? JSON.parse(readFileSync(reviewsPath, 'utf8').replace(/^\uFEFF/, '')) : null;
  const preflight = preflightBatch(manifestPath, items, reviews);
  if (preflightOnly) { console.log(JSON.stringify(preflight)); return; }
  const generationSettings = JSON.parse(readFileSync(manifestPath, 'utf8').replace(/^\uFEFF/, '')).generation_settings;
  if (!PROFILE_ID || !Number.isInteger(TAB_ID) || TAB_ID <= 0) {
    throw new Error('Discover connected profiles/tabs, then explicitly supply --profile and --tab');
  }

  RUN_ID = `${part}-${new Date().toISOString()}`;
  trace('batch_start', { part, clips: items.map((x) => x.clip), trace_path: TRACE_PATH });
  const mcp = new McpClient();
  try {
    await mcp.init();
    const profiles = await mcp.callTool('browser_list_profiles', {});
    const profile = profiles.profiles?.find(p => p.profileId === PROFILE_ID);
    if (profile?.state !== 'online') throw new Error('Selected Profile Bridge profile is not online; reconnect it before generation');
    const tabs = await mcp.callTool('browser_list_tabs', { profileId: PROFILE_ID });
    const tab = tabs.tabs?.find(t => t.tabId === TAB_ID);
    const target = tab?.url ? new URL(tab.url) : null;
    if (!target || !((target.hostname === 'flow.google.com' && target.pathname.startsWith('/project/')) ||
      (target.hostname === 'labs.google' && /\/flow\/project\//.test(target.pathname)))) {
      throw new Error('Selected tab is not an open Google Flow project');
    }
    await mcp.callTool('browser_press_key', { profileId: PROFILE_ID, tabId: TAB_ID, key: 'Escape' });
    await sleep(600);
    const navSnap = await mcp.callTool('browser_observe_page', { profileId: PROFILE_ID, tabId: TAB_ID });
    const hasImg = findNode(navSnap, (n) => n.role === 'button' && n.name === 'image.png');
    const allMediaBtn = findNode(navSnap, (n) => n.ref && n.role === 'button' && typeof n.name === 'string' && n.name.includes('All media'));
    if (allMediaBtn && !hasImg) {
      await mcp.callTool('browser_click', { profileId: PROFILE_ID, tabId: TAB_ID, ref: allMediaBtn.ref });
      await sleep(1200);
    }
    // Never delete tiles automatically
    for (const item of items) {
      await submitSingleClip(mcp, item, { part, generationSettings, settingsAttestation: reviews.flow_settings,
        manifestSha256: reviews.manifest_sha256,
        verifyReview: () => {
          try { preflightBatch(manifestPath, [item], reviews); }
          catch (error) { throw new Error(`REVIEW_STALE: ${error.message}`); }
        },
      });
    }
    trace('batch_done', { part, submitted: items.length });
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

const S10_DIR = 'C:\\Users\\LifeCycle\\.gemini\\antigravity\\scratch\\series10-fake-tattoo-trap-farsi';
const S11_DIR = 'C:\\Users\\LifeCycle\\.gemini\\antigravity\\scratch\\series11-big-lips-pear-farsi';

BATCHES.ft_part1 = [
  {
    clip: 1,
    kf: `${S10_DIR}\\part1\\keyframes\\KF_01.jpg`,
    prompt:
      '[FT1_C01] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), inside the neon INK & LUXE studio the 3D brown squirrel girl (Sandy with warm brown fur, pointed squirrel ears, fluffy tail, long dark hair, sleek black tank top, and dark jeans) sits in the chair smiling mischievously at the 3D rectangular yellow porous sponge artist in a brown apron (strictly NO human faces), as the squirrel girl speaks in native Persian (Farsi) with exact vowel pronunciation and a playful clever young female voice: «لِیْلا هَر کاری مَن می‌کُنَم رُو تَقْلید می‌کُنه، اِمْرُوز بَراش یِک تَلِه‌یِ حِسابی گُذاشْتَم!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S10_DIR}\\part1\\keyframes\\KF_02.jpg`,
    prompt:
      '[FT1_C02] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), inside the neon INK & LUXE studio the 3D rectangular yellow porous sponge artist in a brown apron carefully applies a peel-and-stick colorful tribal sticker onto the furry cheek of the 3D brown squirrel girl in a black tank top (strictly NO human faces), as the sponge artist speaks in native Persian (Farsi) with exact vowel pronunciation and a friendly cheerful male voice: «بِفَرْما سَنْدی، این بَرْچَسْبِ خالْکُوبیِ مُوَقَّت فَقَط پَنْج دُلاره و عِیْنِ خالْکُوبیِ واقِعی بِه نَظَر می‌رِسه!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S10_DIR}\\part1\\keyframes\\KF_03.jpg`,
    prompt:
      '[FT1_C03] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), inside the neon studio the 3D brown squirrel girl in a black tank top holds up her smartphone taking a selfie showing off the colorful fake tribal sticker on her furry cheek while the 3D yellow porous sponge artist laughs beside her (strictly NO human faces), as the squirrel girl speaks in native Persian (Farsi) with exact vowel pronunciation and an excited mischievous young female voice: «عالی شُد! حالا یِک سِلْفی می‌گیرَم و می‌نِویسَم بالَاَخَره رُویِ صُورَتَم خالْکُوبیِ دائِمی زَدَم!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S10_DIR}\\part1\\keyframes\\KF_04.jpg`,
    prompt:
      '[FT1_C04] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human lemon character and outfit in the reference image, static medium shot keeping the character in frame the entire time (no camera cuts), sitting on a bedroom bed in glossy red satin pajamas the 3D anthropomorphic bright-yellow lemon girl (Leila with a round yellow citrus-peel lemon head, big amber eyes, and long dark braided dreads, strictly NO human face) stares at her glowing smartphone in jealous shock, speaking in native Persian (Farsi) with exact vowel pronunciation and a jealous dramatic young female voice: «چی؟! سَنْدی رُویِ صُورَتِش خالْکُوبی زَده؟! اِمْکان نَداره بِذارَم اَز مَن خُوشْگِل‌تر و خاص‌تر بِشه!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S10_DIR}\\part1\\keyframes\\KF_05.jpg`,
    prompt:
      '[FT1_C05] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human lemon character and outfit in the reference image, static medium shot keeping the character in frame the entire time (no camera cuts), sitting on her bed in glossy red satin pajamas the 3D bright-yellow lemon girl with dark braided dreads clenches her fist with a competitive smirk while clutching her smartphone (strictly NO human face), speaking in native Persian (Farsi) with exact vowel pronunciation and a determined competitive young female voice: «مَن هَم هَمین اَلآن می‌رَم یِک خالْکُوبیِ واقِعی و خِیْلی بُزُرْگ‌تر رُویِ صُورَتَم می‌زَنَم!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S10_DIR}\\part1\\keyframes\\KF_06.jpg`,
    prompt:
      '[FT1_C06] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), in a brick tattoo parlor the 3D bright-yellow lemon girl with dark braided dreads in a black hoodie sits in the leather chair pointing at her cheek and holding up her phone to the 3D teal octopus tattoo artist in round glasses holding a tattoo machine (strictly NO human faces), as the lemon girl speaks in native Persian (Farsi) with exact vowel pronunciation and a demanding arrogant young female voice: «آقا، دَقیقاً هَمین طَرْح رُو با سُوزَن و جَوْهَرِ دائِمی رُویِ صُورَتِ مَن بِزَنید!» Zero on-screen subtitles.',
  },
];

BATCHES.ft_part2 = [
  {
    clip: 1,
    kf: `${S10_DIR}\\part2\\keyframes\\KF_01.jpg`,
    prompt:
      '[FT2_C01] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), in the brick tattoo parlor the 3D teal octopus tattoo artist in round glasses and brown leather apron holds a buzzing rotary tattoo gun and warns the 3D bright-yellow lemon girl sitting stubbornly in the chair in her black hoodie (strictly NO human faces), as the octopus artist speaks in native Persian (Farsi) with exact vowel pronunciation and a deep serious warning male voice: «مُطْمَئِنّی دُخْتَرَم؟ این سُوزَن و جَوْهَرِ دائِمیه و تا آخِرِ عُمْرِت اَز رُویِ صُورَتِت پاک نِمی‌شه!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S10_DIR}\\part2\\keyframes\\KF_02.jpg`,
    prompt:
      '[FT2_C02] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human lemon character and outfit in the reference image, static medium close-up shot keeping the character in frame the entire time (no camera cuts), outside the INK & LUXE brick shop the 3D bright-yellow lemon girl with dark braided dreads in a black hoodie takes a proud smartphone selfie pointing at the newly inked black-and-red permanent tribal tattoo on her lemon cheek (strictly NO human face), speaking in native Persian (Farsi) with exact vowel pronunciation and a pained boastful young female voice: «آخ، صُورَتَم آتیش گِرِفْت! وَلی اَرْزِشِش رُو داشْت، خالْکُوبیِ مَن اَز مالِ سَنْدی خِیْلی خَفَن‌تره!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S10_DIR}\\part2\\keyframes\\KF_03.jpg`,
    prompt:
      '[FT2_C03] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), on a sunny wooden house porch the 3D bright-yellow lemon girl in a black hoodie points smugly at her permanent cheek tattoo while the 3D brown squirrel girl in a black tank top smiles calmly wearing her matching sticker (strictly NO human faces), as the lemon girl speaks in native Persian (Farsi) with exact vowel pronunciation and a smug bragging young female voice: «سَلام سَنْدی! بِبین مَن هَم رُویِ صُورَتَم خالْکُوبی زَدَم، وَلی طَرْحِ مَن خِیْلی بُزُرْگ‌تر و قَشَنْگ‌تره!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S10_DIR}\\part2\\keyframes\\KF_04.jpg`,
    prompt:
      '[FT2_C04] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), on the wooden porch the 3D brown squirrel girl in a black tank top smirks and peels the temporary tattoo sticker cleanly off her furry cheek with a white pad while the 3D yellow lemon girl freezes in wide-eyed shock (strictly NO human faces), as the squirrel girl speaks in native Persian (Farsi) with exact vowel pronunciation and an amused laughing young female voice: «وای لِیْلا، واقِعاً با سُوزَن خالْکُوبی کَرْدی؟! مالِ مَن فَقَط یِک بَرْچَسْبِ مُوَقَّتِ پَنْج دُلاری بُود!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S10_DIR}\\part2\\keyframes\\KF_04.jpg`,
    prompt:
      '[FT2_C05] Stylized 3D CGI cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), on the wooden porch the 3D yellow citrus girl in a black hoodie touches the colorful tribal design on her cheek in disbelief while the 3D brown squirrel girl holds up the peeled-off sticker decal (strictly NO human faces), as the yellow citrus girl speaks in native Persian (Farsi) with exact vowel pronunciation and a surprised emotional young female voice: «چی می‌گی؟! یَعْنی بَرْچَسْب بُود؟! وای نَه، پَس چِرا خالْکُوبیِ مَن با دَسْت پاک نِمی‌شه؟!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S10_DIR}\\part2\\keyframes\\KF_06.jpg`,
    prompt:
      '[FT2_C06] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), on the wooden porch the 3D bright-yellow lemon girl in a black hoodie weeps big cartoon tears furiously scrubbing her red swollen tattooed cheek with a white tissue while the 3D brown squirrel girl stands beside her with arms crossed smiling (strictly NO human faces), as the squirrel girl speaks in native Persian (Farsi) with exact vowel pronunciation and a confident witty young female voice: «هَر چِقَدْر دَسْتْمال بِکِشی پاک نِمی‌شه! این هَم نَتیجِه‌یِ حَسادَت و تَقْلیدِ کُورْکُورانه!» Zero on-screen subtitles.',
  },
];

BATCHES.bl_part1 = [
  {
    clip: 1,
    kf: `${S11_DIR}\\part1\\keyframes\\KF_01.jpg`,
    prompt:
      '[BL1_C01] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human fruit characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), at a bright grocery store checkout counter a 3D round orange fruit clerk in a navy polo shirt points in shock and laughs at a 3D green-yellow pear boy in a black graphic tee who has gigantic puffy pink cartoon lips (strictly NO human faces), as the orange clerk speaks in native Persian (Farsi) with exact vowel pronunciation and a loud mocking male voice: «بَچّه‌ها لَبْ‌هایِ این یارُو رُو بِبینید! اِنْگار دُو تا قایِقِ بادیِ بُزُرْگ بِه صُورَتِش چَسْبُونْده!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S11_DIR}\\part1\\keyframes\\KF_02.jpg`,
    prompt:
      '[BL1_C02] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human fruit characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), at the grocery checkout counter the 3D round orange clerk laughs clutching his stomach while the 3D green-yellow pear boy with gigantic puffy pink cartoon lips and black dread twists glares in annoyance (strictly NO human faces), as the pear boy speaks in native Persian (Farsi) with exact vowel pronunciation and an annoyed defensive young male voice: «چِرا می‌خَنْدی آقا؟! مَن فَقَط اُومَدَم یِک بَسْته چیپْس بِخَرَم، لَبْ‌هایِ مَن چِه رَبْطی بِه تُو داره؟!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S11_DIR}\\part1\\keyframes\\KF_03.jpg`,
    prompt:
      '[BL1_C03] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human fruit characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), in the grocery store snack aisle a 3D glossy red apple bully in a green hoodie doubles over laughing and pointing while the 3D green-yellow pear boy with gigantic puffy pink cartoon lips throws his hands up in frustration (strictly NO human faces), as the red apple bully speaks in native Persian (Farsi) with exact vowel pronunciation and a teasing laughing male voice: «مُراقِب باشید! اَلآن با یِک نَفَسِ عَمیق کُلِّ هَوایِ فُرُوشْگاه رُو قُورْت می‌ده!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S11_DIR}\\part1\\keyframes\\KF_04.jpg`,
    prompt:
      '[BL1_C04] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human pear character and outfit in the reference image, static medium close-up shot keeping the character in frame the entire time (no camera cuts), in front of his bathroom mirror the sad 3D green-yellow pear boy with short black dread twists squishes his giant pink lips with tears in his eyes while holding a black cloth face mask (strictly NO human face), speaking in native Persian (Farsi) with exact vowel pronunciation and a sad emotional young male voice: «خَسْته شُدَم اَز بَس هَمه مَسْخَره‌م کَرْدَن! دیگه نِمی‌خْوام هیچ‌کَس صُورَتِ مَن رُو بِبینه!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S11_DIR}\\part1\\keyframes\\KF_05.jpg`,
    prompt:
      '[BL1_C05] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human pear character and outfit in the reference image, static medium close-up shot keeping the character in frame the entire time (no camera cuts), in his bedroom the 3D green-yellow pear boy with short black dread twists and a black tee wears a sleek black fabric half-mask concealing his giant lips with a relieved confident expression (strictly NO human face), speaking in native Persian (Farsi) with exact vowel pronunciation and a relieved young male voice: «با این ماسْکِ مِشْکی لَبْ‌هام کامِلاً قایِم می‌شه و دیگه هیچ‌کَس نِمی‌تُونه مَسْخَره‌م کُنه!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S11_DIR}\\part1\\keyframes\\KF_06.jpg`,
    prompt:
      '[BL1_C06] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human fruit characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), by the chain-link fence of an outdoor basketball court at dusk a 3D golden pineapple jock with a crown of green leaves in a red-and-white varsity jacket points and laughs at the masked 3D green-yellow pear boy standing with arms crossed (strictly NO human faces), as the pineapple jock speaks in native Persian (Farsi) with exact vowel pronunciation and an arrogant mocking male voice: «تُویِ این گَرْما چِرا ماسْک زَدی رَفیق؟! نَکُنه می‌تَرْسی قِیافِه‌یِ عَجیْب و غَریبِت رُو بِبینیم؟!» Zero on-screen subtitles.',
  },
];

BATCHES.bl_part2 = [
  {
    clip: 1,
    kf: `${S11_DIR}\\part2\\keyframes\\KF_01.jpg`,
    prompt:
      '[BL2_C01] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human fruit characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), on the basketball court at dusk the 3D golden pineapple jock in a red-and-white varsity jacket laughs hysterically with tears in his eyes while the 3D green-yellow pear boy glares with his black mask pulled down under his chin exposing his giant pink lips (strictly NO human faces), as the pineapple jock speaks in native Persian (Farsi) with exact vowel pronunciation and a loud mocking laughing male voice: «پَس بِه خاطِرِ این لَبْ‌هایِ غُول‌پِیْکَر ماسْک زَده بُودی؟! عَجَب قِیافِه‌یِ خَنْده‌داری داری!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S11_DIR}\\part2\\keyframes\\KF_02.jpg`,
    prompt:
      '[BL2_C02] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human fruit characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), sitting on a wooden park bench at dusk under a warm streetlamp the 3D magenta-pink dragonfruit girl with green-tipped scales and dark wavy hair in a pink cardigan gestures kindly toward the masked 3D green-yellow pear boy (strictly NO human faces), as the dragonfruit girl speaks in native Persian (Farsi) with exact vowel pronunciation and a sweet gentle young female voice: «بِه حَرْفْ‌هاشُون اَهَمِّیَّت نَده کامْران... چِرا صُورَتِت رُو پُشْتِ اُون ماسْکِ مِشْکی قایِم کَرْدی؟» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S11_DIR}\\part2\\keyframes\\KF_03.jpg`,
    prompt:
      '[BL2_C03] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human fruit characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), on the park bench at dusk the masked 3D green-yellow pear boy in a black graphic tee points hesitantly to his black mask while the 3D magenta-pink dragonfruit girl in a pink cardigan smiles reassuringly (strictly NO human faces), as the pear boy speaks in native Persian (Farsi) with exact vowel pronunciation and a shy hesitant young male voice: «اَگه این ماسْک رُو بَرْدارَم، تُو هَم مِثْلِ بَقِیّه بِه قِیافِه‌یِ مَن می‌خَنْدی و مَسْخَره‌م می‌کُنی!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S11_DIR}\\part2\\keyframes\\KF_04.jpg`,
    prompt:
      '[BL2_C04] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human fruit characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), on the park bench at dusk the 3D green-yellow pear boy holds his black mask in his hand revealing his giant pink lips and touches his chest in amazement as the 3D magenta-pink dragonfruit girl smiles warmly at him (strictly NO human faces), as the dragonfruit girl speaks in native Persian (Farsi) with exact vowel pronunciation and a warm loving young female voice: «اَصْلاً هَم خَنْده‌دار نیسْتی! بِه نَظَرِ مَن لَبْ‌هات خِیْلی هَم خاص و بامَزه‌سْت، بِیا با هَم دُوسْت بِشیم!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S11_DIR}\\part2\\keyframes\\KF_05.jpg`,
    prompt:
      '[BL2_C05] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human fruit characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), standing together on the warm evening city sidewalk the unmasked 3D green-yellow pear boy with giant pink lips beams with pure joy beside the 3D magenta-pink dragonfruit girl in a pink cardigan (strictly NO human faces), as the pear boy speaks in native Persian (Farsi) with exact vowel pronunciation and an excited grateful young male voice: «باوَرَم نِمی‌شه رُژان! فِکْر می‌کَرْدَم هیچ‌کَس تُویِ دُنْیا پِیْدا نِمی‌شه کِه قِیافِه‌یِ مَن رُو دَرْک کُنه!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S11_DIR}\\part2\\keyframes\\KF_06.jpg`,
    prompt:
      '[BL2_C06] 3D Pixar/Cinema4D stylized cartoon animation matching the exact 3D non-human fruit characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), on the evening city sidewalk the 3D magenta-pink dragonfruit girl turns in profile pointing playfully at a gigantic puffy pair of pink cartoon lips protruding from her face while the 3D green-yellow pear boy freezes with his jaw dropped in hilarious comic shock (strictly NO human faces), as the pear boy shouts in native Persian (Farsi) with exact vowel pronunciation and a comedic shocked young male voice: «یا اَبُوالْفَضْل، چِرا اَز نیم‌رُخ لَبْ‌هات سِه بَرابَرِ مالِ مَنه؟! یِکی ماسْکِ مَن رُو بِده فَرار کُنَم!» Zero on-screen subtitles.',
  },
];

const S12_DIR = 'C:\\Users\\LifeCycle\\.gemini\\antigravity\\scratch\\series12-weighted-vest-sponge-farsi';
const S13_DIR = 'C:\\Users\\LifeCycle\\.gemini\\antigravity\\scratch\\series13-red-wig-copycat-trap-farsi';

BATCHES.wv_part1 = [
  {
    clip: 1,
    kf: `${S12_DIR}\\part1\\keyframes\\KF_03.jpg`,
    prompt:
      '[WV1_C01] Stylized 3D CGI cartoon animation matching the exact 3D non-human squirrel character and outfit in the reference image, static medium close-up keeping the character in frame the entire time (no camera cuts), in a cozy room the 3D warm-brown woodland squirrel mother with perky squirrel ears and fluffy tail in a white tank top gestures in surprise while speaking to her husband (strictly NO human face), speaking in native Persian (Farsi) with exact vowel pronunciation and a surprised female voice: «صَبْر کُن بَهْرام، داری چی کار می‌کُنی؟! چِرا این جِلیقِه‌یِ وَرْزِشیِ سَنْگین رُو آوُرْدی؟!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S12_DIR}\\part1\\keyframes\\KF_02.jpg`,
    prompt:
      '[WV1_C02] Stylized 3D CGI cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium shot keeping the characters in frame the entire time (no camera cuts), in the nursery room the muscular 3D dark charcoal-black porous rectangular sponge father kneels beside the tiny 3D yellow toddler sponge holding the black weighted vest and grinning confidently while the 3D brown squirrel mother looks worried (strictly NO human faces), as the dark sponge father speaks in native Persian (Farsi) with exact vowel pronunciation and a confident deep male voice: «نِگَران نَباش خانُوم، بِذار کارَم رُو بُکُنَم! پِسَرَم وَقْتی بُزُرْگ بِشه خُودِش اَزَم تَشَکُّر می‌کُنه!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S12_DIR}\\part1\\keyframes\\KF_03.jpg`,
    prompt:
      '[WV1_C03] Stylized 3D CGI cartoon animation matching the exact 3D non-human squirrel character and outfit in the reference image, static medium close-up keeping the character in frame the entire time (no camera cuts), in the nursery room the 3D warm-brown woodland squirrel mother with perky squirrel ears and fluffy tail in a white tank top points her finger angrily and protectively while scolding her husband (strictly NO human face), speaking in native Persian (Farsi) with exact vowel pronunciation and an angry protective motherly female voice: «اُون جِلیقِه‌یِ سَنْگین رُو اَز تَنِش دَرْبِیار! این بَچّه تازه سِه سالِشه، اَلآن فَقَط بایَد راه بِره!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S12_DIR}\\part1\\keyframes\\KF_04.jpg`,
    prompt:
      '[WV1_C04] Stylized 3D CGI cartoon animation matching the exact 3D non-human sponge character and outfit in the reference image, static medium close-up keeping the character in frame the entire time (no camera cuts), in the nursery room the muscular 3D dark charcoal-black porous rectangular sponge father in a white athletic tank top glares sternly and speaks firmly with flexed arms (strictly NO human face), speaking in native Persian (Farsi) with exact vowel pronunciation and a strict commanding deep male voice: «حَرْف نَباشه خانُوم! مَن خُودَم می‌دُونَم چِطَوْر یِک قَهْرَمانِ واقِعی تَرْبِیَت کُنَم، دِخالَت نَکُن!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S12_DIR}\\part1\\keyframes\\KF_05.jpg`,
    prompt:
      '[WV1_C05] Stylized 3D CGI cartoon animation matching the exact 3D non-human sponge characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), in a sunny living room a 10-year-old 3D yellow porous rectangular sponge boy wearing a black tactical weighted vest and black wrist and ankle weights struggles on the rug trying to do a push-up while the muscular 3D dark charcoal sponge father points down at him sternly (strictly NO human faces), as the dark sponge father speaks in native Persian (Farsi) with exact vowel pronunciation and a loud strict male voice: «این چِه وَضْعِشه سُهْراب؟! دَه سالِت شُده و هَنُوز نِمی‌تُونی با این وَزْنه‌ها حَتّی یِک دُونه شِنا بِری؟!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S12_DIR}\\part1\\keyframes\\KF_06.jpg`,
    prompt:
      '[WV1_C06] Stylized 3D CGI cartoon animation matching the exact 3D non-human sponge characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), in the sunny living room the muscular 3D dark charcoal porous sponge father bends down adjusting the black weighted vest on the exhausted 10-year-old 3D yellow porous sponge boy wearing black wrist and ankle weights (strictly NO human faces), as the dark sponge father speaks in native Persian (Farsi) with exact vowel pronunciation and a stern authoritative male voice: «بِه خاطِرِ هَمین تَنْبَلی، تا هِجْدَه سالِگی حَق نَداری این جِلیقه و وَزْنه‌ها رُو اَز تَنِت دَرْبِیاری!» Zero on-screen subtitles.',
  },
];

BATCHES.wv_part2 = [
  {
    clip: 1,
    kf: `${S12_DIR}\\part2\\keyframes\\KF_01.jpg`,
    prompt:
      '[WV2_C01] Stylized 3D CGI cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium shot keeping the characters in frame the entire time (no camera cuts), at a family dining room table the 16-year-old 3D yellow porous rectangular sponge teen wearing a black weighted vest and wrist weights pleads with the muscular 3D dark charcoal sponge father while the 3D brown squirrel mother watches (strictly NO human faces), as the yellow sponge teen speaks in native Persian (Farsi) with exact vowel pronunciation and a tired frustrated young male voice: «بابا، دیگه شُونْزْدَه سالَم شُده و خَسْته شُدَم! این وَزْنه‌هایِ سَنْگین هیچ فایِده‌ای بَرام نَداشْته!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S12_DIR}\\part2\\keyframes\\KF_02.jpg`,
    prompt:
      '[WV2_C02] Stylized 3D CGI cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium shot keeping the characters in frame the entire time (no camera cuts), in the family dining room the muscular 3D dark charcoal porous sponge father in a white tank top stands up dismissively waving his hand at the 16-year-old 3D yellow porous sponge teen in a black weighted vest (strictly NO human faces), as the dark sponge father speaks in native Persian (Farsi) with exact vowel pronunciation and a dismissive harsh deep male voice: «هَر کاری دِلِت می‌خْواد بُکُن! دَرِشُون بِیار، تُو اَز اَوَّلِش هَم ضَعیف و تَنْبَل بُودی!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S12_DIR}\\part2\\keyframes\\KF_03.jpg`,
    prompt:
      '[WV2_C03] Stylized 3D CGI cartoon animation matching the exact 3D non-human sponge character and outfit in the reference image, static medium shot keeping the character in frame the entire time (no camera cuts), in a teen bedroom next to a mirror and dumbbells on the floor the 16-year-old 3D yellow porous rectangular sponge teen unstraps his heavy black weighted vest and wrist weights with huge relief (strictly NO human face), speaking in native Persian (Farsi) with exact vowel pronunciation and a relieved amazed young male voice: «آخیش! باوَرَم نِمی‌شه چِقَدْر سَنْگین بُودَن! اِنْگار یِک کُوهِ بُزُرْگ اَز رُویِ دُوشَم بَرْداشْته شُد!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S12_DIR}\\part2\\keyframes\\KF_04.jpg`,
    prompt:
      '[WV2_C04] Stylized 3D CGI cartoon animation matching the exact 3D non-human sponge character in the reference image, static medium shot keeping the character in frame the entire time (no camera cuts), in a cozy bedroom at night the muscular 3D yellow porous rectangular sponge teen lies back comfortably on his bed pillow under a blanket with his hands behind his head smiling blissfully (strictly NO human face), speaking in native Persian (Farsi) with exact vowel pronunciation and a happy relaxed young male voice: «وای چِه حِسِّ فَوْقُ‌الْعاده‌ایه! بَعْد اَز شُونْزْدَه سال بالَاَخَره می‌تُونَم یِک خْوابِ راحَت بُکُنَم!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S12_DIR}\\part2\\keyframes\\KF_05.jpg`,
    prompt:
      '[WV2_C05] Stylized 3D CGI cartoon animation matching the exact 3D non-human sponge character in the reference image, static medium shot keeping the character in frame the entire time (no camera cuts), in a bright modern bathroom the shredded muscular 3D yellow porous rectangular sponge bodybuilder stands in front of the sink mirror gasping in wide-eyed amazement at his massive sculpted yellow sponge chest and abs (strictly NO human face), speaking in native Persian (Farsi) with exact vowel pronunciation and a shocked excited young male voice: «یا اَبُوالْفَضْل، این دیگه چِه مُعْجِزه‌ایه؟! مَن کِه فِکْر می‌کَرْدَم بَدَنَم ضَعیف و لاغَره!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S12_DIR}\\part2\\keyframes\\KF_06.jpg`,
    prompt:
      '[WV2_C06] Stylized 3D CGI cartoon animation matching the exact 3D non-human sponge character in the reference image, static medium shot keeping the character in frame the entire time (no camera cuts), in front of the bright bathroom sink mirror the shredded muscular 3D yellow porous rectangular sponge bodybuilder flexes both massive sculpted yellow sponge arms with a huge triumphant grin (strictly NO human face), speaking in native Persian (Farsi) with exact vowel pronunciation and a proud ecstatic young male voice: «نَگُو تَمامِ این سال‌ها زیرِ اُون وَزْنه‌ها داشْتَم تَبْدیل بِه یِک غُولِ عَضُلانی می‌شُدَم!» Zero on-screen subtitles.',
  },
];

BATCHES.rw_part1 = [
  {
    clip: 1,
    kf: `${S13_DIR}\\part1\\keyframes\\KF_01.jpg`,
    prompt:
      '[RW1_C01] Stylized 3D CGI cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), inside a bright hair salon with warm mirror bulbs the 3D brown woodland squirrel girl with long sleek black hair in a pink salon cape sits in the styling chair smiling mischievously while the 3D dark charcoal porous sponge stylist holds up a giant crimson-red curly afro wig (strictly NO human faces), as the squirrel girl speaks in native Persian (Farsi) with exact vowel pronunciation and a playful clever young female voice: «لِیْلا عاشِقِ اینه کِه مُو بِه مُو اَز مَن تَقْلید کُنه، اِمْرُوز بَراش یِک نَقْشِه‌یِ حِسابی کِشیدَم!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S13_DIR}\\part1\\keyframes\\KF_02.jpg`,
    prompt:
      '[RW1_C02] Stylized 3D CGI cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), in the hair salon the 3D dark charcoal porous sponge stylist in a black barber apron places the giant fluffy crimson-red curly afro wig onto the head of the 3D brown squirrel girl in the pink salon cape (strictly NO human faces), as the sponge stylist speaks in native Persian (Farsi) with exact vowel pronunciation and a cheerful friendly male voice: «بِفَرْما سَنْدی، این کُلاه‌گیسِ قِرْمِزِ فِرْفِری رُو بِذار سَرِت، هیچ‌کَس نِمی‌فَهْمه مُویِ خُودِت نیسْت!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S13_DIR}\\part1\\keyframes\\KF_03.jpg`,
    prompt:
      '[RW1_C03] Stylized 3D CGI cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), in the hair salon the 3D brown squirrel girl wearing the giant crimson-red curly afro wig and pink salon cape holds up her smartphone taking a selfie with a playful grin while the 3D dark sponge stylist smiles behind her (strictly NO human faces), as the squirrel girl speaks in native Persian (Farsi) with exact vowel pronunciation and an excited mischievous young female voice: «عالی شُد! حالا عَکْسِش رُو اِسْتُوری می‌کُنَم و می‌نِویسَم مُوهایِ بُلَنْدَم رُو کُوتاه و قِرْمِز کَرْدَم!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S13_DIR}\\part1\\keyframes\\KF_04.jpg`,
    prompt:
      '[RW1_C04] Stylized 3D CGI cartoon animation matching the exact 3D non-human citrus lemon character and outfit in the reference image, static medium shot keeping the character in frame the entire time (no camera cuts), sitting on her bed in glossy red satin pajamas the 3D bright-yellow round citrus lemon girl with long dark braids stares at her glowing smartphone in jealous surprise (strictly NO human face), speaking in native Persian (Farsi) with exact vowel pronunciation and a jealous competitive young female voice: «واو! سَنْدی واقِعاً مُوهاش رُو کُوتاه و قِرْمِزِ فِرْفِری کَرْده؟! رُویِ سَرِ مَن خِیْلی قَشَنْگ‌تر می‌شه!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S13_DIR}\\part1\\keyframes\\KF_05.jpg`,
    prompt:
      '[RW1_C05] Stylized 3D CGI cartoon animation matching the exact 3D non-human fruit characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), in the hair salon the 3D bright-yellow lemon girl with long dark braids in a black salon cape points eagerly at her smartphone showing it to the 3D pink fruit female hairstylist holding salon scissors (strictly NO human faces), as the yellow lemon girl speaks in native Persian (Farsi) with exact vowel pronunciation and an eager demanding young female voice: «خانُوم آرایِشْگَر، مُوهایِ بُلَنْدِ مَن رُو اَز تَه قِیْچی کُنید و دَقیقاً هَمین شِکْلی قِرْمِز و فِرْفِری کُنید!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S13_DIR}\\part1\\keyframes\\KF_06.jpg`,
    prompt:
      '[RW1_C06] Stylized 3D CGI cartoon animation matching the exact 3D non-human fruit characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), in the hair salon the 3D pink fruit female hairstylist in a black barber apron holds silver salon scissors looking hesitantly at the 3D bright-yellow lemon girl sitting in the chair (strictly NO human faces), as the pink fruit stylist speaks in native Persian (Farsi) with exact vowel pronunciation and a cautious polite female voice: «مُطْمَئِنّی عَزیزَم؟ این تَغْییر خِیْلی بُزُرْگه و مُوهایِ بُلَنْد و قَشَنْگِت کامِلاً کُوتاه می‌شه ها!» Zero on-screen subtitles.',
  },
];

BATCHES.rw_part2 = [
  {
    clip: 1,
    kf: `${S13_DIR}\\part2\\keyframes\\KF_01.jpg`,
    prompt:
      '[RW2_C01] Stylized 3D CGI cartoon animation matching the exact 3D non-human fruit characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), in the bright hair salon the 3D bright-yellow lemon girl in a black salon cape now sporting a giant crimson-red curly afro touches her new hair proudly while the 3D pink fruit female stylist smiles behind her (strictly NO human faces), as the yellow lemon girl speaks in native Persian (Farsi) with exact vowel pronunciation and a proud boasting young female voice: «واو، مَحْشَر شُد! حالا می‌رَم بِه سَنْدی نِشُون بِدَم کِه مُویِ قِرْمِز بِه مَن خِیْلی بیشْتَر میاد!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S13_DIR}\\part2\\keyframes\\KF_02.jpg`,
    prompt:
      '[RW2_C02] Stylized 3D CGI cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), on a sunny wooden front porch the 3D bright-yellow lemon girl in a colorful floral shirt and jeans struts up showing off her giant crimson-red curly afro to the 3D brown squirrel girl (strictly NO human faces), as the yellow lemon girl speaks in native Persian (Farsi) with exact vowel pronunciation and a smug bragging young female voice: «سَلام سَنْدی! بِبین مَن هَم مُوهام رُو مِثْلِ تُو کُوتاه و قِرْمِز کَرْدَم، بِه مَن بیشْتَر میاد نَه؟!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S13_DIR}\\part2\\keyframes\\KF_03.jpg`,
    prompt:
      '[RW2_C03] Stylized 3D CGI cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), on the sunny wooden porch the 3D bright-yellow lemon girl with a giant red curly afro freezes in wide-eyed shock pointing at the 3D brown squirrel girl who has her real long sleek black hair flowing over her shoulders while holding the detached red curly wig (strictly NO human faces), as the yellow lemon girl speaks in native Persian (Farsi) with exact vowel pronunciation and a shocked confused young female voice: «صَبْر کُن بِبینَم... پَس مُوهایِ قِرْمِزِت کُو؟! چِرا مُوهایِ مِشْکی و بُلَنْدِت سَرِ جاشه؟!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S13_DIR}\\part2\\keyframes\\KF_04.jpg`,
    prompt:
      '[RW2_C04] Stylized 3D CGI cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), on the sunny wooden porch the 3D brown squirrel girl with long sleek black hair laughs holding out the detached crimson-red curly afro wig in her hand while the 3D yellow lemon girl touches her own chopped red hair in disbelief (strictly NO human faces), as the squirrel girl speaks in native Persian (Farsi) with exact vowel pronunciation and an amused witty young female voice: «دُنْبالِ این می‌گَرْدی؟! اُون مُوهایِ قِرْمِز فَقَط یِک کُلاه‌گیس بُود، مَن اَصْلاً مُوهام رُو کُوتاه نَکَرْدَم!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S13_DIR}\\part2\\keyframes\\KF_05.jpg`,
    prompt:
      '[RW2_C05] Stylized 3D CGI cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), on the sunny wooden porch the 3D bright-yellow lemon girl with a giant red curly afro in a floral shirt shouts in frustration with cartoon tears in her eyes while the red wig rests on the floor beside the calm 3D brown squirrel girl (strictly NO human faces), as the yellow lemon girl speaks in native Persian (Farsi) with exact vowel pronunciation and an upset crying young female voice: «تُو اَز قَصْد سَرِ مَن کُلاه گُذاشْتی! بِه خاطِرِ تُو زَدَم مُوهایِ بُلَنْد و واقِعیم رُو نابُود کَرْدَم!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S13_DIR}\\part2\\keyframes\\KF_06.jpg`,
    prompt:
      '[RW2_C06] Stylized 3D CGI cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), on the sunny wooden porch the 3D brown squirrel girl with long sleek black hair gestures with a confident smile while the 3D yellow lemon girl turns away holding her giant red curly hair in regret (strictly NO human faces), as the squirrel girl speaks in native Persian (Farsi) with exact vowel pronunciation and a confident sassy young female voice: «تَقْصیرِ مَن نیسْت، کَسی مَجْبُورِت نَکَرْد اَز مَن تَقْلید کُنی! دَفْعِه‌یِ بَعْد سَعْی کُن خُودِت باشی!» Zero on-screen subtitles.',
  },
];

const S14_DIR = 'C:\\Users\\LifeCycle\\.gemini\\antigravity\\scratch\\series14-rap-son-ceo-daughter-farsi';
const S15_DIR = 'C:\\Users\\LifeCycle\\.gemini\\antigravity\\scratch\\series15-janitor-apple-bench-press-farsi';

BATCHES.rs_part1 = [
  {
    clip: 1,
    kf: `${S14_DIR}\\part1\\keyframes\\KF_01.jpg`,
    prompt:
      '[RS1_C01] Stylized 3D CGI cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium shot keeping the characters in frame the entire time (no camera cuts), at a cozy dining table the 3D dark charcoal-black porous rectangular sponge father in a white polo shirt and gold chain happily hands green cash bills to his 3D dark charcoal porous sponge teen son in a black puffer jacket, backwards cap, and headphones while the 3D brown squirrel girl in a navy hoodie watches (strictly NO human faces), as the dark sponge father speaks in native Persian (Farsi) with exact vowel pronunciation and a warm proud fatherly male voice: «بِیا پِسَرَم، این پَنْجاه دُلار بَرایِ شُرُوعِ خْوانَنْدِگیت! مَن بِه اِسْتِعْدادِت ایمان دارَم!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S14_DIR}\\part1\\keyframes\\KF_02.jpg`,
    prompt:
      '[RS1_C02] Stylized 3D CGI cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), at the dining table the 3D dark charcoal-black porous rectangular sponge father in a white polo shirt and gold chain waves his hand and shouts dismissively at the sad 3D brown woodland squirrel girl in a navy hoodie (strictly NO human faces), as the dark sponge father speaks in native Persian (Farsi) with exact vowel pronunciation and an angry harsh male voice: «پُول بَرایِ کِتابِ دانِشْگاه؟! نَخِیْر، مَگه مَن رُویِ گَنْج نِشَسْتَم؟! بُرُو خُودِت کار کُن!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S14_DIR}\\part1\\keyframes\\KF_03.jpg`,
    prompt:
      '[RS1_C03] Stylized 3D CGI cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), in a bright supermarket aisle the 3D brown woodland squirrel girl in a navy hoodie holds cardboard boxes and pleads earnestly with the 3D coral-pink cone-headed store manager in an orange polo shirt (strictly NO human faces), as the squirrel girl speaks in native Persian (Farsi) with exact vowel pronunciation and a pleading earnest young female voice: «آقا تُورُوخُدا بِذارید اِمْشَب هَم اِضافِه‌کاری بِمُونَم، بایَد پُولِ کِتابْ‌هایِ دانِشْگاهَم رُو جُور کُنَم!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S14_DIR}\\part1\\keyframes\\KF_04.jpg`,
    prompt:
      '[RS1_C04] Stylized 3D CGI cartoon animation matching the exact 3D non-human sponge characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), inside a neon purple music recording studio the 3D dark charcoal porous sponge teen in a black puffer jacket and headphones stands at a studio microphone while the 3D dark charcoal porous sponge father in a white polo shirt proudly holds up a black credit card (strictly NO human faces), as the dark sponge father speaks in native Persian (Farsi) with exact vowel pronunciation and a boastful generous male voice: «پُونْصَد دُلار کِه چیزی نیسْت! کُلِّ اِسْتُودِیُو رُو بَرایِ پِسَرَم رِزِرْو کُنید تا آهَنْگِش رُو ضَبْط کُنه!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S14_DIR}\\part1\\keyframes\\KF_05.jpg`,
    prompt:
      '[RS1_C05] Stylized 3D CGI cartoon animation matching the exact 3D non-human sponge characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), on a sunny suburban driveway in front of a shiny black luxury sports car with a giant red ribbon bow on the hood the 3D dark charcoal porous sponge father in a white polo shirt hands car keys to the jumping excited 3D dark charcoal sponge teen in a black puffer jacket (strictly NO human faces), as the dark sponge father speaks in native Persian (Farsi) with exact vowel pronunciation and a proud excited male voice: «یِک سِتارِه‌یِ مُوسیقی کِه نِمی‌تُونه با اُتُوبُوس بِره! این ماشینِ مُدِل‌بالا هِدْیِه‌یِ مَن بِه تُوئه!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S14_DIR}\\part1\\keyframes\\KF_06.jpg`,
    prompt:
      '[RS1_C06] Stylized 3D CGI cartoon animation matching the exact 3D non-human squirrel character and outfit in the reference image, static medium shot keeping the character in frame the entire time (no camera cuts), on a rainy city sidewalk the soaked 3D brown woodland squirrel girl in a navy hoodie and backpack walks in the pouring rain hugging her university books with a sad but determined expression as a black sports car drives away in the background (strictly NO human face), speaking in native Persian (Farsi) with exact vowel pronunciation and an emotional determined young female voice: «تُویِ این بارُونِ شَدید حَتّی سَوارَم نَکَرْدَن... عِیْب نَداره، یِه رُوزی نَتیجِه‌یِ این سَخْتی‌ها رُو می‌بینید!» Zero on-screen subtitles.',
  },
];

BATCHES.rs_part2 = [
  {
    clip: 1,
    kf: `${S14_DIR}\\part2\\keyframes\\KF_01.jpg`,
    prompt:
      '[RS2_C01] Stylized 3D CGI cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), in a university classroom the 3D bright-red crustacean professor in round glasses and a brown tweed suit hands an exam paper to the smiling 3D brown woodland squirrel girl in a navy hoodie sitting at her desk (strictly NO human faces), as the red crustacean professor speaks in native Persian (Farsi) with exact vowel pronunciation and a warm proud academic male voice: «آفَرین سَنْدی! بالاتَرین نُمْرِه‌یِ دانِشْگاه! تُو باهُوش‌ترین دانِشْجُویِ دَه سالِ اَخیری!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S14_DIR}\\part2\\keyframes\\KF_02.jpg`,
    prompt:
      '[RS2_C02] Stylized 3D CGI cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), in the living room the 3D brown woodland squirrel girl in a navy hoodie holds up her exam paper toward the 3D dark charcoal porous sponge father sitting on the sofa who waves her away annoyed to watch the TV (strictly NO human faces), as the dark sponge father speaks in native Persian (Farsi) with exact vowel pronunciation and an annoyed dismissive male voice: «بُرُو کِنار سَنْدی، جُلُویِ تِلِویزْیُون رُو گِرِفْتی! دارَم مُوزیک‌ویدِیُویِ بَرادَرِت رُو می‌بینَم!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S14_DIR}\\part2\\keyframes\\KF_03.jpg`,
    prompt:
      '[RS2_C03] Stylized 3D CGI cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium shot keeping the characters in frame the entire time (no camera cuts), in the kitchen the 3D brown woodland squirrel girl in a navy hoodie holds a tuition bill with cartoon tears in her eyes while the 3D dark charcoal porous sponge father hands a thick bundle of cash to the 3D dark charcoal sponge teen son (strictly NO human faces), as the squirrel girl speaks in native Persian (Farsi) with exact vowel pronunciation and a heartbroken young female voice: «بابا، بیسْت هِزار دُلار بِه اُون می‌دی، وَلی پُونْصَد دُلار بَرایِ شَهْرِیِه‌یِ دانِشْگاهِ مَن نَداری؟!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S14_DIR}\\part2\\keyframes\\KF_04.jpg`,
    prompt:
      '[RS2_C04] Stylized 3D CGI cartoon animation matching the exact 3D non-human characters and outfits in the reference image, static medium shot keeping the characters in frame the entire time (no camera cuts), by the front hallway stairs the 3D brown woodland squirrel girl in a navy hoodie and backpack stands firmly holding a blue rolling suitcase facing the 3D dark charcoal porous sponge father and teen son (strictly NO human faces), as the squirrel girl speaks in native Persian (Farsi) with exact vowel pronunciation and a firm resolute young female voice: «دیگه یِک دُلار هَم اَزَتُون نِمی‌خْوام! خُودَم تَنْهایی هَم کار می‌کُنَم و هَم دَرْسَم رُو تَمُوم می‌کُنَم!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S14_DIR}\\part2\\keyframes\\KF_05.jpg`,
    prompt:
      '[RS2_C05] Stylized 3D CGI cartoon animation matching the exact 3D non-human squirrel character and outfit in the reference image, static medium shot keeping the character in frame the entire time (no camera cuts), inside a gleaming glass skyscraper executive office overlooking a sunny city skyline the 3D brown woodland squirrel woman wearing a sharp tailored black executive business suit stands beside her mahogany desk looking at her ringing smartphone with a confident smile (strictly NO human face), speaking in native Persian (Farsi) with exact vowel pronunciation and a poised confident young female voice: «پَنْج سال گُذَشْت و حالا مُدیرْعامِلِ بُزُرْگ‌ترین شِرْکَتِ شَهْرَم... عَجَب، بابا داره زَنْگ می‌زَنه!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S14_DIR}\\part2\\keyframes\\KF_06.jpg`,
    prompt:
      '[RS2_C06] Stylized 3D CGI cartoon animation matching the exact 3D non-human squirrel character and outfit in the reference image, static medium close-up keeping the character in frame the entire time (no camera cuts), inside the glass skyscraper executive office the 3D brown woodland squirrel CEO in a tailored black business suit holds her smartphone to her ear with a calm victorious smile (strictly NO human face), speaking in native Persian (Farsi) with exact vowel pronunciation and a witty confident young female voice: «اَلُو بابا؟ پِسَرِت کُلِّ پُولْ‌هات رُو بِه باد داد و حالا اَز مَنِ کِتاب‌خُون کُمَک می‌خْوای؟!» Zero on-screen subtitles.',
  },
];

BATCHES.jb_part1 = [
  {
    clip: 1,
    kf: `${S15_DIR}\\part1\\keyframes\\KF_01.jpg`,
    prompt:
      '[JB1_C01] Stylized 3D CGI cartoon animation matching the exact 3D non-human fruit characters and outfits in the reference image, static medium shot keeping both characters in frame the entire time (no camera cuts), inside a modern fitness gym the tiny 3D glossy green apple janitor in a white tank top, jeans, and yellow gloves effortlessly lifts one side of a heavy bench-press frame with one hand while mopping underneath as the huge muscular 3D yellow banana bodybuilder lies on the bench in shock (strictly NO human faces), as the green apple janitor speaks in native Persian (Farsi) with exact vowel pronunciation and a polite casual young male voice: «آقا بی‌زَحْمَت پاهاتُون رُو بِدید بالا، می‌خْوام زیرِ این دَسْتْگاهِ پِرْس سینه رُو طِی بِکِشَم!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S15_DIR}\\part1\\keyframes\\KF_02.jpg`,
    prompt:
      '[JB1_C02] Stylized 3D CGI cartoon animation matching the exact 3D non-human fruit characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), on the gym floor next to a yellow mop bucket the towering muscular 3D yellow banana gym boss in black shorts and gold chain points angrily down at the tiny 3D green apple janitor holding his wooden mop (strictly NO human faces), as the yellow banana boss shouts in native Persian (Farsi) with exact vowel pronunciation and an angry booming male voice: «چِطَوْر جُرْئَت کَرْدی مَوْقِعِ تَمْرین مُزاحِمِ مَن بِشی؟! هَمین اَلآن اَز باشْگاهِ مَن اِخْراجی، بُرُو بیرُون!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S15_DIR}\\part1\\keyframes\\KF_03.jpg`,
    prompt:
      '[JB1_C03] Stylized 3D CGI cartoon animation matching the exact 3D non-human fruit characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), outside a glowing stadium arena entrance the muscular 3D green-striped watermelon security officer in a dark blue uniform gestures encouragingly to the tiny 3D green apple janitor holding his wooden mop (strictly NO human faces), as the watermelon officer speaks in native Persian (Farsi) with exact vowel pronunciation and a supportive deep male voice: «مَن دیدَم چِطَوْر اُون دَسْتْگاهِ سَنْگین رُو با یِک دَسْت بُلَنْد کَرْدی! بِیا تُویِ مُسابِقِه‌یِ قَهْرِمانی شِرْکَت کُن!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S15_DIR}\\part1\\keyframes\\KF_04.jpg`,
    prompt:
      '[JB1_C04] Stylized 3D CGI cartoon animation matching the exact 3D non-human fruit characters and outfits in the reference image, static medium shot keeping the characters in frame the entire time (no camera cuts), at the bright stadium registration desk the 3D red strawberry receptionist in red glasses looks down in surprise at the tiny 3D green apple janitor holding his wooden mop beside the 3D green watermelon security officer (strictly NO human faces), as the strawberry receptionist speaks in native Persian (Farsi) with exact vowel pronunciation and a surprised skeptical female voice: «عَزیزَم، با این جُثِّه‌یِ کُوچیک و طِیِ نِظافَت اُومَدی سالُن رُو تَمیز کُنی یا واقِعاً شِرْکَت کُنی؟!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S15_DIR}\\part1\\keyframes\\KF_05.jpg`,
    prompt:
      '[JB1_C05] Stylized 3D CGI cartoon animation matching the exact 3D non-human fruit characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), backstage by the stadium weight racks the colossal spiky 3D golden-green durian bodybuilder flexes his massive muscular arms and laughs down at the tiny 3D green apple janitor holding his mop (strictly NO human faces), as the spiky durian champion speaks in native Persian (Farsi) with exact vowel pronunciation and a booming arrogant male voice: «این نِظافَتْچیِ فِسْقِلی رَقیبِ مَنه؟! بُرُو کَفِ سالُن رُو طِی بِکِش کُوچُولُو، اینْجا جایِ غُولْ‌هاسْت!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S15_DIR}\\part1\\keyframes\\KF_06.jpg`,
    prompt:
      '[JB1_C06] Stylized 3D CGI cartoon animation matching the exact 3D non-human fruit characters and outfits in the reference image, static medium close-up shot keeping the characters in frame the entire time (no camera cuts), standing beside the 3D green watermelon security officer under the stadium lights the tiny 3D green apple janitor in a white tank top and yellow gloves looks up with calm fearless confidence (strictly NO human faces), as the green apple janitor speaks in native Persian (Farsi) with exact vowel pronunciation and a calm confident young male voice: «هَر چِقَدْر دِلِتُون می‌خْواد بِخَنْدید! چَنْد دَقیقِه‌یِ دیگه مَعْلُوم می‌شه کی قَراره کَفِ سالُن رُو تَمیز کُنه!» Zero on-screen subtitles.',
  },
];

BATCHES.jb_part2 = [
  {
    clip: 1,
    kf: `${S15_DIR}\\part2\\keyframes\\KF_01.jpg`,
    prompt:
      '[JB2_C01] Stylized 3D CGI cartoon animation matching the exact 3D non-human fruit character and outfit in the reference image, static medium shot keeping the character in frame the entire time (no camera cuts), on the bright neon stadium stage the colossal spiky 3D golden-green durian bodybuilder lies on the bench press pushing a heavy steel barbell loaded with weight plates straight up with a triumphant roar (strictly NO human face), speaking in native Persian (Farsi) with exact vowel pronunciation and a booming boastful male voice: «صَد و پَنْجاه کیلُوگِرَم مِثْلِ آبِ خُورْدَن! هیچ‌کَس تُویِ این سالُن نِمی‌تُونه رِکُورْدِ مَن رُو بِزَنه!» Zero on-screen subtitles.',
  },
  {
    clip: 2,
    kf: `${S15_DIR}\\part2\\keyframes\\KF_02.jpg`,
    prompt:
      '[JB2_C02] Stylized 3D CGI cartoon animation matching the exact 3D non-human fruit characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), sitting in the front row seats of the stadium the muscular 3D yellow banana gym boss in black shorts points and laughs beside the 3D green watermelon security officer (strictly NO human faces), as the yellow banana boss speaks in native Persian (Farsi) with exact vowel pronunciation and a mocking laughing male voice: «نِگاهِش کُنید، دَسْتِش حَتّی بِه میلِه‌یِ هالْتِر هَم نِمی‌رِسه! اَلآن زیرِ وَزْنه لِه می‌شه!» Zero on-screen subtitles.',
  },
  {
    clip: 3,
    kf: `${S15_DIR}\\part2\\keyframes\\KF_03.jpg`,
    prompt:
      '[JB2_C03] Stylized 3D CGI cartoon animation matching the exact 3D non-human fruit characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), on the stadium stage next to the heavy loaded bench-press rack the tiny 3D green apple janitor in a white tank top and yellow gloves speaks calmly to the 3D round orange fruit announcer in a turquoise tuxedo holding a microphone (strictly NO human faces), as the green apple janitor speaks in native Persian (Farsi) with exact vowel pronunciation and a calm deadpan young male voice: «آقایِ داوَر یِک سُؤال دارَم... فَقَط میلِه‌یِ هالْتِر رُو بُلَنْد کُنَم یا کُلِّ دَسْتْگاه رُو با هَم؟!» Zero on-screen subtitles.',
  },
  {
    clip: 4,
    kf: `${S15_DIR}\\part2\\keyframes\\KF_04.jpg`,
    prompt:
      '[JB2_C04] Stylized 3D CGI cartoon animation matching the exact 3D non-human fruit characters and outfits in the reference image, static medium two-shot keeping both characters in frame the entire time (no camera cuts), in the stadium front row the muscular 3D yellow banana gym boss jumps up from his seat shouting in wide-eyed panic while the 3D green watermelon officer smirks beside him (strictly NO human faces), as the yellow banana boss shouts in native Persian (Farsi) with exact vowel pronunciation and a panicked male voice: «صَبْر کُنید، نَذارید دَسْت بِه پایِه‌هایِ فِلِزّیِ دَسْتْگاه بِزَنه! مَن می‌دُونَم این فِسْقِلی چِقَدْر زُور داره!» Zero on-screen subtitles.',
  },
  {
    clip: 5,
    kf: `${S15_DIR}\\part2\\keyframes\\KF_05.jpg`,
    prompt:
      '[JB2_C05] Stylized 3D CGI cartoon animation matching the exact 3D non-human fruit characters and outfits in the reference image, static medium shot keeping the characters in frame the entire time (no camera cuts), on the neon stadium stage the tiny 3D green apple janitor in a white tank top and yellow gloves effortlessly lifts the ENTIRE steel bench-press frame, bench, and loaded barbell high above his head while the spiky 3D durian bodybuilder stares in shock (strictly NO human faces), as the green apple janitor speaks in native Persian (Farsi) with exact vowel pronunciation and a cheerful confident young male voice: «گُفْتَم کِه، بُلَنْد کَرْدَنِ کُلِّ دَسْتْگاه با نیمْکَتِش بَرایِ مَن اَز جابِه‌جا کَرْدَنِ سَطْلِ آب هَم راحَت‌تره!» Zero on-screen subtitles.',
  },
  {
    clip: 6,
    kf: `${S15_DIR}\\part2\\keyframes\\KF_06.jpg`,
    prompt:
      '[JB2_C06] Stylized 3D CGI cartoon animation matching the exact 3D non-human fruit characters and outfits in the reference image, static medium shot keeping the characters in frame the entire time (no camera cuts), on the stadium stage under falling gold confetti the tiny 3D green apple janitor holds a gleaming golden championship trophy in one hand and his wooden mop in the other smiling at the stunned 3D yellow banana boss (strictly NO human faces), as the green apple janitor speaks in native Persian (Farsi) with exact vowel pronunciation and a triumphant witty young male voice: «این جایْزِه‌یِ بُزُرْگ مالِ مَنه! رَئیسِ عَزیز، حالا خُودِت بِیا با این طِی کَفِ باشْگاهِت رُو تَمیز کُن!» Zero on-screen subtitles.',
  },
];

const isMain = process.argv[1] && import.meta.url.endsWith(process.argv[1].replace(/\\/g, '/').split('/').pop());
if (isMain) main().catch((err) => {
  console.error('FATAL:', err);
  process.exit(1);
});

export { BATCHES };
