import json, re, sys
from urllib.parse import urlparse
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup
HEADERS={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36","Accept-Language":"en-IN,en;q=0.9"}
SIZE_PATTERN=re.compile(r'^(?:XS|S|M|L|XL|XXL|XXXL|3XL|4XL|5XL|6XL)$',re.I)
def check(url):
 p=urlparse(url); host=(p.hostname or '').lower()
 if p.scheme not in ('http','https') or not (host=='flipkart.com' or host.endswith('.flipkart.com')): raise ValueError('Only Flipkart product URLs are accepted.')
 r=requests.get(url,headers=HEADERS,timeout=30)
 if r.status_code!=200: raise ValueError(f'Flipkart returned HTTP {r.status_code}.')
 soup=BeautifulSoup(r.content,'html.parser'); title=soup.title.get_text(' ',strip=True) if soup.title else 'Flipkart product'; found={}; tags=['a','button','div','span','li','label']
 for e in soup.find_all(tags):
  size=e.get_text(' ',strip=True).upper()
  if not SIZE_PATTERN.fullmatch(size): continue
  if e.find(lambda c:c.name in tags and c.get_text(' ',strip=True).upper()==size): continue
  old=found.get(size)
  if old is None or ('color:' not in old.get('style','').lower() and 'color:' in e.get('style','').lower()): found[size]=e
 if not found: raise ValueError('No sizes found in returned HTML; browser rendering may be required.')
 results=[]
 for size,e in found.items():
  cur=e; status='AVAILABLE'; reason='No grey/cross-out indicator detected'
  for _ in range(4):
   if cur is None: break
   style=cur.get('style','').lower(); classes=' '.join(cur.get('class',[])).lower(); combined=style+' '+classes
   if str(cur.get('aria-disabled','')).lower()=='true' or cur.has_attr('disabled'): status,reason='OUT OF STOCK','Disabled element'; break
   if re.search(r'text-decoration\s*:[^;]*line-through|line-through|strikethrough|strike-through',combined): status,reason='OUT OF STOCK','Strike-through detected'; break
   m=re.search(r'color\s*:\s*#([0-9a-f]{6,8})',style)
   if m and m.group(1)[:6]=='707070': status,reason='OUT OF STOCK','Grey text (#707070)'; break
   cur=cur.parent
  results.append({'size':size,'status':status,'reason':reason})
 return {'ok':True,'product_url':url,'title':title,'checked_at':datetime.now(timezone.utc).isoformat(),'http_status':r.status_code,'results':results,'available_count':sum(x['status']=='AVAILABLE' for x in results),'out_of_stock_count':sum(x['status']=='OUT OF STOCK' for x in results),'unknown_count':sum(x['status']=='UNKNOWN' for x in results),'note':'Uses observed grey/cross-out rule; verify against product page.'}
if __name__=='__main__':
 out=sys.argv[2] if len(sys.argv)>2 else 'result.json'
 try:
  if len(sys.argv)!=3: raise ValueError('Usage: python stock_check.py PRODUCT_URL OUTPUT_JSON')
  data=check(sys.argv[1]); code=0
 except Exception as exc:
  data={'ok':False,'error':str(exc),'checked_at':datetime.now(timezone.utc).isoformat()}; code=1
 with open(out,'w',encoding='utf-8') as f: json.dump(data,f,ensure_ascii=False,indent=2)
 print(json.dumps(data,ensure_ascii=False,indent=2)); sys.exit(code)
