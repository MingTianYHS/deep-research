from __future__ import annotations
import json,os,tempfile,time,uuid
from contextlib import contextmanager
from datetime import datetime,timezone
from pathlib import Path
from typing import Any,Iterator
def utc_now()->str:return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
def read_json(path:Path,default:Any)->Any:return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
def _pid_alive(pid:int)->bool:
 if pid<=0:return False
 try:os.kill(pid,0);return True
 except PermissionError:return True
 except (ProcessLookupError,OSError):return False
def _lock_owner(path:Path)->dict[str,Any]:
 try:return json.loads(path.read_text(encoding="utf-8"))
 except (OSError,json.JSONDecodeError):return {}
@contextmanager
def exclusive_lock(path:Path,timeout_seconds:float=10.0,stale_seconds:float=300.0):
 path.parent.mkdir(parents=True,exist_ok=True);deadline=time.monotonic()+timeout_seconds;fd=None;token=uuid.uuid4().hex;payload=json.dumps({"pid":os.getpid(),"token":token,"created_at":utc_now()}).encode()
 while fd is None:
  try:fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,payload);os.fsync(fd)
  except FileExistsError:
   try:
    owner=_lock_owner(path);stale=time.time()-path.stat().st_mtime>stale_seconds
    if stale and not _pid_alive(int(owner.get("pid",0))):path.unlink();continue
   except FileNotFoundError:continue
   if time.monotonic()>=deadline:raise TimeoutError(f"timed out waiting for lock: {path}")
   time.sleep(.05)
 try:yield
 finally:
  if fd is not None:os.close(fd)
  try:
   if _lock_owner(path).get("token")==token:path.unlink()
  except FileNotFoundError:pass
def atomic_write_json(path:Path,value:Any)->None:
 path.parent.mkdir(parents=True,exist_ok=True);fd,temp_name=tempfile.mkstemp(prefix=f".{path.name}.",dir=path.parent,text=True)
 try:
  with os.fdopen(fd,"w",encoding="utf-8") as handle:json.dump(value,handle,ensure_ascii=False,indent=2);handle.write("\n");handle.flush();os.fsync(handle.fileno())
  os.replace(temp_name,path)
 finally:
  if os.path.exists(temp_name):os.unlink(temp_name)
def iter_jsonl(path:Path)->Iterator[tuple[int,dict[str,Any]]]:
 if not path.exists():return
 for number,line in enumerate(path.read_text(encoding="utf-8").splitlines(),1):
  if line.strip():yield number,json.loads(line)
def append_jsonl(path:Path,records:list[dict[str,Any]])->None:
 if not records:return
 path.parent.mkdir(parents=True,exist_ok=True)
 with exclusive_lock(path.with_name(path.name+".lock")):
  with path.open("a",encoding="utf-8") as handle:
   for record in records:handle.write(json.dumps(record,ensure_ascii=False,separators=(",",":"))+"\n")
   handle.flush();os.fsync(handle.fileno())
