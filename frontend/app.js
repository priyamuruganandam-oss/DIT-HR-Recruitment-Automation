
const API_BASE =
    localStorage.getItem("DIT_API_BASE") ||
    "https://dit-hr-recruitment-automation.onrender.com";

let candidates = [];
let exceptions = [];
let chart = null;

const $ = id => document.getElementById(id);

// Notifications
function toast(msg) {
    const t = $("toast");
    if (!t) {
        alert(msg);
        return;
    }

    t.textContent = msg;
    t.style.display = "block";

    setTimeout(() => {
        t.style.display = "none";
    }, 3000);
}

// Navigation
function setView(view) {
    document.querySelectorAll(".view").forEach(x =>
        x.classList.toggle("active", x.id === view)
    );

    document.querySelectorAll(".nav").forEach(x =>
        x.classList.toggle("active", x.dataset.view === view)
    );

    const titles = {
        overview: "Recruitment overview",
        screening: "Candidate screening",
        candidates: "Candidate directory",
        reports: "Reports & exports"
    };

    $("pageTitle").textContent =
        titles[view] || "Recruitment overview";

    if (view === "overview") loadDashboard();
    if (view === "candidates") renderDirectory();
}

document.querySelectorAll(".nav").forEach(b =>
    b.addEventListener("click", () => setView(b.dataset.view))
);

document.querySelectorAll("[data-go]").forEach(b =>
    b.addEventListener("click", () => setView(b.dataset.go))
);

// FIXED REFRESH BUTTON
$("refreshBtn").addEventListener("click", async () => {
    const btn = $("refreshBtn");
    const originalText = btn.innerHTML;

    btn.disabled = true;
    btn.textContent = "Refreshing...";

    const success = await loadDashboard();

    if (success) {
        toast("Dashboard refreshed successfully!");
    } else {
        toast("Refresh failed. Please check your backend connection.");
    }

    btn.disabled = false;
    btn.innerHTML = originalText;
});

// Screening message
function message(text, type = "success") {
    $("screeningMessage").textContent = text;
    $("screeningMessage").className = `message ${type}`;
}

// HTML safety
function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, c => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    }[c]));
}

// Candidate table row
function rowHTML(c) {
    const status = c.hr_review_status || "Pending HR review";

    return `
        <tr>
            <td>
                <b>${esc(c.full_name)}</b><br>
                <small>${esc(c.candidate_id)}</small>
            </td>
            <td>${esc(c.email)}</td>
            <td>${esc(c.experience_years)} yrs</td>
            <td><b>${Number(c.match_score || 0).toFixed(1)}%</b></td>
            <td>
                <span class="pill ${Number(c.match_score) >= 60 ? "good" : "warn"}">
                    ${esc(c.screening_recommendation)}
                </span>
            </td>
            <td>
                <select class="review-select" data-id="${esc(c.candidate_id)}">
                    <option ${status === "Pending HR review" ? "selected" : ""}>
                        Pending HR review
                    </option>
                    <option ${status === "HR approved for interview" ? "selected" : ""}>
                        HR approved for interview
                    </option>
                    <option ${status === "Hold" ? "selected" : ""}>
                        Hold
                    </option>
                    <option ${status === "Not selected by HR" ? "selected" : ""}>
                        Not selected by HR
                    </option>
                </select>
            </td>
        </tr>
    `;
}

// Render screening results
function renderResults() {
    $("resultRows").innerHTML = candidates.length
        ? candidates.map(rowHTML).join("")
        : '<tr><td colspan="6" class="empty-note">No screening results yet.</td></tr>';

    $("recentRows").innerHTML = candidates.slice(0, 5).map(c => `
        <tr>
            <td>${esc(c.full_name)}</td>
            <td>${esc(c.applied_role)}</td>
            <td>${Number(c.match_score || 0).toFixed(1)}%</td>
            <td>${esc(c.screening_recommendation)}</td>
            <td>${esc(c.hr_review_status)}</td>
        </tr>
    `).join("") ||
        '<tr><td colspan="5" class="empty-note">No candidate records yet.</td></tr>';

    $("rTotal").textContent = candidates.length + exceptions.length;
    $("rValid").textContent = candidates.length;
    $("rExceptions").textContent = exceptions.length;

    $("rAbove").textContent = candidates.filter(
        c => c.screening_recommendation === "Meets review threshold"
    ).length;
}

// Process candidate files
async function processFiles() {
    const data = $("candidateFile").files[0];
    const pdfs = [...$("resumeFiles").files];

    if (!data && !pdfs.length) {
        message("Choose a CSV/Excel sheet or at least one PDF resume.", "error");
        return;
    }

    if (API_BASE.includes("YOUR-BACKEND")) {
        message("Backend URL not configured.", "error");
        return;
    }

    const fd = new FormData();

    if (data) fd.append("candidate_file", data);

    pdfs.forEach(f => fd.append("resumes", f));

    fd.append("role", $("role").value);
    fd.append("skills", $("skills").value);
    fd.append("min_experience", $("experience").value);
    fd.append("education_keywords", $("education").value);
    fd.append("max_notice_days", $("notice").value);
    fd.append("threshold", $("threshold").value);

    $("processBtn").disabled = true;
    $("processBtn").textContent = "Processing…";

    try {
        const r = await fetch(API_BASE + "/api/screen", {
            method: "POST",
            body: fd
        });

        const j = await r.json();

        if (!r.ok) {
            throw new Error(j.detail || "Processing failed");
        }

        candidates = j.candidates || [];
        exceptions = j.exceptions || [];

        renderResults();

        $("resultsPanel").scrollIntoView({
            behavior: "smooth"
        });

        message(
            `Processed ${j.total_rows} uploaded records. ${candidates.length} valid candidate(s), ${exceptions.length} exception(s). HR review is required.`
        );

        await loadDashboard();

    } catch (e) {
        message(e.message, "error");
    } finally {
        $("processBtn").disabled = false;
        $("processBtn").innerHTML = 'Process candidates <b>→</b>';
    }
}

$("processBtn").addEventListener("click", processFiles);

$("candidateFile").addEventListener("change", updateFileNames);
$("resumeFiles").addEventListener("change", updateFileNames);

function updateFileNames() {
    const a = $("candidateFile").files[0]?.name;
    const b = [...$("resumeFiles").files].map(x => x.name);

    $("fileNames").textContent =
        [a, ...b].filter(Boolean).join(" · ") || "No files selected";
}

// HR review status update
document.addEventListener("change", async e => {
    if (!e.target.matches(".review-select")) return;

    const id = e.target.dataset.id;
    const status = e.target.value;

    try {
        const r = await fetch(API_BASE + "/api/review", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                candidate_id: id,
                hr_review_status: status
            })
        });

        if (!r.ok) {
            throw new Error("Could not save review status");
        }

        const c = candidates.find(
            x => String(x.candidate_id) === String(id)
        );

        if (c) c.hr_review_status = status;

        toast("HR review status saved");

        await loadDashboard();

    } catch (err) {
        toast(err.message);
    }
});

// Candidate directory
function renderDirectory() {
    const q = ($("candidateSearch").value || "").toLowerCase();

    const filtered = candidates.filter(c =>
        [
            c.full_name,
            c.email,
            c.applied_role,
            c.candidate_id
        ].join(" ").toLowerCase().includes(q)
    );

    $("directoryRows").innerHTML = filtered.map(c => `
        <tr>
            <td>${esc(c.candidate_id)}</td>
            <td>${esc(c.full_name)}</td>
            <td>${esc(c.email)}</td>
            <td>${esc(c.applied_role)}</td>
            <td>${esc(c.experience_years)}</td>
            <td>${Number(c.match_score || 0).toFixed(1)}%</td>
            <td>${esc(c.hr_review_status)}</td>
        </tr>
    `).join("") ||
        '<tr><td colspan="7" class="empty-note">No matching candidates.</td></tr>';
}

$("candidateSearch").addEventListener("input", renderDirectory);

// CSV download
function downloadCSV(rows, name) {
    if (!rows.length) {
        toast("No data to export yet");
        return;
    }

    const keys = [...new Set(rows.flatMap(o => Object.keys(o)))];

    const csv = [
        keys.join(","),
        ...rows.map(r =>
            keys.map(k =>
                `"${String(r[k] ?? "").replace(/"/g, '""')}"`
            ).join(",")
        )
    ].join("\n");

    const blob = new Blob([csv], {
        type: "text/csv;charset=utf-8;"
    });

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");

    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();

    URL.revokeObjectURL(url);
}

$("downloadExcel").addEventListener("click", () =>
    downloadCSV(candidates, "DIT_HR_Screening_Results.csv")
);

$("reportCsv").addEventListener("click", () =>
    downloadCSV(candidates, "DIT_HR_Candidate_Report.csv")
);

$("reportExceptions").addEventListener("click", () =>
    downloadCSV(exceptions, "DIT_HR_Data_Exceptions.csv")
);

// DASHBOARD LOAD AND REFRESH
async function loadDashboard() {
    if (API_BASE.includes("YOUR-BACKEND")) {
        toast("Backend URL is not configured.");
        return false;
    }

    try {
        const r = await fetch(API_BASE + "/api/dashboard", {
            method: "GET",
            cache: "no-store"
        });

        if (!r.ok) {
            throw new Error("Backend error: " + r.status);
        }

        const d = await r.json();

        candidates = d.candidates || [];

        const s = d.stats || {};

        $("mTotal").textContent = s.total_candidates || 0;
        $("mValid").textContent = s.valid_candidates || 0;

        $("mScore").textContent =
            Number(s.average_match_score || 0).toFixed(1) + "%";

        $("mPending").textContent = s.pending_review || 0;

        $("lastUpdated").textContent = d.updated_at
            ? "Updated " + new Date(d.updated_at).toLocaleString()
            : "No saved activity";

        $("pipeline").innerHTML =
            Object.entries(s.status_counts || {})
                .map(([k, v]) => `
                    <div class="pipe-row">
                        <span>${esc(k)}</span>
                        <b class="pipe-count">${v}</b>
                    </div>
                `).join("") ||
            '<div class="empty-note">No review activity yet.</div>';

        renderResults();
        renderDirectory();

        const ctx = $("scoreChart");

        $("chartEmpty").style.display =
            candidates.length ? "none" : "block";

        if (chart) {
            chart.destroy();
            chart = null;
        }

        if (
            candidates.length &&
            typeof Chart !== "undefined" &&
            ctx
        ) {
            const ranges = [
                [0, 20],
                [20, 40],
                [40, 60],
                [60, 80],
                [80, 100]
            ];

            chart = new Chart(ctx, {
                type: "bar",

                data: {
                    labels: [
                        "0–20",
                        "21–40",
                        "41–60",
                        "61–80",
                        "81–100"
                    ],

                    datasets: [{
                        label: "Candidates",

                        data: ranges.map(([min, max], i) =>
                            candidates.filter(c => {
                                const n = Number(c.match_score);

                                if (i === 0) return n <= max;
                                if (i === 4) return n > min;

                                return n > min && n <= max;
                            }).length
                        ),

                        backgroundColor: "#4b86c4",
                        borderRadius: 5
                    }]
                },

                options: {
                    responsive: true,
                    maintainAspectRatio: false,

                    plugins: {
                        legend: {
                            display: false
                        }
                    },

                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                precision: 0
                            }
                        },

                        x: {
                            grid: {
                                display: false
                            }
                        }
                    }
                }
            });
        }

        return true;

    } catch (e) {
        console.error("Dashboard loading error:", e);
        return false;
    }
}

// Initial dashboard load
loadDashboard();
