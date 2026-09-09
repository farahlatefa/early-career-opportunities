const SECTORS = [
  "Biology & Life Sciences","Consulting","Data & Analytics","Finance","Healthcare",
  "Humanitarian / NGO","International Development","Marketing & Communications","Operations",
  "Policy / Government","Procurement","Research","Sales / Business Development","Sports",
  "Supply Chain","Sustainability / ESG","Technology / IT"
];

const state = { jobs: [], meta: {} };
const $ = id => document.getElementById(id);
const els = {
  search: $("searchInput"), type: $("typeFilter"), location: $("locationFilter"),
  deadline: $("deadlineFilter"), reports: $("reportsFilter"), sector: $("sectorFilter"),
  workMode: $("workModeFilter"), sort: $("sortSelect"), clear: $("clearFilters"),
  jobs: $("jobs"), empty: $("emptyState"), count: $("jobCount"), updated: $("lastUpdated"),
  active: $("activeFilters")
};

SECTORS.forEach(s => { const o=document.createElement('option');o.value=s;o.textContent=s;els.sector.appendChild(o); });

function norm(v){ return String(v ?? '').toLowerCase().trim(); }
function formatDate(v){ if(!v) return 'Not listed / rolling'; const d=new Date(v+'T12:00:00'); return Number.isNaN(d.getTime())?v:d.toLocaleDateString(undefined,{year:'numeric',month:'short',day:'numeric'}); }
function daysUntil(v){ if(!v) return null; const d=new Date(v+'T23:59:59'); return Math.ceil((d-Date.now())/86400000); }
function locationText(j){ return [j.location?.city,j.location?.region,j.location?.country,j.location?.workMode].filter(Boolean).join(', '); }
function reportsText(j){ return [j.reportsTo?.name,j.reportsTo?.title].filter(Boolean).join(' · ') || 'Not listed'; }
function escapeHtml(s=''){ return s.replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }

function isNew(j){ if(!j.postedDate) return false; const d=new Date(j.postedDate+'T00:00:00'); return (Date.now()-d.getTime()) <= 3*86400000; }
function matchesDeadline(job, filter){
  if(!filter) return true;
  if(filter==='rolling') return !job.deadline;
  if(!job.deadline) return false;
  const days=daysUntil(job.deadline); return days>=0 && days<=Number(filter);
}

function filteredJobs(){
  const q=norm(els.search.value), loc=norm(els.location.value), rep=norm(els.reports.value);
  let rows=state.jobs.filter(j=>{
    const hay=norm([j.title,j.company,j.summary,j.description,(j.sectors||[]).join(' '),locationText(j)].join(' '));
    return (!q||hay.includes(q)) &&
      (!els.type.value||j.employmentType===els.type.value) &&
      (!loc||norm(locationText(j)).includes(loc)) &&
      matchesDeadline(j,els.deadline.value) &&
      (!rep||norm(reportsText(j)).includes(rep)) &&
      (!els.sector.value||(j.sectors||[]).includes(els.sector.value)) &&
      (!els.workMode.value||j.location?.workMode===els.workMode.value);
  });
  rows.sort((a,b)=>{
    if(els.sort.value==='deadline') return (a.deadline||'9999-12-31').localeCompare(b.deadline||'9999-12-31');
    if(els.sort.value==='company') return (a.company||'').localeCompare(b.company||'');
    return (b.postedDate||'').localeCompare(a.postedDate||'');
  });
  return rows;
}

function render(){
  const jobs=filteredJobs();
  els.count.textContent=`${jobs.length} ${jobs.length===1?'opportunity':'opportunities'}`;
  els.jobs.innerHTML=jobs.map(j=>{
    const d=daysUntil(j.deadline); const soon=d!==null&&d>=0&&d<=7;
    const badges=[isNew(j)?'<span class="badge new">NEW</span>':'',soon?'<span class="badge soon">CLOSING SOON</span>':'',`<span class="badge">${escapeHtml(j.employmentType||'Early Career')}</span>`].join('');
    const sectors=(j.sectors||[]).map(s=>`<span class="sector">${escapeHtml(s)}</span>`).join('');
    return `<article class="job-card">
      <div class="job-top"><div><div class="company">${escapeHtml(j.company||'Unknown organization')}</div><h2 class="job-title">${escapeHtml(j.title||'Untitled role')}</h2></div><div class="badges">${badges}</div></div>
      <div class="details">
        <div class="detail"><span>Location</span>${escapeHtml(locationText(j)||'Not listed')}</div>
        <div class="detail"><span>Deadline</span>${escapeHtml(formatDate(j.deadline))}</div>
        <div class="detail"><span>Reports to</span>${escapeHtml(reportsText(j))}</div>
        <div class="detail"><span>Posted</span>${escapeHtml(formatDate(j.postedDate))}</div>
      </div>
      <div class="sectors">${sectors}</div>
      ${j.summary?`<div class="summary">${escapeHtml(j.summary)}</div>`:''}
      <div class="card-actions"><span class="source">Source: ${escapeHtml(j.source||'Public listing')}</span><a class="apply" href="${escapeHtml(j.applicationUrl)}" target="_blank" rel="noopener noreferrer">Open application ↗</a></div>
    </article>`;
  }).join('');
  els.empty.classList.toggle('hidden',jobs.length!==0);
  renderActive();
}

function renderActive(){
  const items=[];
  if(els.type.value) items.push(`Type: ${els.type.value}`);
  if(els.location.value) items.push(`Location: ${els.location.value}`);
  if(els.deadline.value) items.push(`Deadline: ${els.deadline.options[els.deadline.selectedIndex].text}`);
  if(els.reports.value) items.push(`Reports to: ${els.reports.value}`);
  if(els.sector.value) items.push(`Sector: ${els.sector.value}`);
  if(els.workMode.value) items.push(`Work: ${els.workMode.value}`);
  els.active.innerHTML=items.map(x=>`<span class="chip">${escapeHtml(x)}</span>`).join('');
}

[els.search,els.type,els.location,els.deadline,els.reports,els.sector,els.workMode,els.sort].forEach(el=>el.addEventListener(el.tagName==='INPUT'?'input':'change',render));
els.clear.addEventListener('click',()=>{[els.search,els.location,els.reports].forEach(x=>x.value='');[els.type,els.deadline,els.sector,els.workMode].forEach(x=>x.value='');els.sort.value='newest';render();});

async function init(){
  try{
    const res=await fetch(`data/opportunities.json?ts=${Date.now()}`,{cache:'no-store'});
    if(!res.ok) throw new Error('Could not load jobs');
    const payload=await res.json();
    state.jobs=payload.jobs||[]; state.meta=payload.meta||{};
    const u=state.meta.lastUpdated ? new Date(state.meta.lastUpdated) : null;
    els.updated.textContent=`Last updated: ${u&&!Number.isNaN(u.getTime())?u.toLocaleString():'Not yet scanned'}`;
    render();
  }catch(err){
    els.updated.textContent='Last updated: unavailable';
    els.jobs.innerHTML='<div class="empty"><h2>Job data could not be loaded.</h2><p>Refresh the page or try again shortly.</p></div>';
  }
}
init();
