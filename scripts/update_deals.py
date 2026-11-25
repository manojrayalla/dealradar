import hashlib, html, json, re, time, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path

OUT = Path("data/deals.json")
HEADERS = {"User-Agent": "DealRadar/1.0 (+https://github.com/manojrayalla/dealradar)"}
SOURCES = [
    ("Slickdeals", "https://slickdeals.net/rss.php"),
    ("Slickdeals Frontpage", "https://slickdeals.net/newsearch.php?mode=frontpage&rss=1&searcharea=deals&searchin=first"),
    ("DealNews", "https://www.dealnews.com/rss/todays-edition"),
    ("DealNews Editors Choice", "https://www.dealnews.com/rss/editors-choice/"),
]
TERMS = ["leather sectional sofa","sectional sofa","leather couch","room heater","space heater","infrared heater","home gym","gym equipment","adjustable dumbbells","treadmill","north face jacket","northface jacket","winter jacket","puffer jacket","kids shoes","kids sneakers","children shoes","running shoes","boots","laptop","tablet","headphones","smart tv","robot vacuum","air fryer","mattress","office chair","patio furniture","bedding","kitchen appliances","gaming","monitor","tools","baby gear","toys","backpack","washer dryer","refrigerator","coffee maker"]
for term in TERMS:
    params = urllib.parse.urlencode({"searchin":"first","search":term,"rss":"1"})
    SOURCES.append(("Slickdeals Search", "https://slickdeals.net/newsearch.php?"+params))

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.hrefs=[]
    def handle_starttag(self, tag, attrs):
        if tag.lower()=="a":
            href=dict(attrs).get("href","")
            if href.startswith(("http://","https://")): self.hrefs.append(href)

def clean_text(s):
    return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",s or ""))).strip()

def classify(title, desc):
    s=(title+" "+desc).lower()
    groups=[
      ("Furniture",["sectional","sofa","couch","recliner","loveseat","mattress","bed frame","dresser"]),
      ("Heating & Cooling",["space heater","room heater","infrared heater","heater","air purifier","humidifier","fan","air conditioner"]),
      ("Home Gym",["home gym","dumbbell","barbell","weight bench","treadmill","exercise bike","rowing machine","elliptical","gym equipment"]),
      ("Jackets & Outerwear",["north face","northface","jacket","parka","puffer","fleece","coat","vest"]),
      ("Kids Shoes",["kids shoes","kid shoes","children shoes","toddler shoes","kids sneaker","toddler sneaker","youth shoes"]),
      ("Shoes",["sneaker","running shoe","hiking shoe","boots","footwear","shoes"]),
      ("Tech",["laptop","computer","tablet","phone","iphone","android","headphone","earbud","monitor","tv","television","camera","ssd","router","gaming","speaker"]),
      ("Kitchen",["air fryer","cookware","blender","coffee maker","espresso","instant pot","microwave","dishwasher","kitchen"]),
      ("Home",["vacuum","bedding","duvet","pillow","towel","storage","furniture","home decor","washer","dryer","refrigerator"]),
      ("Kids & Toys",["lego","toy","stroller","car seat","baby","kids","children","diaper"]),
      ("Fashion",["jeans","shirt","dress","clothing","apparel","backpack","handbag","sunglasses"]),
      ("Tools & Outdoors",["tool","drill","saw","grill","camping","patio","outdoor","garden"])]
    for category,keys in groups:
        if any(k in s for k in keys): return category
    return "Other Deals"

def get_text(node, tags):
    for tag in tags:
        el=node.find(tag)
        if el is not None and el.text: return el.text.strip()
    return ""

def parse_item(item, source):
    title=get_text(item,["title"])
    feed_url=get_text(item,["link"])
    desc=get_text(item,["description","{http://purl.org/rss/1.0/modules/content/}encoded"])
    if not title or not feed_url.startswith(("http://","https://")): return None
    plain=clean_text(desc)
    host=urllib.parse.urlparse(feed_url).netloc.lower()
    merchant_url=None
    # Prefer an explicit outbound retailer link embedded in the publisher's feed description.
    parser=Links()
    try: parser.feed(desc or "")
    except Exception: pass
    publisher_hosts=("slickdeals.net","dealnews.com")
    for candidate in parser.hrefs:
        candidate_host=urllib.parse.urlparse(candidate).netloc.lower()
        if candidate_host and not any(candidate_host==p or candidate_host.endswith("."+p) for p in publisher_hosts):
            merchant_url=candidate; break
    # If the feed item itself is a retailer URL, it is already the direct destination.
    if host and not any(host==p or host.endswith("."+p) for p in publisher_hosts):
        merchant_url=feed_url
    pub=get_text(item,["pubDate","{http://purl.org/dc/elements/1.1/}date"])
    try:
        dt=parsedate_to_datetime(pub) if pub else datetime.now(timezone.utc)
        if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
        published=dt.astimezone(timezone.utc).isoformat()
    except Exception: published=datetime.now(timezone.utc).isoformat()
    guid=get_text(item,["guid"]) or feed_url
    ident=hashlib.sha1(guid.encode()).hexdigest()[:16]
    blob=title+" "+plain
    pm=re.search(r"\$\s?(\d[\d,]*(?:\.\d{1,2})?)",blob)
    dm=re.search(r"(\d{1,2})\s?%\s?(?:off|discount)?",blob,re.I)
    price=float(pm.group(1).replace(",","")) if pm else None
    discount=int(dm.group(1)) if dm and int(dm.group(1))<=95 else None
    category=classify(title,plain)
    score=min(99,50+(min(discount,40) if discount else 0)+(8 if source.startswith("DealNews") else 4))
    return {"id":ident,"title":title,"url":feed_url,"merchant_url":merchant_url,"description":plain[:500],"source":source,"merchant":urllib.parse.urlparse(merchant_url or feed_url).netloc.replace("www.","") or source,"category":category,"price":price,"discount":discount,"score":score,"published":published}

def main():
    items={}; errors=[]
    for source,url in SOURCES:
        try:
            req=urllib.request.Request(url,headers=HEADERS)
            with urllib.request.urlopen(req,timeout=25) as response: raw=response.read(4000000)
            root=ET.fromstring(raw)
            nodes=root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
            for node in nodes:
                deal=parse_item(node,source)
                if deal: items[deal["id"]]=deal
            time.sleep(.2)
        except Exception as exc: errors.append(source+": "+type(exc).__name__)
    previous=[]
    if OUT.exists():
        try: previous=json.loads(OUT.read_text(encoding="utf-8")).get("deals",[])
        except Exception: pass
    for deal in previous: items.setdefault(deal["id"],deal)
    deals=sorted(items.values(),key=lambda d:(d.get("published",""),d.get("score",0)),reverse=True)[:1000]
    OUT.parent.mkdir(parents=True,exist_ok=True)
    payload={"updated_at":datetime.now(timezone.utc).isoformat(),"count":len(deals),"target_count":500,"sources":sorted({d["source"] for d in deals}),"feed_errors":errors,"deals":deals}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Saved",len(deals),"unique offers; feed errors:",len(errors))
    if len(deals)<500: print("Fewer than 500 offers currently available; no fake deals were generated.")
if __name__=="__main__": main()
