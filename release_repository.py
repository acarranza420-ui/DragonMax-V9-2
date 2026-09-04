#!/usr/bin/env python3
import ast, hashlib, io, zipfile
from pathlib import Path

VERSION='4.9.0'
HOST='https://dragonmax.onrender.com/'
XML='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'

REPO=f'''{XML}\n<addon id="repository.dragonmax" name="DragonMax Repository" version="{VERSION}" provider-name="DragonMax RD"><extension point="xbmc.addon.repository" name="DragonMax Repository"><dir minversion="21.0.0" maxversion="21.89.0"><info compressed="false">{HOST}addons.xml</info><checksum>{HOST}addons.xml.md5</checksum><datadir zip="true">{HOST}</datadir></dir></extension><extension point="xbmc.addon.metadata"><summary>DragonMax V12 Unified repository</summary><description>DragonMax V12 Unified repository for Kodi 21 Omega.</description><platform>all</platform></extension></addon>'''

ADDON=f'''{XML}\n<addon id="plugin.program.dragonmaxwizard" name="DragonMax Wizard" version="{VERSION}" provider-name="DragonMax RD"><requires><import addon="xbmc.python" version="3.0.0"/></requires><extension point="xbmc.python.pluginsource" library="default.py"><provides>executable</provides></extension><extension point="xbmc.addon.metadata"><summary>DragonMax V12 launch-candidate installer</summary><description>Protocol-4 installer with clean-runtime verification, AuraMOD Omega dependency bootstrap, transactional rollback, existing-skin preservation, and Android-safe atomic writes.</description><platform>all</platform></extension></addon>'''

DEFAULT=r'''#!/usr/bin/env python3
import hashlib,json,os,shutil,time,traceback,urllib.request,zipfile
import xml.etree.ElementTree as ET
import xbmc,xbmcaddon,xbmcgui,xbmcvfs
HOST='https://dragonmax.onrender.com/'; BUILD_JSON=HOST+'build.json'; ADDON_ID='plugin.program.dragonmaxwizard'; VERSION='4.9.0'; MIN_PROTOCOL=4
MAX_PAYLOAD_BYTES=1024*1024*1024; MAX_EXPANDED_BYTES=2*MAX_PAYLOAD_BYTES; MAX_MEMBERS=25000; SPACE_RESERVE_BYTES=64*1024*1024
AURAMOD_MIN_VERSION=(2,0,4)
ALLOWED=('addons/','userdata/','artwork/','audio/','startup/','dragonmax/'); META={'dragonmax_manifest.json','dragonmax/install_manifest.json'}
PROTECTED=('userdata/Database/','userdata/Thumbnails/','userdata/temp/','addons/packages/','temp/','cache/','dragonmax_backups/'); PROTECTED_FILES={'userdata/guisettings.xml'}
OWNED=('addons/service.dragonmax.voice/','userdata/addon_data/service.dragonmax.voice/','dragonmax/','artwork/','audio/','startup/')
BOOTSTRAP=('repository.auramod.aio','repository.jurialmunkey','repository.marcelveldt','script.colorbox')

def log(m,l=xbmc.LOGINFO): xbmc.log('[DragonMaxWizard] '+str(m),l)
def pu(p,n,m=''): p.update(int(max(0,min(100,n))),m)
def norm(r): return r.replace('\\','/').lstrip('/')
def safe_rel(r):
 r=norm(r); parts=r.split('/')
 return bool(r) and ':' not in parts[0] and not any(part in ('','.','..') for part in parts)
def protected(r): r=norm(r); return r in PROTECTED_FILES or any(r.startswith(x) for x in PROTECTED)
def installable(r): r=norm(r); return safe_rel(r) and r not in META and not protected(r) and any(r.startswith(x) for x in ALLOWED)
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
def download(u,d,p,max_bytes=MAX_PAYLOAD_BYTES):
 with req(u,300) as r,open(d,'wb') as f:
  total=int(r.headers.get('Content-Length') or 0); done=0
  if total and total>max_bytes: raise RuntimeError('Server payload exceeds the 1 GiB safety ceiling')
  while True:
   c=r.read(1048576)
   if not c: break
   f.write(c); done+=len(c)
   if done>max_bytes: raise RuntimeError('Downloaded payload exceeded the 1 GiB safety ceiling')
   if total: pu(p,min(20,done*20/total),'Downloading DragonMax V12')
 return done
def extract(zp,out,p,max_bytes=MAX_EXPANDED_BYTES,max_members=MAX_MEMBERS):
 with zipfile.ZipFile(zp) as z:
  ms=z.infolist(); total=max(1,len(ms)); base=os.path.abspath(out); seen=set()
  if len(ms)>max_members: raise RuntimeError('Payload contains too many files for the Fire TV safety budget')
  expanded=sum(m.file_size for m in ms)
  if expanded>max_bytes: raise RuntimeError('Expanded payload exceeds its declared safety limit')
  for i,m in enumerate(ms,1):
   n=m.filename.replace('\\','/').rstrip('/')
   if not safe_rel(n): raise RuntimeError('Unsafe ZIP path rejected: '+m.filename)
   if n in seen: raise RuntimeError('Duplicate ZIP path rejected: '+n)
   seen.add(n)
   mode=(m.external_attr>>16)&0o170000
   if mode==0o120000: raise RuntimeError('Symbolic links are not allowed in the payload: '+n)
   dst=os.path.abspath(os.path.join(out,n))
   if dst!=base and not dst.startswith(base+os.sep): raise RuntimeError('Unsafe ZIP path rejected: '+n)
   z.extract(m,out)
   if i==1 or i==total or i%25==0: pu(p,25+20*i/total,'Extracting package\n'+n[-70:])
  return expanded,len(ms)
def verify(root,p):
 mp=os.path.join(root,'dragonmax','install_manifest.json')
 if not os.path.isfile(mp): raise RuntimeError('Payload install manifest missing')
 manifest=json.load(open(mp,encoding='utf-8'))
 if int(manifest.get('install_protocol',0))<MIN_PROTOCOL: raise RuntimeError('Payload manifest uses obsolete install protocol')
 if str(manifest.get('version',''))!=VERSION: raise RuntimeError('Payload manifest version does not match this wizard')
 rows=manifest.get('files',[])
 if not isinstance(rows,list): raise RuntimeError('Payload install manifest file list is malformed')
 total=max(1,len(rows)); seen=set()
 for i,row in enumerate(rows,1):
  r=norm(row['path'])
  if not safe_rel(r): raise RuntimeError('Unsafe payload manifest path: '+r)
  if r in seen: raise RuntimeError('Duplicate payload manifest path: '+r)
  seen.add(r); f=os.path.join(root,r.replace('/',os.sep))
  if protected(r): raise RuntimeError('Protected runtime path leaked into payload: '+r)
  if r!='dragonmax_manifest.json' and not installable(r): raise RuntimeError('Unexpected payload manifest path: '+r)
  if not os.path.isfile(f) or os.path.getsize(f)!=int(row['size']) or sha(f).lower()!=str(row['sha256']).lower(): raise RuntimeError('Payload verification failed: '+r)
  if i==1 or i==total or i%50==0: pu(p,45+10*i/total,'Verifying payload\n'+r[-70:])
 actual=set()
 for b,_,ns in os.walk(root):
  for n in ns:
   r=norm(os.path.relpath(os.path.join(b,n),root))
   if r!='dragonmax/install_manifest.json': actual.add(r)
 if actual!=seen:
  missing=sorted(actual-seen); extra=sorted(seen-actual)
  detail=((' unlisted='+','.join(missing[:3])) if missing else '')+((' missing='+','.join(extra[:3])) if extra else '')
  raise RuntimeError('Payload manifest does not exactly cover the archive.'+detail)
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
def version_tuple(value):
 out=[]
 for part in str(value).replace('-','.').split('.'):
  digits=''.join(ch for ch in part if ch.isdigit())
  if not digits: break
  out.append(int(digits))
 return tuple(out or [0])
def addon_installed(aid):
 try: xbmcaddon.Addon(aid); return True
 except Exception: return False
def active_auramod(home):
 try:
  node=ET.parse(os.path.join(home,'addons','skin.auramod','addon.xml')).getroot()
  return version_tuple(node.attrib.get('version','0'))>=AURAMOD_MIN_VERSION
 except Exception:return False
def filter_device(home,fs):
 out=[]
 for r,s in fs:
  if active_auramod(home) and r.startswith('addons/skin.auramod/'): continue
  out.append((r,s))
 return out
def required_skin_dependencies(root):
 skin=ET.parse(os.path.join(root,'addons','skin.auramod','addon.xml')).getroot(); deps=[]
 req=skin.find('requires')
 if req is not None:
  for node in req.findall('import'):
   dep=node.attrib.get('addon',''); optional=node.attrib.get('optional','').lower()=='true'
   if optional or not dep or dep.startswith('xbmc.') or dep.startswith('kodi.'): continue
   deps.append(dep)
 return sorted(set(deps))
def bootstrap_dependencies(root,home,p):
 pu(p,95,'Preparing AuraMOD Omega dependencies')
 for aid in BOOTSTRAP:
  srcroot=os.path.join(root,'addons',aid)
  if not os.path.isfile(os.path.join(srcroot,'addon.xml')): raise RuntimeError('Dependency bootstrap addon missing from payload: '+aid)
  if not os.path.isfile(os.path.join(home,'addons',aid,'addon.xml')): raise RuntimeError('Dependency bootstrap addon was not installed: '+aid)
 xbmc.executebuiltin('UpdateLocalAddons'); xbmc.sleep(1500); xbmc.executebuiltin('UpdateAddonRepos'); xbmc.sleep(3500)
 deps=required_skin_dependencies(root); missing=[d for d in deps if not addon_installed(d) and not os.path.isdir(os.path.join(home,'addons',d))]
 if missing:
  pu(p,96,'Installing AuraMOD dependencies\n'+', '.join(missing[:3]))
  for dep in missing: xbmc.executebuiltin('InstallAddon('+dep+')')
  deadline=time.time()+120
  while time.time()<deadline:
   unresolved=[d for d in missing if not addon_installed(d) and not os.path.isdir(os.path.join(home,'addons',d))]
   if not unresolved: break
   if p.iscanceled(): raise RuntimeError('Installation cancelled during dependency setup')
   xbmc.sleep(2000)
  unresolved=[d for d in missing if not addon_installed(d) and not os.path.isdir(os.path.join(home,'addons',d))]
  if unresolved: raise RuntimeError('AuraMOD dependency installation did not complete: '+', '.join(unresolved))
 pu(p,97,'AuraMOD dependencies verified')
def preflight(home,fs):
 for top in sorted(set(r.split('/',1)[0] for r,_ in fs)):
  target=os.path.join(home,top); par=target if os.path.isdir(target) else home; q=os.path.join(par,'.dragonmax-write-probe')
  try:
   with open(q,'wb') as f:f.write(b'ok')
   os.remove(q)
  except Exception as e: raise RuntimeError('Kodi destination not writable: %s (%s)'%(par,e))
def same_file(src,dst):
 try:return os.path.getsize(src)==os.path.getsize(dst) and sha(src)==sha(dst)
 except OSError:return False
def changed_files(home,fs):
 out=[]
 for r,s in fs:
  d=os.path.join(home,r.replace('/',os.sep))
  if os.path.isfile(d) and same_file(s,d): continue
  out.append((r,s))
 return out
def expected_sizes(build):
 for key in ('compressed_size_bytes','uncompressed_size_bytes','file_count'):
  if key not in build: raise RuntimeError('Server payload metadata is missing '+key)
 compressed=int(build['compressed_size_bytes'])
 expanded=int(build['uncompressed_size_bytes'])
 members=int(build['file_count'])
 if compressed<=0 or compressed>MAX_PAYLOAD_BYTES: raise RuntimeError('Server payload size metadata is invalid')
 if expanded<compressed or expanded>MAX_EXPANDED_BYTES: raise RuntimeError('Server expanded-size metadata is invalid')
 if members<=0 or members>MAX_MEMBERS: raise RuntimeError('Server payload file-count metadata is invalid')
 return compressed,expanded,members
def ensure_space(path,required,label):
 try: free=shutil.disk_usage(path).free
 except Exception as e: raise RuntimeError('Could not verify '+label+' free space: '+str(e))
 if free<required: raise RuntimeError(label+' needs about '+str((required+1048575)//1048576)+' MB free; only '+str(free//1048576)+' MB is available')
def existing_bytes(home,fs,extra=()):
 total=0; seen=set()
 for r,_ in list(fs)+[(x,None) for x in extra]:
  d=os.path.join(home,r.replace('/',os.sep))
  if d in seen: continue
  seen.add(d)
  try:
   if os.path.isfile(d): total+=os.path.getsize(d)
  except OSError: pass
 return total
def backup(home,fs,root,p,extra=()):
 originals=[]; created=[]; rows=list(fs)+[(x,None) for x in extra]; total=max(1,len(rows)); seen=set(); os.makedirs(root,exist_ok=True)
 for i,(r,_) in enumerate(rows,1):
  if not safe_rel(r): raise RuntimeError('Unsafe rollback target: '+str(r))
  d=os.path.join(home,r.replace('/',os.sep))
  if d in seen: continue
  seen.add(d)
  if os.path.isfile(d):
   b=os.path.join(root,'originals',r.replace('/',os.sep))
   try: os.makedirs(os.path.dirname(b),exist_ok=True); shutil.copy2(d,b); originals.append((d,b))
   except (PermissionError,OSError) as e: raise RuntimeError('Could not create rollback backup for '+r+': '+str(e))
  elif not os.path.exists(d): created.append(d)
  if i==1 or i==total or i%100==0: pu(p,58+2*i/total,'Preparing transactional rollback\n'+r[-70:])
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
  if i==1 or i==total or i%25==0: pu(p,60+35*i/total,'Applying DragonMax V12\n'+r[-70:])
def main():
 dlg=xbmcgui.Dialog(); p=xbmcgui.DialogProgress()
 try: build=getjson(BUILD_JSON)['builds'][0]
 except Exception as e: dlg.ok('DragonMax Wizard','Could not load staging metadata.\n\n'+str(e)); return
 if str(build.get('version',''))!=VERSION: dlg.ok('DragonMax Wizard','Server release version does not match this wizard. Refresh the DragonMax repository and try again.'); return
 if int(build.get('install_protocol',0))<MIN_PROTOCOL: dlg.ok('DragonMax Wizard','Server payload has not passed the launch-candidate protocol gate.'); return
 if not build.get('ready',False) and not dlg.yesno('DragonMax V12 DEVICE VALIDATION','Launch-candidate package. The server has verified the clean runtime, AuraMOD Omega source, dependency repositories, payload integrity, fresh install, upgrade, and rollback simulations.\n\nRun the Fire TV validation install?'): return
 try: compressed_bytes,expanded_bytes,file_count=expected_sizes(build)
 except Exception as e: dlg.ok('DragonMax Wizard','Server release metadata failed validation.\n\n'+str(e)); return
 home=xbmcvfs.translatePath('special://home/'); w=work(); zp=os.path.join(w,'dragonmax.zip'); ex=os.path.join(w,'extract'); br=os.path.join(profile(),'backups',time.strftime('%Y%m%d-%H%M%S')); o=[]; c=[]
 try:
  ensure_space(w,compressed_bytes+expanded_bytes+SPACE_RESERVE_BYTES,'DragonMax temporary storage')
  p.create('DragonMax Wizard','Downloading DragonMax V12'); downloaded=download(HOST+str(build['zip']).lstrip('/'),zp,p); pu(p,20,'Validating package')
  if downloaded!=compressed_bytes: raise RuntimeError('Downloaded payload size does not match release metadata')
  if os.path.getsize(zp)<float(build.get('minimum_size_mb',60))*1048576: raise RuntimeError('Downloaded payload too small')
  if not build.get('sha256') or sha(zp).lower()!=str(build['sha256']).lower(): raise RuntimeError('Payload checksum mismatch')
  os.makedirs(ex,exist_ok=True); actual_expanded,actual_members=extract(zp,ex,p,max_bytes=expanded_bytes,max_members=file_count)
  if actual_expanded!=expanded_bytes or actual_members!=file_count: raise RuntimeError('Expanded payload does not match release metadata')
  roots=[os.path.join(ex,n) for n in os.listdir(ex) if os.path.isdir(os.path.join(ex,n))]
  if len(roots)!=1: raise RuntimeError('Unexpected payload layout')
  root=roots[0]; verify(root,p); fs=changed_files(home,filter_device(home,files(root)))
  marker='userdata/addon_data/service.dragonmax.voice/pending_skin_activation.json'; preflight(home,fs)
  ensure_space(home,expanded_bytes+existing_bytes(home,fs,(marker,))+SPACE_RESERVE_BYTES,'Kodi installation storage')
  o,c=backup(home,fs,br,p,(marker,)); apply(home,fs,p); bootstrap_dependencies(root,home,p); pu(p,100,'Installation complete'); p.close(); dlg.ok('DragonMax V12 Installed','Fire TV validation install completed.\n\nFully exit Kodi and reopen it.\n\nTransactional rollback data: '+br)
 except Exception as e:
  log(traceback.format_exc(),xbmc.LOGERROR)
  try:p.close()
  except Exception:pass
  if o or c:
   rollback(o,c); dlg.ok('DragonMax Install Failed',str(e)+'\n\nTransactional rollback restored the previous installation. Dependency addons installed by Kodi may remain available for reuse.')
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
  for n in sorted(files):
   info=zipfile.ZipInfo(folder+'/'+n,date_time=(2026,1,1,0,0,0))
   info.compress_type=zipfile.ZIP_DEFLATED; info.create_system=3; info.external_attr=0o100644<<16
   q.writestr(info,files[n])
 return out.getvalue()
def frag(x): return x.replace(XML,'',1).strip()
def gates(s):
 tree=ast.parse(s)
 for token in ['MIN_PROTOCOL=4','MAX_PAYLOAD_BYTES','bootstrap_dependencies','InstallAddon(','UpdateAddonRepos','UpdateLocalAddons','BOOTSTRAP','filter_device','changed_files','expected_sizes','ensure_space','atomic','rollback','preflight','Transactional rollback']:
  if token not in s: raise RuntimeError('Installer gate missing '+token)
 for node in ast.walk(tree):
  if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr in ('create','update') and isinstance(node.func.value,ast.Name) and node.func.value.id=='p' and len(node.args)>2: raise RuntimeError('Kodi DialogProgress API arity regression')
def publish(root:Path,out:Path):
 addons=XML+'\n<addons>\n'+frag(REPO)+'\n'+frag(ADDON)+'\n</addons>\n'; compile(DEFAULT,'default.py','exec'); gates(DEFAULT)
 ET.fromstring(addons)
 addons_bytes=addons.encode('utf-8')
 (out/'addons.xml').write_bytes(addons_bytes); (out/'addons.xml.md5').write_text(hashlib.md5(addons_bytes).hexdigest(),encoding='ascii')
 rz=z('repository.dragonmax',{'addon.xml':REPO}); wz=z('plugin.program.dragonmaxwizard',{'addon.xml':ADDON,'default.py':DEFAULT})
 for aid,data in [('repository.dragonmax',rz),('plugin.program.dragonmaxwizard',wz)]:
  d=out/aid; d.mkdir(parents=True,exist_ok=True); (out/f'{aid}-{VERSION}.zip').write_bytes(data); (d/f'{aid}-{VERSION}.zip').write_bytes(data)
  with zipfile.ZipFile(out/f'{aid}-{VERSION}.zip') as q:
    if q.testzip(): raise RuntimeError('Corrupt generated installer ZIP')
    names=[n.replace('\\','/').strip('/') for n in q.namelist() if n and not n.endswith('/')]
    if {n.split('/',1)[0] for n in names}!={aid}: raise RuntimeError('Malformed installer root for '+aid)
    if aid+'/addon.xml' not in names: raise RuntimeError('Installer missing root addon.xml for '+aid)
    if len(names)!=len(set(names)): raise RuntimeError('Duplicate installer path for '+aid)
 print('DragonMax Wizard '+VERSION+' generated; protocol-4 Omega dependency-bootstrap gates passed.')
