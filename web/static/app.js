/*
  Repo Analyzer - Phase 2 Frontend
  Workspace management, File Explorer + Code Viewer, Markdown chat,
  auto-resize textarea, toast notifications, save-workspace modal.
*/

/* -- Globals ---------------------------------------------------------------- */
const state = { streaming: false };

/* -- DOM helpers ------------------------------------------------------------ */
const $  = id  => document.getElementById(id);
const el = (tag, cls, html) => {
  const e = document.createElement(tag);
  if (cls)  e.className = cls;
  if (html !== undefined) e.innerHTML = html;
  return e;
};
const show = id => $(id).classList.remove('hidden');
const hide = id => $(id).classList.add('hidden');

function setActive(id) {
  ['emptyState', 'loadingState', 'contentArea'].forEach(hide);
  show(id);
  if (id === 'contentArea') {
    $('saveWorkspaceBtn').disabled = false;
    $('newChatBtn').style.display = '';
  }
}

/* -- HTML escaping ---------------------------------------------------------- */
function esc(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/* == TOAST NOTIFICATIONS ==================================================== */
function toast(message, type, duration) {
  type     = type     || 'info';
  duration = duration || 3000;
  const icons = { success: '[OK]', error: '[!]', info: '[i]' };
  const t = el('div', 'toast ' + type, '<span>' + icons[type] + '</span> ' + esc(message));
  $('toasts').appendChild(t);
  setTimeout(function() { t.remove(); }, duration);
}

/* == CODE VIEWER PANEL ====================================================== */
function openCodeViewer(path, content, language) {
  $('cvPath').textContent = path;
  const codeEl = $('cvCode');
  codeEl.textContent = content;
  codeEl.className = 'language-' + language;
  hljs.highlightElement(codeEl);
  $('codeViewer').classList.add('open');
  $('overlay').classList.add('show');
}

function closeCodeViewer() {
  $('codeViewer').classList.remove('open');
  $('overlay').classList.remove('show');
}

$('cvClose').addEventListener('click', closeCodeViewer);
$('overlay').addEventListener('click', closeCodeViewer);
$('cvCopy').addEventListener('click', function() {
  navigator.clipboard.writeText($('cvCode').textContent)
    .then(function() { toast('Code copied!', 'success'); });
});

async function openFilePath(path) {
  try {
    const res  = await fetch('/api/file?path=' + encodeURIComponent(path));
    if (!res.ok) { toast('File not found', 'error'); return; }
    const data = await res.json();
    openCodeViewer(data.path, data.content, data.language);
  } catch (e) { toast('Failed to load file', 'error'); }
}

/* == WORKSPACE MANAGEMENT =================================================== */
async function loadWorkspaceList() {
  try {
    const res  = await fetch('/api/workspaces');
    const data = await res.json();
    renderWorkspaceList(data.workspaces || []);
  } catch (e) { /* silent */ }
}

function renderWorkspaceList(workspaces) {
  const list = $('workspaceList');
  if (!workspaces.length) {
    list.innerHTML = '<div class="ws-empty">No saved workspaces</div>';
    return;
  }
  list.innerHTML = '';
  workspaces.forEach(function(ws) {
    const repoNames = (ws.repos || []).map(function(r) { return r.name; }).join(', ') || 'none';
    const date      = (ws.created_at || '').slice(0, 10);
    const item      = el('div', 'ws-item');
    item.innerHTML  =
      '<div class="ws-item-info">' +
        '<div class="ws-name" title="' + esc(ws.name) + '">' + esc(ws.name) + '</div>' +
        '<div class="ws-meta">' + esc(repoNames) + ' &middot; ' + esc(date) + '</div>' +
      '</div>' +
      '<button class="ws-del" title="Delete workspace">X</button>';

    item.querySelector('.ws-item-info').addEventListener('click', function() {
      doLoadWorkspace(ws.name);
    });
    item.querySelector('.ws-del').addEventListener('click', async function(e) {
      e.stopPropagation();
      if (!confirm('Delete workspace "' + ws.name + '"?')) return;
      await fetch('/api/workspaces/' + encodeURIComponent(ws.name), { method: 'DELETE' });
      toast('Workspace "' + ws.name + '" deleted', 'info');
      loadWorkspaceList();
    });
    list.appendChild(item);
  });
}

async function doLoadWorkspace(name) {
  try {
    const res = await fetch('/api/workspaces/load', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name }),
    });
    if (!res.ok) {
      const err = await res.json();
      toast(err.detail || 'Load failed', 'error');
      return;
    }
    const data = await res.json();
    renderIndexedSidebar(data.repos);
    renderOverviewCards(data.repos);
    updateTopbar(data.repos);
    setActive('contentArea');
    $('messages').innerHTML = '';
    toast('Workspace "' + name + '" loaded - no re-indexing needed!', 'success', 4000);
    loadFileTree();
  } catch (e) { toast('Failed to load workspace', 'error'); }
}

$('refreshWorkspacesBtn').addEventListener('click', function() { loadWorkspaceList(); });

/* Save workspace modal */
$('saveWorkspaceBtn').addEventListener('click', function() {
  const backdrop = el('div', 'modal-backdrop');
  backdrop.innerHTML =
    '<div class="modal">' +
      '<h3>Save Workspace</h3>' +
      '<input type="text" id="wsNameInput" placeholder="e.g. firecrawl-analysis" />' +
      '<div class="modal-actions">' +
        '<button class="modal-cancel" id="modalCancelBtn">Cancel</button>' +
        '<button class="modal-confirm" id="modalSaveBtn">Save</button>' +
      '</div>' +
    '</div>';
  document.body.appendChild(backdrop);
  const input = backdrop.querySelector('#wsNameInput');
  input.focus();

  const close = function() { backdrop.remove(); };
  backdrop.querySelector('#modalCancelBtn').addEventListener('click', close);
  backdrop.querySelector('#modalSaveBtn').addEventListener('click', async function() {
    const name = input.value.trim();
    if (!name) { input.focus(); return; }
    close();
    const res = await fetch('/api/workspaces/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name }),
    });
    if (res.ok) {
      toast('Workspace "' + name + '" saved!', 'success');
      loadWorkspaceList();
    } else {
      const err = await res.json();
      toast(err.detail || 'Save failed', 'error');
    }
  });
  input.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') backdrop.querySelector('#modalSaveBtn').click();
  });
});

/* == URL INPUTS ============================================================= */
function addUrlRow(value) {
  value = value || '';
  const row = el('div', 'url-item');
  row.innerHTML =
    '<input type="text" class="url-input" placeholder="https://github.com/user/repo" value="' + esc(value) + '" />' +
    '<button class="btn-remove" title="Remove">&times;</button>';
  row.querySelector('.btn-remove').addEventListener('click', function() {
    row.remove();
    if ($('urlList').children.length === 0) addUrlRow();
  });
  $('urlList').appendChild(row);
  row.querySelector('input').focus();
}

$('addUrlBtn').addEventListener('click', function() { addUrlRow(); });
addUrlRow();

/* == TABS =================================================================== */
document.addEventListener('click', function(e) {
  if (!e.target.matches('.tab')) return;
  switchTab(e.target.dataset.tab);
});

function switchTab(tab) {
  document.querySelectorAll('.tab').forEach(function(t) {
    t.classList.toggle('active', t.dataset.tab === tab);
  });
  document.querySelectorAll('.tab-pane').forEach(function(p) {
    p.classList.add('hidden');
  });
  $('tab-' + tab).classList.remove('hidden');
  if (tab === 'explorer') loadFileTree();
}

/* == TOPBAR ================================================================= */
function updateTopbar(repos) {
  const total = repos.reduce(function(s, r) { return s + (r.file_count || 0); }, 0);
  $('topbarInfo').innerHTML =
    '<span class="topbar-pill">' + repos.length + ' repo' + (repos.length !== 1 ? 's' : '') + '</span>' +
    '<span class="topbar-pill">' + total + ' files</span>';
}

/* == ANALYSE (INGEST) ======================================================= */
$('analyzeBtn').addEventListener('click', async function() {
  const urls = [...document.querySelectorAll('.url-input')]
    .map(function(i) { return i.value.trim(); })
    .filter(Boolean);
  if (!urls.length) { toast('Add at least one repository URL', 'error'); return; }

  const branch = $('branchInput').value.trim() || 'main';

  setActive('loadingState');
  $('loadingTitle').textContent    = 'Indexing repositories...';
  $('progressLog').innerHTML       = '';
  $('analyzeBtn').disabled         = true;
  $('analyzeBtnText').textContent  = 'Indexing...';

  const logLine = function(text, cls) {
    cls = cls || '';
    const line = el('div', 'progress-line ' + cls, esc(text));
    $('progressLog').appendChild(line);
    $('progressLog').scrollTop = $('progressLog').scrollHeight;
  };

  try {
    const res     = await fetch('/api/ingest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ urls: urls, branch: branch }),
    });
    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    let   buffer  = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split('\n\n');
      buffer = lines.pop();

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line.startsWith('data:')) continue;
        const evt = JSON.parse(line.slice(5).trim());

        if (evt.type === 'progress') {
          const ok = evt.message.includes('Loaded') || evt.message.includes('Created') ||
                     evt.message.includes('ready') || evt.message.includes('Vector') ||
                     evt.message.charAt(0) === '\u2714';
          logLine(evt.message, ok ? 'ok' : '');

        } else if (evt.type === 'done') {
          renderIndexedSidebar(evt.repos);
          renderOverviewCards(evt.repos);
          updateTopbar(evt.repos);
          $('messages').innerHTML = '';
          loadFileTree();
          setActive('contentArea');
          toast('Indexing complete! Ready to chat.', 'success');

        } else if (evt.type === 'error') {
          logLine('Error: ' + evt.message, 'err');
          $('loadingTitle').textContent = 'Indexing failed';
          toast(evt.message, 'error');
        }
      }
    }
  } catch (err) {
    logLine('Network error: ' + err.message, 'err');
    toast('Network error', 'error');
  } finally {
    $('analyzeBtn').disabled        = false;
    $('analyzeBtnText').textContent = 'Analyze Repos';
  }
});

/* == SIDEBAR INDEXED LIST =================================================== */
function renderIndexedSidebar(repos) {
  $('indexedList').innerHTML = '';
  repos.forEach(function(r) {
    const topLangs = Object.keys(r.languages || {}).slice(0, 3).join(', ') || 'none';
    const item = el('div', 'indexed-item');
    item.innerHTML =
      '<div class="repo-name">' + esc(r.name) + '</div>' +
      '<div class="repo-meta">' + r.file_count + ' files &middot; ' + esc(topLangs) + '</div>';
    $('indexedList').appendChild(item);
  });
  show('indexedSection');
}

/* == OVERVIEW CARDS ========================================================= */
function renderOverviewCards(repos) {
  $('repoCards').innerHTML = '';
  repos.forEach(function(r) {
    const s = r.summary || {};

    const mkBullets = function(arr) {
      return (arr || []).map(function(x) {
        return '<div class="feature-item"><span class="fi-icon">-</span>' + esc(x) + '</div>';
      }).join('');
    };

    const mkTags = function(arr, cls) {
      return (arr || []).map(function(x) {
        return '<span class="' + cls + '">' + esc(x) + '</span>';
      }).join('');
    };

    const langTags = Object.entries(r.languages || {}).map(function(entry) {
      return '<span class="lang-tag">' + esc(entry[0]) +
             ' <span class="lang-count">' + entry[1] + '</span></span>';
    }).join('');

    const card = el('div', 'repo-card');
    let html =
      '<div class="card-header">' +
        '<div class="card-title">' + esc(r.name) + '</div>' +
        '<a class="card-link" href="' + esc(r.url) + '" target="_blank">View on GitHub &rarr;</a>' +
      '</div>';

    if (s.overview)
      html += '<div class="card-overview">' + esc(s.overview) + '</div>';
    if (s.purpose)
      html += '<div class="card-purpose">Goal: ' + esc(s.purpose) + '</div>';
    if (s.key_features && s.key_features.length)
      html += '<div><div class="card-section-title">Key Features</div>'  +
              '<div class="features-list">' + mkBullets(s.key_features) + '</div></div>';
    if (s.use_cases && s.use_cases.length)
      html += '<div><div class="card-section-title">Use Cases</div>' +
              '<div class="features-list">' + mkBullets(s.use_cases) + '</div></div>';
    if (s.tech_stack && s.tech_stack.length)
      html += '<div><div class="card-section-title">Tech Stack</div>' +
              '<div class="tech-tags">' + mkTags(s.tech_stack, 'tech-tag') + '</div></div>';
    if (s.external_dependencies && s.external_dependencies.length)
      html += '<div><div class="card-section-title">Dependencies</div>' +
              '<div class="tech-tags">' + mkTags(s.external_dependencies, 'dep-tag') + '</div></div>';
    if (langTags)
      html += '<div><div class="card-section-title">Languages</div>' +
              '<div class="lang-tags">' + langTags + '</div></div>';
    if (s.architecture)
      html += '<div><div class="card-section-title">Architecture</div>' +
              '<div class="card-arch">' + esc(s.architecture) + '</div></div>';
    if (s.entry_points && s.entry_points.length)
      html += '<div><div class="card-section-title">Entry Points</div>' +
              '<div class="features-list">' + mkBullets(s.entry_points) + '</div></div>';
    if (s.getting_started)
      html += '<div><div class="card-section-title">Getting Started</div>' +
              '<div class="card-getting-started">' + esc(s.getting_started) + '</div></div>';
    if (s.limitations && s.limitations.length)
      html += '<div><div class="card-section-title">Limitations</div>' +
              '<div class="features-list limitations">' + mkBullets(s.limitations) + '</div></div>';

    html += '<div class="card-stats"><span><span class="stat-val">' +
            r.file_count + '</span> files indexed</span></div>';

    card.innerHTML = html;
    $('repoCards').appendChild(card);
  });
}

/* == FILE EXPLORER ========================================================== */
let _treeData = [];

async function loadFileTree() {
  try {
    const res  = await fetch('/api/files');
    const data = await res.json();
    _treeData  = data.trees || [];
    renderFileTree(_treeData);
  } catch (e) { /* explorer unavailable */ }
}

const FILE_EXT_LABEL = {
  '.py':'PY','.js':'JS','.ts':'TS','.jsx':'JSX','.tsx':'TSX',
  '.java':'JAVA','.go':'GO','.rs':'RS','.cpp':'CPP','.c':'C',
  '.h':'H','.html':'HTML','.css':'CSS','.json':'JSON',
  '.yaml':'YML','.yml':'YML','.md':'MD','.sh':'SH',
  '.sql':'SQL','.toml':'TOML','.rb':'RB','.php':'PHP',
};

function renderFileTree(trees) {
  const container = $('fileTree');
  container.innerHTML = '';
  if (!trees.length) {
    container.innerHTML = '<div style="padding:10px;color:var(--muted);font-size:12px">No files indexed</div>';
    return;
  }
  trees.forEach(function(tree) { container.appendChild(buildTreeNode(tree)); });
}

function buildTreeNode(node) {
  const wrapper = el('div', 'tree-node');
  const row     = el('div', 'tree-node-row');

  if (node.type === 'dir') {
    const icon = el('span', 'tree-icon', '[+]');
    const name = el('span', 'tree-name', esc(node.name));
    row.appendChild(icon);
    row.appendChild(name);
    row.addEventListener('click', function(e) {
      e.stopPropagation();
      wrapper.classList.toggle('collapsed');
      icon.textContent = wrapper.classList.contains('collapsed') ? '[+]' : '[-]';
    });
    wrapper.appendChild(row);
    if (node.children && node.children.length) {
      const kids = el('div', 'tree-children');
      node.children.forEach(function(child) { kids.appendChild(buildTreeNode(child)); });
      wrapper.appendChild(kids);
    }
  } else {
    const extLabel = FILE_EXT_LABEL[node.ext] || 'FILE';
    const icon = el('span', 'tree-icon tree-ext', extLabel);
    const name = el('span', 'tree-name', esc(node.name));
    row.appendChild(icon);
    row.appendChild(name);
    row.addEventListener('click', function(e) {
      e.stopPropagation();
      document.querySelectorAll('.tree-node-row.selected').forEach(function(r) {
        r.classList.remove('selected');
      });
      row.classList.add('selected');
      previewFile(node.path);
    });
    wrapper.appendChild(row);
  }
  return wrapper;
}

async function previewFile(path) {
  const panel = $('filePreviewPanel');
  try {
    const res  = await fetch('/api/file?path=' + encodeURIComponent(path));
    if (!res.ok) return;
    const data = await res.json();
    panel.innerHTML =
      '<div class="preview-header">' +
        '<div class="preview-path">' + esc(data.path) + '</div>' +
        '<button class="preview-copy" id="pcopyBtn">Copy</button>' +
      '</div>' +
      '<div class="preview-code-wrap">' +
        '<pre><code class="language-' + esc(data.language) + '" id="previewCode">' +
        esc(data.content) + '</code></pre>' +
      '</div>';
    hljs.highlightElement(panel.querySelector('#previewCode'));
    panel.querySelector('#pcopyBtn').addEventListener('click', function() {
      navigator.clipboard.writeText(data.content).then(function() { toast('Copied!', 'success'); });
    });
  } catch (e) { /* silent */ }
}

$('treeSearch').addEventListener('input', function(e) {
  const q = e.target.value.trim().toLowerCase();
  if (!q) { renderFileTree(_treeData); return; }
  function filterTree(node) {
    if (node.type === 'file') return node.name.toLowerCase().includes(q) ? node : null;
    const kids = (node.children || []).map(filterTree).filter(Boolean);
    return kids.length ? Object.assign({}, node, { children: kids }) : null;
  }
  renderFileTree(_treeData.map(filterTree).filter(Boolean));
});

/* == CHAT =================================================================== */
$('sendBtn').addEventListener('click', sendMessage);
$('chatInput').addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});

$('chatInput').addEventListener('input', function() {
  const t = $('chatInput');
  t.style.height = 'auto';
  t.style.height = Math.min(t.scrollHeight, 120) + 'px';
});

$('newChatBtn').addEventListener('click', async function() {
  await fetch('/api/chat/clear', { method: 'POST' });
  $('messages').innerHTML = '';
  toast('Chat history cleared', 'info');
});

async function sendMessage() {
  if (state.streaming) return;
  const question = $('chatInput').value.trim();
  if (!question) return;

  $('chatInput').value        = '';
  $('chatInput').style.height = 'auto';

  switchTab('chat');

  appendMessage('user', question);
  const botWrap = appendMessage('bot', '');
  const bubble  = botWrap.querySelector('.msg-bubble');
  const cursor  = el('span', 'cursor');
  bubble.appendChild(cursor);

  $('sendBtn').disabled = true;
  state.streaming = true;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: question }),
    });
    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    let   buffer  = '';
    let   rawText = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop();

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line.startsWith('data:')) continue;
        const evt = JSON.parse(line.slice(5).trim());

        if (evt.type === 'token') {
          rawText += evt.content;
          cursor.remove();
          renderMarkdownBubble(bubble, rawText);
          bubble.appendChild(cursor);
          $('messages').scrollTop = $('messages').scrollHeight;
        } else if (evt.type === 'done') {
          cursor.remove();
          renderMarkdownBubble(bubble, rawText);
          if (evt.sources && evt.sources.length) renderSources(botWrap, evt.sources);
        } else if (evt.type === 'error') {
          cursor.remove();
          bubble.textContent = 'Error: ' + evt.message;
        }
      }
    }
  } catch (err) {
    if (cursor.parentNode) cursor.remove();
    bubble.textContent = 'Network error: ' + err.message;
  } finally {
    $('sendBtn').disabled = false;
    state.streaming = false;
    $('messages').scrollTop = $('messages').scrollHeight;
  }
}

function renderMarkdownBubble(bubble, text) {
  bubble.innerHTML = marked.parse(text);
  bubble.querySelectorAll('pre code').forEach(function(block) {
    hljs.highlightElement(block);
    const pre = block.parentElement;
    if (!pre.querySelector('.code-copy-btn')) {
      const cpBtn = el('button', 'code-copy-btn', 'Copy');
      cpBtn.addEventListener('click', function() {
        navigator.clipboard.writeText(block.textContent).then(function() {
          cpBtn.textContent = 'Copied!';
          setTimeout(function() { cpBtn.textContent = 'Copy'; }, 1500);
        });
      });
      pre.style.position = 'relative';
      pre.appendChild(cpBtn);
    }
  });
}

function renderSources(wrap, sources) {
  const row = el('div', 'msg-sources');
  sources.slice(0, 6).forEach(function(src) {
    const chip = el('span', 'source-chip', esc(src.split('/').slice(-2).join('/')));
    chip.title = src;
    chip.addEventListener('click', function() { openFilePath(src); });
    row.appendChild(chip);
  });
  wrap.appendChild(row);
}

function appendMessage(role, text) {
  const labelText = role === 'user' ? 'You' : 'Assistant';
  const avatar    = role === 'user' ? 'U'   : 'AI';
  const wrap = el('div', 'msg ' + role);
  wrap.innerHTML =
    '<div class="msg-meta">' +
      '<div class="msg-avatar">' + avatar + '</div>' +
      '<div class="msg-label">' + labelText + '</div>' +
    '</div>' +
    '<div class="msg-bubble">' + (role === 'user' ? esc(text) : '') + '</div>';
  $('messages').appendChild(wrap);
  $('messages').scrollTop = $('messages').scrollHeight;
  return wrap;
}

/* == CLEAR SESSION ========================================================== */
$('clearBtn').addEventListener('click', async function() {
  if (!confirm('Clear the session? This deletes the vector database and cloned repos.')) return;
  await fetch('/api/clear', { method: 'POST' });
  hide('indexedSection');
  $('repoCards').innerHTML  = '';
  $('messages').innerHTML   = '';
  $('fileTree').innerHTML   = '';
  $('filePreviewPanel').innerHTML =
    '<div class="preview-empty"><span>FILE</span>' +
    '<p>Click a file in the tree to preview it</p></div>';
  $('urlList').innerHTML    = '';
  $('topbarInfo').innerHTML = '';
  $('saveWorkspaceBtn').disabled = true;
  $('newChatBtn').style.display  = 'none';
  addUrlRow();
  setActive('emptyState');
  toast('Session cleared', 'info');
});

/* == BOOT =================================================================== */
marked.setOptions({ breaks: true, gfm: true, highlight: null });
loadWorkspaceList();