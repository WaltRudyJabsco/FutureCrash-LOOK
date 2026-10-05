from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_albert_image_attachment_and_camera_path_reaches_shared_cognition():
    html=(ROOT/'albert'/'index.html').read_text()
    server=(ROOT/'albert'/'server.py').read_text()
    assert "context:{...context,session,artifacts:attachmentIds}" in html
    assert "q||'Please inspect the attached object(s).'" in html
    assert 'accept="image/*"' in html
    assert 'capture="environment"' in html
    assert "what am I looking at?" in html
    assert 'selected_paths=list(selected_paths or [])' in server
    assert 'context.get("artifacts")' in server
