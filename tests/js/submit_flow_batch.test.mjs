// node --test tests/js/submit_flow_batch.test.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { countIngredientChips, BATCHES, submitSingleClip, trace } from '../../scripts/submit_flow_batch.mjs';

const snap = (...children) => ({ frames: [{ frameId: 0, tree: { role: 'main', children } }] });
const cancel = (ref) => ({ tag: 'mat-icon', text: 'cancel', ref });
const img = (ref) => ({ role: 'img', name: 'Uploaded image ingredient', ref });

test('empty composer has 0 chips', () => {
  assert.equal(countIngredientChips(snap({ role: 'textbox', name: 'What do you want to create?' })), 0);
  assert.throws(() => countIngredientChips(null), /snapshot/);
});
test('one pasted keyframe = 1 chip (img + its cancel icon count once)', () => {
  assert.equal(countIngredientChips(snap(img('e1'), cancel('e2'))), 1);
  assert.equal(countIngredientChips(snap(cancel('e2'))), 1);
});
test('leftover chip + new paste = 2 chips (contamination)', () => {
  assert.equal(countIngredientChips(snap(img('e1'), cancel('e2'), img('e3'), cancel('e4'))), 2);
});
test('fop_part1..5 use their own clean KF_01..06, one per clip', () => {
  for (let p = 1; p <= 5; p++) {
    const b = BATCHES[`fop_part${p}`];
    assert.deepEqual(b.map((x) => x.clip), [1, 2, 3, 4, 5, 6], `fop_part${p} clips`);
    b.forEach((x, i) => {
      assert.ok(x.kf.endsWith(`\\part${p}\\keyframes\\KF_0${i + 1}.jpg`), `${x.kf}`);
      assert.ok(!x.noImage, 'no text-only fallback on keyframed clips');
    });
  }
});

import { mkdtempSync, writeFileSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const textbox = { role: 'textbox', name: 'What do you want to create?', ref: 'prompt' };
const start = { role: 'button', name: 'Start generation', ref: 'start' };
const clear = { role: 'button', name: 'Clear prompt', ref: 'clear' };
const prompt = 'An explicit synthetic test prompt, never sent to Flow.';
const empty = () => snap(textbox, start);
const uploaded = (n = 1, text = false) => snap(textbox, start, clear,
  ...Array.from({length: n}, (_, i) => img(`image${i}`)),
  ...(text ? [{role: 'paragraph', text: prompt}] : []));

async function exercise(t, snapshots, overrides = {}, expectedError = null) {
  const dir = mkdtempSync(join(tmpdir(), 'flow-submit-test-'));
  t.after(() => rmSync(dir, {recursive: true, force: true}));
  const kf = join(dir, 'synthetic-kf.png');
  writeFileSync(kf, 'fixture; clipboard is mocked, no keyframe rendering occurs');
  const original = readFileSync(kf);
  const tracePath = join(dir, 'flow_submission_trace.jsonl');
  const calls = [];
  let at = 0;
  const mcp = {async callTool(name, args) {
    calls.push({name, args});
    if (name === 'browser_observe_page') {
      assert.ok(at < snapshots.length, `unexpected observation ${at}`);
      return snapshots[at++];
    }
    return {};
  }};
  const ctx = {part: 'test', sleep: async () => {}, copyImage: () => {},
    trace: (event, data) => trace(event, data, tracePath)};
  const item = {clip: 1, kf, prompt, ...overrides};
  if (expectedError) await assert.rejects(submitSingleClip(mcp, item, ctx), expectedError);
  else assert.equal(await submitSingleClip(mcp, item, ctx), true);
  assert.deepEqual(readFileSync(kf), original, 'keyframe bytes changed');
  const rows = readFileSync(tracePath, 'utf8').trim().split('\n').map(JSON.parse);
  assert.ok(rows.every((r) => r.ts && r.run && r.event && r.clip === 1));
  if (expectedError) {
    assert.equal(rows.at(-1).event, 'fail');
    assert.equal(calls.filter((x) => x.name === 'browser_click' && x.args.ref === 'start').length, 0);
  }
  return {calls, rows};
}

test('guarded single-image submission writes JSONL and never mutates keyframe', async (t) => {
  const {calls, rows} = await exercise(t, [empty(), empty(), empty(), uploaded(), uploaded(1, true), empty()]);
  assert.equal(calls.filter((x) => x.name === 'browser_press_key').length, 1);
  assert.equal(calls.filter((x) => x.name === 'browser_click' && x.args.ref === 'start').length, 1);
  assert.equal(rows.find((r) => r.event === 'pre_paste_chips').chips, 0);
  assert.equal(rows.find((r) => r.event === 'paste_chips').chips, 1);
  assert.equal(rows.find((r) => r.event === 'pre_submit_chips').chips, 1);
  assert.match(rows.find((r) => r.event === 'start').kf_sha256, /^[0-9a-f]{64}$/);
  assert.equal(rows.at(-1).event, 'submitted');
});

test('leftover two ingredients blocks before paste', async (t) => {
  const {calls} = await exercise(t, [snap(textbox, img('a'), img('b'))], {}, /before paste/);
  assert.equal(calls.filter((x) => x.name === 'browser_press_key').length, 0);
});

test('two ingredients after paste blocks before generation', async (t) => {
  await exercise(t, [empty(), empty(), empty(), uploaded(2)], {}, /exactly 1 ingredient/);
});

test('lost image before Start blocks rather than text-to-video', async (t) => {
  await exercise(t, [empty(), empty(), empty(), uploaded(), uploaded(0, true)], {}, /before Start/);
});

test('delayed upload prevents a duplicate paste on retry', async (t) => {
  const {calls} = await exercise(t, [empty(), empty(), empty(),
    ...Array.from({length: 10}, empty), uploaded(), uploaded()], {}, /before every paste/);
  assert.equal(calls.filter((x) => x.name === 'browser_press_key').length, 1);
});

test('zero ingredient upload times out with no T2V fallback', async (t) => {
  await exercise(t, Array.from({length: 37}, empty), {}, /Timed out/);
});

test('missing keyframe, noImage and implicit text-only all fail before browser use', async (t) => {
  await exercise(t, [], {kf: '/nonexistent/keyframe.png'}, /not found/);
  await exercise(t, [], {noImage: true}, /refusing Text-to-Video/);
  await exercise(t, [], {kf: null}, /no keyframe/);
});

test('malformed snapshots cannot prove an empty composer', () => {
  for (const bad of [undefined, {}, {frames: []}, {frames: [{}]}]) {
    assert.throws(() => countIngredientChips(bad), /snapshot/);
  }
});

test('trace write failures fail closed instead of silently losing evidence', () => {
  assert.throws(() => trace('test', {}, '/nonexistent-parent/flow_submission_trace.jsonl'));
});
