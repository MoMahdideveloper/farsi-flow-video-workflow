"""Offline integrity tests, NOT live URL, checkout, audio or conversion verification."""
from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs/instagram-10-ideas'
MANIFEST = ROOT / 'pipeline/manifests/instagram_10_conversion_ideas.json'
SOURCE = DOCS / '00-kelidbox-instagram-and-catalog-context.md'
STAGE1 = DOCS / '01-opus55-10-instagram-conversion-ideas.md'
PLAYBOOK = DOCS / '02-astra-verified-conversion-playbook.md'
DATA = json.loads(MANIFEST.read_text(encoding='utf-8'))
IDEAS = DATA['ideas']
# Independent seed parser: never trust the generated verified_in_seed flag alone.
CATALOG = {
    pid: (title, int(price.replace(',', '')))
    for title, pid, price in re.findall(
        r'\*\*(.*?)\*\* \(`id: ([^`]+)`\) — از ([0-9,]+) تومان',
        SOURCE.read_text(encoding='utf-8'),
    )
}
PERSIAN = re.compile(r'[\u0621-\u063a\u0641-\u064a\u067e\u0686\u0698\u06a9\u06af\u06cc]')
EXPECTED_IDS = [f'IG10_{n:02d}' for n in range(1, 11)]
EXPECTED_KEYWORDS = ['تیزر', 'انیمیشن', 'مجری', 'تولد', 'نقاشی', 'اسلاید', 'درآمد', 'قیمت', 'بدون تبلیغ', 'گیم']


def validate_idea(idea):
    assert len(idea['shots']) == 5
    assert idea['hook_duration_sec'] == 3
    hook = idea['hook_3s_spoken_fa']
    assert PERSIAN.search(hook) and 1 <= len(hook.split()) <= 7
    assert idea['shots'][0]['spoken_fa'] == hook
    assert idea['shots'][0]['visual_prompt_flow'] == idea['hook_3s_visual']
    assert hook in idea['shots'][0]['motion_prompt_flow']
    for key in ('title_fa', 'persona_fa', 'pain_point_fa', 'psychological_trigger'):
        assert PERSIAN.search(idea[key])
    assert idea['target_segment'].strip()
    for key in ('before_fa', 'after_fa'):
        assert PERSIAN.search(idea['before_after_demo'][key])
    products = idea['featured_products']
    assert products and len({p['id'] for p in products}) == len(products)
    primary = [p for p in products if p['role'] == 'primary']
    assert len(primary) == 1 and primary[0]['id'] == idea['primary_product_id']
    assert idea['price_anchor_toman'] == primary[0]['min_price_toman']
    for product in products:
        assert product['id'] in CATALOG
        assert (product['title'], product['min_price_toman']) == CATALOG[product['id']]
        assert product['verified_in_seed'] is True
        assert product['role'] in {'primary', 'optional_or_alternative'}
        url = urlparse(product['product_url'])
        assert url.scheme == 'https' and url.netloc == 'kelidbox.com'
        assert url.path.endswith('/' + product['id'])
        assert product['url_status'] == 'candidate_unverified_route'
    cta = idea['cta_fa']
    for term in (idea['comment_keyword'], 'WELCOME10', '۱۰٪', '۱۵۰٬۰۰۰', '۱۰۰٬۰۰۰', '۴ قسط', 'ترب‌پی', 'دیجی‌پی'):
        assert term in cta
    for unsupported in ('اسنپ‌پی', 'بدون بهره', 'تحویل فوری', '۲ کلیکی'):
        assert unsupported not in cta
    assert 35 <= idea['total_duration_sec'] <= 45
    assert idea['total_duration_sec'] == sum(s['duration_sec'] for s in idea['shots'])


def test_manifest_shape_and_provenance():
    assert len(IDEAS) == 10
    assert [i['idea_id'] for i in IDEAS] == EXPECTED_IDS
    assert [i['comment_keyword'] for i in IDEAS] == EXPECTED_KEYWORDS
    assert DATA['schema_version'] == 2
    assert DATA['brand'] == 'kelidbox.com' and DATA['instagram'] == '@kelidbox_com'
    assert (ROOT / DATA['catalog_source']).resolve() == SOURCE
    assert DATA['verification']['live_checkout_checked'] is False
    assert DATA['verification']['product_urls_verified'] is False
    assert DATA['render_contract']['direct_build_compatible'] is False
    assert DATA['subtitle_style']['direction'] == 'rtl'
    assert DATA['video']['aspect'] == '9:16'
    assert DATA['video']['width'] * 16 == DATA['video']['height'] * 9


@pytest.mark.parametrize('idea', IDEAS, ids=EXPECTED_IDS)
def test_each_idea_has_seeded_products_hook_and_conversion_cta(idea):
    validate_idea(idea)


SHOTS = [(idea, n, shot) for idea in IDEAS for n, shot in enumerate(idea['shots'], 1)]


@pytest.mark.parametrize('idea,n,shot', SHOTS, ids=[s['shot_id'] for _, _, s in SHOTS])
def test_each_shot_has_flow_prompts_and_timed_rtl_subtitles(idea, n, shot):
    assert shot['shot_id'] == f"{idea['idea_id']}_S{n:02d}"
    assert shot['duration_sec'] == 8
    for key in ('visual_prompt_flow', 'motion_prompt_flow'):
        assert len(shot[key].strip()) > 30
    assert PERSIAN.search(shot['spoken_fa'])
    cues = shot['subtitles_rtl']
    assert cues
    end = 0
    for cue in cues:
        assert end <= cue['start'] < cue['end'] <= shot['duration_sec']
        assert cue['direction'] == 'rtl' and PERSIAN.search(cue['text'])
        end = cue['end']
    if n == 1:
        assert cues == [{'start': 0, 'end': 3, 'text': idea['hook_3s_spoken_fa'], 'direction': 'rtl'}]
    if n == 5:
        assert idea['comment_keyword'] in shot['spoken_fa']
        assert 'WELCOME10' in ' '.join(c['text'] for c in cues)
