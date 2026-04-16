let emiChart;
let currentBankComparison = [];

function initEmiChart() {
  const ctx = document.getElementById("emiChart");
  if (!ctx) return;

  emiChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Bank A", "Bank B", "Bank C"],
      datasets: [
        {
          label: "EMI (₹)",
          data: [0, 0, 0],
          borderRadius: 10,
          backgroundColor: [
            "rgba(56, 189, 248, 0.95)", // sky
            "rgba(59, 130, 246, 0.95)", // blue
            "rgba(99, 102, 241, 0.95)", // indigo
          ],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: {
            color: "rgba(15, 23, 42, 0.85)",
            font: { size: 11, family: "Inter" },
          },
        },
        tooltip: {
          callbacks: {
            label: function (context) {
              const idx = context.dataIndex;
              const b = currentBankComparison[idx];
              if (!b) return ` EMI: ₹${(context.parsed.y || 0).toLocaleString()}`;
              return [
                ` EMI: ₹${b.emi.toLocaleString()}`,
                ` Interest Rate: ${b.rate}%`,
                ` Approval Prob: ${b.prob}`
              ];
            },
          },
        },
      },
      scales: {
        x: {
          ticks: {
            color: "rgba(100, 116, 139, 1)",
            font: { size: 10 },
          },
          grid: { display: false },
        },
        y: {
          ticks: {
            color: "rgba(100, 116, 139, 1)",
            font: { size: 10 },
            callback: (val) => `₹${val}`,
          },
          grid: {
            color: "rgba(148, 163, 184, 0.6)",
          },
        },
      },
    },
  });
}

function updateEmiChart(bankComparison) {
  if (!emiChart || !Array.isArray(bankComparison)) return;
  currentBankComparison = bankComparison;
  
  const labels = bankComparison.map((b) => b.bank);
  const data = bankComparison.map((b) => b.emi);

  const colors = bankComparison.map((b) => {
    if (b.is_user_profile) return "rgba(139, 92, 246, 0.95)"; // Violet
    if (b.prob === "High") return "rgba(22, 163, 74, 0.95)"; // Green
    if (b.prob === "Medium") return "rgba(245, 158, 11, 0.95)"; // Amber
    if (b.prob === "Low") return "rgba(220, 38, 38, 0.95)"; // Red
    return "rgba(56, 189, 248, 0.95)"; // Default Sky
  });

  emiChart.data.labels = labels;
  emiChart.data.datasets[0].data = data;
  emiChart.data.datasets[0].backgroundColor = colors;
  emiChart.update();
}

function setEligibilityPill(status) {
  const pill = document.getElementById("eligibility-pill");
  if (!pill) return;
  if (status === "Yes") {
    pill.textContent = "Eligible";
    pill.className =
      "px-3 py-1 rounded-full text-xs font-semibold border border-sky-400/70 text-sky-700 bg-sky-500/10";
  } else if (status === "No") {
    pill.textContent = "Not Eligible";
    pill.className =
      "px-3 py-1 rounded-full text-xs font-semibold border border-rose-300/80 text-rose-700 bg-rose-100/70";
  } else {
    pill.textContent = "Awaiting Input";
    pill.className =
      "px-3 py-1 rounded-full text-xs font-semibold border border-sky-200/80 text-sky-700 bg-white/80";
  }
}

function updateAAIBar(aai) {
  const bar = document.getElementById("aai-bar");
  const valueLabel = document.getElementById("aai_value");
  if (!bar || !valueLabel) return;

  const clamped = Math.max(0, Math.min(100, Number(aai) || 0));
  bar.style.width = clamped + "%";
  valueLabel.innerHTML = `AAI: <span class="font-semibold text-sky-700">${clamped.toFixed(
    1
  )}</span> / 100`;
}

function formatCurrency(val) {
  const num = Number(val);
  if (!isFinite(num)) return "—";
  return "₹" + num.toLocaleString();
}

function formatRatio(val) {
  const num = Number(val);
  if (!isFinite(num)) return "—";
  return (num * 100).toFixed(1) + "%";
}

function attachFormHandler() {
  const form = document.getElementById("loan-form");
  if (!form) return;

  const spinner = document.getElementById("submit-spinner");
  const icon = document.getElementById("submit-icon");
  const generateBtn = document.getElementById("generate-random");

  if (generateBtn) {
    generateBtn.addEventListener("click", () => {
      // Helper to set a field if it exists
      const setVal = (name, value) => {
        const el = form.elements[name];
        if (el) el.value = value;
      };

      // Simple random helpers
      const randInt = (min, max) =>
        Math.floor(Math.random() * (max - min + 1)) + min;
      const randFloat = (min, max, step = 1) => {
        const val = Math.random() * (max - min) + min;
        return Math.round(val / step) * step;
      };

      // Dependents: 0–4
      setVal("dependents", randInt(0, 4));

      // Education
      setVal("education", Math.random() < 0.6 ? "Graduate" : "Not Graduate");

      // Self employed
      setVal("self_employed", Math.random() < 0.3 ? "Yes" : "No");

      // Income: 2L – 25L
      const income = randFloat(200000, 2500000, 10000);
      setVal("income", income);

      // Loan term: 1–20 years
      const term = randInt(1, 20);
      setVal("loan_term", term);

      // CIBIL: 550–850
      const cibil = randInt(550, 850);
      setVal("cibil", cibil);

      // Loan amount: 1L – 80% of 5x income (bounded)
      const maxLoanFromIncome = Math.min(income * 5, 10000000);
      const loanAmount = randFloat(100000, maxLoanFromIncome * 0.8, 10000);
      setVal("loan_amount", loanAmount);

      // Assets: random but consistent with income/loan
      const resAssets = randFloat(0, loanAmount * 1.2, 50000);
      const comAssets = randFloat(0, income * 1.0, 50000);
      const luxAssets = randFloat(0, income * 0.5, 25000);
      const bankAssets = randFloat(income * 0.1, income * 1.5, 10000);

      setVal("res_assets", resAssets);
      setVal("com_assets", comAssets);
      setVal("lux_assets", luxAssets);
      setVal("bank_assets", bankAssets);
    });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (spinner) spinner.classList.remove("hidden");
    if (icon) icon.classList.add("hidden");

    const formData = new FormData(form);
    const payload = Object.fromEntries(formData.entries());

    try {
      const res = await fetch("/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error("Network error");
      }

      const data = await res.json();
      applyResultsToUI(data);
    } catch (err) {
      console.error(err);
      alert("Something went wrong while running the eligibility check.");
    } finally {
      if (spinner) spinner.classList.add("hidden");
      if (icon) icon.classList.remove("hidden");
    }
  });
}

function applyResultsToUI(data) {
  if (!data) return;

  // Eligibility & main badges
  document.getElementById("loan_status").textContent = data.loan_status ?? "—";
  document.getElementById("risk_category").textContent = data.risk_category ?? "—";
  document.getElementById("loan_type").textContent = data.loan_type ?? "—";
  setEligibilityPill(data.loan_status);

  // Metrics
  document.getElementById("interest_rate").textContent =
    (data.interest_rate ?? "—") + (data.interest_rate ? " %" : "");
  document.getElementById("emi").textContent = formatCurrency(data.emi);
  document.getElementById("dti_value").textContent = formatRatio(data.dti);
  document.getElementById("lti_value").textContent = (data.lti || data.lti === 0)
    ? data.lti.toFixed(2)
    : "—";
  document.getElementById("max_eligible_loan").textContent = formatCurrency(data.max_eligible_loan);

  // AAI & CIBIL
  updateAAIBar(data.aai);
  document.getElementById("cibil_category").innerHTML =
    'CIBIL Health: <span class="font-semibold text-sky-700">' +
    (data.cibil_category ?? "—") +
    "</span>";

  // Advisory list
  const advisoryList = document.getElementById("advisory_list");
  advisoryList.innerHTML = "";
  if (Array.isArray(data.advisory) && data.advisory.length > 0) {
    data.advisory.forEach((item) => {
      const li = document.createElement("li");
      li.innerHTML = `<span class="text-sky-700 mr-1">•</span>${item}`;
      advisoryList.appendChild(li);
    });
  } else {
    advisoryList.innerHTML =
      '<li class="text-slate-500/80">No specific advisory generated for this profile.</li>';
  }

  // SHAP reasons
  const reasonsList = document.getElementById("reasons_list");
  reasonsList.innerHTML = "";
  if (Array.isArray(data.main_reasons) && data.main_reasons.length > 0) {
    data.main_reasons.forEach((item) => {
      const li = document.createElement("li");
      li.innerHTML = `<span class="text-cyan-700 mr-1">•</span>${item}`;
      reasonsList.appendChild(li);
    });
  } else {
    reasonsList.innerHTML =
      '<li class="text-slate-500/80">Model did not expose detailed reasons for this profile.</li>';
  }

  // Bank comparison chart
  if (Array.isArray(data.bank_comparison)) {
    updateEmiChart(data.bank_comparison);
  }
  
  // Reveal Export PDF button safely
  const exportBtn = document.getElementById("export-report-btn");
  if (exportBtn) {
    exportBtn.classList.remove("hidden");
  }

  // Trigger small animation for metric cards
  document.querySelectorAll("[data-animate='true']").forEach((el, idx) => {
    setTimeout(() => {
      el.classList.add("is-visible");
    }, idx * 80);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initEmiChart();
  attachFormHandler();
  attachCibilFormHandler();
  initAnalyticsCharts();
});

function attachCibilFormHandler() {
  const form = document.getElementById("cibil-form");
  if (!form) return;

  const generateBtn = document.getElementById("generate-cibil");
  const submitBtnIcon = document.getElementById("cibil-btn-icon");
  const submitBtnSpinner = document.getElementById("cibil-btn-spinner");

  if (generateBtn) {
    generateBtn.addEventListener("click", () => {
      const setVal = (name, value) => {
        const el = form.elements[name];
        if (el) el.value = value;
      };

      const randFloat = (min, max, step = 1) => {
        const val = Math.random() * (max - min) + min;
        return Math.round(val / step) * step;
      };
      const randInt = (min, max) =>
        Math.floor(Math.random() * (max - min + 1)) + min;
        
      const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];

      // Profile
      setVal("age", randInt(22, 60));
      setVal("employment", pick(["Salaried", "Self-employed", "Student"]));
      setVal("experience", randInt(1, 20));

      // Capacity
      const inc = randFloat(30000, 200000, 5000);
      setVal("income", inc);
      setVal("expenses", randFloat(inc * 0.3, inc * 0.7, 1000));
      setVal("emi", randFloat(0, inc * 0.5, 1000));

      // Loans
      setVal("active_loans", randInt(0, 4));
      setVal("outstanding_loan", randFloat(0, inc * 20, 10000));
      
      setVal("home_loans", randInt(0, 1));
      setVal("car_loans", randInt(0, 1));
      setVal("personal_loans", randInt(0, 2));
      setVal("education_loans", randInt(0, 1));

      // Credit Cards
      const ccCount = randInt(0, 4);
      setVal("credit_cards", ccCount);
      const limit = ccCount > 0 ? randFloat(50000, 500000, 10000) : 0;
      setVal("cc_limit", limit);
      // Mostly good utilization, sometimes bad
      const utilRate = Math.random() > 0.8 ? randFloat(0.7, 1.0, 0.05) : randFloat(0.05, 0.3, 0.05);
      setVal("cc_used", limit > 0 ? Math.round(limit * utilRate) : 0);

      // Repayment
      const hasDefaults = Math.random() > 0.85;
      setVal("missed_payments", hasDefaults ? randInt(1, 5) : 0);
      setVal("max_delay", hasDefaults ? pick(["30 Days", "60 Days", "90+ Days"]) : "No Delay");
      setVal("default_history", Math.random() > 0.95 ? "Yes" : "No");
      setVal("settled_loans", Math.random() > 0.9 ? "Yes" : "No");

      // History
      setVal("history_years", randInt(1, 15));
      setVal("closed_loans", randInt(0, 5));
      setVal("inquiries", randInt(0, 4));
    });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (submitBtnSpinner) {
      submitBtnSpinner.classList.remove("hidden");
      if (submitBtnIcon) submitBtnIcon.classList.add("hidden");
    }

    const formData = new FormData(form);
    const payload = Object.fromEntries(formData.entries());

    try {
      const res = await fetch("/calc_cibil", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Network error");
      const data = await res.json();

      const container = document.getElementById("cibil_calc_result");
      const bar = document.getElementById("cibil-score-bar");
      const bandPill = document.getElementById("cibil_band_pill");
      
      if (container && data.cibil_score) {
        container.innerHTML =
          'Score: <span class="font-bold text-slate-800 text-lg mr-1">' +
          data.cibil_score +
          '</span> <span class="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-semibold">' +
          (data.category ?? "—") +
          "</span>";
      }

      if (bar && data.cibil_score) {
        const score = Number(data.cibil_score);
        const pct = Math.max(0, Math.min(100, ((score - 300) / 600) * 100));
        bar.style.width = pct + "%";
      }

      if (bandPill && data.category) {
        const cat = data.category;
        bandPill.textContent = cat;
        let classes = "px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider border ";
        if (cat === "Excellent" || cat === "Good" || cat === "Very Good") {
          classes += "border-emerald-200 text-emerald-700 bg-emerald-50";
        } else if (cat === "Fair") {
          classes += "border-amber-200 text-amber-700 bg-amber-50";
        } else {
          classes += "border-rose-200 text-rose-700 bg-rose-50";
        }
        bandPill.className = classes;
      }

      // Populate Insights Lists
      const populateList = (id, items) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.innerHTML = "";
        if (Array.isArray(items) && items.length > 0) {
          items.forEach(item => {
            const li = document.createElement("li");
            li.className = "flex items-start gap-2 text-[11.5px]";
            li.innerHTML = `<i class="fa-solid fa-check text-[9px] text-sky-400 mt-[3px]"></i> <span>${item}</span>`;
            el.appendChild(li);
          });
        } else {
          el.innerHTML = '<li class="italic text-slate-400">Nothing significant identified.</li>';
        }
      };

      populateList("cibil-factors-list", data.factors);
      populateList("cibil-tips-list", data.tips);

    } catch (err) {
      console.error(err);
      alert("Unable to calculate approximate CIBIL right now.");
    } finally {
      if (submitBtnSpinner) {
        submitBtnSpinner.classList.add("hidden");
        if (submitBtnIcon) submitBtnIcon.classList.remove("hidden");
      }
    }
  });
}

function initAnalyticsCharts() {
  if (typeof analyticsData === "undefined") return;

  const aff = analyticsData.affordability;
  const ctxAff = document.getElementById("affordabilityChart");
  if (ctxAff && aff) {
    new Chart(ctxAff, {
      type: "bar",
      data: {
        labels: ["Monthly Setup"],
        datasets: [
          {
            label: "Monthly Income",
            data: [aff.monthly_income],
            backgroundColor: "rgba(37, 99, 235, 0.9)", // blue-600
            borderRadius: 6,
          },
          {
            label: "Safe EMI (20% Limit)",
            data: [aff.safe_emi],
            backgroundColor: "rgba(22, 163, 74, 0.9)", // green-600
            borderRadius: 6,
          },
          {
            label: "Requested EMI",
            data: [aff.actual_emi],
            backgroundColor: aff.actual_emi <= aff.safe_emi ? "rgba(22, 163, 74, 0.9)" : (aff.actual_emi <= aff.safe_emi * 1.5 ? "rgba(245, 158, 11, 0.9)" : "rgba(220, 38, 38, 0.9)"), // dynamic green/amber/red
            borderRadius: 6,
          }
        ],
      },
      options: {
        indexAxis: 'x',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: "rgba(15, 23, 42, 0.85)",
              font: { size: 11, family: "Inter" },
            },
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                return context.dataset.label + ': ₹' + Number(context.raw).toLocaleString(undefined, {maximumFractionDigits:0});
              }
            }
          }
        },
        scales: {
          x: {
            grid: { display: false },
          },
          y: {
            grid: { color: "rgba(148,163,184,0.3)" },
            ticks: {
                callback: function(value) {
                    return '₹' + value.toLocaleString();
                }
            }
          },
        },
      },
    });
  }

  const ts = analyticsData.timeseries || {};
  const ctxLine = document.getElementById("cibilAaiChart");
  if (ctxLine) {
    new Chart(ctxLine, {
      type: "line",
      data: {
        labels: ts.labels || [],
        datasets: [
          {
            label: "CIBIL",
            data: ts.cibil || [],
            borderColor: "rgba(37, 99, 235, 1)",
            backgroundColor: "rgba(37, 99, 235, 0.2)",
            tension: 0.3,
            pointBackgroundColor: (ts.cibil || []).map((v, i, arr) => i > 0 && v > arr[i-1] ? "rgba(22, 163, 74, 1)" : "rgba(37, 99, 235, 1)"),
            pointRadius: (ts.cibil || []).map((v, i, arr) => i > 0 && v > arr[i-1] ? 5 : 3),
            pointBorderColor: "#fff",
            borderWidth: 2,
          },
          {
            label: "AAI",
            data: ts.aai || [],
            borderColor: "rgba(124, 58, 237, 1)",
            backgroundColor: "rgba(124, 58, 237, 0.2)",
            tension: 0.3,
            pointBackgroundColor: (ts.aai || []).map((v, i, arr) => i > 0 && v > arr[i-1] ? "rgba(22, 163, 74, 1)" : "rgba(124, 58, 237, 1)"),
            pointRadius: (ts.aai || []).map((v, i, arr) => i > 0 && v > arr[i-1] ? 5 : 3),
            pointBorderColor: "#fff",
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: "rgba(15, 23, 42, 0.85)",
              font: { size: 11, family: "Inter" },
            },
          },
        },
        scales: {
          x: {
            ticks: { color: "rgba(100, 116, 139, 1)", font: { size: 10 } },
            grid: { display: false },
          },
          y: {
            ticks: { color: "rgba(100, 116, 139, 1)", font: { size: 10 } },
            grid: { color: "rgba(148,163,184,0.6)" },
          },
        },
      },
    });
  }

  const riskCounts = analyticsData.risk_counts || {};
  const ctxPie = document.getElementById("riskPieChart");
  if (ctxPie) {
    const labels = Object.keys(riskCounts);
    const values = Object.values(riskCounts);
    const dynamicColors = labels.map(label => {
      if (label.includes("Safe")) return "rgba(22, 163, 74, 0.9)";
      if (label.includes("Moderate")) return "rgba(245, 158, 11, 0.9)";
      return "rgba(220, 38, 38, 0.9)";
    });
    new Chart(ctxPie, {
      type: "doughnut",
      data: {
        labels,
        datasets: [
          {
            data: values,
            backgroundColor: dynamicColors,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: "rgba(15, 23, 42, 0.85)",
              font: { size: 11, family: "Inter" },
            },
          },
        },
      },
    });
  }

  const loanCounts = analyticsData.loan_type_counts || {};
  const ctxBar = document.getElementById("loanTypeBarChart");
  if (ctxBar) {
    const labels = Object.keys(loanCounts);
    const values = Object.values(loanCounts);
    new Chart(ctxBar, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Count",
            data: values,
            backgroundColor: "rgba(56, 189, 248, 0.9)",
            borderRadius: 8,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
        },
        scales: {
          x: {
            ticks: { color: "rgba(100, 116, 139, 1)", font: { size: 10 } },
            grid: { display: false },
          },
          y: {
            ticks: { color: "rgba(100, 116, 139, 1)", font: { size: 10 } },
            grid: { color: "rgba(148,163,184,0.6)" },
          },
        },
      },
    });
  }

  const scatterPoints = analyticsData.income_loan_points || [];
  const ctxScatter = document.getElementById("incomeLoanScatter");
  if (ctxScatter) {
    new Chart(ctxScatter, {
      type: "scatter",
      data: {
        datasets: [
          {
            label: "Income vs Loan",
            data: scatterPoints,
            backgroundColor: "rgba(99, 102, 241, 0.85)",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: "rgba(15, 23, 42, 0.85)",
              font: { size: 11, family: "Inter" },
            },
          },
        },
        scales: {
          x: {
            title: {
              display: true,
              text: "Annual Income",
              color: "rgba(100, 116, 139, 1)",
            },
            ticks: {
              color: "rgba(100, 116, 139, 1)",
              font: { size: 10 },
              callback: (val) => "₹" + val,
            },
            grid: { color: "rgba(148,163,184,0.6)" },
          },
          y: {
            title: {
              display: true,
              text: "Loan Amount",
              color: "rgba(100, 116, 139, 1)",
            },
            ticks: {
              color: "rgba(100, 116, 139, 1)",
              font: { size: 10 },
              callback: (val) => "₹" + val,
            },
            grid: { color: "rgba(148,163,184,0.6)" },
          },
        },
      },
    });
  }

  // Profile radar + trend text
  const profile = analyticsData.profile || {};
  const trends = analyticsData.trends || {};
  const ctxRadar = document.getElementById("profileRadarChart");

  if (ctxRadar && Object.keys(profile).length > 0) {
    const avgCibil = profile.avg_cibil || 0;
    const avgAai = profile.avg_aai || 0;
    const avgDti = profile.avg_dti || 0;
    const avgLti = profile.avg_lti || 0;

    const cibilScore = Math.max(0, Math.min(100, avgCibil / 9)); // 900 -> 100
    const aaiScore = Math.max(0, Math.min(100, avgAai));
    const dtiScore = Math.max(0, Math.min(100, ((0.6 - avgDti) / 0.6) * 100)); // lower DTI better
    const ltiScore = Math.max(0, Math.min(100, ((6 - avgLti) / 6) * 100)); // lower LTI better

    new Chart(ctxRadar, {
      type: "radar",
      data: {
        labels: ["CIBIL strength", "AAI", "DTI comfort", "LTI comfort"],
        datasets: [
          {
            label: "Profile score",
            data: [cibilScore, aaiScore, dtiScore, ltiScore],
            backgroundColor: "rgba(56, 189, 248, 0.2)",
            borderColor: "rgba(59, 130, 246, 1)",
            pointBackgroundColor: "rgba(14, 165, 233, 1)",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: "rgba(15, 23, 42, 0.85)",
              font: { size: 11, family: "Inter" },
            },
          },
        },
        scales: {
          r: {
            angleLines: { color: "rgba(148,163,184,0.6)" },
            grid: { color: "rgba(148,163,184,0.6)" },
            pointLabels: {
              color: "rgba(15, 23, 42, 0.85)",
              font: { size: 10 },
            },
            ticks: { display: false, max: 100 },
          },
        },
      },
    });
  }

  const trendCibil = document.getElementById("trend_cibil");
  const trendAai = document.getElementById("trend_aai");
  const trendRisk = document.getElementById("trend_risk");

  if (trendCibil && trends) {
    const dir = trends.cibil_direction || "flat";
    const delta = trends.cibil_change || 0;
    let label = "CIBIL trend: ";
    if (dir === "up") label += `improving by +${delta} points`;
    else if (dir === "down") label += `declining by ${delta} points`;
    else label += "largely stable";
    trendCibil.textContent = label;
  }

  if (trendAai && trends) {
    const dir = trends.aai_direction || "flat";
    const delta = trends.aai_change || 0;
    let label = "AAI trend: ";
    if (dir === "up") label += `improving by +${delta}`;
    else if (dir === "down") label += `declining by ${delta}`;
    else label += "largely stable";
    trendAai.textContent = label;
  }

  if (trendRisk && trends) {
    trendRisk.textContent = "Risk profile trend: " + (trends.risk_trend || "Not enough data");
  }
}

