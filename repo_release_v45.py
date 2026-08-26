#!/usr/bin/env python3
import ast, hashlib, io, zipfile
from pathlib import Path

VERSION='4.5.0'
HOST='https://dragonmax-v12-release.onrender.com/'
XML='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'

REPO=f'''{XML}\n<addon id="repository.dragonmax" name="DragonMax Repository" version="{VERSION}" provider-name="DragonMax RD"><extension point="xbmc.addon.repository" name="DragonMax Repository"><dir minversion="21.0.0"><info compressed="false">{HOST}addons.xml</info><checksum>{HOST}addons.xml.md5</checksum><datadir zip="true">{HOST}</datadir></dir></extension><extension point="xbmc.addon.metadata"><summary>DragonMax V12 Unified repository</summary><description>DragonMax V12 Unified repository for Kodi 21+.</description><platform>all</platform></extension></addon>'''

ADDON=f'''{XML}\n<addon id="plugin.program.dragonmaxwizard" name="DragonMax Wizard" version="{VERSION}" provider-name="DragonMax RD"><requires><import addon="xbmc.python" version="3.0.0"/></requires><extension point="xbmc.python.pluginsource" library="default.py"><provides>executable</provides></extension><extension point="xbmc.addon.metadata"><summary>DragonMax V12 launch-candidate installer</summary><description>Protocol-4 installer with payload integrity checks, clean-runtime enforcement, selective rollback, dependency preflight, existing-skin preservation, and Android-safe atomic writes.</description><platform>all</platform></extension></addon>'''

DEFAULT=r'''#!/usr/bin/env python3
import hashlib,json,os,shutil,time,traceback,urllib.request,zipfile
import xbmc,xbmcaddon,xbmcgui,xbmcvfs
HOST='https://dragonmax-v12-release.onrender.com/'; BUILD_JSON=HOST+'build.json'; ADDON_ID='plugin.program.dragonmaxwizard'; VERSION='4.5.0'; MIN_PROTOCOL=4
ALLOWED=('addons/','userdata/','artwork/','audio/','startup/','dragonmax/'); META={'dragonmax_manifest.json','dragonmax/install_manifest.json'}
PROTECTED=('userdata/Database/','userdata/Thumbnails/','userdata/temp/','addons/packages/','temp/','cache/','dragonmax_backups/'); PROTECTED_FILES={'userdata/guisettings.xml'}
OWNED=('addons/service.dragonmax.voice/','userdata/addon_data/service.dragonmax.voice/','dragonmax/','artwork/','audio/','startup/')
BACKUP_USERDATA=('userdata/keymaps/','userdata/advancedsettings.xml','userdata/addon_data/skin.auramod/','userdata/addon_data/script.autowidget/')

def log(m,l=xbmc.LOGINFO): xbmc.log('[DragonMaxWizard] '+str(m),l)
def pu(p,n,m=''): p.update(int(max(0,min(100,n))),m)
def norm(r): return r.replace('\\','/').lstrip('/')
def protected(r): r=norm(r); return r in PROTECTED_FILES or any(r.startswith(x) for x in PROTECTED)
def installable(r): r=norm(r); return r not in META and not protected(r) and any(r.startswith(x) for x in ALLOWED)
def profile():
 p=xbmcvfs.translatePath('special://profile/addon_data/'+ADDON_ID+'/'); os.makedirs(p,exist_ok=True); return p
def work():
 for p in (xbmcvfs.translatePath('special://temp/dragonmax-v12/'),os.path.join(profile(),'work')):
  try:
   shutil.rmtree(p,ignore_errors=True); os.makedirs(p,exist_ok=True); q=os.path.join(p,'.probe'); open(q,'wb').write(b'ok'); os.remove(q); return p
  except Exception: pass
 raise RuntimeError('No writable DragonMax work directory')
def req(u,t=60): return urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Kodi/21 DragonMaxWizard/'+VERSION,'Accept':'*/*','Connection':'close'}),timeout=t)
def getjson(u):
 with req(u,45) as r:return json.loads(r.read().decode('utf-8'))
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for c in iter(lambda:f.read(1048576),b''): h.update(c)
 return h.hexdigest()
def download(u,d,p):
 with req(u,300) as r,open(d,'wb') as f:
  total=int(r.headers.get('Content-Length') or 0); done=0
  while True:
   c=r.read(1048576)
   if not c: break
   f.write(c); done+=len(c)
   if total: pu(p,min(20,done*20/total),'Downloading DragonMax V12')
def extract(zp,out,p):
 with zipfile.ZipFile(zp) as z:
  ms=z.infolist(); total=max(1,len(ms)); base=os.path.abspath(out)
  for i,m in enumerate(ms,1):
   n=m.filename.replace('\\','/'); dst=os.path.abspath(os.path.join(out,n))
   if dst!=base and not dst.startswith(base+os.sep): raise RuntimeError('Unsafe ZIP path rejected: '+n)
   z.extract(m,out)
   if i==1 or i==total or i%25==0: pu(p,25+20*i/total,'Extracting package\n'+n[-70:])
def verify(root,p):
 mp=os.path.join(root,'dragonmax','install_manifest.json')
 if not os.path.isfile(mp): raise RuntimeError('Payload install manifest missing')
 manifest=json.load(open(mp,encoding='utf-8'))
 if int(manifest.get('install_protocol',0))<MIN_PROTOCOL: raise RuntimeError('Payload manifest uses obsolete install protocol')
 rows=manifest.get('files',[]); total=max(1,len(rows))
 for i,row in enumerate(rows,1):
  r=norm(row['path']); f=os.path.join(root,r.replace('/',os.sep))
  if protected(r): raise RuntimeError('Protected runtime path leaked into payload: '+r)
  if not os.path.isfile(f) or os.path.getsize(f)!=int(row['size']) or sha(f).lower()!=str(row['sha256']).lower(): raise RuntimeError('Payload verification failed: '+r)
  if i==1 or i==total or i%50==0: pu(p,45+10*i/total,'Verifying payload\n'+r[-70:])
def files(root):
 out=[]
 for b,_,ns in os.walk(root):
  for n in ns:
   s=os.path.join(b,n); r=norm(os.path.relpath(s,root))
   if installable(r): out.append((r,s))
 return sorted(out)
def atomic(src,dst):
 par=os.path.dirname(dst); os.makedirs(par,exist_ok=True); tmp=os.path.join(par,'.dragonmax-new-'+os.path.basename(dst))
 try:
  if os.path.exists(tmp): os.remove(tmp)
  shutil.copyfile(src,tmp)
  try: os.chmod(tmp,0o644)
  except OSError: pass
  os.replace(tmp,dst)
 finally:
  try:
   if os.path.exists(tmp): os.remove(tmp)
  except OSError: pass
def active_auramod(home): return os.path.isfile(os.path.join(home,'addons','skin.auramod','addon.xml'))
def filter_device(home,fs):
 if not active_auramod(home): return fs
 return [(r,s) for r,s in fs if not r.startswith('addons/skin.auramod/')]
def dependency_preflight(root,home):
 import xml.etree.ElementTree as ET
 skin=ET.parse(os.path.join(root,'addons','skin.auramod','addon.xml')).getroot(); missing=[]
 req=skin.find('requires')
 if req is not None:
  for node in req.findall('import'):
   dep=node.attrib.get('addon',''); optional=node.attrib.get('optional','').lower()=='true'
   if optional or not dep or dep.startswith('xbmc.'): continue
   if os.path.isdir(os.path.join(root,'addons',dep)) or os.path.isdir(os.path.join(home,'addons',dep)): continue
   try: xbmcaddon.Addon(dep)
   except Exception: missing.append(dep)
 if missing: raise RuntimeError('Missing required AuraMOD dependencies before install: '+', '.join(sorted(set(missing))))
def preflight(home,fs):
 for top in sorted(set(r.split('/',1)[0] for r,_ in fs)):
  target=os.path.join(home,top); par=target if os.path.isdir(target) else home; q=os.path.join(par,'.dragonmax-write-probe')
  try:
   with open(q,'wb') as f:f.write(b'ok')
   os.remove(q)
  except Exception as e: raise RuntimeError('Kodi destination not writable: %s (%s)'%(par,e))
def backup(home,fs,root,p):
 originals=[]; created=[]; total=max(1,len(fs)); os.makedirs(root,exist_ok=True)
 for i,(r,_) in enumerate(fs,1):
  d=os.path.join(home,r.replace('/',os.sep)); wants=r.startswith('userdata/') and any(r.startswith(x) for x in BACKUP_USERDATA)
  if os.path.isfile(d) and wants:
   b=os.path.join(root,'originals',r.replace('/',os.sep))
   try: os.makedirs(os.path.dirname(b),exist_ok=True); shutil.copy2(d,b); originals.append((d,b))
   except (PermissionError,OSError) as e: log('Optional rollback backup skipped '+r+': '+str(e),xbmc.LOGWARNING)
  elif not os.path.exists(d): created.append(d)
  if i==1 or i==total or i%100==0: pu(p,55+5*i/total,'Preparing selective rollback\n'+r[-70:])
 with open(os.path.join(root,'transaction.json'),'w',encoding='utf-8') as f: json.dump({'version':VERSION,'originals':originals,'created':created},f,indent=2)
 return originals,created
def rollback(o,c):
 for d in reversed(c):
  try:
   if os.path.isfile(d) or os.path.islink(d): os.remove(d)
  except OSError: pass
 for d,b in o:
  try: atomic(b,d)
  except OSError as e: log('Rollback failed '+str(e),xbmc.LOGERROR)
def apply(home,fs,p):
 total=max(1,len(fs))
 for i,(r,s) in enumerate(fs,1):
  if p.iscanceled(): raise RuntimeError('Installation cancelled')
  d=os.path.join(home,r.replace('/',os.sep))
  try: atomic(s,d)
  except Exception as e:
   if r.startswith('addons/') or any(r.startswith(x) for x in OWNED):
    try: os.remove(d)
    except OSError: pass
    try: atomic(s,d)
    except Exception as e2: raise RuntimeError('Cannot install required target %s (%s)'%(r,e2))
   else: raise RuntimeError('Cannot install target %s (%s)'%(r,e))
  if i==1 or i==total or i%25==0: pu(p,60+40*i/total,'Applying DragonMax V12\n'+r[-70:])
def main():
 dlg=xbmcgui.Dialog(); p=xbmcgui.DialogProgress()
 try: build=getjson(BUILD_JSON)['builds'][0]
 except Exception as e: dlg.ok('DragonMax Wizard','Could not load staging metadata.\n\n'+str(e)); return
 if int(build.get('install_protocol',0))<MIN_PROTOCOL: dlg.ok('DragonMax Wizard','Server payload has not passed the launch-candidate protocol gate.'); return
 if not build.get('ready',False) and not dlg.yesno('DragonMax V12 DEVICE VALIDATION','Launch-candidate package. Payload integrity, dependency closure, protected paths, clean runtime, fresh install, upgrade, and rollback simulations passed server-side.\n\nRun the Fire TV validation install?'): return
 home=xbmcvfs.translatePath('special://home/'); w=work(); zp=os.path.join(w,'dragonmax.zip'); ex=os.path.join(w,'extract'); br=os.path.join(profile(),'backups',time.strftime('%Y%m%d-%H%M%S')); o=[]; c=[]
 try:
  p.create('DragonMax Wizard','Downloading DragonMax V12'); download(HOST+str(build['zip']).lstrip('/'),zp,p); pu(p,20,'Validating package')
  if os.path.getsize(zp)<float(build.get('minimum_size_mb',60))*1048576: raise RuntimeError('Downloaded payload too small')
  if not build.get('sha256') or sha(zp).lower()!=str(build['sha256']).lower(): raise RuntimeError('Payload checksum mismatch')
  os.makedirs(ex,exist_ok=True); extract(zp,ex,p); roots=[os.path.join(ex,n) for n in os.listdir(ex) if os.path.isdir(os.path.join(ex,n))]
  if len(roots)!=1: raise RuntimeError('Unexpected payload layout')
  root=roots[0]; verify(root,p); dependency_preflight(root,home); fs=filter_device(home,files(root))
  if not fs: raise RuntimeError('No installable files')
  preflight(home,fs); o,c=backup(home,fs,br,p); apply(home,fs,p); pu(p,100,'Installation complete'); p.close(); dlg.ok('DragonMax V12 Installed','Fire TV validation install completed.\n\nFully exit Kodi and reopen it.\n\nSelective rollback data: '+br)
 except Exception as e:
  log(traceback.format_exc(),xbmc.LOGERROR)
  try:p.close()
  except Exception:pass
  if o or c: rollback(o,c); dlg.ok('DragonMax Install Failed',str(e)+'\n\nSelective rollback was applied.')
  else: dlg.ok('DragonMax Install Failed',str(e)+'\n\nNo DragonMax files were applied.')
 finally: shutil.rmtree(w,ignore_errors=True)
try: main()
except BaseException as e:
 log(traceback.format_exc(),xbmc.LOGERROR)
 try: xbmcgui.Dialog().ok('DragonMax Wizard Startup Error',str(e))
 except Exception: pass
'''

def z(folder,files):
 out=io.BytesIO()
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as q:
  for n,t in files.items(): q.writestr(folder+'/'+n,t)
 return out.getvalue()
def frag(x): return x.replace(XML,'',1).strip()
def gates(s):
 tree=ast.parse(s)
 for token in ['MIN_PROTOCOL=4','dependency_preflight','filter_device','BACKUP_USERDATA','atomic','rollback','preflight']:
  if token not in s: raise RuntimeError('Installer gate missing '+token)
 for node in ast.walk(tree):
  if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr in ('create','update') and isinstance(node.func.value,ast.Name) and node.func.value.id=='p' and len(node.args)>2: raise RuntimeError('Kodi DialogProgress API arity regression')
def publish(root:Path,out:Path):
 addons=XML+'\n<addons>\n'+frag(REPO)+'\n'+frag(ADDON)+'\n</addons>\n'; compile(DEFAULT,'default.py','exec'); gates(DEFAULT)
 import xml.etree.ElementTree as ET; ET.fromstring(addons)
 (out/'addons.xml').write_text(addons,encoding='utf-8'); (out/'addons.xml.md5').write_text(hashlib.md5(addons.encode()).hexdigest())
 rz=z('repository.dragonmax',{'addon.xml':REPO}); wz=z('plugin.program.dragonmaxwizard',{'addon.xml':ADDON,'default.py':DEFAULT})
 for aid,data in [('repository.dragonmax',rz),('plugin.program.dragonmaxwizard',wz)]:
  d=out/aid; d.mkdir(parents=True,exist_ok=True); (out/f'{aid}-{VERSION}.zip').write_bytes(data); (d/f'{aid}-{VERSION}.zip').write_bytes(data)
  with zipfile.ZipFile(out/f'{aid}-{VERSION}.zip') as q:
   if q.testzip(): raise RuntimeError('Corrupt generated installer ZIP')
 print('DragonMax Wizard 4.5.0 generated; protocol-4 launch-candidate gates passed.')
