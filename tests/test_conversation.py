"""AI contracts tested without sending patient information to a provider."""
import json
import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'sahayak_cloud'))
import conversation
from app import create_app, PATIENT
from store import now


@pytest.fixture
def setup(tmp_path):
    app = create_app(tmp_path, False)
    app.config['TESTING'] = True
    c = app.test_client()
    c.post('/api/auth', json={'password': 'test-only-password'})
    s = app.extensions['store']
    c.patch('/api/settings', json={'ai_enabled': True, 'gemini_api_key': 'test-only-key'})
    return app, c, s


def reply(text='Hello there!', action='reply', event_id='', routine_id=''):
    return dict(response=text, action=action, event_id=event_id, routine_id=routine_id)


def test_keys_are_write_only_and_settings_validate_atomically(setup):
    _, c, s = setup
    assert c.get('/api/settings').json['ai_configured'] is True
    assert 'test-only-key' not in c.get('/api/settings').get_data(as_text=True)
    c.patch('/api/settings', json={'gemini_api_key': ''})
    assert s.get('gemini_api_key') == 'test-only-key'
    assert c.patch('/api/settings', json={'room': 'Wrong', 'ai_model': 'arbitrary'}).status_code == 400
    assert not s.get('room')
    assert c.patch('/api/settings', json={'ai_enabled': 'yes'}).status_code == 400
    assert c.patch('/api/settings', json={'gemini_api_key': 'key with spaces'}).status_code == 400


def test_general_chat_and_followups_receive_only_bounded_text_context(setup, monkeypatch):
    _, c, s = setup
    c.post('/api/people', json={'name': 'Asha', 'relationship': 'daughter', 'introduction': 'Your daughter Asha.'})
    ident = c.post('/api/routines', json={'title': 'Breakfast', 'time': '08:00', 'steps': ['Eat breakfast']}).json['id']
    c.post('/api/answers', json={'question': 'Where do I live?', 'answer': 'At home with Asha.'})
    captured = {}
    def generate(key, model, text, history, context):
        captured.update(context=context, history=history, text=text)
        return reply('She is Asha, your daughter.')
    monkeypatch.setattr(conversation, 'generate', generate)
    response = c.post('/api/query', json={'text': 'And who is she?', 'history': [
        {'role': 'user', 'content': 'Tell me about my daughter.'},
        {'role': 'assistant', 'content': 'Your daughter is Asha.'}]}).json
    assert response['engine'] == 'gemini'
    assert response['response'] == 'She is Asha, your daughter.'
    assert len(captured['history']) == 2
    context = captured['context']
    assert context['people'][0]['relationship'] == 'daughter'
    assert context['next_routine']['id'] == ident
    assert context['approved_answers'][0]['answer'] == 'At home with Asha.'
    serialized = json.dumps(context)
    for secret in ('test-only-key', s.get('device_token'), s.get('session_key'), 'password_hash', 'embedding'):
        assert secret not in serialized


def test_sighting_links_are_validated_and_keep_evidence(setup, monkeypatch):
    _, c, s = setup
    stamp = now()
    s.execute('''INSERT INTO events(id,patient_id,first_seen,last_seen,people,objects,detections,source)
        VALUES(?,?,?,?,?,?,?,?)''', ('e1', PATIENT, stamp, stamp, '[]', '["cell phone"]', '[]', 'camera'))
    monkeypatch.setattr(conversation, 'generate', lambda *args: reply('A phone was recorded earlier.', 'memory', 'e1'))
    result = c.post('/api/query', json={'text': 'Any sign of my mobile?'}).json
    assert result['event']['id'] == 'e1'
    monkeypatch.setattr(conversation, 'generate', lambda *args: reply('Imaginary memory', 'memory', 'unknown'))
    result = c.post('/api/query', json={'text': 'Have you seen my phone?'}).json
    assert result['engine'] == 'local'
    assert result['event']['id'] == 'e1'
    assert 'Imaginary' not in result['response']
    assert result['ai_notice']


def test_api_failure_keeps_schedule_and_does_not_trigger_false_alert(setup, monkeypatch):
    _, c, s = setup
    c.post('/api/routines', json={'title': 'Walk', 'time': '17:00', 'steps': ['Wear shoes']})
    def fail(*args):
        raise conversation.ConversationUnavailable('Usage limit reached.')
    monkeypatch.setattr(conversation, 'generate', fail)
    result = c.post('/api/query', json={'text': 'What is my schedule?'}).json
    assert result['engine'] == 'local' and 'Walk' in result['response']
    c.post('/api/query', json={'text': 'Help me understand photosynthesis'})
    c.post('/api/query', json={'text': 'I do not need help'})
    assert not s.rows('SELECT * FROM help')
    result = c.post('/api/query', json={'text': 'Sahayak help'}).json
    assert result['status'] == 'help'
    assert len(s.rows('SELECT * FROM help')) == 1


def test_help_action_uses_server_delivery_state_not_model_claim(setup, monkeypatch):
    _, c, s = setup
    monkeypatch.setattr(conversation, 'generate', lambda *args: reply('Alert delivered!', 'help'))
    result = c.post('/api/query', json={'text': 'Please ask my caretaker to check on me'}).json
    assert result['status'] == 'help'
    assert 'could not be queued' in result['response']
    assert 'delivered!' not in result['response']
    assert len(s.rows('SELECT * FROM help')) == 1


def test_invalid_history_rejected_before_api_call(setup, monkeypatch):
    _, c, _ = setup
    monkeypatch.setattr(conversation, 'generate', lambda *args: pytest.fail('must not call provider'))
    for history in ({}, [{'role': 'system', 'content': 'bad'}], [{'role': 'user', 'content': 'x'}] * 13):
        assert c.post('/api/query', json={'text': 'Hi', 'history': history}).status_code == 400
    assert c.post('/api/query', json={'text': 'x' * 2001}).status_code == 400


def test_gateway_request_and_actual_rest_response_shape(monkeypatch):
    def post(url, **kwargs):
        assert url == 'https://generativelanguage.googleapis.com/v1beta/interactions'
        assert kwargs['headers']['x-goog-api-key'] == 'test-only'
        payload = kwargs['json']
        assert payload['store'] is False
        assert payload['generation_config']['thinking_level'] == 'low'
        assert payload['response_format']['mime_type'] == 'application/json'
        class Response:
            status_code = 200
            def json(self):
                return {'status': 'completed', 'steps': [{'type': 'model_output', 'content': [
                    {'type': 'text', 'text': json.dumps(reply('The answer is four.'))}]}]}
        return Response()
    monkeypatch.setattr(conversation.requests, 'post', post)
    result = conversation.generate('test-only', conversation.MODELS[0], 'What is 2+2?', [], {})
    assert result['response'] == 'The answer is four.'


@pytest.mark.parametrize('status', [401, 403, 429, 503])
def test_gateway_errors_never_expose_provider_payload(monkeypatch, status):
    class Response:
        status_code = status
    monkeypatch.setattr(conversation.requests, 'post', lambda *args, **kwargs: Response())
    with pytest.raises(conversation.ConversationUnavailable) as exc:
        conversation.generate('secret-key', conversation.MODELS[0], 'hello', [], {})
    assert 'secret-key' not in str(exc.value)


def test_gateway_timeout_and_malformed_reply(monkeypatch):
    def fail(*args, **kwargs):
        raise requests.Timeout('Raw secret URL or response')
    monkeypatch.setattr(conversation.requests, 'post', fail)
    with pytest.raises(conversation.ConversationUnavailable, match='could not connect'):
        conversation.generate('test-only', conversation.MODELS[0], 'hello', [], {})
    class Response:
        status_code = 200
        def json(self):
            return {'output_text': '{invalid'}
    monkeypatch.setattr(conversation.requests, 'post', lambda *args, **kwargs: Response())
    with pytest.raises(conversation.ConversationUnavailable, match='reliable reply'):
        conversation.generate('test-only', conversation.MODELS[0], 'hello', [], {})
