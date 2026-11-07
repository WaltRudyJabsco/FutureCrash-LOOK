import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import animation_library as library
import animation_tv
import player_visuals
import saver

class Animations(unittest.TestCase):
    def test_originals_and_photosets(self):
        post={'id':123,'type':'photo','photo-caption':'<b>A &amp; B</b>','photos':[{'photo-url-1280':'https://64.media.tumblr.com/a.gif'},{'photo-url-1280':'https://64.media.tumblr.com/a.jpg'}]}
        rows=library.entries(post)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['title'],'A & B');self.assertEqual(rows[0]['id'],'123-0')
    def test_url_and_identity_boundaries(self):
        for url in ['http://64.media.tumblr.com/a.gif','https://64.media.tumblr.com.evil.test/a.gif','https://user@64.media.tumblr.com/a.gif','https://127.0.0.1/a.gif']:
            self.assertFalse(library.allowed(url))
        for value in ['../a','1/2','-1','1-2/3']:
            with self.assertRaises(ValueError):library.identity(value)
    def test_api_wrapper(self):
        self.assertEqual(library.posts(b'var tumblr_api_read = {"posts-total":2};\n')['posts-total'],2)
    def test_independent_display_lanes(self):
        rows=[({'id':str(i)},Path(str(i))) for i in range(17)]
        with patch.object(animation_tv,'available',return_value=rows):
            for times in [(0,0,0),(30,0,60),(120,90,30)]:
                picks=[animation_tv.choose(t,n,3,42)[0]['id'] for n,t in enumerate(times)]
                self.assertEqual(len(set(picks)),3)
    def test_shared_visual_catalog(self):
        for name in ['Gypsy Astronaut','Afterimage']:
            self.assertIn(name,saver.SCENES)
        for w,h in [(1,1),(80,24),(240,80)]:
            lines=player_visuals.frame(player_visuals.NAMES.index('Afterimage')+1,w,h,12)
            self.assertEqual(len(lines),h);self.assertTrue(all(len(row)==w for row in lines))
    def test_archive_download_and_resume(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(library,'root',return_value=Path(folder)),patch.object(library._stop,'wait',return_value=False):
            post={'id':1,'type':'photo','photo-url-1280':'https://64.media.tumblr.com/a.gif'}
            data=b'GIF89a-test'
            def fetch(url,api=False):return ('var tumblr_api_read = '+json.dumps({'posts-total':1,'posts':[post]})+';').encode() if api else data
            with patch.object(library,'fetch',side_effect=fetch):library.archive()
            result=library.snapshot();self.assertEqual(result['state'],'complete');self.assertEqual(result['downloaded'],1)
            with patch.object(library,'fetch',side_effect=fetch) as mocked:library.archive();self.assertEqual(mocked.call_count,1)

if __name__=='__main__':unittest.main()
