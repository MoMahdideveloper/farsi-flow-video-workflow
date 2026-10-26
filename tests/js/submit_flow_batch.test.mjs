// node --test tests/js/submit_flow_batch.test.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { countIngredientChips, BATCHES } from '../../scripts/submit_flow_batch.mjs';

const snap = (...children) => ({ frames: [{ frameId: 0, tree: { role: 'main', children } }] });
const cancel = (ref) => ({ tag: 'mat-icon', text: 'cancel', ref });
const img = (ref) => ({ role: 'img', name: 'Uploaded image ingredient', ref });

test('empty composer has 0 chips', () => {
  assert.equal(countIngredientChips(snap({ role: 'textbox', name: 'What do you want to create?' })), 0);
  assert.equal(countIngredientChips(null), 0);
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
