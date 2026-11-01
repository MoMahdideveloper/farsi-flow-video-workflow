import importlib.util
import json
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / 'pipeline' / 'validate_story_pipeline.py'
spec = importlib.util.spec_from_file_location('story_validator', MODULE)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def make_manifest(tmp_path, **changes):
    data = {'episode_id': 'test', 'clips_dir': str(tmp_path), 'clips': [
        {'id': 'clip_02', 'file': 'clip_02.mp4', 'shot_type': 'dialogue',
         'generation_prompt': 'Mother says «سلام پسرم» then «خوبی امروز»',
         'subtitles': [[0, 3, 'MOM', 'سلام پسرم خوبی امروز']]}]}
    data.update(changes)
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps(data), encoding='utf-8')
    return path, data


def test_shared_speech_budget(tmp_path):
    path, data = make_manifest(tmp_path)
    data['clips'][0]['subtitles'][0][3] = 'او ' * 19
    path.write_text(json.dumps(data), encoding='utf-8')
    result = validator.validate_manifest(path)
    assert any(i['gate'] == 'GATE1_DIALOGUE_LENGTH' for i in result['issues'])


def test_reordered_clips_and_all_quotes(tmp_path):
    path, _ = make_manifest(tmp_path)
    batch = tmp_path / 'batch.mjs'
    batch.write_text("BATCHES.demo = [\n{ clip: 2, prompt: 'Mother says «سلام پسرم» then «خوبی امروز»' }\n];", encoding='utf-8')
    result = validator.validate_manifest(path, batch_mjs_path=batch, batch_key='demo')
    assert result['passed'], result['issues']


def test_manifest_prompt_is_checked_without_legacy_batch(tmp_path):
    path, data = make_manifest(tmp_path)
    data['clips'][0]['generation_prompt'] = '«اشتباه»'
    path.write_text(json.dumps(data), encoding='utf-8')
    assert not validator.validate_manifest(path)['passed']


def test_requested_asr_does_not_skip_missing_clip(tmp_path):
    path, _ = make_manifest(tmp_path)
    result = validator.validate_manifest(path, run_asr=True, whisper_model=object())
    assert any(i['code'] == 'MISSING_ASR_MEDIA' for i in result['issues'])


def test_requested_asr_requires_model(tmp_path):
    path, _ = make_manifest(tmp_path)
    assert not validator.validate_manifest(path, run_asr=True)['passed']


def test_normalization_does_not_conflate_different_persian_words():
    assert validator.normalize_fa_words('شیر سیر') == ['شیر', 'سیر']
    assert not validator.word_match('خواب', ['خواسته'])


def test_diagnostic_result_is_never_publication_approval(tmp_path):
    path, _ = make_manifest(tmp_path)
    result = validator.validate_manifest(path)
    assert result['ready_to_publish'] is False
    assert result['scope'] == 'diagnostic_checks_only'
