#!/usr/bin/env python3
import hashlib, json, math, shutil, struct, urllib.request, wave, zipfile, zlib
import xml.etree.ElementTree as ET
from pathlib import Path
import repo_release

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'public'
STAGE = ROOT / '.v12_stage' / 'DragonMax_V12_Unified_Build_Content'
RELEASE_VERSION = '4.5.0'
BUILD = OUT / 'builds' / f'DragonMax_V12_Unified_Build_Content-{RELEASE_VERSION}.zip'
IDEAL_SIZE = 280 * 1024 * 1024
SOFT_MAX = 320 * 1024 * 1024
INSTALL_PROTOCOL = 4
RUNTIME_ROOTS = ('addons', 'userdata', 'artwork', 'audio', 'startup', 'dragonmax')
DEV_DIR_NAMES = {'.git', '.github', '.idea', '.vscode', '__pycache__', 'tests', 'test', 'docs', 'doc'}
DEV_FILE_SUFFIXES = ('.pyc', '.pyo', '.log', '.tmp', '.old')
CRITICAL_ADDONS = {'skin.auramod', 'service.dragonmax.voice'}
CORE_DEP_PREFIXES = ('xbmc.', 'kodi.')
AURAMOD_COMMIT = '8038ef9b2575910b3f155c3256d3b5669c887e39'
AURAMOD_MIN_VERSION = (2, 0, 4)
AURAMOD_MIN_GUI = (5, 17, 0)
BOOTSTRAP_PACKAGES = {
    'repository.auramod.aio': 'https://raw.githubusercontent.com/SerpentDrago/repository.auramod.aio/main/repo/omega/zips/repository.auramod.aio/repository.auramod.aio-1.2.zip',
    'repository.jurialmunkey': 'https://raw.githubusercontent.com/SerpentDrago/repository.auramod.aio/main/repo/omega/zips/repository.jurialmunkey/repository.jurialmunkey-3.4.zip',
    'repository.marcelveldt': 'https://raw.githubusercontent.com/SerpentDrago/repository.auramod.aio/main/repo/omega/zips/repository.marcelveldt/repository.marcelveldt-1.0.3.zip',
    'script.colorbox': 'https://raw.githubusercontent.com/SerpentDrago/repository.auramod.aio/main/repo/omega/zips/script.colorbox/script.colorbox-2.0.8.zip',
}
DEPENDENCY_INDEX_URLS = (
    'https://raw.githubusercontent.com/SerpentDrago/repository.auramod.aio/main/repo/omega/zips/addons.xml',
    'https://raw.githubusercontent.com/jurialmunkey/repository.jurialmunkey/master/omega/zips/addons.xml',
    'https://raw.githubusercontent.com/kodi-community-addons/repository.marcelveldt/master/matrix/addons.xml',
)

REALMS = [
    ('dragon_order','Dragon Order',(160,55,20)),
    ('arcane_dominion','Arcane Dominion',(70,45,150)),
    ('crimson_court','Crimson Court',(125,10,30)),
    ('temple_guardians','Temple Guardians',(35,95,70)),
    ('champion_guild','Champion Guild',(35,75,135)),
    ('office_consortium','Office Consortium',(30,50,70)),
]

UNSAFE_STAGE_DIRS = [
    Path('userdata/Database'), Path('userdata/Thumbnails'), Path('userdata/temp'),
    Path('addons/packages'), Path('temp'), Path('cache'), Path('dragonmax_backups')
]
UNSAFE_STAGE_FILES = {Path('userdata/guisettings.xml')}


def clean():
    shutil.rmtree(OUT, ignore_errors=True)
    shutil.rmtree(STAGE.parent, ignore_errors=True)
    (OUT/'builds').mkdir(parents=True, exist_ok=True)
    STAGE.mkdir(parents=True, exist_ok=True)


def fetch(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={'User-Agent':f'DragonMax-V12-Builder/{RELEASE_VERSION}'})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest,'wb') as f:
        shutil.copyfileobj(r,f)


def fetch_text(url):
    req = urllib.request.Request(url, headers={'User-Agent':f'DragonMax-V12-Builder/{RELEASE_VERSION}'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode('utf-8')


def block_noise(seed, bx, by, limit):
    n = (seed * 2654435761 + bx * 2246822519 + by * 3266489917) & 0xffffffff
    n ^= n >> 13; n = (n * 1274126177) & 0xffffffff; n ^= n >> 16
    return n % max(1, limit)


def png_bytes(w,h,tint,seed,detail='normal'):
    raw = bytearray(); tr,tg,tb = tint
    block = 8 if detail == 'normal' else 4; limit = 36 if detail == 'normal' else 72
    blocks_x = (w + block - 1) // block
    for y in range(h):
        raw.append(0); by = y // block
        row_noise = [block_noise(seed, bx, by, limit) for bx in range(blocks_x)]
        for x in range(w):
            noise = row_noise[x // block]
            wavev = int(22 * math.sin((x + seed % 97) / 47.0) + 16 * math.cos((y + seed % 53) / 61.0))
            fade = int(30 * y / max(1,h-1))
            raw.extend((max(0,min(255,tr + noise + wavev + fade)), max(0,min(255,tg + noise//2 + wavev//2 + fade//2)), max(0,min(255,tb + noise//3 - wavev//3))))
    def chunk(tag,data):
        return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(bytes(raw),7))+chunk(b'IEND',b'')


def write_png(path,w,h,tint,seed,detail='normal'):
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(png_bytes(w,h,tint,seed,detail))


def write_wav(path,dur,freqs,vol=.25,sr=44100):
    path.parent.mkdir(parents=True, exist_ok=True); n=int(dur*sr)
    with wave.open(str(path),'w') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr); frames=bytearray()
        for i in range(n):
            t=i/sr; env=min(1.0,t/max(.05,dur*.2))*max(0.0,min(1.0,(dur-t)/max(.05,dur*.25)))
            s=sum(math.sin(2*math.pi*f*t) for f in freqs)/len(freqs)
            frames += struct.pack('<h', int(max(-1,min(1,s*env*vol))*32767))
        wf.writeframes(frames)


def locate_legacy_runtime_root(tmp):
    candidates=[]
    for p in [tmp] + [d for d in tmp.rglob('*') if d.is_dir()]:
        score=sum((p/name).exists() for name in RUNTIME_ROOTS)
        if score: candidates.append((-score, len(p.relative_to(tmp).parts), p))
    if not candidates: return None
    candidates.sort(key=lambda x:(x[0],x[1])); return candidates[0][2]


def copy_legacy():
    legacy = ROOT/'DragonMax_V9_2_Build_Content-1.9.2.zip'
    if not legacy.exists(): return
    tmp = STAGE.parent/'legacy'; tmp.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(legacy) as z: z.extractall(tmp)
    runtime_root=locate_legacy_runtime_root(tmp)
    if runtime_root is None: return
    for top in RUNTIME_ROOTS:
        src=runtime_root/top
        if not src.exists(): continue
        dst=STAGE/top
        if src.is_dir(): shutil.copytree(src,dst,dirs_exist_ok=True,copy_function=shutil.copyfile)
        else: dst.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(src,dst)


def reset_userdata():
    shutil.rmtree(STAGE/'userdata', ignore_errors=True)


def prune_development_debris():
    addons=STAGE/'addons'
    if not addons.exists(): return
    for d in sorted([p for p in addons.rglob('*') if p.is_dir()], key=lambda p:len(p.parts), reverse=True):
        if d.name.lower() in DEV_DIR_NAMES: shutil.rmtree(d,ignore_errors=True)
    for p in list(addons.rglob('*')):
        if p.is_file() and (p.suffix.lower() in DEV_FILE_SUFFIXES or p.name.lower() in ('thumbs.db','.ds_store')):
            try:p.unlink()
            except OSError:pass


def addon_metadata(addon_dir):
    xml=addon_dir/'addon.xml'
    if not xml.exists(): return None
    root=ET.parse(xml).getroot()
    imports=[]
    req=root.find('requires')
    if req is not None:
        for item in req.findall('import'):
            imports.append((item.attrib.get('addon',''), item.attrib.get('version',''), item.attrib.get('optional','').lower()=='true'))
    return {'id':root.attrib.get('id',''), 'version':root.attrib.get('version',''), 'imports':imports}


def version_tuple(v):
    out=[]
    for part in str(v).split('.'):
        try: out.append(int(part))
        except ValueError: break
    return tuple(out or [0])


def prune_kodi21_incompatible_addons():
    addons=STAGE/'addons'
    if not addons.exists(): return
    for d in list(addons.iterdir()):
        if not d.is_dir() or d.name in CRITICAL_ADDONS or d.name in BOOTSTRAP_PACKAGES: continue
        try: meta=addon_metadata(d)
        except Exception:
            shutil.rmtree(d,ignore_errors=True); continue
        if not meta: continue
        py=[x for x in meta['imports'] if x[0]=='xbmc.python' and not x[2]]
        if py and version_tuple(py[0][1]) < (3,0,0):
            print('INFO pruning Python-2-era addon for Kodi 21:', d.name)
            shutil.rmtree(d,ignore_errors=True)


def sanitize_stage():
    for rel in UNSAFE_STAGE_DIRS: shutil.rmtree(STAGE/rel, ignore_errors=True)
    for rel in UNSAFE_STAGE_FILES:
        try:(STAGE/rel).unlink()
        except FileNotFoundError:pass
    prune_development_debris(); prune_kodi21_incompatible_addons()
    for p in list(STAGE.rglob('*')):
        if not p.is_file(): continue
        name=p.name.lower()
        if name.endswith(DEV_FILE_SUFFIXES) or name in ('kodi.log','kodi.old.log'):
            try:p.unlink()
            except OSError:pass


def extract_addon_zip(archive, expected_id):
    tmp=STAGE.parent/('bootstrap_'+expected_id.replace('.','_'))
    shutil.rmtree(tmp,ignore_errors=True); tmp.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        bad=z.testzip()
        if bad: raise RuntimeError(f'Corrupt bootstrap package {expected_id}: {bad}')
        z.extractall(tmp)
    candidates=[]
    for p in [tmp] + [d for d in tmp.rglob('*') if d.is_dir()]:
        xml=p/'addon.xml'
        if xml.exists():
            try:
                if ET.parse(xml).getroot().attrib.get('id') == expected_id: candidates.append(p)
            except Exception: pass
    if not candidates: raise RuntimeError('Bootstrap ZIP did not contain expected addon '+expected_id)
    candidates.sort(key=lambda p:len(p.parts)); src=candidates[0]; dst=STAGE/'addons'/expected_id
    shutil.rmtree(dst,ignore_errors=True); shutil.copytree(src,dst,copy_function=shutil.copyfile)


def install_auramod():
    arc=STAGE.parent/'auramod_omega.zip'
    fetch(f'https://codeload.github.com/SerpentDrago/skin.auramod/zip/{AURAMOD_COMMIT}',arc)
    tmp=STAGE.parent/'auramod_extract'; shutil.rmtree(tmp,ignore_errors=True); tmp.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(arc) as z: z.extractall(tmp)
    roots=[p for p in tmp.iterdir() if p.is_dir()]
    if not roots: raise RuntimeError('AuraMOD Omega archive extracted without a root folder')
    dst=STAGE/'addons'/'skin.auramod'; shutil.rmtree(dst,ignore_errors=True); shutil.copytree(roots[0],dst,copy_function=shutil.copyfile)
    meta=addon_metadata(dst)
    if not meta or version_tuple(meta['version']) < AURAMOD_MIN_VERSION: raise RuntimeError('AuraMOD source is not Omega 2.0.4+')
    gui=[version_tuple(ver) for dep,ver,opt in meta['imports'] if dep=='xbmc.gui' and not opt]
    if not gui or gui[0] < AURAMOD_MIN_GUI: raise RuntimeError('AuraMOD source does not declare Kodi 21 xbmc.gui 5.17+')
    prune_development_debris()
    print('AuraMOD Omega validated:',meta['version'],'commit',AURAMOD_COMMIT)


def install_bootstrap_addons():
    for addon_id,url in BOOTSTRAP_PACKAGES.items():
        arc=STAGE.parent/(addon_id+'.zip'); fetch(url,arc); extract_addon_zip(arc,addon_id)
    print('Dependency bootstrap addons staged:',', '.join(sorted(BOOTSTRAP_PACKAGES)))


def install_dragonmax_addons():
    src = ROOT/'v12_addons'
    if not src.exists(): raise RuntimeError('v12_addons source directory missing')
    for addon in src.iterdir():
        if addon.is_dir():
            dst = STAGE/'addons'/addon.name; shutil.rmtree(dst, ignore_errors=True); shutil.copytree(addon, dst, copy_function=shutil.copyfile)


def generate_media():
    art=STAGE/'artwork'; audio=STAGE/'audio'; startup=STAGE/'startup'; idx=0
    for slug,name,tint in REALMS:
        for i in range(8): idx+=1; write_png(art/'wallpapers'/slug/f'{slug}_{i+1:02d}.png',1280,720,tint,10000+idx)
        for i in range(3): idx+=1; write_png(art/'hero_banners'/slug/f'{slug}_hero_{i+1:02d}.png',1280,480,tint,20000+idx)
        write_png(art/'realm_crests'/f'{slug}_crest.png',512,512,tint,30000+idx)
        for i,level in enumerate(['novice','adept','master','champion','legend']): write_png(art/'achievement_badges'/slug/f'{slug}_{level}.png',320,320,tint,40000+idx*10+i)
    for i in range(10): slug,name,tint=REALMS[i%6]; write_png(art/'loading_screens'/f'loading_{i+1:02d}.png',1280,720,tint,50000+i)
    for i,(slug,name,tint) in enumerate(REALMS):
        write_png(art/'portal_graphics'/f'{slug}_portal.png',1024,576,tint,60000+i); write_png(art/'wizard_graphics'/f'{slug}_wizard.png',1024,576,tint,61000+i)
    write_png(startup/'dragonmax_static_splash.png',1600,900,REALMS[0][2],70000)
    write_wav(audio/'startup_theme.wav',8.0,(55,110,165,220),.26); write_wav(audio/'portal_open.wav',2.0,(140,280,560),.22); write_wav(audio/'achievement.wav',1.4,(523,659,784,1046),.20)
    write_wav(audio/'ui_click.wav',.16,(900,1300),.17); write_wav(audio/'ui_back.wav',.22,(420,260),.17); write_wav(audio/'ui_select.wav',.30,(660,880,1320),.17); write_wav(audio/'error.wav',.45,(180,120),.18)
    for i,(slug,name,tint) in enumerate(REALMS): write_wav(audio/f'realm_change_{slug}.wav',1.0,(140+i*20,280+i*25,560+i*30),.18)


def generate_userdata():
    u=STAGE/'userdata'; cfg=STAGE/'dragonmax'/'config'
    for p in [u/'addon_data'/'skin.auramod',u/'addon_data'/'script.autowidget',u/'addon_data'/'service.dragonmax.voice',u/'keymaps',cfg]: p.mkdir(parents=True,exist_ok=True)
    menus={'layout':'netflix_first','home':['Dragon Portal','Continue Watching','Movies','TV Shows','Anime Universe','Martial Arts','Champion Guild','Office Consortium','Settings'],'portal':['Dragon Voice','Memory','Self Repair','Switch Realm','Resume Last Played','Audio Profile','Performance Mode','Maintenance','Backups','Updates','System Health','Admin']}
    widgets={'max_home_widgets':6,'refresh_hours':6,'rows':['Continue Watching','Trending Movies','Trending TV','Anime Universe','Martial Arts','Favorites']}
    realms={'realms':[{'id':s,'name':n} for s,n,t in REALMS]}
    perf={'default':'balanced','profiles':{'maximum_speed':{'widget_limit':4,'animated_backgrounds':False},'balanced':{'widget_limit':6,'animated_backgrounds':False},'visual_quality':{'widget_limit':6,'animated_backgrounds':True}}}
    voice={'enabled':True,'bridge_port':8765,'wake_phrase':'Dragon','external_ai_enabled':False,'destructive_confirmation_required':True,'manual_fallback':True,'memory_enabled':True,'self_repair_enabled':True,'self_repair_policy':'allowlisted_reversible_only'}
    for p,data in [(cfg/'menus.json',menus),(cfg/'widgets.json',widgets),(cfg/'realms.json',realms),(cfg/'performance.json',perf),(cfg/'voice.json',voice),(u/'addon_data'/'skin.auramod'/'dragonmax_skin_base.json',{'theme':'Dragon Order','portal_enabled':True,'voice_enabled':True}),(u/'addon_data'/'script.autowidget'/'dragonmax_groups.json',widgets)]: p.write_text(json.dumps(data,indent=2),encoding='utf-8')
    (u/'advancedsettings.xml').write_text('<advancedsettings><cache><buffermode>1</buffermode><memorysize>139460608</memorysize><readfactor>4.0</readfactor></cache></advancedsettings>',encoding='utf-8')
    (u/'keymaps'/'dragonmax.xml').write_text('<keymap><global><keyboard><menu>ActivateWindow(Programs,plugin.program.dragonmaxwizard,return)</menu></keyboard></global></keymap>',encoding='utf-8')


def manifest():
    data={'name':'DragonMax V12 Unified','version':RELEASE_VERSION,'install_protocol':INSTALL_PROTOCOL,'merge_policy':'V9.2 runtime assets + V11/V12 overlay; device userdata and dev metadata discarded','target_device':'Fire TV Stick 4K Max','auramod':{'version':'2.0.4+','commit':AURAMOD_COMMIT,'target':'Kodi 21 Omega'},'realms':[n for s,n,t in REALMS],'release_priority':['quality','stability','smooth_use','visual_consistency','package_size'],'capabilities':['Dragon Voice','Dragon AI intent engine','persistent explicit memory','recent conversation context','allow-listed reversible self-repair','repair history','authenticated LAN command bridge','safe confirmations','remote-control fallback']}
    (STAGE/'dragonmax_manifest.json').write_text(json.dumps(data,indent=2),encoding='utf-8')


def payload_file_manifest():
    entries=[]
    for p in sorted(STAGE.rglob('*')):
        if p.is_file() and p.name != 'install_manifest.json':
            rel=str(p.relative_to(STAGE)).replace('\\','/'); h=hashlib.sha256()
            with open(p,'rb') as f:
                for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
            entries.append({'path':rel,'size':p.stat().st_size,'sha256':h.hexdigest()})
    target=STAGE/'dragonmax'/'install_manifest.json'; target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps({'schema':3,'install_protocol':INSTALL_PROTOCOL,'version':RELEASE_VERSION,'files':entries},indent=2),encoding='utf-8')


def dependency_indexes():
    available=set()
    for url in DEPENDENCY_INDEX_URLS:
        try:
            root=ET.fromstring(fetch_text(url))
            for node in root.findall('addon'):
                aid=node.attrib.get('id')
                if aid: available.add(aid)
        except Exception as e:
            raise RuntimeError('Could not validate dependency repository index '+url+': '+str(e))
    return available


def validate_addons_and_dependencies():
    addons=STAGE/'addons'
    if not addons.exists(): raise RuntimeError('Payload addons directory missing')
    metas={}; invalid=[]
    for d in [p for p in addons.iterdir() if p.is_dir()]:
        try: meta=addon_metadata(d)
        except Exception as e: invalid.append(d.name+': '+str(e)); continue
        if not meta: invalid.append(d.name+': missing addon.xml'); continue
        if meta['id'] != d.name: invalid.append(d.name+': addon id '+meta['id']+' does not match directory')
        metas[meta['id']]=meta
    if invalid: raise RuntimeError('Invalid Kodi addons: '+'; '.join(invalid[:12]))

    skin=metas.get('skin.auramod')
    if not skin or version_tuple(skin['version']) < AURAMOD_MIN_VERSION: raise RuntimeError('Kodi 21 AuraMOD 2.0.4+ not staged')
    gui=[version_tuple(ver) for dep,ver,opt in skin['imports'] if dep=='xbmc.gui' and not opt]
    if not gui or gui[0] < AURAMOD_MIN_GUI: raise RuntimeError('AuraMOD does not target Kodi 21 xbmc.gui 5.17+')

    available_remote=dependency_indexes()
    missing=[]
    for aid in CRITICAL_ADDONS:
        meta=metas.get(aid)
        if not meta: missing.append(aid+': addon missing'); continue
        for dep,_ver,optional in meta['imports']:
            if optional or not dep or dep.startswith(CORE_DEP_PREFIXES): continue
            if dep in metas or dep in available_remote: continue
            missing.append(aid+' requires unresolved '+dep)
    if missing: raise RuntimeError('Launch-critical dependency resolution failed: '+'; '.join(missing))
    print('Launch-critical dependencies are bundled or resolvable through validated repositories.')


def validate_python3_critical():
    for aid in CRITICAL_ADDONS:
        root=STAGE/'addons'/aid
        if not root.exists(): continue
        for p in root.rglob('*.py'):
            try: compile(p.read_text(encoding='utf-8'), str(p.relative_to(STAGE)), 'exec')
            except Exception as e: raise RuntimeError(f'Python 3 compile failed for {p.relative_to(STAGE)}: {e}')


def installable_runtime_files():
    for p in STAGE.rglob('*'):
        if not p.is_file(): continue
        rel=p.relative_to(STAGE)
        if not rel.parts or rel.parts[0] not in RUNTIME_ROOTS: continue
        if rel in UNSAFE_STAGE_FILES: continue
        if any(rel == d or d in rel.parents for d in UNSAFE_STAGE_DIRS): continue
        if str(rel).replace('\\','/') == 'dragonmax/install_manifest.json': continue
        yield rel,p


def simulate_install(existing_auramod=False, rollback=False):
    sim=STAGE.parent/('sim_existing' if existing_auramod else 'sim_fresh')
    shutil.rmtree(sim,ignore_errors=True); home=sim/'home'; backup=sim/'backup'; home.mkdir(parents=True)
    if existing_auramod:
        sentinel=home/'addons'/'skin.auramod'/'addon.xml'; sentinel.parent.mkdir(parents=True,exist_ok=True); sentinel.write_text('<sentinel/>',encoding='utf-8')
    old_adv=home/'userdata'/'advancedsettings.xml'; old_adv.parent.mkdir(parents=True,exist_ok=True); old_adv.write_text('<old/>',encoding='utf-8')
    originals=[]; created=[]
    files=list(installable_runtime_files())
    for rel,src in files:
        r=str(rel).replace('\\','/')
        if existing_auramod and r.startswith('addons/skin.auramod/'): continue
        dst=home/rel
        if dst.exists() and r.startswith('userdata/'):
            b=backup/'originals'/rel; b.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(dst,b); originals.append((dst,b))
        elif not dst.exists(): created.append(dst)
        dst.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(src,dst)
    for aid in BOOTSTRAP_PACKAGES:
        if not (home/'addons'/aid/'addon.xml').exists(): raise RuntimeError('Simulated install missing dependency bootstrap addon '+aid)
    if not (home/'addons'/'service.dragonmax.voice'/'addon.xml').exists(): raise RuntimeError('Simulated install missing Dragon Voice')
    if not (home/'dragonmax'/'config'/'voice.json').exists(): raise RuntimeError('Simulated install missing DragonMax config')
    if existing_auramod and (home/'addons'/'skin.auramod'/'addon.xml').read_text(encoding='utf-8') != '<sentinel/>': raise RuntimeError('Existing AuraMOD was overwritten in simulation')
    if not existing_auramod:
        meta=addon_metadata(home/'addons'/'skin.auramod')
        if not meta or version_tuple(meta['version']) < AURAMOD_MIN_VERSION: raise RuntimeError('Fresh install simulation missing AuraMOD Omega')
    if rollback:
        for dst in reversed(created):
            try: dst.unlink()
            except OSError: pass
        for dst,b in originals:
            dst.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(b,dst)
        if old_adv.read_text(encoding='utf-8') != '<old/>': raise RuntimeError('Rollback simulation did not restore userdata')
    shutil.rmtree(sim,ignore_errors=True)


def validate_quality():
    required=[STAGE/'addons'/'skin.auramod'/'addon.xml',STAGE/'addons'/'service.dragonmax.voice'/'addon.xml',STAGE/'addons'/'service.dragonmax.voice'/'service.py',STAGE/'addons'/'service.dragonmax.voice'/'dragon_memory.py',STAGE/'addons'/'service.dragonmax.voice'/'self_repair.py',STAGE/'userdata',STAGE/'dragonmax'/'config'/'menus.json',STAGE/'dragonmax'/'config'/'widgets.json',STAGE/'dragonmax'/'config'/'realms.json',STAGE/'dragonmax'/'config'/'performance.json',STAGE/'dragonmax'/'config'/'voice.json',STAGE/'dragonmax'/'install_manifest.json',STAGE/'startup'/'dragonmax_static_splash.png']
    required += [STAGE/'addons'/aid/'addon.xml' for aid in BOOTSTRAP_PACKAGES]
    missing=[str(p.relative_to(STAGE)) for p in required if not p.exists()]
    if missing: raise RuntimeError('Missing required V12 content: '+', '.join(missing))
    for rel in UNSAFE_STAGE_DIRS:
        if (STAGE/rel).exists(): raise RuntimeError('Unsafe runtime state leaked into payload: '+str(rel))
    for rel in UNSAFE_STAGE_FILES:
        if (STAGE/rel).exists(): raise RuntimeError('Unsafe live Kodi setting leaked into payload: '+str(rel))
    for p in STAGE.rglob('*'):
        rel=p.relative_to(STAGE)
        if any(part.lower() in DEV_DIR_NAMES for part in rel.parts): raise RuntimeError('Development debris leaked into payload: '+str(rel))
        if rel.parts and rel.parts[0] not in RUNTIME_ROOTS and p.is_file() and p.name!='dragonmax_manifest.json': raise RuntimeError('Unexpected payload root: '+str(rel))
        if 'DragonMax_V9_2_Build_Content' in rel.parts: raise RuntimeError('Nested legacy wrapper leaked into payload: '+str(rel))
    for name in ['menus.json','widgets.json','realms.json','performance.json','voice.json']: json.loads((STAGE/'dragonmax'/'config'/name).read_text(encoding='utf-8'))
    validate_addons_and_dependencies(); validate_python3_critical()
    simulate_install(existing_auramod=False, rollback=True)
    simulate_install(existing_auramod=True, rollback=True)
    print('DragonMax launch simulations passed: fresh install, existing AuraMOD, bootstrap repos, rollback restoration.')


def write_zip():
    BUILD.parent.mkdir(parents=True,exist_ok=True)
    if BUILD.exists(): BUILD.unlink()
    with zipfile.ZipFile(BUILD,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in STAGE.rglob('*'):
            if p.is_file(): z.write(p,Path(STAGE.name)/p.relative_to(STAGE))


def sha256_file(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def make_zip():
    validate_quality(); write_zip(); size=BUILD.stat().st_size; mb=size/1024/1024
    print(f'V12 payload size: {mb:.2f} MiB')
    if size < IDEAL_SIZE: print(f'INFO package is below the ~280 MiB ideal by {(IDEAL_SIZE-size)/1024/1024:.2f} MiB; accepted because quality gates take priority.')
    elif size > SOFT_MAX: print(f'WARN package is above the 320 MiB soft ceiling at {mb:.2f} MiB; review before launch.')
    with zipfile.ZipFile(BUILD) as z:
        bad=z.testzip()
        if bad: raise RuntimeError('Corrupt ZIP member: '+bad)
        names=z.namelist(); checks={'userdata':any('/userdata/' in '/'+n for n in names),'AuraMOD Omega':any('/addons/skin.auramod/addon.xml' in '/'+n for n in names),'Dragon Voice':any('/addons/service.dragonmax.voice/' in '/'+n for n in names),'Install manifest':any(n.endswith('/dragonmax/install_manifest.json') for n in names)}
        for aid in BOOTSTRAP_PACKAGES: checks['bootstrap '+aid]=any(('/addons/'+aid+'/addon.xml') in '/'+n for n in names)
        failed=[name for name,ok in checks.items() if not ok]
        if failed: raise RuntimeError('ZIP missing required content: '+', '.join(failed))
        if any('/.github/' in '/'+n or '/.git/' in '/'+n for n in names): raise RuntimeError('Development metadata present in release ZIP')


def publish_repo_files():
    for name in ['index.html','updates.json','themes.json','realms.json']:
        src=ROOT/name
        if src.exists(): shutil.copyfile(src,OUT/name)
    meta=json.loads((ROOT/'build.json').read_text(encoding='utf-8'))
    build=meta['builds'][0]
    build['version']=RELEASE_VERSION
    build['zip']=f'builds/DragonMax_V12_Unified_Build_Content-{RELEASE_VERSION}.zip'
    build['last_built_size_mb']=round(BUILD.stat().st_size/1024/1024,2)
    build['sha256']=sha256_file(BUILD)
    build['install_protocol']=INSTALL_PROTOCOL
    build['protected_runtime_paths']=['userdata/Database','userdata/Thumbnails','userdata/temp','addons/packages','userdata/guisettings.xml']
    build['payload_policy']='clean runtime image; AuraMOD Omega 2.0.4 exact commit; bootstrap repositories bundled; no inherited device userdata; no repository development metadata; dependency indexes verified; fresh/existing-skin/rollback simulations passed'
    build['auramod_version']='2.0.4'
    build['auramod_commit']=AURAMOD_COMMIT
    (OUT/'build.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')


def main():
    clean(); copy_legacy(); reset_userdata(); sanitize_stage(); install_auramod(); install_bootstrap_addons(); install_dragonmax_addons(); generate_media(); generate_userdata(); sanitize_stage(); manifest(); payload_file_manifest(); make_zip(); publish_repo_files(); repo_release.publish(ROOT, OUT); print('DragonMax V12 launch-candidate distribution complete:',BUILD)

if __name__=='__main__': main()
