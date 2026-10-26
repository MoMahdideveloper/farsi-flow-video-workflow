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


def test_offer_terms_are_exact_and_attributed():
    coupon = DATA['coupon']
    assert {k: coupon[k] for k in ('code', 'percent', 'max_discount_toman', 'min_order_toman')} == {
        'code': 'WELCOME10', 'percent': 10, 'max_discount_toman': 150000, 'min_order_toman': 100000}
    assert 'Stage-2 brief' in coupon['source']
    installments = DATA['installments']
    assert installments['count'] == 4
    assert installments['providers'] == ['TorobPay', 'DigiPay']
    assert installments['eligibility_required'] is True
    assert installments['coupon_stacking_verified'] is False
    assert 'interest' not in installments  # no unsupported zero-interest assertion


@pytest.mark.parametrize('price,expected', [(99999, None), (100000, 10000), (380000, 38000),
                                          (1500000, 150000), (1710000, 150000), (None, None)])
def test_coupon_boundaries(price, expected):
    sys.path.insert(0, str(ROOT / 'pipeline/tools'))
    from ig10.common import coupon_saving
    assert coupon_saving(price) == expected


def test_generated_manifest_and_stage1_document_are_current():
    check = subprocess.run([sys.executable, str(ROOT / 'pipeline/tools/ig10/build_manifest.py'), '--check'],
                           cwd=ROOT, text=True, capture_output=True, check=False)
    assert check.returncode == 0, check.stdout + check.stderr
    sys.path.insert(0, str(ROOT / 'pipeline/tools'))
    from ig10.ideas_01_05 import IDEAS as first
    from ig10.ideas_06_10 import IDEAS as second
    from ig10.render_md import render
    assert STAGE1.read_text(encoding='utf-8') == render(first + second)


def test_stage1_markdown_has_all_ten_complete_ideas():
    text = STAGE1.read_text(encoding='utf-8')
    sections = re.split(r'^## Idea \d+ — ', text, flags=re.M)[1:]
    assert len(sections) == 10
    for section, idea in zip(sections, IDEAS):
        for marker in ('### (a)', '### (b)', '### (c)', '### (d)', '### (e)', '### (f)'):
            assert marker in section
        assert section.count('— image/keyframe prompt') == 5
        assert section.count('— motion + audio prompt') == 5
        assert idea['hook_3s_spoken_fa'] in section
        assert idea['primary_product_id'] in section
        assert idea['comment_keyword'] in section and 'WELCOME10' in section


def test_playbook_has_substantive_ranking_profile_calendar_and_launch_gates():
    text = PLAYBOOK.read_text(encoding='utf-8')
    assert len(text) > 15000
    ranked = re.findall(r'^\| (\d+) \| (IG10_\d{2}) /', text, re.M)
    assert len(ranked) == 10 and {i for _, i in ranked} == set(EXPECTED_IDS)
    assert [i for _, i in ranked[:3]] == ['IG10_01', 'IG10_02', 'IG10_06']
    bio = text.split('```text\n', 1)[1].split('```', 1)[0].strip()
    assert PERSIAN.search(bio) and 50 <= len(bio) <= 150
    assert len(re.findall(r'^### Pinned post [123]', text, re.M)) == 3
    for title in ('🎬 با AI چی بسازم؟', '💰 درآمد با ویدیو AI', '💳 خرید قسطی ۴ ماهه',
                  '🎁 کد تخفیف ۱۰٪', '🛡️ نماد اعتماد اینماد'):
        block = text.split('#### ' + title, 1)[1].split('\n##', 1)[0]
        assert all(f'\n{n}. ' in block for n in range(1, 5))
    calendar = re.findall(r'^\| (\d+) \| (Viral 3D|Conversion|Support|Conversion variant) \|', text, re.M)
    assert [int(n) for n, _ in calendar] == list(range(1, 31))
    assert sum(kind == 'Viral 3D' for _, kind in calendar) == 10
    assert sum(kind == 'Conversion' for _, kind in calendar) == 10
    for marker in ('RELEASE BLOCKER', 'candidate_unverified_route', 'توقف', '7-day',
                   'Launch gates', 'three-minute tutorial', 'not a promise', 'not installed'):
        assert marker in text


@pytest.mark.parametrize('idea', IDEAS, ids=EXPECTED_IDS)
def test_each_dm_contains_matching_product_offer_and_installment_steps(idea):
    text = PLAYBOOK.read_text(encoding='utf-8')
    marker = f"#### DM {idea['idea_id']} — {idea['comment_keyword']}"
    assert text.count(marker) == 1
    block = text.split(marker, 1)[1].split('\n##', 1)[0]
    product = next(p for p in idea['featured_products'] if p['role'] == 'primary')
    for term in (product['id'], product['product_url'], product['title'], 'WELCOME10', '۱۰٪',
                 '۱۵۰٬۰۰۰', '۱۰۰٬۰۰۰', '۴ قسط', 'ترب‌پی', 'دیجی‌پی', 'تسویه', 'توقف',
                 'candidate_unverified_route'):
        assert term in block
    assert len(block) > 500


@pytest.mark.parametrize('fault', ['missing_shot', 'unknown_product', 'wrong_price', 'wrong_anchor',
                                  'english_hook', 'long_hook', 'mismatched_hook', 'missing_coupon'])
def test_validation_rejects_regressions(fault):
    idea = copy.deepcopy(IDEAS[0])
    if fault == 'missing_shot': idea['shots'].pop()
    elif fault == 'unknown_product': idea['featured_products'][0]['id'] = 'not-in-seed'
    elif fault == 'wrong_price': idea['featured_products'][0]['min_price_toman'] += 1
    elif fault == 'wrong_anchor': idea['price_anchor_toman'] = 190000
    elif fault == 'english_hook': idea['hook_3s_spoken_fa'] = 'English only'
    elif fault == 'long_hook': idea['hook_3s_spoken_fa'] = 'سلام ' * 20
    elif fault == 'mismatched_hook': idea['shots'][0]['spoken_fa'] = 'یک جمله دیگر'
    elif fault == 'missing_coupon': idea['cta_fa'] = idea['cta_fa'].replace('WELCOME10', '')
    with pytest.raises(AssertionError): validate_idea(idea)
