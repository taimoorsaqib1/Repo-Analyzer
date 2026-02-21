/* ── State ───────────────────────────────────────────── */
const state = { streaming: false };

/* ── Helpers ─────────────────────────────────────────── */
const $  = id => document.getElementById(id);
const el = (tag, cls, html = '') => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html) e.innerHTML = html;
  return e;
};

function show(id)  { $(id).classList.remove('hidden'); }
function hide(id)  { $(id).classList.add('hidden'); }
function setActive(id) {
  ['emptyState','loadingState','contentArea'].forEach(hide);
  show(id);
}

/* ── URL inputs ──────────────────────────────────────── */
function addUrlRow(value = '') {
  const row = el('div', 'url-item');
  row.innerHTML = `
    <input type="text" class="url-input" placeholder="https://github.com/user/repo" value="${value}" />
    <button class="btn-remove" title="Remove">×</button>`;
  row.querySelector('.btn-remove').addEventListener('click', () => {
    row.remove();
    if ($('urlList').children.length === 0) addUrlRow();
  });
  $('urlList').appendChild(row);
  row.querySelector('input').focus();
}

$('addUrlBtn').addEventListener('click', () => addUrlRow());
addUrlRow(); // start with one

/* ── Tabs ────────────────────────────────────────────── */
document.addEventListener('click', e => {
  if (!e.target.matches('.tab')) return;
  const tab = e.target.dataset.tab;
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.add('hidden'));
  e.target.classList.add('active');
  $(`tab-${tab}`).classList.remove('hidden');
});

/* ── Analyse ─────────────────────────────────────────── */
$('analyzeBtn').addEventListener('click', async () => {
  const urls = [...document.querySelectorAll('.url-input')]
    .map(i => i.value.trim()).filter(Boolean);
  if (!urls.length) return alert('Add at least one repository URL.');

  const branch = $('branchInput').value.trim() || 'main';

  // UI
  setActive('loadingState');
  $('loadingTitle').textContent = 'Indexing repositories…';
  $('progressLog').innerHTML = '';
  $('analyzeBtn').disabled = true;
  $('analyzeBtnText').textContent = 'Indexing…';

  const logLine = (text, cls = '') => {
    const line = el('div', `progress-line ${cls}`, text);
    $('progressLog').appendChild(line);
    $('progressLog').scrollTop = $('progressLog').scrollHeight;
  };

  try {
    const res = await fetch('/api/ingest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ urls, branch }),
    });

    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    let   buffer  = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split('\n\n');
      buffer = lines.pop(); // keep incomplete chunk

      for (const raw of lines) {
        const line = raw.trim();
        if (!line.startsWith('data:')) continue;
        const evt = JSON.parse(line.slice(5).trim());

        if (evt.type === 'progress') {
          const ok = evt.message.startsWith('✔') || evt.message.startsWith('🧠');
          logLine(evt.message, ok ? 'ok' : '');

        } else if (evt.type === 'done') {
          renderIndexedSidebar(evt.repos);
          renderOverviewCards(evt.repos);
          setActive('contentArea');

        } else if (evt.type === 'error') {
          logLine('Error: ' + evt.message, 'err');
          $('loadingTitle').textContent = 'Indexing failed';
        }
      }
    }
  } catch (err) {
    logLine('Network error: ' + err.message, 'err');
  } finally {
    $('analyzeBtn').disabled = false;
    $('analyzeBtnText').textContent = 'Analyze Repos';
  }
});

/* ── Sidebar indexed list ────────────────────────────── */
function renderIndexedSidebar(repos) {
  $('indexedList').innerHTML = '';
  repos.forEach(r => {
    const item = el('div', 'indexed-item');
    const topLangs = Object.keys(r.languages || {}).slice(0, 3).join(', ') || '—';
    item.innerHTML = `
      <div class="repo-name">${r.name}</div>
      <div class="repo-meta">${r.file_count} files · ${topLangs}</div>`;
    $('indexedList').appendChild(item);
  });
  show('indexedSection');
}

/* ── Overview cards ──────────────────────────────────── */
function renderOverviewCards(repos) {
  $('repoCards').innerHTML = '';
  repos.forEach(r => {
    const s = r.summary || {};

    const mkBullets = (arr, icon = '▸') =>
      (arr || []).map(x => `<div class="feature-item"><span class="fi-icon">${icon}</span>${escHtml(x)}</div>`).join('');

    const mkTags = (arr, cls) =>
      (arr || []).map(x => `<span class="${cls}">${escHtml(x)}</span>`).join('');

    const langTags = Object.entries(r.languages || {}).map(([lang, cnt]) =>
      `<span class="lang-tag">${lang} <span class="lang-count">${cnt}</span></span>`).join('');

    const features    = mkBullets(s.key_features, '▸');
    const useCases    = mkBullets(s.use_cases, '◆');
    const entryPoints = mkBullets(s.entry_points, '📄');
    const limits      = mkBullets(s.limitations, '⚠');
    const techTags    = mkTags(s.tech_stack, 'tech-tag');
    const depTags     = mkTags(s.external_dependencies, 'dep-tag');

    const card = el('div', 'repo-card');
    card.innerHTML = `
      <div class="card-header">
        <div class="card-title">📦 ${escHtml(r.name)}</div>
        <a class="card-link" href="${escHtml(r.url)}" target="_blank">↗ GitHub</a>
      </div>

      ${s.overview ? `<div class="card-overview">${escHtml(s.overview)}</div>` : ''}

      ${s.purpose ? `
        <div class="card-purpose">🎯 ${escHtml(s.purpose)}</div>` : ''}

      ${features ? `
        <div>
          <div class="card-section-title">✨ Key Features</div>
          <div class="features-list">${features}</div>
        </div>` : ''}

      ${useCases ? `
        <div>
          <div class="card-section-title">💡 Use Cases</div>
          <div class="features-list">${useCases}</div>
        </div>` : ''}

      ${techTags ? `
        <div>
          <div class="card-section-title">🛠 Tech Stack</div>
          <div class="tech-tags">${techTags}</div>
        </div>` : ''}

      ${depTags ? `
        <div>
          <div class="card-section-title">🔗 External Dependencies</div>
          <div class="tech-tags">${depTags}</div>
        </div>` : ''}

      ${langTags ? `
        <div>
          <div class="card-section-title">📊 Languages</div>
          <div class="lang-tags">${langTags}</div>
        </div>` : ''}

      ${s.architecture ? `
        <div>
          <div class="card-section-title">🏗 Architecture</div>
          <div class="card-arch">${escHtml(s.architecture)}</div>
        </div>` : ''}

      ${entryPoints ? `
        <div>
          <div class="card-section-title">🚪 Entry Points</div>
          <div class="features-list">${entryPoints}</div>
        </div>` : ''}

      ${s.getting_started ? `
        <div>
          <div class="card-section-title">🚀 Getting Started</div>
          <div class="card-getting-started">${escHtml(s.getting_started)}</div>
        </div>` : ''}

      ${limits ? `
        <div>
          <div class="card-section-title">⚠ Limitations</div>
          <div class="features-list limitations">${limits}</div>
        </div>` : ''}

      <div class="card-stats">
        <span><span class="stat-val">${r.file_count}</span> files indexed</span>
      </div>`;

    $('repoCards').appendChild(card);
  });
}

/* ── Chat ────────────────────────────────────────────── */
$('sendBtn').addEventListener('click', sendMessage);
$('chatInput').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});

async function sendMessage() {
  if (state.streaming) return;
  const question = $('chatInput').value.trim();
  if (!question) return;

  $('chatInput').value = '';

  // Switch to chat tab
  document.querySelectorAll('.tab').forEach(t =>
    t.classList.toggle('active', t.dataset.tab === 'chat'));
  document.querySelectorAll('.tab-pane').forEach(p =>
    p.classList.add('hidden'));
  $('tab-chat').classList.remove('hidden');

  appendMessage('user', question);
  const botBubble = appendMessage('bot', '');
  const cursor = el('span', 'cursor', '▌');
  botBubble.querySelector('.msg-bubble').appendChild(cursor);

  $('sendBtn').disabled = true;
  state.streaming = true;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });

    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    let   buffer  = '';
    let   text    = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split('\n\n');
      buffer = lines.pop();

      for (const raw of lines) {
        const line = raw.trim();
        if (!line.startsWith('data:')) continue;
        const evt = JSON.parse(line.slice(5).trim());

        if (evt.type === 'token') {
          text += evt.content;
          const bubble = botBubble.querySelector('.msg-bubble');
          bubble.textContent = text;
          bubble.appendChild(cursor);
          $('messages').scrollTop = $('messages').scrollHeight;

        } else if (evt.type === 'done') {
          cursor.remove();
          if (evt.sources?.length) {
            const src = botBubble.querySelector('.msg-sources');
            src.innerHTML = '📄 Sources: ' +
              evt.sources.slice(0, 5).map(s => `<span>${escHtml(s)}</span>`).join(' · ');
          }

        } else if (evt.type === 'error') {
          cursor.remove();
          botBubble.querySelector('.msg-bubble').textContent = '⚠ ' + evt.message;
        }
      }
    }
  } catch (err) {
    cursor.remove();
    botBubble.querySelector('.msg-bubble').textContent = '⚠ Network error: ' + err.message;
  } finally {
    $('sendBtn').disabled = false;
    state.streaming = false;
  }
}

function appendMessage(role, text) {
  const wrap = el('div', `msg ${role}`);
  wrap.innerHTML = `
    <div class="msg-label">${role === 'user' ? 'You' : 'Assistant'}</div>
    <div class="msg-bubble">${escHtml(text)}</div>
    ${role === 'bot' ? '<div class="msg-sources"></div>' : ''}`;
  $('messages').appendChild(wrap);
  $('messages').scrollTop = $('messages').scrollHeight;
  return wrap;
}

/* ── Clear ───────────────────────────────────────────── */
$('clearBtn').addEventListener('click', async () => {
  if (!confirm('Clear the session? This deletes the vector database and cloned repos.')) return;
  await fetch('/api/clear', { method: 'POST' });
  hide('indexedSection');
  $('repoCards').innerHTML = '';
  $('messages').innerHTML = '';
  $('urlList').innerHTML = '';
  addUrlRow();
  setActive('emptyState');
});

/* ── Utils ───────────────────────────────────────────── */
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
