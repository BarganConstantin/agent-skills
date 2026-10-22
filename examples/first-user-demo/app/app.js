// Intentional baseline defects are confined to four switches in this local fixture.
const baseline = window.DEMO_VARIANT === 'baseline';
document.body.classList.add(baseline ? 'baseline' : 'fixed');
const app = document.querySelector('#app');
const key = 'task-cabin-demo-v1';
const stored = () => JSON.parse(localStorage.getItem(key) || '[]');
const escape = value => value.replace(/[&<>"']/g, char => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[char]));
document.querySelector('#privacy-link').href = baseline ? '/privacy-policy' : '/privacy';
document.querySelector('#reset').addEventListener('click', () => {localStorage.clear(); sessionStorage.clear(); location.href = '/';});
const pages = {
  '/pricing': '<h1>Pricing</h1><p>This synthetic local demo is free. No payment, trial, subscription, or external service is connected.</p>',
  '/terms': '<h1>Demo terms</h1><p>Use synthetic workspace names only. This fixture is for local testing and provides no hosted service.</p>',
  '/privacy': '<h1>Demo privacy</h1><p>Workspace data stays in this browser\'s localStorage. Nothing is sent to an external service. Reset demo data removes it.</p>'
};
if (pages[location.pathname]) {
  app.innerHTML = pages[location.pathname] + '<p><a href="/">Back to start</a></p>';
} else if (location.pathname === '/create') {
  app.innerHTML = '<p class="eyebrow">Your first workspace</p><h1>Make room for your next project</h1><p>Create a workspace and get a starter task. No account needed.</p><form novalidate><label for="name">Workspace name</label><input id="name" name="name" autocomplete="off" placeholder="My test project" aria-describedby="error"><p id="error" role="alert"></p><button type="submit">Create workspace</button></form>';
  let pending = false;
  document.querySelector('form').addEventListener('submit', event => {
    event.preventDefault();
    const name = document.querySelector('#name').value.trim();
    if (!baseline && name.length < 3) {document.querySelector('#error').textContent = 'Enter a workspace name with at least 3 characters.'; document.querySelector('#name').setAttribute('aria-invalid', 'true'); return;}
    if (!baseline && pending) return;
    pending = true;
    if (!baseline) document.querySelector('button[type="submit"]').disabled = true;
    const workspaces = stored();
    workspaces.push({id: workspaces.length + 1, name, tasks: ['Plan first release']});
    localStorage.setItem(key, JSON.stringify(workspaces));
    location.href = '/workspace';
  });
} else if (location.pathname === '/workspace') {
  const workspaces = stored();
  const workspace = workspaces.at(-1);
  if (!workspace) {location.replace('/create');}
  else {app.innerHTML = '<p class="eyebrow">Workspace ready</p><h1>' + escape(workspace.name) + '</h1><h2>Your first task</h2><ul><li>Plan first release</li></ul><p data-testid="workspace-count">' + workspaces.length + ' workspace(s) in this browser</p>';}
} else {
  app.innerHTML = '<p class="eyebrow">A simple place to begin</p><h1>Turn your next idea into a small plan</h1><p>Create a workspace, start with one useful task, and keep the next step visible.</p><p>No signup. No payment. Your data stays in this browser.</p><div class="hero-action"><a class="button" href="' + (baseline ? '#start' : '/create') + '">Start a workspace</a></div>';
}
