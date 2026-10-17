"""One-time, branch-scoped build of the approved transparent SVG school icons."""
from pathlib import Path
import base64, gzip, hashlib, json, subprocess, xml.etree.ElementTree as ET
ROOT=Path.cwd()
def blob(path):
 b=Path(path).read_bytes(); return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
assert blob('index.html')=='6ba277ffaae5ee8e98e27a05f954c0c3cdf51990'
assert blob('tools/build.py')=='cf8e56b83546b4e74a0671ad0b748371e66021d0'
assert blob('src/app.css')=='0113c52fe3aafa06b67f1b17186b0abf937cd7e9'
assert blob('tools/browser_test.py')=='421dff56e5e0b2845b4c5acb7021564c36a45b5e'
schools=['Conjuration','Divination','Enchantment','Evocation','Illusion','Necromancy','Transmutation']
encoded=''.join((ROOT/'.github'/f'school-svg-{i}.txt').read_text().strip() for i in range(1,4))
svg_data=json.loads(gzip.decompress(base64.b64decode(encoded,validate=True)))
assert set(svg_data)=={s.lower()+'.svg' for s in schools}
for name,svg in svg_data.items():
 tree=ET.fromstring(svg)
 assert tree.attrib['aria-label'].lower()+'.svg'==name
 assert {e.tag.rsplit('}',1)[-1] for e in tree.iter()}=={'svg','title','path'}
 assert not any(key.endswith('href') for e in tree.iter() for key in e.attrib)
 (ROOT/name).write_text(svg,encoding='utf-8')
p=ROOT/'tools/build.py';text=p.read_text()
old="SCHOOLS={'Abjuration':'abjuration.svg',**{s:s.lower()+'.png' for s in ['Conjuration','Divination','Enchantment','Evocation','Illusion','Necromancy','Transmutation']}}"
new="SCHOOLS={s:s.lower()+'.svg' for s in ['Abjuration','Conjuration','Divination','Enchantment','Evocation','Illusion','Necromancy','Transmutation']}"
assert text.count(old)==1;text=text.replace(old,new)
text=text.replace('width="26" height="26" alt="" loading="lazy"','width="26" height="26" alt="" draggable="false" loading="lazy"')
text=text.replace('class="school-emblem" src="{icon}"','class="school-emblem" draggable="false" src="{icon}"')
p.write_text(text)
p=ROOT/'src/app.css';text=p.read_text();text+='\n/* Decorative school vectors are not interactive image thumbnails. */\n.school-emblem, .spell-link > img { pointer-events:none; user-select:none; }\n';p.write_text(text)
p=ROOT/'tools/browser_test.py';text=p.read_text()
for school in schools:text=text.replace(school.lower()+'.png',school.lower()+'.svg')
needle="        assert await page.locator('.spell-meta img').count()==0"
checks='''        # School artwork must remain vector-only, transparent, and non-interactive.
        await page.evaluate("""async files => {
          for (const file of files) {
            const image = new Image(); image.src=file; await image.decode();
            const canvas=document.createElement('canvas');canvas.width=128;canvas.height=128;
            const ctx=canvas.getContext('2d');ctx.drawImage(image,0,0,128,128);
            for (const [x,y] of [[0,0],[127,0],[0,127],[127,127]]) {
              if(ctx.getImageData(x,y,1,1).data[3]!==0) throw new Error(file+' has an opaque background');
            }
          }
        }""",list(expected.values()))
        assert await page.locator('.school-emblem,.spell-link > img').evaluate_all("es=>es.every(e=>getComputedStyle(e).pointerEvents==='none' && e.getAttribute('draggable')==='false')")
        badge=page.locator('#spell-fireball .school-emblem')
        box=await badge.bounding_box()
        await page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2)
        assert await page.evaluate("p=>document.elementFromPoint(p.x,p.y).tagName!=='IMG'",{'x':box['x']+box['width']/2,'y':box['y']+box['height']/2})
'''
assert text.count(needle)==1;text=text.replace(needle,checks+needle);p.write_text(text)
p=ROOT/'tools/verify.py';text=p.read_text();needle="    assert len(page.select('.spell-card'))==len(data)==391"
checks='''    # Match Abjuration: real path-only SVG assets, never embedded raster images.
    import xml.etree.ElementTree as ET
    school_files={s['school']:s['school'].lower()+'.svg' for s in data}
    for school,file in school_files.items():
        vector=ET.fromstring((ROOT/file).read_text())
        assert vector.attrib['aria-label']==school
        assert {e.tag.rsplit('}',1)[-1] for e in vector.iter()}=={'svg','title','path'}
        assert not any(k.endswith('href') for e in vector.iter() for k in e.attrib)
    for card in page.select('.spell-card'):
        want=school_files[card['data-school']]
        assert card.select_one('.school-emblem')['src']==want
        assert page.select_one(f'.sidebar a[href="#{card["id"]}"] img')['src']==want
'''
assert text.count(needle)==1;text=text.replace(needle,checks+needle);p.write_text(text)
subprocess.run(['python','tools/build.py'],check=True)
assert blob('favicon.svg')=='d34110ce6a1459a857c6bca849b6edb80acfe5f1'
assert blob('abjuration.svg')=='c8f42d89e5f794c4296589c380d43ed660a6285c'
assert subprocess.check_output(['git','diff','--name-only','--','data','src/app.js']).strip()==b''
print('SVG assets and static reference prepared.')
