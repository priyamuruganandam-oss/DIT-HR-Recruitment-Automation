const API_BASE = localStorage.getItem("DIT_API_BASE") || "https://dit-hr-recruitment-automation.onrender.com";
let candidates=[], exceptions=[], chart=null;
const $=id=>document.getElementById(id);
const matched=()=>candidates.filter(c=>c.screening_recommendation==="Meets review threshold");
const rejected=()=>candidates.filter(c=>c.screening_recommendation!=="Meets review threshold");
function toast(msg){const t=$("toast");t.textContent=msg;t.style.display="block";setTimeout(()=>t.style.display="none",3000)}
function setView(view){
 document.querySelectorAll(".view").forEach(x=>x.classList.toggle("active",x.id===view));
 document.querySelectorAll(".nav").forEach(x=>x.classList.toggle("active",x.dataset.view===view));
 const titles={overview:"Recruitment overview",screening:"Candidate screening",matched:"Matched candidates",rejected:"Rejected candidates",exceptions:"Data exceptions",candidates:"Candidate directory",reports:"Reports & exports"};
 $("pageTitle").textContent=titles[view]||"Recruitment overview";
 if(view==="overview")loadDashboard();
 if(view==="candidates")renderDirectory();
 if(["matched","rejected","exceptions"].includes(view))renderSeparatedViews();
}
document.querySelectorAll(".nav").forEach(b=>b.addEventListener("click",()=>setView(b.dataset.view)));
document.querySelectorAll("[data-go]").forEach(b=>b.addEventListener("click",()=>setView(b.dataset.go)));
$("refreshBtn").addEventListener("click",async()=>{const b=$("refreshBtn");b.disabled=true;b.textContent="↻ Refreshing…";const ok=await loadDashboard();b.disabled=false;b.textContent="↻ Refresh";toast(ok?"Dashboard refreshed":"Could not refresh dashboard");});
function message(text,type="success"){$("screeningMessage").textContent=text;$("screeningMessage").className=`message ${type}`;}
function esc(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
function statusSelect(c){const status=c.hr_review_status||"Pending HR review";return `<select class="review-select" data-id="${esc(c.candidate_id)}"><option ${status==="Pending HR review"?"selected":""}>Pending HR review</option><option ${status==="HR approved for interview"?"selected":""}>HR approved for interview</option><option ${status==="Hold"?"selected":""}>Hold</option><option ${status==="Not selected by HR"?"selected":""}>Not selected by HR</option></select>`}
function renderResults(){
 $("recentRows").innerHTML=matched().slice(0,5).map(c=>`<tr><td>${esc(c.full_name)}</td><td>${esc(c.applied_role)}</td><td>${Number(c.match_score).toFixed(1)}%</td><td>${esc(c.screening_recommendation)}</td><td>${esc(c.hr_review_status)}</td></tr>`).join("")||'<tr><td colspan="5" class="empty-note">No matched candidates yet.</td></tr>';
 $("rTotal").textContent=candidates.length+exceptions.length;$("rValid").textContent=candidates.length;$("rExceptions").textContent=exceptions.length;$("rAbove").textContent=matched().length;
 renderSeparatedViews();
}
function renderSeparatedViews(){
 const yes=matched(),no=rejected();
 $("matchedCount").textContent=`${yes.length} matched`;$("rejectedCount").textContent=`${no.length} rejected`;$("exceptionCount").textContent=`${exceptions.length} exceptions`;
 $("matchedRows").innerHTML=yes.map(c=>`<tr><td><b>${esc(c.full_name)}</b><br><small>${esc(c.candidate_id)}</small></td><td>${esc(c.email)}</td><td>${esc(c.experience_years)} yrs</td><td><b>${Number(c.match_score).toFixed(1)}%</b></td><td>${statusSelect(c)}</td></tr>`).join("")||'<tr><td colspan="5" class="empty-note">No matched candidates for the current requirements.</td></tr>';
 $("rejectedRows").innerHTML=no.map(c=>`<tr><td><b>${esc(c.full_name)}</b><br><small>${esc(c.candidate_id)}</small></td><td>${esc(c.email)}</td><td>${esc(c.experience_years)} yrs</td><td>${Number(c.match_score).toFixed(1)}%</td><td>${esc(c.screening_recommendation)} (${esc($("threshold").value)}% threshold)</td><td>${statusSelect(c)}</td></tr>`).join("")||'<tr><td colspan="6" class="empty-note">No rejected candidates for the current requirements.</td></tr>';
 $("exceptionRows").innerHTML=exceptions.map(c=>`<tr><td>${esc(c.candidate_id)}</td><td>${esc(c.full_name)}</td><td>${esc(c.email)}</td><td>${esc(c.validation_issues)}</td></tr>`).join("")||'<tr><td colspan="4" class="empty-note">No data exceptions.</td></tr>';
}
async function readResponse(r){let j={};try{j=await r.json()}catch{}if(!r.ok)throw new Error(j.detail||"Request failed");return j}
function requirementPayload(){return {role:$("role").value,skills:$("skills").value,min_experience:Number($("experience").value),education_keywords:$("education").value,max_notice_days:Number($("notice").value),threshold:Number($("threshold").value)}}
function updateFromResponse(j){candidates=j.candidates||[];exceptions=j.exceptions||[];renderResults();renderDirectory();loadDashboard();}
async function processFiles(){
 const data=$("candidateFile").files[0],pdfs=[...$("resumeFiles").files];
 if(!data&&!pdfs.length){message("Choose a CSV/Excel sheet or at least one PDF resume.","error");return}
 const fd=new FormData();if(data)fd.append("candidate_file",data);pdfs.forEach(f=>fd.append("resumes",f));
 Object.entries(requirementPayload()).forEach(([k,v])=>fd.append(k,v));
 $("processBtn").disabled=true;$("processBtn").textContent="Processing…";
 try{const r=await fetch(API_BASE+"/api/screen",{method:"POST",body:fd});const j=await readResponse(r);updateFromResponse(j);$("resultsPanel").scrollIntoView({behavior:"smooth"});message(`New upload replaced the previous active dataset. Processed ${j.total_rows} rows: ${candidates.length} valid, ${exceptions.length} data exceptions.`);$("candidateFile").value="";$("resumeFiles").value="";updateFileNames();}
 catch(e){message(e.message,"error")}finally{$("processBtn").disabled=false;$("processBtn").innerHTML='Process candidates <b>→</b>'}
}
$("processBtn").addEventListener("click",processFiles);
$("applyRequirements").addEventListener("click",async()=>{
 const b=$("applyRequirements");b.disabled=true;b.textContent="Re-screening current dataset…";
 try{const r=await fetch(API_BASE+"/api/requirements",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(requirementPayload())});const j=await readResponse(r);updateFromResponse(j);message(`Requirements updated. Current dataset re-screened: ${matched().length} matched, ${rejected().length} rejected, ${exceptions.length} exceptions.`);toast("Requirements applied successfully");}
 catch(e){message(e.message,"error")}finally{b.disabled=false;b.textContent="↻ Apply updated requirements to current dataset"}
});
$("candidateFile").addEventListener("change",updateFileNames);$("resumeFiles").addEventListener("change",updateFileNames);
function updateFileNames(){const a=$("candidateFile").files[0]?.name;const b=[...$("resumeFiles").files].map(x=>x.name);$("fileNames").textContent=[a,...b].filter(Boolean).join(" · ")||"No files selected"}
document.addEventListener("change",async e=>{
 if(!e.target.matches(".review-select"))return;
 const id=e.target.dataset.id,status=e.target.value;
 try{const r=await fetch(API_BASE+"/api/review",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({candidate_id:id,hr_review_status:status})});await readResponse(r);const c=candidates.find(x=>String(x.candidate_id)===String(id));if(c)c.hr_review_status=status;toast("HR review status saved");renderResults();loadDashboard()}
 catch(err){toast(err.message)}
});
function renderDirectory(){if(!$("directoryRows"))return;const q=($("candidateSearch").value||"").toLowerCase();const filtered=candidates.filter(c=>[c.full_name,c.email,c.applied_role,c.candidate_id].join(" ").toLowerCase().includes(q));$("directoryRows").innerHTML=filtered.map(c=>`<tr><td>${esc(c.candidate_id)}</td><td>${esc(c.full_name)}</td><td>${esc(c.email)}</td><td>${esc(c.applied_role)}</td><td>${esc(c.experience_years)}</td><td>${Number(c.match_score).toFixed(1)}%</td><td>${esc(c.hr_review_status)}</td></tr>`).join("")||'<tr><td colspan="7" class="empty-note">No matching candidates.</td></tr>'}
$("candidateSearch").addEventListener("input",renderDirectory);
function downloadCSV(rows,name){if(!rows.length){toast("No data to export yet");return}const keys=[...new Set(rows.flatMap(o=>Object.keys(o)))];const csv=[keys.join(","),...rows.map(r=>keys.map(k=>`"${String(r[k]??"").replace(/"/g,'""')}"`).join(","))].join("\n");const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));a.download=name;a.click();URL.revokeObjectURL(a.href)}
$("downloadExcel").addEventListener("click",()=>downloadCSV(candidates,"DIT_HR_Screening_Results.csv"));
$("reportCsv").addEventListener("click",()=>downloadCSV(candidates,"DIT_HR_Candidate_Report.csv"));
$("reportExceptions").addEventListener("click",()=>downloadCSV(exceptions,"DIT_HR_Data_Exceptions.csv"));
async function loadDashboard(){
 try{const r=await fetch(API_BASE+"/api/dashboard",{cache:"no-store"});const d=await readResponse(r);candidates=d.candidates||[];exceptions=d.exceptions||[];const s=d.stats||{};
 $("mTotal").textContent=s.total_candidates||0;$("mValid").textContent=s.valid_candidates||0;$("mScore").textContent=`${Number(s.average_match_score||0).toFixed(1)}%`;$("mPending").textContent=s.pending_review||0;
 $("lastUpdated").textContent=d.updated_at?`Updated ${new Date(d.updated_at).toLocaleString()}`:"No saved activity";
 $("pipeline").innerHTML=Object.entries(s.status_counts||{}).map(([k,v])=>`<div class="pipe-row"><span>${esc(k)}</span><b class="pipe-count">${v}</b></div>`).join("")||'<div class="empty-note">No review activity yet.</div>';
 renderResults();renderDirectory();
 const ctx=$("scoreChart");$("chartEmpty").style.display=candidates.length?"none":"block";if(chart)chart.destroy();
 if(candidates.length){chart=new Chart(ctx,{type:"bar",data:{labels:["0–20","21–40","41–60","61–80","81–100"],datasets:[{label:"Candidates",data:[0,0,0,0,0].map((_,i)=>candidates.filter(c=>{const n=Number(c.match_score);return i===0?n<=20:i===1?n>20&&n<=40:i===2?n>40&&n<=60:i===3?n>60&&n<=80:n>80}).length),backgroundColor:"#4b86c4",borderRadius:5}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,ticks:{precision:0}},x:{grid:{display:false}}}}})}
 return true;
 }catch(e){console.warn(e);return false}
}
loadDashboard();
