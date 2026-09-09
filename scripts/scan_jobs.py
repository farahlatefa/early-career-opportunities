#!/usr/bin/env python3
"""Hourly collector for public early-career job listings.

Sources included by default:
- Arbeitnow public API
- Remotive public API
- Remote OK public API
- Adzuna API when ADZUNA_APP_ID and ADZUNA_APP_KEY are configured as GitHub secrets

The collector is intentionally source-agnostic: it does not maintain a whitelist of companies.
It searches broad early-career terms and classifies qualifying roles into the dashboard sectors.
"""
from __future__ import annotations
import json, os, re, hashlib, html
from datetime import datetime, timezone, date
from pathlib import Path
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "opportunities.json"
TIMEOUT = 20
UA = {"User-Agent": "EarlyCareerOpportunitiesBot/1.0 (+GitHub Pages project; public-job aggregation)"}

SECTOR_KEYWORDS = {
 "Biology & Life Sciences": ["biology","biologist","biotech","biotechnology","life science","molecular","cell culture","microbiology","genomics","laboratory","lab technician","clinical research"],
 "Consulting": ["consultant","consulting","advisory"],
 "Data & Analytics": ["data analyst","analytics","business intelligence","bi analyst","data science"],
 "Finance": ["finance","financial analyst","investment","treasury","accounting","audit"],
 "Healthcare": ["healthcare","health care","public health","clinical","hospital"],
 "Humanitarian / NGO": ["humanitarian","ngo","nonprofit","relief","refugee","human rights"],
 "International Development": ["international development","development programme","development program","sdg","global development"],
 "Marketing & Communications": ["marketing","communications","public relations","content","social media","brand"],
 "Operations": ["operations","operational"],
 "Policy / Government": ["policy","government","public affairs","public policy"],
 "Procurement": ["procurement","buyer","purchasing","strategic sourcing","sourcing analyst"],
 "Research": ["research assistant","research associate","research analyst","research intern"],
 "Sales / Business Development": ["sales","business development","account executive","growth"],
 "Sports": ["sports","sport","football","soccer","athletics","formula 1","motorsport"],
 "Supply Chain": ["supply chain","logistics","inventory","demand planning","distribution","warehouse"],
 "Sustainability / ESG": ["sustainability","esg","climate","environmental"],
 "Technology / IT": ["software","developer","engineer","information technology","it analyst","cybersecurity","cloud","systems analyst"]
}
EARLY = ["intern","internship","graduate","new grad","entry level","entry-level","early career","junior","trainee","apprentice","rotational","rotation program","associate","analyst","research assistant","0-1 year","0-2 year","1-2 year"]
SENIOR = ["senior manager","sr manager","director","vice president","vp ","head of","principal","staff engineer","lead engineer","5+ years","6+ years","7+ years","8+ years","10+ years"]
REPORT_PATTERNS = [
 r"reports? (?:directly )?to (?:the )?([^.;\n]{3,100})",
 r"reporting (?:directly )?to (?:the )?([^.;\n]{3,100})",
 r"you(?:'|’)ll report (?:directly )?to (?:the )?([^.;\n]{3,100})"
]


def clean_text(s):
    soup=BeautifulSoup(html.unescape(s or ""),"html.parser")
    return re.sub(r"\s+"," ",soup.get_text(" ")).strip()

def early_career(title, desc):
    text=(title+" "+desc).lower()
    if any(x in text for x in SENIOR): return False
    return any(x in text for x in EARLY)

def employment_type(title, desc, raw=""):
    text=(title+" "+desc+" "+raw).lower()
    return "Internship" if "intern" in text else "Full-Time"

def classify(title, desc):
    text=(title+" "+desc).lower()
    out=[s for s,ks in SECTOR_KEYWORDS.items() if any(k in text for k in ks)]
    return out or ["Operations"]

def reports_to(desc):
    for p in REPORT_PATTERNS:
        m=re.search(p,desc,re.I)
        if m:
            val=m.group(1).strip(" :-")[:100]
            return {"name": None, "title": val}
    return {"name": None, "title": None}

def parse_deadline(desc):
    # Conservative: only parse explicit closing/deadline phrases.
    m=re.search(r"(?:deadline|closing date|applications? close(?:s)?(?: on)?|apply by)[:\s-]{0,8}([A-Za-z]{3,9}\s+\d{1,2},?\s+20\d{2}|\d{1,2}[/-]\d{1,2}[/-]20\d{2}|20\d{2}-\d{2}-\d{2})",desc,re.I)
    if not m: return None
    try: return dateparser.parse(m.group(1),dayfirst=False).date().isoformat()
    except Exception: return None

def work_mode(text):
    t=text.lower()
    if "hybrid" in t:return "Hybrid"
    if "remote" in t:return "Remote"
    return "On-site"

def stable_id(company,title,location,url):
    raw="|".join([company or "",title or "",location or "",url or ""])
    return hashlib.sha1(raw.encode()).hexdigest()[:16]

def normalize(title,company,location,desc,url,source,posted=None,raw_type="",country=None):
    desc=clean_text(desc)
    if not title or not url or not early_career(title,desc): return None
    loc=location or ""
    city=loc; region=None; ctry=country
    parts=[p.strip() for p in loc.split(',') if p.strip()]
    if parts: city=parts[0]
    if len(parts)>=2 and not ctry: ctry=parts[-1]
    return {
      "id": stable_id(company,title,loc,url),
      "title": title.strip(), "company": (company or "Unknown organization").strip(),
      "employmentType": employment_type(title,desc,raw_type),
      "location": {"city": city or None,"region": region,"country": ctry,"workMode": work_mode(title+" "+desc+" "+loc)},
      "sectors": classify(title,desc), "deadline": parse_deadline(desc),
      "postedDate": posted, "reportsTo": reports_to(desc),
      "summary": desc[:260] + ("…" if len(desc)>260 else ""),
      "applicationUrl": url, "source": source
    }

def fetch_json(url,params=None):
    r=requests.get(url,params=params,headers=UA,timeout=TIMEOUT);r.raise_for_status();return r.json()

def scan_arbeitnow():
    out=[]
    for page in range(1,4):
        try:data=fetch_json("https://www.arbeitnow.com/api/job-board-api",{"page":page})
        except Exception:break
        for x in data.get("data",[]):
posted=datetime.fromtimestamp(x["created_at"], timezone.utc).strftime("%Y-%m-%d") if isinstance(x.get("created_at"), (int, float)) else str(x.get("created_at") or "")[:10] or None            j=normalize(x.get("title",""),x.get("company_name",""),x.get("location",""),x.get("description",""),x.get("url",""),"Arbeitnow",posted,"",None)
            if j:out.append(j)
    return out

def scan_remotive():
    out=[]
    try:data=fetch_json("https://remotive.com/api/remote-jobs")
    except Exception:return out
    for x in data.get("jobs",[]):
        posted=(x.get("publication_date") or "")[:10] or None
        j=normalize(x.get("title",""),x.get("company_name",""),x.get("candidate_required_location") or "Remote",x.get("description",""),x.get("url",""),"Remotive",posted,x.get("job_type","") ,None)
        if j:out.append(j)
    return out

def scan_remoteok():
    out=[]
    try:data=fetch_json("https://remoteok.com/api")
    except Exception:return out
    for x in data[1:] if isinstance(data,list) else []:
        posted=None
        if x.get("date"):
            try: posted=dateparser.parse(x["date"]).date().isoformat()
            except Exception: pass
        j=normalize(x.get("position",""),x.get("company",""),x.get("location") or "Remote",x.get("description",""),x.get("url") or x.get("apply_url") or "","Remote OK",posted,"",None)
        if j:out.append(j)
    return out

def scan_adzuna():
    app_id=os.getenv("ADZUNA_APP_ID"); key=os.getenv("ADZUNA_APP_KEY")
    if not app_id or not key:return []
    out=[]
    countries=[c.strip() for c in os.getenv("ADZUNA_COUNTRIES","us,gb,ca").split(',') if c.strip()]
    queries=[
      "internship","entry level analyst","graduate program","junior analyst","procurement analyst",
      "supply chain analyst","biology research assistant","life sciences associate","marketing associate",
      "operations analyst","policy assistant","data analyst","finance analyst","consulting analyst"
    ]
    for country in countries:
      for q in queries:
        try:data=fetch_json(f"https://api.adzuna.com/v1/api/jobs/{country}/search/1",{"app_id":app_id,"app_key":key,"results_per_page":50,"what":q,"content-type":"application/json"})
        except Exception:continue
        for x in data.get("results",[]):
          loc=(x.get("location") or {}).get("display_name") or ""
          posted=None
          if x.get("created"):
            try: posted=dateparser.parse(x["created"]).date().isoformat()
            except Exception:pass
          j=normalize(x.get("title",""),(x.get("company") or {}).get("display_name",""),loc,x.get("description",""),x.get("redirect_url",""),"Adzuna",posted,x.get("contract_type","") ,None)
          if j:out.append(j)
    return out

def load_existing():
    try:return json.loads(OUT.read_text()).get("jobs",[])
    except Exception:return []

def dedupe(rows):
    by={}
    for j in rows:
        key=(j.get("applicationUrl") or j.get("id"))
        by[key]=j
    # Remove listings with explicit past deadlines.
    today=date.today().isoformat()
    return [j for j in by.values() if not j.get("deadline") or j["deadline"]>=today]

def main():
    existing=load_existing()
    jobs=existing + scan_arbeitnow() + scan_remotive() + scan_remoteok() + scan_adzuna()
    jobs=dedupe(jobs)
    jobs.sort(key=lambda x:x.get("postedDate") or "",reverse=True)
    payload={"meta":{"lastUpdated":datetime.now(timezone.utc).isoformat(),"sources":["Arbeitnow","Remotive","Remote OK"] + (["Adzuna"] if os.getenv("ADZUNA_APP_ID") else [])},"jobs":jobs}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False))
    print(f"Saved {len(jobs)} active early-career opportunities")

if __name__=="__main__":main()

