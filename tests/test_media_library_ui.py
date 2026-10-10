from unittest.mock import Mock
from look import media_library_ui as ui


def test_same_album_names_stay_separate_and_tracks_are_ordered():
    rows=[{'album':'Greatest Hits','artist':artist,'title':str(track),'track':track,'disc':disc,'media_type':'audio/flac'}
          for artist,disc,track in [('A',2,1),('A',1,2),('B',1,1),('A',1,1)]]
    rows.append({'album':'Greatest Hits','artist':'A','media_type':'video/mp4'})
    albums=ui.groups(rows,'album')
    assert len(albums)==2
    assert [(row['disc'],row['track']) for row in albums[0]['entries']]==[(1,1),(1,2),(2,1)]
    assert len(ui.groups(rows,'artist'))==2


def test_album_artist_keeps_compilations_together():
    rows=[{'album':'Compilation','artist':artist,'album_artist':'Various Artists'} for artist in ('A','B')]
    assert len(ui.groups(rows,'album'))==1


def test_artist_to_album_back_returns_to_artist(monkeypatch):
    rows=[{'album':'Record','artist':'Band'}];artist=ui.groups(rows,'artist')[0]
    answers=iter([artist,None,None]);monkeypatch.setattr(ui,'choose',lambda *args:next(answers))
    tracks=Mock();assert ui.browse(rows,'artist','',None,None,tracks) is None
    tracks.assert_not_called()
