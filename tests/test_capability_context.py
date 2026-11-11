import capability_context as c


def tool(name):return {'function':{'name':name}}


def test_capability_context_uses_actual_inventory_and_profile():
    text=c.context([tool('read_file'),tool('open_path')],[tool('read_file')],'workspace')
    assert 'Permitted tool catalog: open_path, read_file.' in text
    assert 'Tools callable in this round: read_file.' in text
    assert 'arbitrary shell execution is unavailable in this profile' in text
    assert 'not permission to execute' in text


def test_conversation_can_handoff_without_claiming_execution():
    text=c.context([tool('run_command')],[],'power',conversation=True)
    assert 'NEED_TOOLS' in text
    assert 'Tools callable in this round: none.' in text
    assert 'Do not claim success without a receipt' in text


def test_denial_detection_does_not_retry_concrete_failures():
    assert c.generic_denial('I cannot execute shell commands. I am a language model and do not have that capability.')
    for text in ['The printer is offline.', 'I cannot run arbitrary shell commands in workspace profile.',
                 'I cannot help steal credentials.', 'I am a language model integrated with file tools.']:
        assert not c.generic_denial(text)
