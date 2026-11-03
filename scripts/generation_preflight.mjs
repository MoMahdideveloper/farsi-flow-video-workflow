/** Read-only generation checks. No media transformations or content filtering. */
import { readFileSync, realpathSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const policy = JSON.parse(readFileSync(resolve(root, 'pipeline/production_policy.json'), 'utf8'));
export const speechBudget = policy.speech_budget;
const hash = value => createHash('sha256').update(value).digest('hex');
const fileHash = path => hash(readFileSync(path));
const read = path => JSON.parse(readFileSync(path, 'utf8').replace(/^\uFEFF/, ''));
function pronunciationLexicon(options = {}) {
  const bytes = readFileSync(options.lexiconPath || resolve(root, 'pipeline/pronunciation_lexicon.json'));
  const data = JSON.parse(bytes.toString('utf8').replace(/^\uFEFF/, ''));
  if (data.schema_version !== 1 || !Array.isArray(data.entries) || data.entries.some(e =>
    !e.id || !e.written || !e.spoken || normalizeDialogue(e.spoken) !== normalizeDialogue(e.written))) {
    throw new Error('Invalid pronunciation lexicon');
  }
  return { entries: data.entries, sha256: hash(bytes) };
}

function checkPronunciation(prompt, lexicon) {
  const words = dialogueFromPrompt(prompt).normalize('NFC').match(/[\p{L}\p{N}][\p{L}\p{N}\p{M}\u200c]*/gu) || [];
  for (const word of words) {
    const entry = lexicon.entries.find(e => normalizeDialogue(e.written) === normalizeDialogue(word));
    if (entry && word !== entry.spoken.normalize('NFC')) {
      throw new Error(`Pronunciation requires ${entry.spoken} in spoken dialogue; found ${word}. Subtitles may retain ${entry.written}`);
    }
  }
}
export const normalizeDialogue = text => String(text).normalize('NFC').replace(/[\u064B-\u065F\u0670]/g, '')
  .replace(/ي/g, 'ی').replace(/ك/g, 'ک').replace(/\s+/g, ' ').trim();
export const dialogueFromPrompt = prompt => [...String(prompt).matchAll(/«([^»]*)»/g)].map(m => m[1].trim()).join(' ');

export function checkSpeechBudget(prompt, duration = 8) {
  if (!Number.isFinite(duration) || duration <= 0) throw new Error('Invalid generation duration');
  const text = normalizeDialogue(dialogueFromPrompt(prompt));
  const words = text ? text.split(/\s+/).length : 0;
  const factor = duration / speechBudget.reference_duration_sec;
  if (words > Math.floor(speechBudget.max_words * factor) || text.length > Math.floor(speechBudget.max_chars * factor)) {
    throw new Error(`Dialogue exceeds timing budget (${words} words, ${text.length} characters for ${duration}s); shorten or split the shot`);
  }
}

function expanded(value, data, manifestPath) {
  let text = String(value || '');
  const vars = { MANIFEST_DIR: dirname(resolve(manifestPath)), ...(data.variables || {}) };
  for (let n = 0; n < 10; n++) text = text.replace(/\$\{([^}]+)\}/g, (m, key) => vars[key] ?? m);
  if (!text || /\$\{/.test(text)) throw new Error('Missing or unresolved asset path');
  return realpathSync(resolve(dirname(resolve(manifestPath)), text));
}

export function manifestForBatch(batch) {
  const prefixes = { eg: 'emotional', pz: 'pizza', bs: 'big_sponge', sc: 'sleep_challenge',
    ft: 'fake_tattoo', bl: 'big_lips', wv: 'weighted_vest', rw: 'red_wig', rs: 'rap_son', jb: 'janitor_bench',
    hm: 'honest_miner', pn: 'prison_swap', gj: 'golden_jacket', bm: 'bronze_mirror', mg: 'genius_magic_grapes',
    ld: 'lemon_dna_test', sb: 'blueberry_smoothie', cw: 'cowboy_wife_exchange', oc: 'orion_ceo', qt: 'quantora_ceo', ir: 'infinity_rating', hf: 'hidden_forehead' };
  let file;
  const m = batch.match(/^(\w+)_part(\d+)$/);
  if (m && prefixes[m[1]]) file = `${prefixes[m[1]]}_part${m[2]}.json`;
  if (/^part[12]$/.test(batch)) file = `strawberrina_${batch}.json`;
  const fop = batch.match(/^fop_(?:part|p)(\d+)(?:_[a-z]+)?$/);
  if (fop) file = `fruits_of_power_${Number(fop[1]) >= 6 ? 'finale_' : ''}part${fop[1]}.json`;
  const story = batch.match(/^s4_story(\d+)$/);
  const titles = ['just_studying', 'honest_wooden_boy', 'gorilla_brothers', 'sponge_twins', 'avocado_curse',
    'pink_lemonade', 'chatgpt_plus', 'torob_digipay', 'torob_30m_offer'];
  if (story && titles[Number(story[1]) - 1]) file = `story${story[1]}_${titles[Number(story[1]) - 1]}.json`;
  if (!file) throw new Error(`No manifest mapping for ${batch}; supply --manifest`);
  return resolve(root, 'pipeline/manifests', file);
}

export function itemsFromManifest(manifestPath) {
  const data = read(manifestPath);
  return (data.clips || []).map(c => ({ clip: Number(c.id.match(/(\d+)$/)?.[1]),
    id: c.id, kf: expanded(c.keyframe, data, manifestPath), prompt: c.generation_prompt,
    duration: c.generation_duration_sec || 8 }));
}

function snapshot(manifestPath, items) {
  const data = read(manifestPath), references = {}, keyframes = {};
  for (const value of [...(data.character_references || []), ...(data.location_references || [])]) {
    const path = expanded(value, data, manifestPath); references[path] = fileHash(path);
  }
  for (const item of items) {
    const id = item.id || `clip_${String(item.clip).padStart(2, '0')}`;
    const path = realpathSync(item.kf);
    keyframes[id] = { sha256: fileHash(path), prompt_sha256: hash(item.prompt || '') };
  }
  return { schema_version: 1, manifest_sha256: fileHash(manifestPath), references, keyframes };
}

export function generationTemplate(manifestPath, items, options) {
  const result = snapshot(manifestPath, items);
  result.pronunciation_lexicon_sha256 = pronunciationLexicon(options).sha256;
  const pending = () => ({ status: 'pending', reviewer: '', evidence: '', reviewed_at: '' });
  result.story = pending();
  result.speech = {};
  const data = read(manifestPath);
  for (const id of Object.keys(result.keyframes)) {
    const clip = (data.clips || []).find(c => c.id === id);
    if (clip && (clip.shot_type || 'dialogue') === 'dialogue') {
      result.speech[id] = { sha256: hash(clip.speech_text || ''), scope: 'full_sentence_vowels', ...pending() };
    }
  }
  for (const value of Object.values(result.keyframes)) Object.assign(value, pending());
  return result;
}

const documented = r => r?.status === 'pass' && ['reviewer', 'evidence', 'reviewed_at'].every(k =>
  typeof r[k] === 'string' && r[k].trim()) && Number.isFinite(Date.parse(r.reviewed_at));

export function preflightBatch(manifestPath, items, reviews, options) {
  const data = read(manifestPath);
  const lexicon = pronunciationLexicon(options);
  if (!items.length) throw new Error('No clips selected');
  if (data.fallback_to_source_on_visual_fail === true) throw new Error('Source-footage replacement prohibited; repair or regenerate the shot');
  if ((data.content_edits || []).length) throw new Error('Content-obscuring edits prohibited; no blur, masks, censorship or sanitization');
  const plan = data.story_plan;
  if (!plan?.summary || !plan?.ending || !Array.isArray(plan.required_beats) || !plan.required_beats.length) {
    throw new Error('Complete story plan and ending required before generation');
  }
  const covered = new Set((data.clips || []).flatMap(c => c.beat_ids || []));
  for (const beat of plan.required_beats) if (!covered.has(beat)) throw new Error(`Missing story beat: ${beat}`);
  if (!Array.isArray(data.character_references) || !data.character_references.length) throw new Error('Canonical character references required');
  const current = snapshot(manifestPath, items);
  if (!reviews || reviews.schema_version !== 1 || reviews.manifest_sha256 !== current.manifest_sha256 || !documented(reviews.story)) {
    throw new Error('Current documented story review required');
  }
  if (JSON.stringify(reviews.references) !== JSON.stringify(current.references)) throw new Error('Canonical references changed since review');
  if (reviews.pronunciation_lexicon_sha256 !== lexicon.sha256) throw new Error('Pronunciation lexicon changed or unreviewed; current lexicon review required');
  for (const item of items) {
    const id = item.id || `clip_${String(item.clip).padStart(2, '0')}`;
    const clip = (data.clips || []).find(c => c.id === id);
    if (!clip || !clip.story_beat) throw new Error(`Missing manifest shot/beat: ${id}`);
    if (expanded(clip.keyframe, data, manifestPath) !== realpathSync(item.kf)) throw new Error(`${id}: keyframe does not match manifest`);
    const approved = reviews.keyframes?.[id], actual = current.keyframes[id];
    if (!documented(approved) || approved.sha256 !== actual.sha256 || approved.prompt_sha256 !== actual.prompt_sha256) {
      throw new Error(`${id}: current keyframe and prompt review required; asset changed or unreviewed`);
    }
    const quoted = normalizeDialogue(dialogueFromPrompt(item.prompt));
    checkPronunciation(item.prompt, lexicon);
    const expected = normalizeDialogue((clip.subtitles || []).map(s => Array.isArray(s) ? s[3] : s.text).join(' '));
    if (quoted !== expected) throw new Error(`${id}: prompt dialogue differs from manifest`);
    if (clip.generation_prompt && clip.generation_prompt !== item.prompt) throw new Error(`${id}: full prompt differs from manifest`);
    const type = clip.shot_type || 'dialogue';
    if (!['dialogue', 'action', 'reaction'].includes(type)) throw new Error(`${id}: invalid shot_type`);
    if (type === 'dialogue' && !quoted) throw new Error(`${id}: required dialogue missing`);
    if (type !== 'dialogue' && quoted) throw new Error(`${id}: silent shot contains dialogue`);
    if (type === 'dialogue') {
      if (typeof clip.speech_text !== 'string' || !clip.speech_text.trim()) {
        throw new Error(`${id}: speech_text required; prepare vowel-marked speech separately from subtitles`);
      }
      const preserveVowels = text => text.normalize('NFC').replace(/\s+/g, ' ').trim();
      if (preserveVowels(clip.speech_text) !== preserveVowels(dialogueFromPrompt(item.prompt))) {
        throw new Error(`${id}: speech_text differs from quoted dialogue; preserve every reviewed vowel mark`);
      }
      const review = reviews.speech?.[id];
      if (!documented(review) || review.scope !== 'full_sentence_vowels' || review.sha256 !== hash(clip.speech_text)) {
        throw new Error(`${id}: current full-sentence speech vowel review required`);
      }
    }
    checkSpeechBudget(item.prompt, clip.generation_duration_sec || item.duration || 8);
  }
  return { passed: true, clips: items.map(i => i.id || i.clip), scope: 'preflight_only_not_generated_media_approval' };
}
