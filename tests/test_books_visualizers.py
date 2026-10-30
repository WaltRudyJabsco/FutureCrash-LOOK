import pytest
import player_visuals as visuals


@pytest.mark.parametrize('name',['Orrery','Phosphor Rain'])
@pytest.mark.parametrize('size',[(1,1),(20,6),(100,30),(240,80)])
def test_new_visuals_are_bounded_deterministic_and_cycle(name,size):
    mode=visuals.NAMES.index(name)+1;width,height=size
    frame=visuals.frame(mode,width,height,1.25,True,7)
    assert len(frame)==height and all(len(row)==width for row in frame)
    assert all(ord(c)<128 for row in frame for c in row)
    assert frame==visuals.frame(mode,width,height,1.25,True,7)
    assert visuals.frame(mode,width,height,1,False,7)==visuals.frame(mode,width,height,9,False,7)
    assert mode in {visuals.active_mode(visuals.CYCLE_MODE,n*10) for n in range(visuals.CYCLE_MODE-1)}
    if width>=20:assert frame!=visuals.frame(mode,width,height,4,True,7)
