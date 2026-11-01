import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { preflightBatch, generationTemplate, manifestForBatch } from '../../scripts/generation_preflight.mjs';

function fixture(t) {
  const dir = mkdtempSync(join(tmpdir(), 'flow-preflight-'));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  const frame = join(dir, 'frame.jpg'), ref = join(dir, 'cast.jpg');
  writeFileSync(frame, 'keyframe'); writeFileSync(ref, 'canonical cast');
  const item = { clip: 2, kf: frame, prompt: 'Father speaks: «سلام پسرم»' };
  const manifest = {
    episode_id: 'pilot', character_references: [ref],
    story_plan: { summary: 'A father reassures his son.', ending: 'The son responds.', required_beats: ['greet'] },
    clips: [{ id: 'clip_02', keyframe: frame, story_beat: 'Father greets son', beat_ids: ['greet'],
      shot_type: 'dialogue', generation_prompt: item.prompt, subtitles: [[0, 2, 'DAD', 'سلام پسرم']] }],
  };
  const file = join(dir, 'manifest.json');
  const save = () => writeFileSync(file, JSON.stringify(manifest));
  save();
  const approve = () => {
    const r = generationTemplate(file, [item]);
    for (const entry of [r.story, ...Object.values(r.keyframes)]) Object.assign(entry,
      { status: 'pass', reviewer: 'test reviewer', evidence: 'fixture inspected', reviewed_at: '2026-10-31T21:00:00Z' });
    return r;
  };
  return { file, item, manifest, frame, ref, save, approve };
}

test('maps newer production batch families', () => {
  for (const [key, name] of Object.entries({ wv_part2: 'weighted_vest_part2.json', rw_part1: 'red_wig_part1.json',
    bl_part2: 'big_lips_part2.json', ft_part1: 'fake_tattoo_part1.json' })) assert.equal(manifestForBatch(key).endsWith(name), true);
  assert.throws(() => manifestForBatch('unknown'), /manifest/i);
});
test('matches clip ID, not its reordered position', t => {
  const f = fixture(t); assert.equal(preflightBatch(f.file, [f.item], f.approve()).passed, true);
});
test('missing reviews fail before submission', t => {
  const f = fixture(t); assert.throws(() => preflightBatch(f.file, [f.item]), /review/i);
});
test('changed keyframe or canonical reference invalidates review', t => {
  const f = fixture(t), r = f.approve();
  writeFileSync(f.ref, 'new cast');
  assert.throws(() => preflightBatch(f.file, [f.item], r), /reference|changed/i);
  const r2 = f.approve(); writeFileSync(f.frame, 'new image');
  assert.throws(() => preflightBatch(f.file, [f.item], r2), /keyframe|changed/i);
});
test('mismatched dialogue and missing beat prevent generation', t => {
  const f = fixture(t); f.manifest.clips[0].subtitles[0][3] = 'different words'; f.save();
  assert.throws(() => preflightBatch(f.file, [f.item], f.approve()), /dialogue/i);
  f.manifest.clips[0].subtitles[0][3] = 'سلام پسرم'; f.manifest.story_plan.required_beats.push('ending'); f.save();
  assert.throws(() => preflightBatch(f.file, [f.item], f.approve()), /beat/i);
});
test('all dialogue quotes count toward timing budget', t => {
  const f = fixture(t); f.item.prompt = '«' + 'word '.repeat(10).trim() + '» «' + 'word '.repeat(10).trim() + '»';
  f.manifest.clips[0].generation_prompt = f.item.prompt;
  f.manifest.clips[0].subtitles[0][3] = 'word '.repeat(20).trim(); f.save();
  assert.throws(() => preflightBatch(f.file, [f.item], f.approve()), /budget/i);
});
test('silent action is valid without fabricated speech', t => {
  const f = fixture(t); f.item.prompt = 'The son reacts silently.';
  Object.assign(f.manifest.clips[0], { shot_type: 'reaction', generation_prompt: f.item.prompt, subtitles: [] }); f.save();
  assert.equal(preflightBatch(f.file, [f.item], f.approve()).passed, true);
});
test('source fallback and content-obscuring edits are rejected', t => {
  const f = fixture(t); f.manifest.fallback_to_source_on_visual_fail = true; f.save();
  assert.throws(() => preflightBatch(f.file, [f.item], f.approve()), /source|replacement/i);
  f.manifest.fallback_to_source_on_visual_fail = false; f.manifest.content_edits = ['blur']; f.save();
  assert.throws(() => preflightBatch(f.file, [f.item], f.approve()), /content|obscur/i);
});
