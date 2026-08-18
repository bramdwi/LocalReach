/**
 * LocalReach — Mini SaaS Client Application Logic
 */

const state = {
  currentView: 'home', // 'home' | 'results'
  currentLimit: 10,
  user: {
    name: 'Brahman',
    plan: 'Pro',
    credits_total: 150,
    credits_used: 20
  },
  leadsData: {
    query: '',
    leads: [],
    filename: '',
    enriched_at: null
  },
  history: [],
  selectedLead: null,
  activeTaskId: null,
  pollTimer: null
};

// DOM References
const dom = {
  // Top SaaS Bar
  topCreditsText: document.getElementById('topCreditsText'),
  userNameText: document.getElementById('userNameText'),
  userAvatarText: document.getElementById('userAvatarText'),
  greetingNameTitle: document.getElementById('greetingNameTitle'),
  sidePlanName: document.getElementById('sidePlanName'),
  btnSidebarUpgrade: document.getElementById('btnSidebarUpgrade'),

  // Sidebar
  recentScrapesList: document.getElementById('recentScrapesList'),
  btnSidebarNewSearch: document.getElementById('btnSidebarNewSearch'),
  btnOpenSettings: document.getElementById('btnOpenSettings'),
  
  // Stages
  sectionHomeCanvas: document.getElementById('sectionHomeCanvas'),
  sectionResultsView: document.getElementById('sectionResultsView'),
  btnBackToHome: document.getElementById('btnBackToHome'),
  
  // Prompt Box
  mainPromptInput: document.getElementById('mainPromptInput'),
  btnSubmitPrompt: document.getElementById('btnSubmitPrompt'),
  limitPills: document.querySelectorAll('.limit-pill'),
  signalCards: document.querySelectorAll('.signal-card'),
  
  // Results
  resultsBatchTitle: document.getElementById('resultsBatchTitle'),
  resultsBatchSubtitle: document.getElementById('resultsBatchSubtitle'),
  resMetricTotal: document.getElementById('resMetricTotal'),
  resMetricEmail: document.getElementById('resMetricEmail'),
  resMetricHigh: document.getElementById('resMetricHigh'),
  resMetricSocial: document.getElementById('resMetricSocial'),
  leadsTableBody: document.getElementById('leadsTableBody'),
  btnExportCsv: document.getElementById('btnExportCsv'),
  btnPushSheets: document.getElementById('btnPushSheets'),
  
  // Live Progress Banner
  liveProgressBanner: document.getElementById('liveProgressBanner'),
  liveProgressStage: document.getElementById('liveProgressStage'),
  liveProgressPercent: document.getElementById('liveProgressPercent'),
  liveProgressBarFill: document.getElementById('liveProgressBarFill'),
  liveProgressDetail: document.getElementById('liveProgressDetail'),
  
  // Drawer
  drawerBackdrop: document.getElementById('drawerBackdrop'),
  reviewDrawer: document.getElementById('reviewDrawer'),
  drawerLeadName: document.getElementById('drawerLeadName'),
  drawerLeadSub: document.getElementById('drawerLeadSub'),
  drawerScorePill: document.getElementById('drawerScorePill'),
  drawerBody: document.getElementById('drawerBody'),
  btnCloseDrawer: document.getElementById('btnCloseDrawer'),
  btnCopyPitchBottom: document.getElementById('btnCopyPitchBottom'),
  drawerActionBtnContainer: document.getElementById('drawerActionBtnContainer'),
  
  // Pricing Modal
  pricingModal: document.getElementById('pricingModal'),
  btnClosePricingModal: document.getElementById('btnClosePricingModal'),

  // Settings Modal
  settingsModal: document.getElementById('settingsModal'),
  btnCloseSettingsModal: document.getElementById('btnCloseSettingsModal'),
  btnCancelSettings: document.getElementById('btnCancelSettings'),
  btnSaveSettings: document.getElementById('btnSaveSettings'),
  modalTabBtns: document.querySelectorAll('.modal-tab-btn'),
  settingSerpKey: document.getElementById('settingSerpKey'),
  settingOpenAiKey: document.getElementById('settingOpenAiKey'),
  settingGoogleSheet: document.getElementById('settingGoogleSheet'),
  settingSenderName: document.getElementById('settingSenderName'),
  settingCompanyName: document.getElementById('settingCompanyName'),
  settingValueProp: document.getElementById('settingValueProp'),
  
  toastContainer: document.getElementById('toastContainer')
};

// ===========================================================================
// Application Initialization
// ===========================================================================
document.addEventListener('DOMContentLoaded', async () => {
  initEventListeners();
  await loadUserProfile();
  await loadRecentHistory();
});

function initEventListeners() {
  // Navigation
  dom.btnSidebarNewSearch.addEventListener('click', showHomeView);
  dom.btnBackToHome.addEventListener('click', showHomeView);

  // Limit pills
  dom.limitPills.forEach(pill => {
    pill.addEventListener('click', () => {
      dom.limitPills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      state.currentLimit = parseInt(pill.getAttribute('data-limit'), 10) || 10;
    });
  });

  // Prompt Submit
  dom.btnSubmitPrompt.addEventListener('click', handlePromptSubmit);
  dom.mainPromptInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handlePromptSubmit();
    }
  });

  // Signal starting points
  dom.signalCards.forEach(card => {
    card.addEventListener('click', () => {
      const q = card.getAttribute('data-query');
      if (q) {
        dom.mainPromptInput.value = q;
        handlePromptSubmit();
      }
    });
  });

  // Export CSV & Sheets
  dom.btnExportCsv.addEventListener('click', handleExportCsv);
  dom.btnPushSheets.addEventListener('click', () => {
    showSettingsTab('sheets');
    openModal(dom.settingsModal);
  });

  // Drawer
  dom.btnCloseDrawer.addEventListener('click', closeDrawer);
  dom.drawerBackdrop.addEventListener('click', closeDrawer);
  dom.btnCopyPitchBottom.addEventListener('click', () => {
    if (state.selectedLead && state.selectedLead.cold_email) {
      copyToClipboard(state.selectedLead.cold_email, "Outbound pitch copied to clipboard!");
    }
  });

  // Pricing Modal
  dom.btnSidebarUpgrade.addEventListener('click', () => openModal(dom.pricingModal));
  dom.btnClosePricingModal.addEventListener('click', () => closeModal(dom.pricingModal));

  // Settings Modal
  dom.btnOpenSettings.addEventListener('click', () => openModal(dom.settingsModal));
  dom.btnCloseSettingsModal.addEventListener('click', () => closeModal(dom.settingsModal));
  dom.btnCancelSettings.addEventListener('click', () => closeModal(dom.settingsModal));
  dom.btnSaveSettings.addEventListener('click', handleSaveSettings);

  // Settings Tabs
  dom.modalTabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const tab = btn.getAttribute('data-tab');
      showSettingsTab(tab);
    });
  });
}

// ===========================================================================
// User Profile & SaaS Credits
// ===========================================================================
async function loadUserProfile() {
  try {
    const res = await fetch('/api/user');
    const data = await res.json();
    state.user = data.user || state.user;

    const remaining = Math.max(0, state.user.credits_total - state.user.credits_used);
    dom.topCreditsText.textContent = `${remaining} / ${state.user.credits_total} Credits`;
    dom.userNameText.textContent = state.user.name || 'Brahman';
    dom.userAvatarText.textContent = (state.user.name || 'B')[0].toUpperCase();
    dom.greetingNameTitle.textContent = `Hi ${state.user.name || 'Brahman'} 👋`;
    dom.sidePlanName.textContent = `${state.user.plan || 'Pro'} Plan`;

    if (data.settings) {
      if (dom.settingSenderName) dom.settingSenderName.value = data.settings.sender_name || 'Brahman';
      if (dom.settingCompanyName) dom.settingCompanyName.value = data.settings.company_name || 'LocalReach Agency';
      if (dom.settingValueProp) dom.settingValueProp.value = data.settings.value_prop || 'custom client acquisition systems';
    }
  } catch (err) {
    console.error("Failed to load user profile:", err);
  }
}

async function handleUpgrade(planName) {
  try {
    const res = await fetch('/api/user/upgrade', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plan: planName })
    });

    const data = await res.json();
    if (data.status === 'ok') {
      showToast(`🎉 Upgraded to ${planName} Plan!`, "success");
      closeModal(dom.pricingModal);
      await loadUserProfile();
    }
  } catch (err) {
    showToast(`Upgrade failed: ${err.message}`, "error");
  }
}

// ===========================================================================
// View Controllers
// ===========================================================================
function showHomeView() {
  state.currentView = 'home';
  dom.sectionHomeCanvas.style.display = 'flex';
  dom.sectionResultsView.style.display = 'none';
  document.querySelectorAll('.recent-item').forEach(item => item.classList.remove('active'));
}

function showResultsView() {
  state.currentView = 'results';
  dom.sectionHomeCanvas.style.display = 'none';
  dom.sectionResultsView.style.display = 'flex';
}

function showSettingsTab(tabName) {
  dom.modalTabBtns.forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-tab') === tabName);
  });

  document.querySelectorAll('.settings-tab-pane').forEach(pane => {
    pane.style.display = pane.id === `stab-${tabName}` ? 'block' : 'none';
  });
}

// ===========================================================================
// Recent Scrapes Sidebar
// ===========================================================================
async function loadRecentHistory() {
  try {
    const res = await fetch('/api/history');
    const data = await res.json();
    state.history = data.files || [];

    const enriched = state.history.filter(f => f.type === 'enriched');

    if (enriched.length === 0) {
      dom.recentScrapesList.innerHTML = `
        <div style="font-size: 0.76rem; color: #94a3b8; padding: 0.5rem 0.25rem;">
          No previous scrapes yet.
        </div>
      `;
      return;
    }

    dom.recentScrapesList.innerHTML = enriched.map(item => {
      const title = item.query || item.filename.replace('enriched_leads_', '').replace('.json', '');
      const timeStr = item.modified ? formatTimeAgo(new Date(item.modified)) : '';

      return `
        <button class="recent-item" onclick="loadBatchFile('${escapeHtml(item.filename)}')">
          <span class="recent-item-title" title="${escapeHtml(title)}">${escapeHtml(title)}</span>
          <div class="recent-item-meta">
            <span>${item.leads_count || 0} prospects</span>
            <span>${timeStr}</span>
          </div>
        </button>
      `;
    }).join('');
  } catch (err) {
    console.error("Failed to load history:", err);
  }
}

async function loadBatchFile(filename) {
  try {
    const res = await fetch(`/api/leads/file?filename=${encodeURIComponent(filename)}`);
    const data = await res.json();
    renderBatchResults(data);
    showResultsView();
    showToast(`Loaded: ${data.query || filename}`, 'success');

    document.querySelectorAll('.recent-item').forEach(el => {
      el.classList.toggle('active', el.querySelector('.recent-item-title').textContent.includes(data.query || ''));
    });
  } catch (err) {
    showToast("Failed to load batch file", "error");
  }
}

function renderBatchResults(data) {
  let leads = [];
  if (Array.isArray(data)) {
    leads = data;
  } else if (data && data.leads) {
    leads = data.leads;
  }

  state.leadsData = {
    query: data.query || 'Outbound Batch',
    leads: leads,
    filename: data.filename || '',
    enriched_at: data.enriched_at || null
  };

  dom.resultsBatchTitle.textContent = state.leadsData.query ? `Batch: ${state.leadsData.query}` : 'Prospects Directory';
  dom.resultsBatchSubtitle.textContent = `${leads.length} prospects enriched & verified from Google Maps`;

  // Calculate Metrics
  const total = leads.length;
  dom.resMetricTotal.textContent = total;

  let emailCount = 0;
  let highCount = 0;
  let socialCount = 0;

  leads.forEach(l => {
    const s = Number(l.lead_score) || 0;
    if (s >= 4) highCount++;
    const ems = l.emails || [];
    if (ems.length > 0 && ems[0] !== 'N/A') emailCount++;
    const socs = l.social_media || {};
    if (Object.keys(socs).length > 0) socialCount++;
  });

  dom.resMetricEmail.textContent = total > 0 ? Math.round((emailCount / total) * 100) + '%' : '0%';
  dom.resMetricHigh.textContent = highCount;
  dom.resMetricSocial.textContent = total > 0 ? Math.round((socialCount / total) * 100) + '%' : '0%';

  // Render Table
  if (leads.length === 0) {
    dom.leadsTableBody.innerHTML = `
      <tr>
        <td colspan="6" style="text-align: center; padding: 2.5rem; color: #94a3b8;">
          No prospects found in this batch.
        </td>
      </tr>
    `;
    return;
  }

  dom.leadsTableBody.innerHTML = leads.map((lead, idx) => {
    const score = Number(lead.lead_score) || 0;
    const scoreClass = score >= 4 ? 'score-high' : score === 3 ? 'score-med' : 'score-low';
    const emails = lead.emails || [];
    const socials = lead.social_media || {};
    const currentStatus = lead.status || 'new';

    const contactStr = emails.length > 0 && emails[0] !== 'N/A'
      ? `<div style="font-weight: 600; color: #2563eb;">📧 ${escapeHtml(emails[0])}</div>`
      : `<div style="color: #94a3b8; font-size: 0.76rem;">No email discovered</div>`;

    const phoneStr = lead.phone && lead.phone !== 'N/A'
      ? `<div style="font-size: 0.74rem; color: #64748b;">📞 ${escapeHtml(lead.phone)}</div>`
      : '';

    const webStr = lead.website && lead.website !== 'N/A'
      ? `<a href="${lead.website}" target="_blank" onclick="event.stopPropagation()" style="color: #475569; text-decoration: none; font-size: 0.78rem;">🌐 ${escapeHtml(cleanHostname(lead.website))}</a>`
      : `<span style="color: #94a3b8; font-size: 0.78rem;">No website</span>`;

    const socialBadges = Object.keys(socials).map(n => `<span style="font-size: 0.7rem; padding: 1px 4px; background: #f1f5f9; border-radius: 3px;">${n}</span>`).join(' ');

    return `
      <tr onclick="openLeadDrawer(${idx})">
        <td>
          <span class="score-pill ${scoreClass}">★ ${score}/5</span>
        </td>
        <td>
          <select class="lead-status-select status-${currentStatus}" onclick="event.stopPropagation()" onchange="handleStatusChange(${idx}, this.value)">
            <option value="new" ${currentStatus === 'new' ? 'selected' : ''}>New</option>
            <option value="contacted" ${currentStatus === 'contacted' ? 'selected' : ''}>Contacted</option>
            <option value="qualified" ${currentStatus === 'qualified' ? 'selected' : ''}>Qualified</option>
            <option value="closed" ${currentStatus === 'closed' ? 'selected' : ''}>Closed</option>
          </select>
        </td>
        <td style="max-width: 260px;">
          <div style="font-weight: 700; color: #0f172a; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
            ${escapeHtml(lead.business_name || 'Business')}
          </div>
          <div style="font-size: 0.74rem; color: #64748b;">
            ${escapeHtml(lead.category || 'Local')} • ⭐ ${lead.rating || 'N/A'} (${lead.reviews_count || 0})
          </div>
        </td>
        <td>
          ${contactStr}
          ${phoneStr}
        </td>
        <td>
          ${webStr}
          <div style="margin-top: 3px;">${socialBadges}</div>
        </td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); openLeadDrawer(${idx});">
            Inspect Pitch →
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

// ===========================================================================
// Lead Status Pipeline Updater
// ===========================================================================
async function handleStatusChange(leadIndex, newStatus) {
  if (!state.leadsData.filename) return;

  try {
    const res = await fetch('/api/lead/status', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filename: state.leadsData.filename,
        lead_index: leadIndex,
        status: newStatus
      })
    });

    const data = await res.json();
    if (data.status === 'ok') {
      state.leadsData.leads[leadIndex].status = newStatus;
      showToast(`Lead marked as ${newStatus}`, 'success');
      renderBatchResults(state.leadsData);
    }
  } catch (err) {
    showToast(`Failed to update status: ${err.message}`, 'error');
  }
}

// ===========================================================================
// Prompt Execution & Live Progress
// ===========================================================================
async function handlePromptSubmit() {
  const query = dom.mainPromptInput.value.trim();
  if (!query) {
    showToast("Please type a search query or prospect niche", "error");
    return;
  }

  showResultsView();
  dom.liveProgressBanner.style.display = 'flex';
  dom.liveProgressStage.textContent = "Scraping Google Maps via SerpAPI...";
  dom.liveProgressPercent.textContent = "15%";
  dom.liveProgressBarFill.style.width = "15%";
  dom.liveProgressDetail.textContent = `Query: "${query}" (Limit: ${state.currentLimit})...`;
  dom.resultsBatchTitle.textContent = `Searching: ${query}`;
  dom.resultsBatchSubtitle.textContent = "SaaS Pipeline execution in progress...";
  dom.leadsTableBody.innerHTML = `
    <tr>
      <td colspan="6" style="text-align: center; padding: 3rem; color: #64748b;">
        <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">⚡</div>
        <div>Scraping Google Maps, verifying contact details & generating outreach pitches...</div>
      </td>
    </tr>
  `;

  try {
    const sender = dom.settingSenderName ? dom.settingSenderName.value.trim() : "Brahman";
    const comp = dom.settingCompanyName ? dom.settingCompanyName.value.trim() : "LocalReach Agency";
    const offer = dom.settingValueProp ? dom.settingValueProp.value.trim() : "custom client acquisition systems";

    const res = await fetch('/api/pipeline/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: query,
        limit: state.currentLimit,
        email_from: sender,
        email_company: comp,
        email_service: offer,
        use_ai_email: false
      })
    });

    const data = await res.json();
    if (data.task_id) {
      state.activeTaskId = data.task_id;
      pollPipelineTask(data.task_id);
    }
  } catch (err) {
    dom.liveProgressBanner.style.display = 'none';
    showToast(`Error: ${err.message}`, "error");
  }
}

function pollPipelineTask(taskId) {
  if (state.pollTimer) clearInterval(state.pollTimer);

  state.pollTimer = setInterval(async () => {
    try {
      const res = await fetch(`/api/pipeline/status/${taskId}`);
      const task = await res.json();

      dom.liveProgressBarFill.style.width = `${task.progress || 15}%`;
      dom.liveProgressPercent.textContent = `${task.progress || 15}%`;
      dom.liveProgressStage.textContent = task.stage === 'scraping' ? '1/3 Scraping Google Maps...' : task.stage === 'enriching' ? '2/3 Crawling Websites & Extracting Intel...' : '3/3 Finalizing Deliverable...';

      if (task.logs && task.logs.length > 0) {
        dom.liveProgressDetail.textContent = task.logs[task.logs.length - 1];
      }

      if (task.status === 'success') {
        clearInterval(state.pollTimer);
        dom.liveProgressBanner.style.display = 'none';
        showToast("🎉 Prospects scraped & enriched successfully!", "success");

        if (task.result_data) {
          renderBatchResults(task.result_data);
        }
        await loadRecentHistory();
        await loadUserProfile();
      } else if (task.status === 'error') {
        clearInterval(state.pollTimer);
        dom.liveProgressBanner.style.display = 'none';
        showToast(`Scrape Error: ${task.error}`, "error");
      }
    } catch (err) {
      console.error("Poll error:", err);
    }
  }, 1000);
}

// ===========================================================================
// Lead Pitch Drawer
// ===========================================================================
function openLeadDrawer(idx) {
  const lead = state.leadsData.leads[idx];
  if (!lead) return;
  state.selectedLead = lead;

  dom.drawerLeadName.textContent = lead.business_name || 'Business Overview';
  dom.drawerLeadSub.textContent = `${lead.category || 'Local Business'} • Rating: ${lead.rating || 'N/A'}★ (${lead.reviews_count || 0} reviews)`;

  const score = Number(lead.lead_score) || 0;
  const scoreClass = score >= 4 ? 'score-high' : score === 3 ? 'score-med' : 'score-low';
  dom.drawerScorePill.className = `score-pill ${scoreClass}`;
  dom.drawerScorePill.textContent = `Score: ${score}/5`;

  const emails = lead.emails || [];
  const socials = lead.social_media || {};
  const breakdown = lead.lead_score_breakdown || {};

  dom.drawerBody.innerHTML = `
    <!-- Intel Box -->
    <div style="background: #f8fafc; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 1rem; display: flex; flex-direction: column; gap: 0.6rem;">
      <div style="font-size: 0.72rem; font-weight: 700; color: #64748b; text-transform: uppercase;">Direct Contact Details</div>
      
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem; font-size: 0.82rem;">
        <div>
          <span style="color: #94a3b8; font-size: 0.7rem; font-weight: 600;">PHONE</span>
          <div>${lead.phone && lead.phone !== 'N/A' ? `<a href="tel:${lead.phone}" style="color: #2563eb; text-decoration: none;">${lead.phone}</a>` : '—'}</div>
        </div>

        <div>
          <span style="color: #94a3b8; font-size: 0.7rem; font-weight: 600;">WEBSITE</span>
          <div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
            ${lead.website && lead.website !== 'N/A' ? `<a href="${lead.website}" target="_blank" style="color: #2563eb;">${cleanHostname(lead.website)}</a>` : '—'}
          </div>
        </div>

        <div style="grid-column: span 2;">
          <span style="color: #94a3b8; font-size: 0.7rem; font-weight: 600;">VERIFIED EMAILS</span>
          <div style="margin-top: 3px; display: flex; gap: 0.4rem; flex-wrap: wrap;">
            ${emails.length > 0 ? emails.map(e => `<button class="btn btn-secondary btn-sm" onclick="copyToClipboard('${e}', 'Email copied!')">📧 ${e}</button>`).join('') : '<span style="color: #94a3b8;">None discovered</span>'}
          </div>
        </div>

        <div style="grid-column: span 2;">
          <span style="color: #94a3b8; font-size: 0.7rem; font-weight: 600;">SOCIAL PROFILES</span>
          <div style="margin-top: 3px; display: flex; gap: 0.35rem; flex-wrap: wrap;">
            ${Object.keys(socials).length > 0 ? Object.entries(socials).map(([n, u]) => `<a href="${u}" target="_blank" class="btn btn-secondary btn-sm">🔗 ${n}</a>`).join('') : '<span style="color: #94a3b8;">None found</span>'}
          </div>
        </div>
      </div>
    </div>

    <!-- Score Rubric -->
    <div style="background: #f8fafc; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 1rem;">
      <div style="font-size: 0.72rem; font-weight: 700; color: #64748b; text-transform: uppercase; margin-bottom: 0.5rem;">Quality Scoring Rubric</div>
      <div style="font-size: 0.78rem; color: #475569; display: flex; flex-direction: column; gap: 0.25rem;">
        <div>${breakdown.phone || '• Phone number verification'}</div>
        <div>${breakdown.website || '• Active website check'}</div>
        <div>${breakdown.email || '• Discovered email address'}</div>
        <div>${breakdown.social_media || '• Social profile presence'}</div>
        <div>${breakdown.reputation || '• Reputation & reviews check'}</div>
      </div>
    </div>

    <!-- Cold Pitch Text -->
    <div>
      <div style="font-size: 0.72rem; font-weight: 700; color: #64748b; text-transform: uppercase; margin-bottom: 0.4rem;">
        Tailored Outbound Pitch (${lead.cold_email_method || 'template'})
      </div>
      <div style="background: #ffffff; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 1rem; font-size: 0.84rem; line-height: 1.6; white-space: pre-wrap; color: #1e293b;">
        ${escapeHtml(lead.cold_email || 'No email pitch generated for this lead.')}
      </div>
    </div>
  `;

  if (emails.length > 0) {
    const sub = extractSubject(lead.cold_email);
    const body = extractBody(lead.cold_email);
    dom.drawerActionBtnContainer.innerHTML = `
      <a href="mailto:${emails[0]}?subject=${encodeURIComponent(sub)}&body=${encodeURIComponent(body)}" class="btn btn-primary btn-sm">
        ✉️ Launch Mail Client
      </a>
    `;
  } else {
    dom.drawerActionBtnContainer.innerHTML = '';
  }

  dom.drawerBackdrop.classList.add('active');
  dom.reviewDrawer.classList.add('open');
}

function closeDrawer() {
  dom.drawerBackdrop.classList.remove('active');
  dom.reviewDrawer.classList.remove('open');
}

// ===========================================================================
// Export & Settings
// ===========================================================================
async function handleExportCsv() {
  if (!state.leadsData.leads || state.leadsData.leads.length === 0) {
    showToast("No leads available to export", "error");
    return;
  }

  try {
    showToast("Generating CSV...", "info");
    const res = await fetch('/api/export/csv', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ leads: state.leadsData.leads })
    });

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `localreach_prospects_${Date.now()}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    showToast("CSV downloaded successfully!", "success");
  } catch (err) {
    showToast(`Export error: ${err.message}`, "error");
  }
}

async function handleSaveSettings() {
  const serp = dom.settingSerpKey.value.trim();
  const openai = dom.settingOpenAiKey.value.trim();
  const sheet = dom.settingGoogleSheet.value.trim();
  const sender = dom.settingSenderName ? dom.settingSenderName.value.trim() : null;
  const company = dom.settingCompanyName ? dom.settingCompanyName.value.trim() : null;
  const offer = dom.settingValueProp ? dom.settingValueProp.value.trim() : null;

  try {
    const res = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        serpapi_key: serp || null,
        openai_api_key: openai || null,
        google_sheet_id: sheet || null,
        sender_name: sender,
        company_name: comp,
        value_prop: offer
      })
    });

    const data = await res.json();
    if (data.status === 'ok') {
      showToast("Settings saved successfully!", "success");
      closeModal(dom.settingsModal);
      await loadUserProfile();
    }
  } catch (err) {
    showToast(`Error: ${err.message}`, "error");
  }
}

// ===========================================================================
// Utilities
// ===========================================================================
function openModal(m) { if (m) m.classList.add('active'); }
function closeModal(m) { if (m) m.classList.remove('active'); }

function copyToClipboard(text, msg = "Copied to clipboard!") {
  navigator.clipboard.writeText(text).then(() => {
    showToast(msg, "success");
  }).catch(() => {
    showToast("Failed to copy", "error");
  });
}

function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast`;
  toast.innerHTML = `<span>${type === 'success' ? '✅' : type === 'error' ? '❌' : '⚡'}</span> <span>${escapeHtml(message)}</span>`;
  dom.toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(8px)';
    toast.style.transition = 'all 0.2s ease';
    setTimeout(() => toast.remove(), 200);
  }, 2800);
}

function cleanHostname(url) {
  try {
    const u = new URL(url.startsWith('http') ? url : 'http://' + url);
    return u.hostname.replace('www.', '');
  } catch (e) {
    return url;
  }
}

function extractSubject(text) {
  if (!text) return "Partnership Proposal";
  const m = text.match(/^Subject:\s*(.+)$/m);
  return m ? m[1].trim() : "Partnership Inquiry";
}

function extractBody(text) {
  if (!text) return "";
  return text.replace(/^Subject:.*$/m, "").trim();
}

function formatTimeAgo(date) {
  const diffSec = Math.floor((Date.now() - date.getTime()) / 1000);
  if (diffSec < 60) return "just now";
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  return `${Math.floor(diffSec / 86400)}d ago`;
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
