"""Dependency-free browser UI served by the FastAPI application."""

DASHBOARD_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#0a111b">
  <title>Scout — Competitor Intelligence</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #09111b; --surface: #101b27; --surface-2: #152331; --line: #243545;
      --text: #f3f7fa; --muted: #8fa4b7; --green: #7cdbb5; --orange: #f5ad72;
      --purple: #a8a5ff; --red: #ff8f9e; --blue: #68b8ff;
      --shadow: 0 24px 70px rgba(0,0,0,.28);
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body { margin: 0; min-height: 100vh; background: var(--bg); color: var(--text);
      font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    button, input, select { font: inherit; }
    button, select { color: inherit; }
    button { cursor: pointer; }
    .app-shell { min-height: 100vh; display: grid; grid-template-columns: 238px minmax(0,1fr); }
    .sidebar { position: sticky; top: 0; height: 100vh; padding: 24px 16px; border-right: 1px solid var(--line);
      background: rgba(10,18,28,.94); display: flex; flex-direction: column; z-index: 20; }
    .brand { display: flex; align-items: center; gap: 12px; padding: 2px 10px 26px; }
    .brand-mark { width: 36px; height: 36px; border-radius: 11px; background: var(--green); position: relative;
      box-shadow: 0 0 0 6px rgba(124,219,181,.08); transform: rotate(8deg); }
    .brand-mark::after { content: ""; position: absolute; width: 12px; height: 12px; border: 3px solid #0b1a1a;
      border-radius: 50%; left: 9px; top: 7px; }
    .brand-name { font-size: 19px; font-weight: 800; letter-spacing: -.04em; }
    .brand-copy { color: var(--muted); font-size: 10px; letter-spacing: .12em; text-transform: uppercase; margin-top: 2px; }
    .nav-label { padding: 0 12px 8px; color: #60778a; font-size: 10px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
    .nav { display: grid; gap: 5px; }
    .nav-button { width: 100%; border: 0; background: transparent; color: var(--muted); padding: 11px 12px;
      border-radius: 11px; display: flex; align-items: center; gap: 11px; font-weight: 650; text-align: left; transition: .18s ease; }
    .nav-button:hover { color: var(--text); background: #142231; }
    .nav-button.active { color: #0a1715; background: var(--green); }
    .nav-icon { width: 21px; text-align: center; font-size: 15px; }
    .sidebar-foot { margin-top: auto; padding: 14px; border: 1px solid var(--line); border-radius: 15px; background: #0d1823; }
    .sidebar-foot strong { display: block; font-size: 12px; margin-bottom: 5px; }
    .sidebar-foot p { margin: 0; color: var(--muted); font-size: 11px; line-height: 1.45; }
    .demo-dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: var(--green); margin-right: 6px;
      box-shadow: 0 0 0 5px rgba(124,219,181,.1); }
    main { min-width: 0; }
    .topbar { min-height: 78px; padding: 17px clamp(20px,4vw,48px); border-bottom: 1px solid var(--line);
      display: flex; align-items: center; justify-content: space-between; gap: 20px; position: sticky; top: 0;
      background: rgba(9,17,27,.88); backdrop-filter: blur(18px); z-index: 15; }
    .search { flex: 1; max-width: 540px; position: relative; }
    .search::before { content: "⌕"; position: absolute; left: 14px; top: 8px; color: #6f879b; font-size: 20px; }
    .search input { width: 100%; border: 1px solid transparent; border-radius: 12px; background: #101d29; color: var(--text);
      padding: 11px 14px 11px 42px; outline: none; transition: .2s; }
    .search input:focus { border-color: rgba(124,219,181,.55); box-shadow: 0 0 0 4px rgba(124,219,181,.08); }
    .search input::placeholder { color: #637b8e; }
    .top-actions { display: flex; align-items: center; gap: 10px; }
    .control, .ghost-button, .primary-button { min-height: 40px; border-radius: 11px; border: 1px solid var(--line); padding: 0 13px; background: #101d29; }
    .control { outline: none; }
    .ghost-button:hover { background: #182735; }
    .primary-button { border: 0; background: var(--green); color: #071713; font-weight: 800; padding-inline: 16px; }
    .primary-button:hover { filter: brightness(1.06); transform: translateY(-1px); }
    .content { width: min(1500px, 100%); margin: 0 auto; padding: 38px clamp(20px,4vw,48px) 64px; }
    .view { display: none; animation: fade-in .28s ease both; }
    .view.active { display: block; }
    @keyframes fade-in { from { opacity: 0; transform: translateY(5px); } }
    .page-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; margin-bottom: 26px; }
    .eyebrow { color: var(--green); font-size: 11px; font-weight: 850; letter-spacing: .13em; text-transform: uppercase; }
    h1 { margin: 6px 0 7px; font-size: clamp(30px,4vw,48px); line-height: 1; letter-spacing: -.055em; }
    .lede { margin: 0; color: var(--muted); font-size: 14px; }
    .live-chip { border: 1px solid rgba(124,219,181,.25); border-radius: 999px; background: rgba(124,219,181,.07);
      color: #a7eccf; padding: 8px 12px; font-size: 11px; font-weight: 750; white-space: nowrap; }
    .kpi-grid { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 14px; margin-bottom: 16px; }
    .card { border: 1px solid var(--line); border-radius: 18px; background: linear-gradient(150deg, rgba(21,35,49,.86), rgba(14,25,36,.92));
      box-shadow: var(--shadow); }
    .kpi { padding: 19px; position: relative; overflow: hidden; }
    .kpi::after { content: ""; position: absolute; width: 70px; height: 70px; border-radius: 50%; right: -25px; top: -25px;
      background: var(--kpi-color,var(--green)); opacity: .08; }
    .kpi-label { color: var(--muted); font-size: 11px; font-weight: 750; text-transform: uppercase; letter-spacing: .08em; }
    .kpi-value { font-size: 29px; letter-spacing: -.04em; font-weight: 850; margin-top: 11px; }
    .delta { margin-top: 8px; color: #9ab0c1; font-size: 11px; }
    .delta.up { color: var(--green); } .delta.down { color: var(--red); }
    .grid-2 { display: grid; grid-template-columns: minmax(0,1.65fr) minmax(300px,.8fr); gap: 16px; margin-bottom: 16px; }
    .panel { padding: 22px; min-width: 0; }
    .panel-head { display: flex; align-items: center; justify-content: space-between; gap: 15px; margin-bottom: 20px; }
    .panel-title { font-size: 15px; font-weight: 800; letter-spacing: -.02em; }
    .panel-subtitle { color: var(--muted); font-size: 11px; margin-top: 4px; }
    .legend { display: flex; gap: 12px; color: var(--muted); font-size: 10px; }
    .legend span::before { content: ""; display: inline-block; width: 7px; height: 7px; background: var(--dot); border-radius: 50%; margin-right: 5px; }
    .bar-chart { height: 230px; display: flex; align-items: end; gap: clamp(3px,.7vw,8px); border-bottom: 1px solid var(--line);
      padding: 18px 2px 0; position: relative; }
    .chart-bar { flex: 1; min-width: 3px; max-width: 18px; height: var(--height); border-radius: 4px 4px 1px 1px;
      background: linear-gradient(to top, rgba(124,219,181,.38), var(--green)); position: relative; transition: .25s; }
    .chart-bar:hover { filter: brightness(1.25); transform: scaleY(1.02); transform-origin: bottom; }
    .chart-bar[data-label]::after { content: attr(data-label); position: absolute; left: 50%; bottom: calc(100% + 7px); transform: translateX(-50%);
      background: #071018; color: #dce8f0; padding: 5px 7px; border-radius: 6px; font-size: 9px; white-space: nowrap; opacity: 0; pointer-events: none; }
    .chart-bar:hover::after { opacity: 1; }
    .mix-wrap { display: grid; place-items: center; min-height: 220px; }
    .donut { width: 154px; height: 154px; border-radius: 50%; background: var(--segments); position: relative; display: grid; place-items: center; }
    .donut::after { content: ""; width: 91px; height: 91px; background: #111f2c; border-radius: 50%; }
    .donut-copy { position: absolute; text-align: center; z-index: 1; }
    .donut-copy strong { display: block; font-size: 25px; }.donut-copy span { color: var(--muted); font-size: 10px; }
    .mix-legend { width: 100%; display: grid; gap: 8px; margin-top: 18px; }
    .mix-row { display: flex; justify-content: space-between; color: var(--muted); font-size: 11px; }
    .mix-row b { color: var(--text); }.mix-key { display: inline-flex; align-items: center; gap: 7px; text-transform: capitalize; }
    .mix-key i { width: 8px; height: 8px; border-radius: 3px; background: var(--color); }
    .competitor-list { display: grid; gap: 8px; }
    .competitor-row { display: grid; grid-template-columns: minmax(180px,1.4fr) repeat(5,minmax(70px,.65fr)); align-items: center;
      gap: 14px; border-top: 1px solid var(--line); padding: 14px 2px; font-size: 12px; }
    .competitor-row.header { border: 0; padding-top: 0; color: #6f879a; font-size: 9px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
    .competitor-name { display: flex; align-items: center; gap: 10px; min-width: 0; }
    .avatar { width: 31px; height: 31px; flex: 0 0 31px; display: grid; place-items: center; border-radius: 9px; background: color-mix(in srgb,var(--avatar) 20%,#142331);
      color: var(--avatar); font-size: 12px; font-weight: 850; }
    .competitor-name strong { display:block; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .competitor-name small { color: var(--muted); }
    .positive { color: var(--green); }.negative { color: var(--red); }
    .slots { display: flex; flex-wrap: wrap; gap: 8px; }
    .slot { border: 1px solid var(--line); border-radius: 12px; padding: 9px 11px; background: #0d1924; }
    .slot strong { display: block; font-size: 11px; }.slot span { color: var(--muted); font-size: 9px; }
    .section-grid { display: grid; gap: 12px; }
    .post-card, .mention-card, .ad-card { padding: 17px; display: grid; gap: 12px; }
    .post-card { grid-template-columns: 44px minmax(0,1fr) auto; align-items: start; }
    .format-icon { width: 44px; height: 44px; border-radius: 13px; background: #1b2b39; display: grid; place-items: center;
      color: var(--icon-color,var(--green)); font-weight: 900; text-transform: uppercase; font-size: 10px; }
    .post-meta, .mention-meta { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; color: var(--muted); font-size: 10px; }
    .post-copy, .mention-copy, .ad-copy { margin: 7px 0 0; color: #dbe6ee; line-height: 1.5; font-size: 13px; }
    .post-stats { text-align: right; min-width: 92px; }.post-stats strong { display: block; font-size: 15px; }.post-stats span { color: var(--muted); font-size: 9px; }
    .badge { border-radius: 999px; padding: 4px 7px; background: #1d2c39; color: #a9bdcc; font-size: 9px; font-weight: 750; text-transform: capitalize; }
    .badge.boosted { color: #ffc18b; background: rgba(245,173,114,.12); }
    .sentiment { display: grid; grid-template-columns: repeat(3,1fr); gap: 12px; margin-bottom: 16px; }
    .sentiment-card { padding: 18px; }.sentiment-card strong { display:block; font-size:26px; margin-top:8px; }.sentiment-card span { color:var(--muted); font-size:11px; }
    .sentiment-bar { height: 10px; border-radius: 999px; overflow: hidden; display: flex; background: #1d2b38; margin: 18px 0 6px; }
    .sentiment-bar i { height: 100%; }
    .mention-card { grid-template-columns: minmax(0,1fr) auto; }
    .sentiment-pill { align-self:start; border-radius:999px; padding:6px 9px; font-size:9px; font-weight:800; text-transform:uppercase; }
    .sentiment-pill.positive { background:rgba(124,219,181,.1); }.sentiment-pill.neutral { background:#21303d;color:#a8bac8; }.sentiment-pill.negative { background:rgba(255,143,158,.1); }
    .ads-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }
    .ad-card { min-height:180px; align-content:space-between; }.ad-top { display:flex; justify-content:space-between; gap:10px; }.ad-status { color:var(--green); font-size:10px; font-weight:800; }
    .ad-status.paused { color:var(--muted); }.ad-footer { display:flex; align-items:center; justify-content:space-between; color:var(--muted); font-size:10px; }
    .empty { padding: 40px; text-align:center; color:var(--muted); }.empty strong { display:block;color:var(--text);margin-bottom:6px; }
    .skeleton { height: 90px; border-radius: 16px; background: linear-gradient(90deg,#101c28,#172635,#101c28); background-size: 220% 100%; animation: shimmer 1.4s infinite; }
    @keyframes shimmer { to { background-position: -220% 0; } }
    dialog { width:min(520px,calc(100% - 32px)); border:1px solid var(--line); border-radius:20px; background:#101c28; color:var(--text); padding:0; box-shadow:0 40px 100px #0009; }
    dialog::backdrop { background:rgba(3,8,13,.72); backdrop-filter:blur(5px); }
    .modal-head { padding:22px 24px; display:flex; justify-content:space-between; border-bottom:1px solid var(--line); }.modal-head h2 { margin:0;font-size:20px; }
    .close-button { border:0;background:transparent;color:var(--muted);font-size:22px; }.modal-body { padding:22px 24px;display:grid;gap:14px; }
    .field { display:grid;gap:6px; }.field label { color:#a9bdcb;font-size:11px;font-weight:700; }.field input { border:1px solid var(--line);background:#0c1721;color:var(--text);border-radius:11px;padding:11px;outline:none; }
    .field input:focus { border-color:var(--green); }.modal-actions { display:flex;justify-content:flex-end;gap:9px;margin-top:4px; }
    .field-help,.auth-note { color:var(--muted);font-size:11px;line-height:1.5;margin:0; }.auth-switch { background:transparent;border:0;color:var(--green);padding:0;font-weight:700;cursor:pointer; }
    .toast { position:fixed; right:24px; bottom:24px; z-index:50; background:#152533;border:1px solid var(--line);padding:13px 16px;border-radius:12px;box-shadow:var(--shadow);font-size:12px;transform:translateY(25px);opacity:0;pointer-events:none;transition:.25s; }
    .toast.show { transform:none;opacity:1; }
    @media(max-width:1050px){ .kpi-grid{grid-template-columns:repeat(2,1fr)} .grid-2{grid-template-columns:1fr} .competitor-row{grid-template-columns:minmax(180px,1.4fr) repeat(3,1fr)} .competitor-row > :nth-child(5),.competitor-row > :nth-child(6){display:none} }
    @media(max-width:760px){ .app-shell{display:block}.sidebar{position:fixed;top:auto;bottom:0;width:100%;height:66px;padding:7px 10px;border-right:0;border-top:1px solid var(--line);display:block}.brand,.nav-label,.sidebar-foot{display:none}.nav{grid-template-columns:repeat(4,1fr)}.nav-button{display:grid;place-items:center;gap:1px;padding:5px 2px;font-size:9px}.nav-icon{font-size:14px}.topbar{top:0;padding:12px 16px}.search{display:none}.top-actions{width:100%}.control{min-width:0;flex:1}.ghost-button{display:none}.primary-button{white-space:nowrap}.content{padding:26px 16px 92px}.page-heading{align-items:flex-start}.live-chip{display:none}.kpi-grid{grid-template-columns:repeat(2,1fr);gap:9px}.kpi{padding:15px}.kpi-value{font-size:24px}.panel{padding:17px}.bar-chart{height:180px}.competitor-row{grid-template-columns:1fr auto}.competitor-row.header{display:none}.competitor-row > :nth-child(n+3){display:none}.post-card{grid-template-columns:38px 1fr}.format-icon{width:38px;height:38px}.post-stats{display:none}.sentiment{grid-template-columns:1fr}.ads-grid{grid-template-columns:1fr}.mention-card{grid-template-columns:1fr}.sentiment-pill{justify-self:start} }
  </style>
</head>
<body>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand"><div class="brand-mark"></div><div><div class="brand-name">Scout</div><div class="brand-copy">Market intelligence</div></div></div>
      <div class="nav-label">Workspace</div>
      <nav class="nav" aria-label="Dashboard sections">
        <button class="nav-button active" data-view="overview"><span class="nav-icon">◫</span>Overview</button>
        <button class="nav-button" data-view="content-view"><span class="nav-icon">◩</span>Content</button>
        <button class="nav-button" data-view="mentions-view"><span class="nav-icon">◎</span>Mentions</button>
        <button class="nav-button" data-view="ads-view"><span class="nav-icon">◈</span>Ads</button>
      </nav>
      <div class="sidebar-foot"><strong><span class="demo-dot"></span><span id="workspace-name">Public preview</span></strong><p id="workspace-copy">Sign in to create a private workspace backed by Supabase.</p></div>
    </aside>
    <main>
      <header class="topbar">
        <div class="search"><input id="global-search" type="search" placeholder="Search posts, mentions, or brands…" aria-label="Search dashboard"></div>
        <div class="top-actions">
          <select id="competitor-filter" class="control" aria-label="Filter competitor"><option value="">All competitors</option></select>
          <select id="date-filter" class="control" aria-label="Date range"><option value="7">7 days</option><option value="30" selected>30 days</option><option value="90">90 days</option></select>
          <button id="refresh" class="ghost-button" aria-label="Refresh data">↻</button>
          <button id="auth-button" class="ghost-button">Sign in</button>
          <button id="add-competitor" class="primary-button">+ Add brand</button>
        </div>
      </header>
      <div class="content">
        <section id="overview" class="view active">
          <div class="page-heading"><div><div class="eyebrow">Competitive pulse</div><h1>See what is moving.</h1><p class="lede">Content, conversation, and paid momentum across your market.</p></div><div class="live-chip"><span class="demo-dot"></span>Real records only</div></div>
          <div id="kpis" class="kpi-grid"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div>
          <div class="grid-2">
            <article class="card panel"><div class="panel-head"><div><div class="panel-title">Engagement velocity</div><div class="panel-subtitle">Daily audience actions across tracked content</div></div><div class="legend"><span style="--dot:var(--green)">Engagement</span></div></div><div id="engagement-chart" class="bar-chart"></div></article>
            <article class="card panel"><div class="panel-head"><div><div class="panel-title">Content mix</div><div class="panel-subtitle">Formats published in this period</div></div></div><div id="content-mix" class="mix-wrap"></div></article>
          </div>
          <div class="grid-2">
            <article class="card panel"><div class="panel-head"><div><div class="panel-title">Competitor scorecard</div><div class="panel-subtitle">Side-by-side market activity</div></div></div><div id="competitor-table" class="competitor-list"></div></article>
            <article class="card panel"><div class="panel-head"><div><div class="panel-title">High-response windows</div><div class="panel-subtitle">Best average engagement by posting time</div></div></div><div id="best-times" class="slots"></div></article>
          </div>
        </section>
        <section id="content-view" class="view"><div class="page-heading"><div><div class="eyebrow">Creative intelligence</div><h1>Content that lands.</h1><p class="lede">Compare formats, hooks, organic wins, and paid amplification.</p></div></div><div id="posts-list" class="section-grid"></div></section>
        <section id="mentions-view" class="view"><div class="page-heading"><div><div class="eyebrow">Conversation intelligence</div><h1>What the market says.</h1><p class="lede">Track sentiment shifts and the voices shaping brand perception.</p></div></div><div id="sentiment-summary"></div><div id="mentions-list" class="section-grid"></div></section>
        <section id="ads-view" class="view"><div class="page-heading"><div><div class="eyebrow">Paid intelligence</div><h1>Where brands place bets.</h1><p class="lede">Monitor active creative and spot the organic posts receiving budget.</p></div></div><div id="ads-list" class="ads-grid"></div></section>
      </div>
    </main>
  </div>
  <dialog id="brand-dialog">
    <form id="brand-form" method="dialog">
      <div class="modal-head"><div><div class="eyebrow">Start tracking</div><h2>Add a competitor</h2></div><button class="close-button" type="button" aria-label="Close">×</button></div>
      <div class="modal-body"><div class="field"><label for="brand-name">Brand name *</label><input id="brand-name" name="name" required placeholder="e.g. Northstar Studio"></div><div class="field"><label for="brand-website">Website</label><input id="brand-website" name="website" type="url" placeholder="https://"></div><div class="field"><label for="brand-instagram">Instagram handle</label><input id="brand-instagram" name="handle_instagram" placeholder="northstarstudio"></div><div class="field"><label for="brand-twitter">X / Twitter handle</label><input id="brand-twitter" name="handle_twitter" placeholder="northstarstudio"></div><div class="modal-actions"><button class="ghost-button close-dialog" type="button">Cancel</button><button class="primary-button" type="submit">Add competitor</button></div></div>
    </form>
  </dialog>
  <dialog id="auth-dialog">
    <form id="auth-form">
      <div class="modal-head"><div><div class="eyebrow">Private workspace</div><h2 id="auth-title">Sign in to Scout</h2></div><button class="close-button auth-close" type="button">&times;</button></div>
      <div class="modal-body">
        <div class="field"><label for="auth-email">Work email</label><input id="auth-email" type="email" required autocomplete="email" placeholder="you@brand.com"></div>
        <div class="field"><label for="auth-password">Password</label><input id="auth-password" type="password" minlength="6" required autocomplete="current-password" placeholder="At least 6 characters"></div>
        <p class="auth-note"><span id="auth-prompt">New to Scout?</span> <button id="auth-switch" class="auth-switch" type="button">Create an account</button></p>
        <div class="modal-actions"><button class="ghost-button auth-close" type="button">Cancel</button><button id="auth-submit" class="primary-button" type="submit">Sign in</button></div>
      </div>
    </form>
  </dialog>
  <dialog id="workspace-dialog">
    <form id="workspace-form">
      <div class="modal-head"><div><div class="eyebrow">Set up Scout</div><h2>Create your brand workspace</h2></div></div>
      <div class="modal-body">
        <p class="auth-note">Your workspace starts with real records only. Metrics appear after data is connected or imported.</p>
        <div class="field"><label for="workspace-brand">Your brand name *</label><input id="workspace-brand" name="brand_name" required placeholder="e.g. Acme Studios"></div>
        <div class="field"><label for="workspace-site">Website</label><input id="workspace-site" name="website" type="url" placeholder="https://yourbrand.com"></div>
        <div class="field"><label for="workspace-instagram">Instagram handle</label><input id="workspace-instagram" name="handle_instagram" placeholder="yourbrand"></div>
        <div class="field"><label for="workspace-twitter">X / Twitter handle</label><input id="workspace-twitter" name="handle_twitter" placeholder="yourbrand"></div>
        <div class="field"><label for="workspace-competitors">Competitors</label><input id="workspace-competitors" placeholder="Brand One, Brand Two"><p class="field-help">Separate names with commas.</p></div>
        <div class="modal-actions"><button class="primary-button" type="submit">Create workspace</button></div>
      </div>
    </form>
  </dialog>
  <div id="toast" class="toast" role="status" aria-live="polite"></div>
  <script>
    window.SCOUT_CONFIG = __SCOUT_CONFIG__;
    const state = { data: null, query: "", view: "overview", session: null, account: null, authMode: "signin" };
    const mixColors = ["#7cdbb5", "#f5ad72", "#a8a5ff", "#68b8ff", "#ff8f9e"];
    const $ = (selector) => document.querySelector(selector);
    const escapeHTML = (value="") => String(value).replace(/[&<>'"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
    const compact = (value) => Intl.NumberFormat("en", {notation:"compact", maximumFractionDigits:1}).format(value || 0);
    const titleCase = (value="") => value.replaceAll("_"," ").replace(/\b\w/g, x => x.toUpperCase());
    const relativeTime = (value) => { const days=Math.max(0,Math.round((Date.now()-new Date(value))/86400000)); return days===0?"Today":days===1?"Yesterday":`${days}d ago`; };
    const initials = (name="") => name.split(" ").map(x=>x[0]).join("").slice(0,2).toUpperCase();
    function showToast(message){ const toast=$("#toast"); toast.textContent=message; toast.classList.add("show"); setTimeout(()=>toast.classList.remove("show"),2600); }
    const authHeaders = () => state.session?.access_token ? {Authorization:`Bearer ${state.session.access_token}`} : {};
    function saveSession(session){ state.session=session; if(session)localStorage.setItem("scout_session",JSON.stringify(session));else localStorage.removeItem("scout_session"); }
    async function supabaseAuth(path,body){ const {supabaseUrl,supabaseKey}=window.SCOUT_CONFIG; if(!supabaseUrl||!supabaseKey)throw new Error("Authentication is not configured yet"); const response=await fetch(`${supabaseUrl}/auth/v1/${path}`,{method:"POST",headers:{apikey:supabaseKey,"Content-Type":"application/json"},body:JSON.stringify(body)}); const data=await response.json(); if(!response.ok)throw new Error(data.msg||data.error_description||data.message||"Authentication failed"); return data; }
    function updateAccountUI(){ const workspace=state.account?.workspace; $("#auth-button").textContent=state.session?"Sign out":"Sign in"; $("#workspace-name").textContent=workspace?.brand_name||"Public preview"; $("#workspace-copy").textContent=workspace?"Private workspace · real stored data":"Sign in to create a private workspace backed by Supabase."; }
    async function loadAccount(){ if(!state.session)return; const response=await fetch("/api/me",{headers:authHeaders()}); if(response.status===401){saveSession(null);state.account=null;updateAccountUI();return;} if(!response.ok)throw new Error("Could not load your account"); state.account=await response.json(); updateAccountUI(); if(!state.account.workspace)$("#workspace-dialog").showModal(); }
    function setAuthMode(mode){ state.authMode=mode; const signup=mode==="signup"; $("#auth-title").textContent=signup?"Create your Scout account":"Sign in to Scout"; $("#auth-submit").textContent=signup?"Create account":"Sign in"; $("#auth-prompt").textContent=signup?"Already have an account?":"New to Scout?"; $("#auth-switch").textContent=signup?"Sign in":"Create an account"; }
    function delta(value, suffix=" vs previous period"){ if(typeof value==="string")return `<div class="delta">${escapeHTML(value)}</div>`; const numeric=Number(value||0); const cls=numeric>0?"up":numeric<0?"down":""; const sign=numeric>0?"+":""; return `<div class="delta ${cls}">${sign}${numeric}${suffix}</div>`; }
    function metric(label,value,change,color,suffix="% vs previous period"){ return `<article class="card kpi" style="--kpi-color:${color}"><div class="kpi-label">${label}</div><div class="kpi-value">${value}</div>${delta(change,suffix)}</article>`; }
    function renderKpis(){ const s=state.data.summary; $("#kpis").innerHTML=[metric("Published posts",s.posts,s.posts_change,"var(--green)"),metric("Market mentions",s.mentions,s.mentions_change,"var(--purple)"),metric("Active ads",s.active_ads,"Live now","var(--orange)",""),metric("Avg engagement",`${s.engagement_rate.toFixed(2)}%`,s.engagement_change,"var(--blue)"," pts vs previous period")].join(""); }
    function renderChart(){ const series=state.data.engagement_series; const max=Math.max(...series.map(x=>x.engagement),1); $("#engagement-chart").innerHTML=series.map((item,index)=>{ const height=Math.max(3,item.engagement/max*100); const label=new Date(item.date).toLocaleDateString("en",{month:"short",day:"numeric"}); return `<div class="chart-bar" style="--height:${height}%" data-label="${label} · ${compact(item.engagement)}"></div>`; }).join(""); }
    function renderMix(){ const items=state.data.content_mix; const actualTotal=items.reduce((sum,x)=>sum+x.value,0); const total=actualTotal||1; let cursor=0; const segments=items.map((item,index)=>{ const start=cursor; cursor+=item.value/total*100; return `${mixColors[index%mixColors.length]} ${start}% ${cursor}%`; }).join(","); const legend=items.map((item,index)=>`<div class="mix-row"><span class="mix-key"><i style="--color:${mixColors[index%mixColors.length]}"></i>${escapeHTML(titleCase(item.label))}</span><b>${Math.round(item.value/total*100)}%</b></div>`).join(""); $("#content-mix").innerHTML=`<div class="donut" style="--segments:conic-gradient(${segments||'#20303d 0 100%'})"><div class="donut-copy"><strong>${actualTotal}</strong><span>posts</span></div></div><div class="mix-legend">${legend||'<span class="field-help">No sourced content yet</span>'}</div>`; }
    function renderCompetitors(){ const rows=state.data.competitors.map(c=>`<div class="competitor-row"><div class="competitor-name"><div class="avatar" style="--avatar:${c.color}">${initials(c.name)}</div><div><strong>${escapeHTML(c.name)}</strong><small>@${escapeHTML(c.handle||"untracked")}</small></div></div><div>${c.posts}</div><div>${c.mentions}</div><div>${c.engagement_rate.toFixed(2)}%</div><div>${escapeHTML(titleCase(c.top_format))}</div><div class="${c.search_change>=0?'positive':'negative'}">${c.search_change>=0?'+':''}${c.search_change}%</div></div>`).join(""); $("#competitor-table").innerHTML=`<div class="competitor-row header"><div>Brand</div><div>Posts</div><div>Mentions</div><div>Engagement</div><div>Top format</div><div>Search lift</div></div>${rows||'<div class="empty">No competitors yet.</div>'}`; }
    function renderBestTimes(){ const slots=state.data.best_times; $("#best-times").innerHTML=slots.map(slot=>`<div class="slot"><strong>${escapeHTML(slot.day)} · ${String(slot.hour).padStart(2,"0")}:00</strong><span>${compact(slot.avg_engagement)} avg engagement</span></div>`).join("")||'<div class="empty">More posting history is needed.</div>'; }
    function filtered(items, fields){ const query=state.query.trim().toLowerCase(); if(!query)return items; return items.filter(item=>fields.some(field=>String(item[field]||"").toLowerCase().includes(query))); }
    function renderPosts(){ const posts=filtered(state.data.posts,["competitor","caption","platform","content_type"]); $("#posts-list").innerHTML=posts.map(p=>`<article class="card post-card"><div class="format-icon" style="--icon-color:${p.competitor_color}">${escapeHTML((p.content_type||"post").slice(0,3))}</div><div><div class="post-meta"><strong style="color:${p.competitor_color}">${escapeHTML(p.competitor)}</strong><span>·</span><span>${escapeHTML(titleCase(p.platform))}</span><span>·</span><span>${relativeTime(p.posted_at)}</span>${p.is_boosted?'<span class="badge boosted">Paid support</span>':'<span class="badge">Organic</span>'}</div><p class="post-copy">${escapeHTML(p.caption)}</p></div><div class="post-stats"><strong>${compact(p.engagement)}</strong><span>engagements</span></div></article>`).join("")||'<div class="card empty"><strong>No matching content</strong>Try a different search or filter.</div>'; }
    function renderSentiment(){ const s=state.data.sentiment; const total=s.positive+s.neutral+s.negative||1; $("#sentiment-summary").innerHTML=`<div class="sentiment"><article class="card sentiment-card"><span>Positive mentions</span><strong class="positive">${s.positive}</strong></article><article class="card sentiment-card"><span>Neutral mentions</span><strong>${s.neutral}</strong></article><article class="card sentiment-card"><span>Negative mentions</span><strong class="negative">${s.negative}</strong></article></div><div class="sentiment-bar"><i style="width:${s.positive/total*100}%;background:var(--green)"></i><i style="width:${s.neutral/total*100}%;background:#6f879a"></i><i style="width:${s.negative/total*100}%;background:var(--red)"></i></div>`; }
    function renderMentions(){ const mentions=filtered(state.data.mentions,["competitor","text","author","platform","sentiment"]); $("#mentions-list").innerHTML=mentions.map(m=>`<article class="card mention-card"><div><div class="mention-meta"><strong>${escapeHTML(m.competitor)}</strong><span>·</span><span>@${escapeHTML(m.author||"unknown")}</span><span>·</span><span>${escapeHTML(titleCase(m.platform))}</span><span>·</span><span>${relativeTime(m.published_at)}</span></div><p class="mention-copy">${escapeHTML(m.text)}</p></div><span class="sentiment-pill ${m.sentiment}">${escapeHTML(m.sentiment)}</span></article>`).join("")||'<div class="card empty"><strong>No matching mentions</strong>Try a different search or filter.</div>'; }
    function renderAds(){ const ads=filtered(state.data.ads,["competitor","creative_text","platform"]); $("#ads-list").innerHTML=ads.map(a=>`<article class="card ad-card"><div><div class="ad-top"><div class="post-meta"><strong>${escapeHTML(a.competitor)}</strong><span>·</span><span>${escapeHTML(titleCase(a.platform))}</span></div><span class="ad-status ${a.is_active?'':'paused'}">${a.is_active?'● ACTIVE':'PAUSED'}</span></div><p class="ad-copy">${escapeHTML(a.creative_text)}</p></div><div class="ad-footer"><span>Started ${a.start_date?relativeTime(a.start_date):'recently'}</span><span>${a.is_active?'Running now':'Completed'}</span></div></article>`).join("")||'<div class="card empty"><strong>No matching ads</strong>Try a different search or filter.</div>'; }
    function renderAll(){ renderKpis();renderChart();renderMix();renderCompetitors();renderBestTimes();renderPosts();renderSentiment();renderMentions();renderAds(); }
    function populateCompetitors(){ const select=$("#competitor-filter"); const current=select.value; select.innerHTML='<option value="">All competitors</option>'+state.data.competitors.map(c=>`<option value="${c.id}">${escapeHTML(c.name)}</option>`).join(""); select.value=current; }
    async function loadData(showMessage=false){ const days=$("#date-filter").value; const competitor=$("#competitor-filter").value; const params=new URLSearchParams({days}); if(competitor)params.set("competitor_id",competitor); try{ const response=await fetch(`/api/dashboard?${params}`,{headers:authHeaders()}); if(!response.ok)throw new Error("Dashboard request failed"); state.data=await response.json(); populateCompetitors(); renderAll(); if(showMessage)showToast("Dashboard refreshed"); }catch(error){ console.error(error); showToast("Could not refresh dashboard"); } }
    document.querySelectorAll(".nav-button").forEach(button=>button.addEventListener("click",()=>{ document.querySelectorAll(".nav-button,.view").forEach(el=>el.classList.remove("active")); button.classList.add("active"); state.view=button.dataset.view; document.getElementById(state.view).classList.add("active"); window.scrollTo({top:0,behavior:"smooth"}); }));
    $("#global-search").addEventListener("input",event=>{ state.query=event.target.value; if(state.data){renderPosts();renderMentions();renderAds();} });
    $("#date-filter").addEventListener("change",()=>loadData()); $("#competitor-filter").addEventListener("change",()=>loadData()); $("#refresh").addEventListener("click",()=>loadData(true));
    const dialog=$("#brand-dialog"), authDialog=$("#auth-dialog"), workspaceDialog=$("#workspace-dialog");
    $("#add-competitor").addEventListener("click",()=>state.session?dialog.showModal():authDialog.showModal());
    document.querySelectorAll(".close-button,.close-dialog").forEach(button=>button.addEventListener("click",()=>{ if(button.classList.contains("auth-close"))authDialog.close();else dialog.close(); }));
    $("#auth-button").addEventListener("click",async()=>{ if(state.session){ try{await supabaseAuth("logout",{});}catch(error){} saveSession(null);state.account=null;updateAccountUI();showToast("Signed out");await loadData(); }else authDialog.showModal(); });
    $("#auth-switch").addEventListener("click",()=>setAuthMode(state.authMode==="signin"?"signup":"signin"));
    $("#auth-form").addEventListener("submit",async event=>{ event.preventDefault(); const email=$("#auth-email").value.trim(),password=$("#auth-password").value; try{ const path=state.authMode==="signup"?"signup":"token?grant_type=password"; const data=await supabaseAuth(path,{email,password}); if(!data.access_token){showToast("Check your email to confirm your account");return;} saveSession(data);authDialog.close();await loadAccount();await loadData();showToast(state.authMode==="signup"?"Account created":"Welcome back"); }catch(error){showToast(error.message);} });
    $("#workspace-form").addEventListener("submit",async event=>{ event.preventDefault(); const form=new FormData(event.currentTarget); const payload=Object.fromEntries([...form.entries()].filter(([,value])=>value)); payload.competitor_names=$("#workspace-competitors").value.split(",").map(x=>x.trim()).filter(Boolean); try{ const response=await fetch("/api/workspace",{method:"POST",headers:{"Content-Type":"application/json",...authHeaders()},body:JSON.stringify(payload)}); const data=await response.json();if(!response.ok)throw new Error(data.detail||"Could not create workspace");workspaceDialog.close();await loadAccount();await loadData();showToast("Your real workspace is ready"); }catch(error){showToast(error.message);} });
    $("#brand-form").addEventListener("submit",async event=>{ event.preventDefault(); const form=new FormData(event.currentTarget); const payload=Object.fromEntries([...form.entries()].filter(([,value])=>value)); try{ const response=await fetch("/competitors",{method:"POST",headers:{"Content-Type":"application/json",...authHeaders()},body:JSON.stringify(payload)}); if(!response.ok){const data=await response.json();throw new Error(data.detail||"Could not add competitor");} dialog.close(); event.currentTarget.reset(); showToast(`${payload.name} added to Scout`); await loadData(); }catch(error){showToast(error.message);} });
    async function bootstrap(){ try{ const saved=localStorage.getItem("scout_session");if(saved)state.session=JSON.parse(saved);if(state.session)await loadAccount(); }catch(error){saveSession(null);showToast("Please sign in again");} updateAccountUI();await loadData(); }
    bootstrap();
  </script>
</body>
</html>
"""
