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
import { appendFileSync, existsSync, readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';

// Every submission step is appended here (one JSON object per line).
const TRACE_PATH = process.env.FLOW_TRACE_PATH || 'flow_submission_trace.jsonl';
let RUN_ID = new Date().toISOString();

let PROFILE_ID = process.env.FLOW_PROFILE_ID || '731e6d16-b95b-480f-a245-cb443411400d';
let TAB_ID = Number(process.env.FLOW_TAB_ID || 612095035);
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

BATCHES.fop_rem123 = [
  BATCHES.fop_part1[0],
  BATCHES.fop_part2[4],
  BATCHES.fop_part3[1],
  BATCHES.fop_part3[3],
  BATCHES.fop_part3[5],
];

BATCHES.fop_final_p1 = [
  BATCHES.fop_part3[5],
  BATCHES.fop_part5[0],
  BATCHES.fop_part5[1],
  BATCHES.fop_part5[2],
];

BATCHES.fop_final_p2 = [
  BATCHES.fop_part5[3],
  BATCHES.fop_part5[4],
  BATCHES.fop_part5[5],
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
    const found = nodes.find(predicate);
    if (found) return found;
  }
  return null;
}

/**
 * Count image "ingredient" chips currently attached to the Flow composer.
 * A chip is an attached image tile: its remove control is a `cancel` mat-icon
 * (or a button named Remove/Delete image / حذف تصویر), or an <img>/image node
 * inside the composer whose name mentions ingredient/uploaded image.
 * Returns max(#thumbnails, #remove controls) so one chip is counted once.
 */
export function countIngredientChips(snapshot) {
  // Each attached image chip exposes a thumbnail and/or a remove ("cancel") control.
  // Count both kinds separately and take the larger, so a chip is never double-counted.
  if (!Array.isArray(snapshot?.frames) || snapshot.frames.length === 0 ||
      snapshot.frames.some((f) => !f.tree || typeof f.tree !== 'object')) {
    throw new Error('Cannot count ingredients: missing or malformed page snapshot');
  }
  let imgs = 0;
  let removers = 0;
  for (const frame of snapshot?.frames || []) {
    for (const n of flattenNodes(frame.tree)) {
      const name = String(n.name || '');
      if ((n.role === 'img' || n.tag === 'img') && /ingredient|uploaded image|تصویر بارگذاری/i.test(name)) imgs++;
      else if (
        (n.tag === 'mat-icon' && String(n.text || '').trim() === 'cancel') ||
        (n.role === 'button' && /^(remove|delete) (image|ingredient)|حذف (تصویر|عکس)/i.test(name))
      )
        removers++;
    }
  }
  return Math.max(imgs, removers);
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
  (n.name === 'What do you want to create?' || n.name === 'چه چیزی می‌خواهید بسازید؟');

const isClearButton = (n) =>
  n.role === 'button' &&
  (n.name === 'Clear prompt' || n.name === 'پاک کردن پیام‌واره');

const isStartButton = (n) =>
  n.role === 'button' &&
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
  record('start', { ...base, mode: skipImage ? 'text_to_video_explicit' : 'image_to_video', prompt_chars: item.prompt.length });
  console.log(`\n=== Submitting Clip ${item.clip}: ${skipImage ? '(TEXT-ONLY, explicit)' : item.kf} ===`);
  if (!skipImage) {
    copyImage(item.kf);
    record('clipboard_image', base);
    console.log(`  [1/5] Copied image to clipboard: ${item.kf}`);
  }

  // Ensure the composer is 100% empty (no prompt, NO leftover ingredient chips)
  let snap = null;
  let chipsBefore = -1;
  for (let clearTry = 1; clearTry <= 6; clearTry++) {
    snap = await mcp.callTool('browser_observe_page', {
      profileId: PROFILE_ID,
      tabId: TAB_ID,
    });
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

      for (let attempt = 1; attempt <= 10; attempt++) {
        await pause(1500);
        const s = await mcp.callTool('browser_observe_page', {
          profileId: PROFILE_ID,
          tabId: TAB_ID,
        });
        const clearBtn = findNode(s, isClearButton);
        const cancelIcon = findNode(s, (n) => n.tag === 'mat-icon' && n.text === 'cancel');
        const chips = countIngredientChips(s);
        if ((clearBtn || cancelIcon) && chips >= 1) {
          record('paste_chips', { ...base, try: pasteTry, attempt, chips });
          if (chips !== 1) {
            throw new Error(`Clip ${item.clip}: expected exactly 1 ingredient chip after paste, found ${chips}`);
          }
          uploadedSnap = s;
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

    await mcp.callTool('browser_type', {
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

  for (let submitTry = 1; submitTry <= 3; submitTry++) {
    const curSnap =
      submitTry === 1
        ? readySnap
        : await mcp.callTool('browser_observe_page', {
            profileId: PROFILE_ID,
            tabId: TAB_ID,
          });
    {
      const chipsNow = countIngredientChips(curSnap);
      record('pre_submit_chips', { ...base, try: submitTry, chips: chipsNow });
      const requiredChips = skipImage ? 0 : 1;
      if (chipsNow !== requiredChips) {
        throw new Error(`Clip ${item.clip}: ${chipsNow} ingredient chips right before Start (need exactly ${requiredChips})`);
      }
    }
    const startBtn = findNode(curSnap, isStartButton);
    if (!startBtn) {
      throw new Error('Could not find "Start generation" button');
    }

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
    console.log(`  [!] Prompt still has Clear button after click (try ${submitTry}), retrying...`);
  }
  record('fail', { ...base, reason: 'submission not confirmed after 3 tries' });
  throw new Error(`Clip ${item.clip}: submission not confirmed`);
}

export async function submitSingleClip(mcp, item, ctx = {}) {
  try {
    return await submitSingleClipImpl(mcp, item, ctx);
  } catch (error) {
    (ctx.trace || trace)('fail', { part: ctx.part, clip: item.clip, reason: error.message });
    throw error;
  }
}

async function main() {
  const argv = process.argv.slice(2);
  let part = 'part1';
  let clipFilter = null;
  let startClip = 1;
  let endClip = 999;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--part' && argv[i + 1]) part = argv[++i];
    else if (argv[i] === '--clip' && argv[i + 1]) clipFilter = Number(argv[++i]);
    else if (argv[i] === '--start-clip' && argv[i + 1]) startClip = Number(argv[++i]);
    else if (argv[i] === '--end-clip' && argv[i + 1]) endClip = Number(argv[++i]);
    else if (argv[i] === '--profile' && argv[i + 1]) PROFILE_ID = argv[++i];
    else if (argv[i] === '--tab' && argv[i + 1]) TAB_ID = Number(argv[++i]);
  }

  const batch = BATCHES[part];
  if (!batch) throw new Error(`Unknown --part ${part}`);
  const items = clipFilter
    ? batch.filter((x) => x.clip === clipFilter)
    : batch.filter((x) => x.clip >= startClip && x.clip <= endClip);

  RUN_ID = `${part}-${new Date().toISOString()}`;
  trace('batch_start', { part, clips: items.map((x) => x.clip), trace_path: TRACE_PATH });
  const mcp = new McpClient();
  try {
    await mcp.init();
    // Clean any failed tiles at the top of the list before submitting
    for (let round = 0; round < 6; round++) {
      const snap = await mcp.callTool('browser_observe_page', {
        profileId: PROFILE_ID,
        tabId: TAB_ID,
      });
      const delBtn = findNode(
        snap,
        (n) => n.ref && n.role === 'button' && (n.name === 'Delete' || n.name === 'حذف')
      );
      if (!delBtn) break;
      console.log(`  [clean] Deleting failed tile [${delBtn.ref}] (${delBtn.name})...`);
      await mcp.callTool('browser_click', {
        profileId: PROFILE_ID,
        tabId: TAB_ID,
        ref: delBtn.ref,
      });
      await sleep(1000);
    }
    for (const item of items) {
      await submitSingleClip(mcp, item, { part });
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

const isMain = process.argv[1] && import.meta.url.endsWith(process.argv[1].replace(/\\/g, '/').split('/').pop());
if (isMain) main().catch((err) => {
  console.error('FATAL:', err);
  process.exit(1);
});

export { BATCHES };
