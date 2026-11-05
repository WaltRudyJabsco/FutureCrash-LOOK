import pytest
import player_visuals as visuals
import saver

@pytest.mark.parametrize('name',['Parallax Gates','Silk Current'])
@pytest.mark.parametrize('size',[(1,1),(24,8),(80,24),(240,80)])
def test_shared_visual_motion(name,size):
    mode=visuals.NAMES.index(name)+1
    assert name in saver.SCENES
    assert mode in visuals.playback_modes()
    frame=visuals.frame(mode,*size,1.5,True,23)
    assert len(frame)==size[1] and all(len(row)==size[0] for row in frame)
    assert frame==visuals.frame(mode,*size,1.5,True,23)
    assert visuals.frame(mode,*size,1,False,23)==visuals.frame(mode,*size,7,False,23)
    if size[0]>1:
        assert frame!=visuals.frame(mode,*size,8,True,23)
        assert any(c!=' ' for row in frame for c in row)
