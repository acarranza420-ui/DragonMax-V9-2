#!/usr/bin/env python3
import json, math, shutil, struct, urllib.request, wave, zipfile, zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'public'
STAGE = ROOT / '.v12_stage' / 'DragonMax_V12_Unified_Build_Content'
BUILD = OUT / 'builds' / 'DragonMax_V12_Unified_Build_Content-4.0.0.zip'
IDEAL_SIZE = 280 * 1024 * 1024
SOFT_MAX = 320 * 1024 * 1024

REALMS = [
    ('dragon_order','Dragon Order',(160,55,20)),
    ('arcane_dominion','Arcane Dominion',(70,45,150)),
    ('crimson_court','Crimson Court',(125,10,30)),
    ('temple_guardians','Temple Guardians',(35,95,70)),
    ('champion_guild','Champion Guild',(35,75,135)),
    ('office_consortium','Office Consortium',(30,50,70)),
]


def clean():
    shutil.rmtree(OUT, ignore_errors=True)
    shutil.rmtree(STAGE.parent, ignore_errors=True)
    (OUT/'builds').mkdir(parents=True, exist_ok=True)
    STAGE.mkdir(parents=True, exist_ok=True)


def fetch(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={'User-Agent':'DragonMax-V12-Builder/4.0'})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest,'wb') as f:
        shutil.copyfileobj(r,f)


def block_noise(seed, bx, by, limit):
    # Fast deterministic integer hash. Avoids constructing Random() for every pixel.
    n = (seed * 2654435761 + bx * 2246822519 + by * 3266489917) & 0xffffffff
    n ^= n >> 13
    n = (n * 1274126177) & 0xffffffff
    n ^= n >> 16
    return n % max(1, limit)


def png_bytes(w,h,tint,seed,detail='normal'):
    raw = bytearray()
    tr,tg,tb = tint
    block = 8 if detail == 'normal' else 4
    limit = 36 if detail == 'normal' else 72
    blocks_x = (w + block - 1) // block
    for y in range(h):
        raw.append(0)
        by = y // block
        row_noise = [block_noise(seed, bx, by, limit) for bx in range(blocks_x)]
        for x in range(w):
            bx = x // block
            noise = row_noise[bx]
            wavev = int(22 * math.sin((x + seed % 97) / 47.0) + 16 * math.cos((y + seed % 53) / 61.0))
            fade = int(30 * y / max(1,h-1))
            r = max(0,min(255,tr + noise + wavev + fade))
            g = max(0,min(255,tg + noise//2 + wavev//2 + fade//2))
            b = max(0,min(255,tb + noise//3 - wavev//3))
            raw.extend((r,g,b))
    def chunk(tag,data):
        return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(bytes(raw),7))+chunk(b'IEND',b'')


def write_png(path,w,h,tint,seed,detail='normal'):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png_bytes(w,h,tint,seed,detail))


def write_wav(path,dur,freqs,vol=.25,sr=44100):
    path.parent.mkdir(parents=True, exist_ok=True)
    n=int(dur*sr)
    with wave.open(str(path),'w') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        frames=bytearray()
        for i in range(n):
            t=i/sr
            env=min(1.0,t/max(.05,dur*.2))*max(0.0,min(1.0,(dur-t)/max(.05,dur*.25)))
            s=sum(math.sin(2*math.pi*f*t) for f in freqs)/len(freqs)
            frames += struct.pack('<h', int(max(-1,min(1,s*env*vol))*32767))
        wf.writeframes(frames)


def copy_legacy():
    legacy = ROOT/'DragonMax_V9_2_Build_Content-1.9.2.zip'
    if not legacy.exists():
        return
    tmp = STAGE.parent/'legacy'
    tmp.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(legacy) as z:
        z.extractall(tmp)
    for p in tmp.rglob('*'):
        if not p.is_file():
            continue
        rel = p.relative_to(tmp)
        dst = STAGE/rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(p,dst)


def install_auramod():
    arc = STAGE.parent/'auramod.zip'
    fetch('https://codeload.github.com/jojobrogess/skin.auramod/zip/refs/heads/Matrix', arc)
    tmp = STAGE.parent/'auramod_extract'
    with zipfile.ZipFile(arc) as z:
        z.extractall(tmp)
    roots=[p for p in tmp.iterdir() if p.is_dir()]
    if not roots:
        raise RuntimeError('AuraMOD archive extracted without a root folder')
    dst=STAGE/'addons'/'skin.auramod'
    shutil.rmtree(dst,ignore_errors=True)
    shutil.copytree(roots[0],dst)


def install_dragonmax_addons():
    src = ROOT/'v12_addons'
    if not src.exists():
        raise RuntimeError('v12_addons source directory missing')
    for addon in src.iterdir():
        if addon.is_dir():
            dst = STAGE/'addons'/addon.name
            shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(addon, dst)


def generate_media():
    art=STAGE/'artwork'; audio=STAGE/'audio'; startup=STAGE/'startup'
    idx=0
    for slug,name,tint in REALMS:
        for i in range(8):
            idx+=1; write_png(art/'wallpapers'/slug/f'{slug}_{i+1:02d}.png',1280,720,tint,10000+idx)
        for i in range(3):
            idx+=1; write_png(art/'hero_banners'/slug/f'{slug}_hero_{i+1:02d}.png',1280,480,tint,20000+idx)
        write_png(art/'realm_crests'/f'{slug}_crest.png',512,512,tint,30000+idx)
        for i,level in enumerate(['novice','adept','master','champion','legend']):
            write_png(art/'achievement_badges'/slug/f'{slug}_{level}.png',320,320,tint,40000+idx*10+i)
    for i in range(10):
        slug,name,tint=REALMS[i%6]
        write_png(art/'loading_screens'/f'loading_{i+1:02d}.png',1280,720,tint,50000+i)
    for i,(slug,name,tint) in enumerate(REALMS):
        write_png(art/'portal_graphics'/f'{slug}_portal.png',1024,576,tint,60000+i)
        write_png(art/'wizard_graphics'/f'{slug}_wizard.png',1024,576,tint,61000+i)
    write_png(startup/'dragonmax_static_splash.png',1600,900,REALMS[0][2],70000)
    write_wav(audio/'startup_theme.wav',8.0,(55,110,165,220),.26)
    write_wav(audio/'portal_open.wav',2.0,(140,280,560),.22)
    write_wav(audio/'achievement.wav',1.4,(523,659,784,1046),.20)
    write_wav(audio/'ui_click.wav',.16,(900,1300),.17)
    write_wav(audio/'ui_back.wav',.22,(420,260),.17)
    write_wav(audio/'ui_select.wav',.30,(660,880,1320),.17)
    write_wav(audio/'error.wav',.45,(180,120),.18)
    for i,(slug,name,tint) in enumerate(REALMS):
        write_wav(audio/f'realm_change_{slug}.wav',1.0,(140+i*20,280+i*25,560+i*30),.18)


def generate_userdata():
    u=STAGE/'userdata'; cfg=STAGE/'dragonmax'/'config'
    (u/'addon_data'/'skin.auramod').mkdir(parents=True,exist_ok=True)
    (u/'addon_data'/'script.autowidget').mkdir(parents=True,exist_ok=True)
    (u/'addon_data'/'plugin.video.themoviedb.helper').mkdir(parents=True,exist_ok=True)
    (u/'addon_data'/'service.dragonmax.voice').mkdir(parents=True,exist_ok=True)
    (u/'keymaps').mkdir(parents=True,exist_ok=True)
    cfg.mkdir(parents=True,exist_ok=True)
    menus={'layout':'netflix_first','home':['Dragon Portal','Continue Watching','Movies','TV Shows','Anime Universe','Martial Arts','Champion Guild','Office Consortium','Settings'],'portal':['Dragon Voice','Switch Realm','Resume Last Played','Audio Profile','Performance Mode','Maintenance','Backups','Updates','System Health','Admin']}
    widgets={'max_home_widgets':6,'refresh_hours':6,'rows':['Continue Watching','Trending Movies','Trending TV','Anime Universe','Martial Arts','Favorites']}
    realms={'realms':[{'id':s,'name':n} for s,n,t in REALMS]}
    perf={'default':'balanced','profiles':{'maximum_speed':{'widget_limit':4,'animated_backgrounds':False},'balanced':{'widget_limit':6,'animated_backgrounds':False},'visual_quality':{'widget_limit':6,'animated_backgrounds':True}}}
    voice={'enabled':True,'bridge_port':8765,'wake_phrase':'Dragon','external_ai_enabled':False,'destructive_confirmation_required':True,'manual_fallback':True}
    for p,data in [
        (cfg/'menus.json',menus),(cfg/'widgets.json',widgets),(cfg/'realms.json',realms),(cfg/'performance.json',perf),(cfg/'voice.json',voice),
        (u/'addon_data'/'skin.auramod'/'dragonmax_skin_base.json',{'theme':'Dragon Order','portal_enabled':True,'voice_enabled':True}),
        (u/'addon_data'/'script.autowidget'/'dragonmax_groups.json',widgets)
    ]:
        p.write_text(json.dumps(data,indent=2),encoding='utf-8')
    (u/'advancedsettings.xml').write_text('<advancedsettings><cache><buffermode>1</buffermode><memorysize>139460608</memorysize><readfactor>4.0</readfactor></cache></advancedsettings>',encoding='utf-8')
    (u/'favourites.xml').write_text('<favourites><favourite name="Dragon Portal">ActivateWindow(Programs,plugin.program.dragonmaxwizard,return)</favourite></favourites>',encoding='utf-8')
    (u/'keymaps'/'dragonmax.xml').write_text('<keymap><global><keyboard><menu>ActivateWindow(Programs,plugin.program.dragonmaxwizard,return)</menu></keyboard></global></keymap>',encoding='utf-8')


def manifest():
    data={
        'name':'DragonMax V12 Unified','version':'4.0.0','merge_policy':'V9.2 baseline + V11/V12 overlay',
        'target_device':'Fire TV Stick 4K Max','realms':[n for s,n,t in REALMS],
        'release_priority':['quality','stability','smooth_use','visual_consistency','package_size'],
        'capabilities':['Dragon Voice','Dragon AI intent engine','authenticated LAN command bridge','safe confirmations','remote-control fallback']
    }
    (STAGE/'dragonmax_manifest.json').write_text(json.dumps(data,indent=2),encoding='utf-8')


def write_zip():
    BUILD.parent.mkdir(parents=True,exist_ok=True)
    if BUILD.exists(): BUILD.unlink()
    with zipfile.ZipFile(BUILD,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in STAGE.rglob('*'):
            if p.is_file(): z.write(p,Path(STAGE.name)/p.relative_to(STAGE))


def validate_quality():
    required = [
        STAGE/'addons'/'skin.auramod',
        STAGE/'addons'/'service.dragonmax.voice'/'addon.xml',
        STAGE/'addons'/'service.dragonmax.voice'/'service.py',
        STAGE/'userdata',
        STAGE/'dragonmax'/'config'/'menus.json',
        STAGE/'dragonmax'/'config'/'widgets.json',
        STAGE/'dragonmax'/'config'/'realms.json',
        STAGE/'dragonmax'/'config'/'performance.json',
        STAGE/'dragonmax'/'config'/'voice.json',
        STAGE/'startup'/'dragonmax_static_splash.png',
    ]
    missing=[str(p.relative_to(STAGE)) for p in required if not p.exists()]
    if missing:
        raise RuntimeError('Missing required V12 content: '+', '.join(missing))
    for name in ['menus.json','widgets.json','realms.json','performance.json','voice.json']:
        json.loads((STAGE/'dragonmax'/'config'/name).read_text(encoding='utf-8'))
    # Compile the Python service without importing Kodi-only modules.
    compile((STAGE/'addons'/'service.dragonmax.voice'/'service.py').read_text(encoding='utf-8'), 'service.py', 'exec')


def make_zip():
    validate_quality()
    write_zip()
    size=BUILD.stat().st_size
    mb=size/1024/1024
    print(f'V12 payload size: {mb:.2f} MiB')
    if size < IDEAL_SIZE:
        print(f'INFO package is below the ~280 MiB ideal by {(IDEAL_SIZE-size)/1024/1024:.2f} MiB; accepted because quality gates take priority.')
    elif size > SOFT_MAX:
        print(f'WARN package is above the 320 MiB soft ceiling at {mb:.2f} MiB; review before launch for Fire TV storage/performance impact.')
    with zipfile.ZipFile(BUILD) as z:
        bad=z.testzip()
        if bad: raise RuntimeError('Corrupt ZIP member: '+bad)
        names=z.namelist()
        checks={
            'userdata': any('/userdata/' in '/'+n for n in names),
            'AuraMOD': any('/addons/skin.auramod/' in '/'+n for n in names),
            'DragonMax config': any('/dragonmax/config/' in '/'+n for n in names),
            'Dragon Voice': any('/addons/service.dragonmax.voice/' in '/'+n for n in names),
        }
        failed=[name for name,ok in checks.items() if not ok]
        if failed: raise RuntimeError('ZIP missing required content: '+', '.join(failed))


def publish_repo_files():
    for name in ['index.html','addons.xml','addons.xml.md5','build.json','updates.json','themes.json','realms.json']:
        src=ROOT/name
        if src.exists(): shutil.copy2(src,OUT/name)


def main():
    clean()
    copy_legacy()
    install_auramod()
    install_dragonmax_addons()
    generate_media()
    generate_userdata()
    manifest()
    make_zip()
    publish_repo_files()
    print('DragonMax V12 distribution build complete:',BUILD)

if __name__=='__main__':
    main()
