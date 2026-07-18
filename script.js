/* ============================================================
   BACKEND CONFIG
   The auth service (register/login/logout) and the api service
   (everything else) run as two separate Flask apps. Change these two
   lines if you run them on different hosts/ports.
   ============================================================ */
const AUTH_BASE = 'http://localhost:5000';
const API_BASE = 'http://localhost:5001';

/* Small wrapper around fetch that always sends/expects JSON, always
   includes cookies (the auth service uses a session cookie), and
   throws with the backend's own error message so callers can toast it. */
async function apiRequest(base, path, { method = 'GET', body } = {}) {
  let res;
  try {
    res = await fetch(base + path, {
      method,
      credentials: 'include',
      headers: body ? { 'Content-Type': 'application/json' } : {},
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    throw new Error(`Could not reach the server at ${base}. Is the backend running?`);
  }
  let data = null;
  try { data = await res.json(); } catch (_) { /* empty body, e.g. some errors */ }
  if (!res.ok) {
    throw new Error((data && data.error) || `Request failed (${res.status})`);
  }
  return data;
}
const authApi = (path, opts) => apiRequest(AUTH_BASE, path, opts);
const api = (path, opts) => apiRequest(API_BASE, path, opts);

/* ============================================================
   ICONS — tiny inline SVG set, injected wherever data-icon appears
   ============================================================ */
const ICONS = {
  mail: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/></svg>',
  file: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>',
  upload: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 16V4M6 10l6-6 6 6"/><path d="M4 18v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/></svg>',
  user: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M4 21c1.8-4 5-6 8-6s6.2 2 8 6"/></svg>',
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>',
  message: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
  calendar: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>',
  bell: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.9 1.9 0 0 0 3.4 0"/></svg>',
  users: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="8" r="3.5"/><path d="M2 20c1.3-3.2 3.8-5 7-5s5.7 1.8 7 5"/><path d="M16 5.5a3.5 3.5 0 0 1 0 7"/><path d="M17.5 15c2.6.4 4 1.9 4.9 5"/></svg>',
  logout: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/></svg>',
  camera: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>',
  'user-plus': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M19 8v6M22 11h-6"/></svg>',
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"/></svg>'
};
function stampIcons(root = document) {
  root.querySelectorAll('[data-icon]').forEach(el => {
    el.innerHTML = ICONS[el.getAttribute('data-icon')] || '';
  });
}
stampIcons();
// stamp the logo template into both logo slots
const logoMarkup = document.getElementById('logo-tpl').innerHTML;
document.getElementById('auth-logo').innerHTML = logoMarkup;
document.querySelector('.sidebar-top .mark').innerHTML = logoMarkup;

/* ============================================================
   TOAST
   ============================================================ */
function toast(msg){
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.remove('show'), 2400);
}

/* ============================================================
   APP STATE
   ============================================================ */
let currentUser = null;      // { user_id, name, email, ... } — the logged in user's row
let degrees = [];
let categories = [];
let mySkills = { teach: [], learn: [] };
let peopleIndex = [];        // merged user + skills, used by the Search page
let conversations = [];
let activeConvId = null;
let sessionsByTab = { upcoming: [], pending: [], completed: [], declined: [] };
let notifications = [];
let groupSessions = [];
const userCache = {};        // user_id -> { name, ... }, filled in lazily
const skillDescCache = {};   // user_skill_id -> description string, filled in lazily

function initials(name){
  return (name || '?').split(' ').filter(Boolean).slice(0, 2).map(w => w[0].toUpperCase()).join('');
}

/* ============================================================
   AUTH SCREEN
   ============================================================ */
const authTabs = document.querySelectorAll('.auth-tab');
function setAuthPanel(name){
  authTabs.forEach(t => t.classList.toggle('active', t.dataset.tab === name));
  document.querySelectorAll('.auth-form').forEach(f => f.classList.toggle('active', f.dataset.panel === name));
  document.querySelectorAll('[data-show-when]').forEach(el => el.classList.toggle('hidden', el.dataset.showWhen !== name));
}
authTabs.forEach(tab => tab.addEventListener('click', () => setAuthPanel(tab.dataset.tab)));
document.querySelectorAll('[data-goto]').forEach(a => a.addEventListener('click', e => {
  e.preventDefault(); setAuthPanel(a.dataset.goto);
}));

// verification method toggle
document.querySelectorAll('.verify-opt').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.verify-opt').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.verify-panel').forEach(p => p.classList.toggle('active', p.dataset.verifyPanel === btn.dataset.verify));
  });
});

// document upload (still local-only preview — no verification-document
// upload endpoint exists on the backend yet, so we just send the
// filename as a placeholder path)
const uploadDrop = document.getElementById('upload-drop');
uploadDrop.addEventListener('click', () => document.getElementById('signup-doc').click());
document.getElementById('signup-doc').addEventListener('change', e => {
  if(e.target.files[0]){
    document.getElementById('upload-label').textContent = e.target.files[0].name;
    uploadDrop.classList.add('has-file');
  }
});

function populateSelect(select, items, valueKey, labelKey, placeholder){
  select.innerHTML = `<option value="">${placeholder}</option>` +
    items.map(item => `<option value="${item[valueKey]}">${item[labelKey]}</option>`).join('');
}

async function loadLookupData(){
  try {
    const [degreesRes, categoriesRes] = await Promise.all([
      api('/api/degrees'),
      api('/api/skill-categories'),
    ]);
    degrees = degreesRes.degrees || [];
    categories = categoriesRes.categories || [];
    populateSelect(document.getElementById('signup-degree'), degrees, 'degree_id', 'degree_name', 'Select a degree');
    populateSelect(document.getElementById('gs-category'), categories, 'category_id', 'category_name', 'Select a category');
  } catch (err) {
    toast(err.message);
  }
}
loadLookupData();

// LOGIN
document.getElementById('login-form').addEventListener('submit', async e => {
  e.preventDefault();
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;
  try {
    const data = await authApi('/login', { method: 'POST', body: { email, password } });
    currentUser = data.user;
    sessionStorage.setItem('ubuntuskills_user', JSON.stringify(currentUser));
    toast(`Welcome back, ${currentUser.name}!`);
    await enterApp();
  } catch (err) {
    toast(err.message);
  }
});

// SIGN UP
document.getElementById('signup-form').addEventListener('submit', async e => {
  e.preventDefault();
  const name = document.getElementById('signup-name').value.trim();
  const password = document.getElementById('signup-password').value;
  const degreeId = document.getElementById('signup-degree').value;
  const classYear = document.getElementById('signup-class-year').value;
  const usingDocument = document.querySelector('.verify-opt.active').dataset.verify === 'document';

  const body = {
    name,
    password,
    degree_id: degreeId ? Number(degreeId) : null,
    class_year: classYear ? Number(classYear) : null,
  };

  if (usingDocument) {
    const file = document.getElementById('signup-doc').files[0];
    body.email = document.getElementById('signup-email').value.trim() || `${name.toLowerCase().replace(/\s+/g, '.')}@example.com`;
    body.verification_document_path = file ? `uploads/${file.name}` : null;
  } else {
    body.email = document.getElementById('signup-email').value.trim();
  }

  if (!body.email) { toast('Enter an email address first'); return; }

  try {
    const data = await authApi('/register', { method: 'POST', body });
    if (data.verification_status === 'verified') {
      toast('Account created — logging you in…');
      const loginData = await authApi('/login', { method: 'POST', body: { email: body.email, password } });
      currentUser = loginData.user;
      sessionStorage.setItem('ubuntuskills_user', JSON.stringify(currentUser));
      await enterApp();
    } else {
      toast('Account created — your document is pending manual review.');
      setAuthPanel('login');
    }
  } catch (err) {
    toast(err.message);
  }
});

async function enterApp(){
  document.getElementById('auth-screen').classList.add('hidden');
  document.getElementById('app-shell').classList.remove('hidden');
  await refreshEverything();
}

document.getElementById('logout-btn').addEventListener('click', async () => {
  try { await authApi('/logout', { method: 'POST' }); } catch (_) { /* log out locally regardless */ }
  currentUser = null;
  sessionStorage.removeItem('ubuntuskills_user');
  document.getElementById('app-shell').classList.add('hidden');
  document.getElementById('auth-screen').classList.remove('hidden');
});

// Resume a session on page refresh if we already have one
(function tryResumeSession(){
  const saved = sessionStorage.getItem('ubuntuskills_user');
  if (saved) {
    currentUser = JSON.parse(saved);
    enterApp();
  }
})();

/* ============================================================
   NAV ROUTING
   ============================================================ */
document.querySelectorAll('.nav-btn[data-view]').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-btn[data-view]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById('view-' + btn.dataset.view).classList.add('active');
  });
});
document.getElementById('profile-message-btn').addEventListener('click', () => {
  document.querySelector('.nav-btn[data-view="messages"]').click();
});

/* ============================================================
   LOAD EVERYTHING FOR THE LOGGED IN USER
   ============================================================ */
async function refreshEverything(){
  await loadLookupData();
  await Promise.all([
    loadProfile(),
    loadPeopleIndex(),
    loadConversations(),
    loadSessions(),
    loadNotifications(),
    loadGroupSessions(),
  ]);
}

/* ============================================================
   PROFILE
   ============================================================ */
async function loadProfile(){
  try {
    const { user } = await api(`/api/users/${currentUser.user_id}`);
    currentUser = { ...currentUser, ...user };

    document.querySelector('#view-profile h1').textContent = user.name;
    const degree = degrees.find(d => d.degree_id === user.degree_id);
    document.querySelector('#view-profile .muted').textContent =
      [degree ? degree.degree_name : null, user.class_year ? `Class of ${user.class_year}` : null].filter(Boolean).join(' · ') || 'No degree set yet';
    document.querySelector('#view-profile .stars').dataset.rating = user.credits_average;
    document.querySelector('#view-profile .credits-label').innerHTML =
      `${user.credits_average} <span class="muted">Ubuntu Credits (${user.credits_count} reviews)</span>`;

    const avatarEl = document.getElementById('profile-avatar');
    avatarEl.innerHTML = user.avatar_url ? `<img src="${user.avatar_url}" alt="">` : initials(user.name);

    const [teachRes, learnRes] = await Promise.all([
      api(`/api/users/${currentUser.user_id}/skills?type=teach`),
      api(`/api/users/${currentUser.user_id}/skills?type=learn`),
    ]);
    mySkills = { teach: teachRes.skills, learn: learnRes.skills };
    renderSkillChips();

    const { reviews } = await api(`/api/users/${currentUser.user_id}/reviews`);
    renderReviews(reviews);
  } catch (err) {
    toast(err.message);
  }
}

function renderSkillChips(){
  document.querySelectorAll('.chip-input').forEach(group => {
    const type = group.dataset.chipGroup; // 'teach' or 'learn'
    const input = group.querySelector('input');
    const chipClass = type === 'teach' ? 'chip-teal' : 'chip-steel';
    group.querySelectorAll('.chip').forEach(c => c.remove());
    mySkills[type].forEach(skill => {
      const chip = document.createElement('span');
      chip.className = `chip ${chipClass}`;
      chip.dataset.userSkillId = skill.user_skill_id;
      chip.innerHTML = `${skill.description} <button data-remove>×</button>`;
      group.insertBefore(chip, input);
    });
  });
}

document.querySelectorAll('.chip-input').forEach(group => {
  const input = group.querySelector('input');
  const type = group.dataset.chipGroup;

  input.addEventListener('keydown', async e => {
    if (e.key === 'Enter' && input.value.trim()) {
      e.preventDefault();
      const description = input.value.trim();

      if (!categories.length) { toast('Skill categories are still loading, try again in a second'); return; }
      // Best-effort match of the free text to an existing category name,
      // otherwise fall back to asking which category it belongs to.
      let category = categories.find(c => description.toLowerCase().includes(c.category_name.toLowerCase()));
      if (!category) {
        const listing = categories.map((c, i) => `${i + 1}. ${c.category_name}`).join('\n');
        const pick = prompt(`Which category is "${description}" under?\n\n${listing}`, '1');
        const idx = Number(pick) - 1;
        category = categories[idx] || categories[0];
      }

      try {
        await api(`/api/users/${currentUser.user_id}/skills`, {
          method: 'POST',
          body: { category_id: category.category_id, description, skill_type: type },
        });
        input.value = '';
        await loadProfile();
        toast('Skill added to your profile');
      } catch (err) {
        toast(err.message);
      }
    }
  });

  group.addEventListener('click', async e => {
    if (e.target.matches('[data-remove]')) {
      const chip = e.target.closest('.chip');
      const userSkillId = chip.dataset.userSkillId;
      try {
        await api(`/api/users/${currentUser.user_id}/skills/${userSkillId}`, { method: 'DELETE' });
        chip.remove();
        toast('Skill removed');
      } catch (err) {
        toast(err.message);
      }
    }
  });
});

document.getElementById('avatar-input').addEventListener('change', e => {
  const file = e.target.files[0];
  if(!file) return;
  const reader = new FileReader();
  reader.onload = async ev => {
    document.getElementById('profile-avatar').innerHTML = `<img src="${ev.target.result}" alt="">`;
    try {
      await api(`/api/users/${currentUser.user_id}`, { method: 'PATCH', body: { avatar_url: ev.target.result } });
    } catch (err) {
      toast(err.message);
    }
  };
  reader.readAsDataURL(file);
});

function renderReviews(reviews){
  document.getElementById('reviews-list').innerHTML = (reviews || []).map(r => `
    <div class="review-item">
      <div class="avatar avatar-sm">${initials(r.reviewer_name || '')}</div>
      <div class="review-body">
        <div class="review-top">
          <span class="review-name">${r.reviewer_name || 'A student'}</span>
          <span class="review-stars">${'★'.repeat(r.rating)}${'☆'.repeat(5 - r.rating)}</span>
        </div>
        <p class="review-text">${r.comment || ''}</p>
        <p class="review-date">${(r.created_at || '').slice(0, 10)}</p>
      </div>
    </div>`).join('') || `<p class="muted">No reviews yet.</p>`;
  document.querySelector('#view-profile .card-head .muted').textContent = `${(reviews || []).length} total`;
}

/* ============================================================
   SEARCH — powered by /api/search/users and /api/search/skills
   ============================================================ */
async function loadPeopleIndex(){
  try {
    const [usersRes, teachRes, learnRes] = await Promise.all([
      api('/api/search/users'),
      api('/api/search/skills?type=teach'),
      api('/api/search/skills?type=learn'),
    ]);

    const byId = {};
    (usersRes.users || []).forEach(u => {
      if (u.user_id === currentUser.user_id) return; // don't show yourself in search
      byId[u.user_id] = {
        user_id: u.user_id,
        name: u.name,
        meta: [degrees.find(d => d.degree_id === u.degree_id)?.degree_name, u.class_year ? `Class of ${u.class_year}` : null].filter(Boolean).join(' · '),
        rating: u.credits_average,
        initials: initials(u.name),
        teach: [],
        learn: [],
        teachSkillIds: [],
      };
    });
    (teachRes.results || []).forEach(s => {
      if (byId[s.user_id]) { byId[s.user_id].teach.push(s.description); byId[s.user_id].teachSkillIds.push(s.user_skill_id); }
    });
    (learnRes.results || []).forEach(s => {
      if (byId[s.user_id]) byId[s.user_id].learn.push(s.description);
    });

    peopleIndex = Object.values(byId);
    renderResults(document.getElementById('search-input').value);
  } catch (err) {
    toast(err.message);
  }
}

let activeFilter = 'all';
function renderResults(query=''){
  const q = query.toLowerCase();
  let list = peopleIndex.filter(p => {
    const text = (p.name + ' ' + p.teach.join(' ') + ' ' + p.learn.join(' ')).toLowerCase();
    return text.includes(q);
  });
  if(activeFilter === 'top') list = list.filter(p => p.rating >= 4.7);
  if(activeFilter === 'teach') list = list.filter(p => p.teach.length);
  if(activeFilter === 'learn') list = list.filter(p => p.learn.length);
  document.getElementById('results-grid').innerHTML = list.map((p, i) => `
    <div class="result-card">
      <div class="result-top">
        <div class="avatar avatar-md">${p.initials}</div>
        <div>
          <div class="result-name">${p.name}</div>
          <div class="result-meta">${p.meta} · ★ ${p.rating}</div>
        </div>
      </div>
      <div class="result-tags">
        ${p.teach.map(s => `<span class="tag">Teaches ${s}</span>`).join('')}
        ${activeFilter !== 'teach' ? p.learn.map(s => `<span class="tag" style="background:var(--teal);color:#0F3A30">Wants ${s}</span>`).join('') : ''}
      </div>
      <div class="result-actions">
        <button class="btn btn-secondary" data-request-idx="${i}" ${p.teachSkillIds.length ? '' : 'disabled'}>Request session</button>
        <button class="btn btn-primary" data-message-idx="${i}">Message</button>
      </div>
    </div>`).join('') || `<p class="muted">No one matches that search yet.</p>`;

  document.querySelectorAll('[data-message-idx]').forEach(btn => btn.addEventListener('click', async () => {
    const person = list[Number(btn.dataset.messageIdx)];
    try {
      const { conversation_id } = await api('/api/conversations', { method: 'POST', body: { participant_ids: [currentUser.user_id, person.user_id] } });
      await loadConversations();
      activeConvId = conversation_id;
      document.querySelector('.nav-btn[data-view="messages"]').click();
      renderConvList(); renderChat();
    } catch (err) {
      toast(err.message);
    }
  }));

  document.querySelectorAll('[data-request-idx]').forEach(btn => btn.addEventListener('click', async () => {
    const person = list[Number(btn.dataset.requestIdx)];
    const when = prompt(`When would you like to meet ${person.name}? (YYYY-MM-DDTHH:MM)`, '2026-07-25T16:00');
    if (!when) return;
    try {
      await api('/api/sessions', { method: 'POST', body: { learner_id: currentUser.user_id, user_skill_id: person.teachSkillIds[0], scheduled_time: when } });
      toast(`Session requested with ${person.name}`);
      await loadSessions();
    } catch (err) {
      toast(err.message);
    }
  }));
}
document.getElementById('search-input').addEventListener('input', e => renderResults(e.target.value));
document.querySelectorAll('#filter-row .filter-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    document.querySelectorAll('#filter-row .filter-chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
    activeFilter = chip.dataset.filter;
    renderResults(document.getElementById('search-input').value);
  });
});

/* ============================================================
   MESSAGES
   ============================================================ */
async function loadConversations(){
  try {
    const { conversations: convs } = await api(`/api/users/${currentUser.user_id}/conversations`);
    conversations = (convs || []).map(c => {
      const others = (c.participants || []).filter(p => p.user_id !== currentUser.user_id);
      const name = c.is_group ? 'Group chat' : (others[0]?.name || 'Conversation');
      return { id: c.conversation_id, name, initials: initials(name), group: !!c.is_group };
    });
    if (!activeConvId && conversations.length) activeConvId = conversations[0].id;
    renderConvList();
    if (activeConvId) await renderChat();
  } catch (err) {
    toast(err.message);
  }
}
function renderConvList(){
  document.getElementById('conv-items').innerHTML = conversations.map(c => `
    <div class="conv-item ${c.id === activeConvId ? 'active' : ''}" data-conv="${c.id}">
      <div class="avatar avatar-md">${c.initials}</div>
      <div class="conv-info">
        <div class="conv-name">${c.name}${c.group ? '<span class="group-icon-badge">GROUP</span>' : ''}</div>
        <div class="conv-preview">${c.preview || ''}</div>
      </div>
    </div>`).join('') || `<p class="muted" style="padding:16px">No conversations yet — message someone from Search.</p>`;
  document.querySelectorAll('.conv-item').forEach(el => el.addEventListener('click', async () => {
    activeConvId = Number(el.dataset.conv);
    renderConvList(); await renderChat();
  }));
}
async function renderChat(){
  const c = conversations.find(x => x.id === activeConvId);
  if (!c) { document.getElementById('chat-header').innerHTML = ''; document.getElementById('chat-body').innerHTML = ''; return; }
  document.getElementById('chat-header').innerHTML = `<div class="avatar avatar-sm">${c.initials}</div><span>${c.name}</span>`;
  try {
    const { messages } = await api(`/api/conversations/${c.id}/messages`);
    document.getElementById('chat-body').innerHTML = (messages || [])
      .map(m => `<div class="msg-bubble ${m.sender_id === currentUser.user_id ? 'msg-me' : 'msg-them'}">${m.message_text}</div>`)
      .join('');
    const body = document.getElementById('chat-body');
    body.scrollTop = body.scrollHeight;
  } catch (err) {
    toast(err.message);
  }
}
document.getElementById('chat-form').addEventListener('submit', async e => {
  e.preventDefault();
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if(!text || !activeConvId) return;
  try {
    await api(`/api/conversations/${activeConvId}/messages`, { method: 'POST', body: { sender_id: currentUser.user_id, message_text: text } });
    input.value = '';
    await renderChat();
  } catch (err) {
    toast(err.message);
  }
});
document.getElementById('new-group-btn').addEventListener('click', () => {
  toast('Pick two or more people from Search to start a group chat.');
});

/* ============================================================
   SESSIONS
   ============================================================ */
async function getCachedUser(userId){
  if (userCache[userId]) return userCache[userId];
  try {
    const { user } = await api(`/api/users/${userId}`);
    userCache[userId] = user;
    return user;
  } catch (_) {
    return null;
  }
}
async function getCachedSkillDescription(teacherId, userSkillId){
  if (skillDescCache[userSkillId]) return skillDescCache[userSkillId];
  try {
    const { skills } = await api(`/api/users/${teacherId}/skills`);
    (skills || []).forEach(s => { skillDescCache[s.user_skill_id] = s.description; });
    return skillDescCache[userSkillId] || 'Session';
  } catch (_) {
    return 'Session';
  }
}
async function enrichSessions(rawSessions){
  return Promise.all(rawSessions.map(async s => {
    const isTeacher = s.teacher_id === currentUser.user_id;
    const otherId = isTeacher ? s.learner_id : s.teacher_id;
    const [otherUser, description] = await Promise.all([
      getCachedUser(otherId),
      getCachedSkillDescription(s.teacher_id, s.user_skill_id),
    ]);
    return { ...s, isTeacher, otherName: otherUser ? otherUser.name : `User #${otherId}`, description };
  }));
}

async function loadSessions(){
  try {
    const [upcoming, pending, completed, declined] = await Promise.all([
      api(`/api/users/${currentUser.user_id}/sessions?status=approved`),
      api(`/api/users/${currentUser.user_id}/sessions?status=pending`),
      api(`/api/users/${currentUser.user_id}/sessions?status=completed`),
      api(`/api/users/${currentUser.user_id}/sessions?status=declined`),
    ]);
    const [u, p, c, d] = await Promise.all([
      enrichSessions(upcoming.sessions || []),
      enrichSessions(pending.sessions || []),
      enrichSessions(completed.sessions || []),
      enrichSessions(declined.sessions || []),
    ]);
    sessionsByTab = { upcoming: u, pending: p, completed: c, declined: d };
    renderSessions();
  } catch (err) {
    toast(err.message);
  }
}

let currentSessionTab = 'upcoming';
function sessionLabel(s){
  return `${s.description || 'Session'} with ${s.otherName}`;
}
function renderSessions(){
  const list = sessionsByTab[currentSessionTab] || [];
  document.getElementById('sessions-list').innerHTML = list.map((s, i) => {
    const statusLabel = s.status.charAt(0).toUpperCase() + s.status.slice(1);
    let actions = '';
    if (currentSessionTab === 'upcoming') {
      actions = `<button class="btn btn-secondary" data-cancel-idx="${i}">Cancel</button>`;
    }
    if (currentSessionTab === 'pending') {
      actions = s.isTeacher
        ? `<button class="btn btn-primary" data-approve-idx="${i}">Approve</button><button class="btn btn-secondary" data-decline-idx="${i}">Decline</button>`
        : `<button class="btn btn-secondary" data-cancel-idx="${i}">Withdraw</button>`;
    }
    if (currentSessionTab === 'completed') {
      const myFlag = s.isTeacher ? s.completed_by_teacher : s.completed_by_learner;
      const bothDone = s.completed_by_teacher && s.completed_by_learner;
      if (!bothDone && !myFlag) actions = `<button class="btn btn-secondary" data-confirm-idx="${i}">Confirm it happened</button>`;
      else if (!s.isTeacher) actions = `<button class="btn btn-primary" data-review-idx="${i}">Leave review</button>`;
      else actions = `<span class="muted">Waiting on learner review</span>`;
    }
    return `
      <div class="session-card">
        <div class="session-info">
          <div class="session-skill">${sessionLabel(s)}</div>
          <div class="session-meta">${s.scheduled_time}</div>
        </div>
        <span class="status-badge status-${s.status}">${statusLabel}</span>
        <div class="session-actions">${actions}</div>
      </div>`;
  }).join('') || `<p class="muted">Nothing here yet.</p>`;

  document.querySelectorAll('[data-approve-idx]').forEach(btn => btn.addEventListener('click', () => respondSession(list[Number(btn.dataset.approveIdx)], 'approved')));
  document.querySelectorAll('[data-decline-idx]').forEach(btn => btn.addEventListener('click', () => respondSession(list[Number(btn.dataset.declineIdx)], 'declined')));
  document.querySelectorAll('[data-cancel-idx]').forEach(btn => btn.addEventListener('click', () => cancelSession(list[Number(btn.dataset.cancelIdx)])));
  document.querySelectorAll('[data-confirm-idx]').forEach(btn => btn.addEventListener('click', () => completeSession(list[Number(btn.dataset.confirmIdx)])));
  document.querySelectorAll('[data-review-idx]').forEach(btn => btn.addEventListener('click', () => openReviewModal(list[Number(btn.dataset.reviewIdx)])));
}
document.querySelectorAll('[data-session-tab]').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-session-tab]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentSessionTab = btn.dataset.sessionTab;
    renderSessions();
  });
});

async function respondSession(session, status){
  try {
    await api(`/api/sessions/${session.session_id}/respond`, { method: 'PATCH', body: { status } });
    toast(`Session ${status}`);
    await loadSessions();
  } catch (err) { toast(err.message); }
}
async function cancelSession(session){
  try {
    await api(`/api/sessions/${session.session_id}/cancel`, { method: 'PATCH', body: { cancelled_by: currentUser.user_id } });
    toast('Session cancelled');
    await loadSessions();
  } catch (err) { toast(err.message); }
}
async function completeSession(session){
  try {
    await api(`/api/sessions/${session.session_id}/complete`, { method: 'PATCH', body: { user_id: currentUser.user_id } });
    toast('Marked as completed on your side');
    await loadSessions();
  } catch (err) { toast(err.message); }
}

/* review modal */
let selectedStars = 0;
let reviewTargetSession = null;
function openReviewModal(session){
  reviewTargetSession = session;
  document.getElementById('review-modal-sub').textContent = `How was your session? (${sessionLabel(session)})`;
  selectedStars = 0;
  document.querySelectorAll('#star-picker button').forEach(b => b.classList.remove('selected'));
  document.getElementById('review-text').value = '';
  document.getElementById('review-modal').classList.add('active');
}
document.querySelectorAll('#star-picker button').forEach(btn => {
  btn.addEventListener('click', () => {
    selectedStars = Number(btn.dataset.star);
    document.querySelectorAll('#star-picker button').forEach(b => b.classList.toggle('selected', Number(b.dataset.star) <= selectedStars));
  });
});
document.getElementById('submit-review-btn').addEventListener('click', async () => {
  if(!selectedStars){ toast('Pick a star rating first'); return; }
  if(!reviewTargetSession) return;
  try {
    await api(`/api/sessions/${reviewTargetSession.session_id}/review`, {
      method: 'POST',
      body: { reviewer_id: currentUser.user_id, rating: selectedStars, comment: document.getElementById('review-text').value.trim() },
    });
    closeModals();
    await Promise.all([loadSessions(), loadProfile()]);
    toast(`Review submitted — ${selectedStars} Ubuntu Credits awarded!`);
  } catch (err) {
    toast(err.message);
  }
});

/* ============================================================
   NOTIFICATIONS
   ============================================================ */
const NOTIF_ICON = {
  session_requested: 'calendar', session_approved: 'calendar', session_declined: 'calendar',
  session_cancelled: 'calendar', session_reminder: 'bell', review_prompt: 'bell',
  group_session_announced: 'users', new_message: 'message',
};
async function loadNotifications(){
  try {
    const { notifications: list } = await api(`/api/users/${currentUser.user_id}/notifications`);
    notifications = list || [];
    renderNotifications();
  } catch (err) {
    toast(err.message);
  }
}
function renderNotifications(){
  document.getElementById('notif-list').innerHTML = notifications.map(n => `
    <div class="notif-item ${!n.is_read ? 'unread' : ''}">
      <div class="notif-icon"><i data-icon="${NOTIF_ICON[n.notification_type] || 'bell'}"></i></div>
      <div class="notif-body">
        <p class="notif-text">${n.message}</p>
        <p class="notif-time">${(n.created_at || '').slice(0, 16).replace('T', ' ')}</p>
        ${n.notification_type === 'session_requested' && !n.is_read ? `<div class="notif-actions"><button class="btn btn-primary" data-approve="${n.related_session_id}">Approve</button><button class="btn btn-secondary" data-decline="${n.related_session_id}">Decline</button></div>` : ''}
      </div>
    </div>`).join('') || `<p class="muted">No notifications yet.</p>`;
  stampIcons(document.getElementById('notif-list'));
  updateNotifBadge();
}
function updateNotifBadge(){
  const count = notifications.filter(n => !n.is_read).length;
  const badge = document.getElementById('notif-badge');
  badge.textContent = count;
  badge.style.display = count ? '' : 'none';
}
document.getElementById('mark-all-read').addEventListener('click', async () => {
  try {
    await api(`/api/users/${currentUser.user_id}/notifications/read-all`, { method: 'PATCH' });
    await loadNotifications();
  } catch (err) { toast(err.message); }
});
document.getElementById('notif-list').addEventListener('click', async e => {
  if(e.target.matches('[data-approve]')){
    await api(`/api/sessions/${e.target.dataset.approve}/respond`, { method: 'PATCH', body: { status: 'approved' } });
    toast('Session approved — added to your upcoming sessions.');
    await Promise.all([loadNotifications(), loadSessions()]);
  }
  if(e.target.matches('[data-decline]')){
    await api(`/api/sessions/${e.target.dataset.decline}/respond`, { method: 'PATCH', body: { status: 'declined' } });
    toast('Session declined.');
    await Promise.all([loadNotifications(), loadSessions()]);
  }
});

/* ============================================================
   COMMUNITY
   ============================================================ */
async function loadGroupSessions(){
  try {
    const { group_sessions } = await api('/api/group-sessions');
    groupSessions = group_sessions || [];
    renderCommunity();
  } catch (err) {
    toast(err.message);
  }
}
function renderCommunity(){
  document.getElementById('community-grid').innerHTML = groupSessions.map(g => {
    const memberCount = g.current_members ?? 0;
    const full = memberCount >= g.max_participants;
    return `
    <div class="gs-card">
      <div class="gs-top">
        <div>
          <div class="gs-topic">${g.topic}</div>
          <div class="gs-teacher">Hosted by ${g.teacher_name || `User #${g.teacher_id}`}</div>
        </div>
        <button class="btn-icon gs-chat-icon" data-gs-chat="${g.group_session_id}" title="Group chat"><i data-icon="message"></i></button>
      </div>
      <div class="gs-time"><i data-icon="calendar"></i> ${g.scheduled_time}</div>
      <div class="gs-seats">${memberCount} / ${g.max_participants} joined</div>
      <div class="seats-bar"><div class="seats-fill" style="width:${(memberCount/g.max_participants)*100}%"></div></div>
      <div class="gs-actions">
        <button class="btn ${full ? 'btn-secondary' : 'btn-primary'}" data-gs-join="${g.group_session_id}" ${full ? 'disabled' : ''}>${full ? 'Full' : 'Join session'}</button>
      </div>
    </div>`;
  }).join('') || `<p class="muted">No group sessions scheduled yet — host one!</p>`;
  stampIcons(document.getElementById('community-grid'));
  document.querySelectorAll('[data-gs-join]').forEach(btn => btn.addEventListener('click', async () => {
    try {
      await api(`/api/group-sessions/${btn.dataset.gsJoin}/join`, { method: 'POST', body: { user_id: currentUser.user_id } });
      toast('You joined the session — added to the group chat.');
      await Promise.all([loadGroupSessions(), loadConversations()]);
    } catch (err) {
      toast(err.message);
    }
  }));
  document.querySelectorAll('[data-gs-chat]').forEach(btn => btn.addEventListener('click', () => {
    document.querySelector('.nav-btn[data-view="messages"]').click();
  }));
}

document.getElementById('create-group-session-btn').addEventListener('click', () => {
  document.getElementById('group-session-modal').classList.add('active');
});
document.getElementById('publish-group-session').addEventListener('click', async () => {
  const topic = document.getElementById('gs-topic').value.trim();
  const time = document.getElementById('gs-time').value;
  const categoryId = document.getElementById('gs-category').value;
  if(!topic || !time || !categoryId){ toast('Add a topic, category, and time slot first'); return; }
  try {
    await api('/api/group-sessions', {
      method: 'POST',
      body: { teacher_id: currentUser.user_id, category_id: Number(categoryId), topic, scheduled_time: time, max_participants: 5 },
    });
    document.getElementById('gs-topic').value = '';
    document.getElementById('gs-time').value = '';
    document.getElementById('gs-category').value = '';
    closeModals();
    await loadGroupSessions();
    toast('Group session published!');
  } catch (err) {
    toast(err.message);
  }
});

/* ============================================================
   MODAL HELPERS
   ============================================================ */
function closeModals(){ document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('active')); }
document.querySelectorAll('[data-close-modal]').forEach(btn => btn.addEventListener('click', closeModals));
document.querySelectorAll('.modal-overlay').forEach(overlay => overlay.addEventListener('click', e => { if(e.target === overlay) closeModals(); }));
