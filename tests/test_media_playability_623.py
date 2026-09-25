from core import intent_normalizer
from look import media_core


def test_prompt_glyph_does_not_change_selector_meaning():
    a=intent_normalizer.resolve('play any movie')
    b=intent_normalizer.resolve('› play any movie')
    assert a['status']==b['status']=='resolved'
    assert a['intent']==b['intent']


def test_playability_is_conservative_about_browser_support():
    assert media_core.media_playability('m4p','audio/mp4')['status']=='protected_or_restricted'
    assert media_core.media_playability('m4v','video/mp4')['status']=='browser_candidate'
    assert media_core.media_playability('avi','video/x-msvideo')['status']=='native_preferred'


def test_old_catalog_rows_gain_playability_when_queued():
    row={'id':'old','path':'/media/movie.avi','title':'movie','format':'avi','media_type':'video/x-msvideo'}
    queued=media_core.queue_entry(row)
    assert queued['playability']['status']=='native_preferred'
