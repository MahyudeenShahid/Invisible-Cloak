(() => {
  const $ = id => document.getElementById(id);

  const sliderIds = ['h_min', 'h_max', 's_min', 's_max', 'v_min', 'v_max'];
  let debounceTimer = null;

  // ─── Utility ────────────────────────────────────────────────────
  function showMsg(text, isError = false) {
    const el = $('action-msg');
    el.textContent = text;
    el.className = 'msg' + (isError ? ' error' : '');
    clearTimeout(el._t);
    el._t = setTimeout(() => { el.textContent = ''; }, 3000);
  }

  async function post(url, data) {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return res.json();
  }

  // ─── Sliders ────────────────────────────────────────────────────
  sliderIds.forEach(id => {
    const slider = $(id);
    const lbl = $('lbl-' + id);
    slider.addEventListener('input', () => {
      lbl.textContent = slider.value;
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(pushHSV, 200);
    });
  });

  function pushHSV() {
    post('/set_hsv', {
      h_min: +$('h_min').value, h_max: +$('h_max').value,
      s_min: +$('s_min').value, s_max: +$('s_max').value,
      v_min: +$('v_min').value, v_max: +$('v_max').value,
    });
  }

  function applySliders(data) {
    ['h_min','h_max','s_min','s_max','v_min','v_max'].forEach(k => {
      if (data[k] !== undefined) {
        $(k).value = data[k];
        $('lbl-' + k).textContent = data[k];
      }
    });
  }

  // Sensitivity label
  $('sensitivity').addEventListener('input', () => {
    $('sens-val').textContent = $('sensitivity').value;
  });

  // ─── Capture Background ─────────────────────────────────────────
  $('btn-capture').addEventListener('click', async () => {
    $('btn-capture').textContent = '⏳ Capturing...';
    const d = await post('/capture_background', {});
    $('btn-capture').textContent = '📷 Capture Background';
    showMsg(d.message || 'Done!', d.status !== 'ok');
  });

  // ─── Mode Toggle ────────────────────────────────────────────────
  let currentMode = 'invisible';
  document.querySelectorAll('.mode-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentMode = btn.dataset.mode;
      $('panel-invisible').style.display = currentMode === 'invisible' ? '' : 'none';
      $('panel-virtual').style.display   = currentMode === 'virtual'   ? '' : 'none';
      // stop if running
      if (running) {
        running = false;
        $('btn-toggle').textContent = '▶ Start';
        $('btn-toggle').className = 'btn btn-primary';
        const badge = $('status-badge');
        badge.textContent = 'OFF'; badge.className = 'badge badge-off';
      }
      await post('/set_bg_mode', { mode: currentMode });
    });
  });

  // ─── Built-in Background Tiles ───────────────────────────────────
  document.querySelectorAll('.bg-tile').forEach(tile => {
    tile.addEventListener('click', async () => {
      document.querySelectorAll('.bg-tile').forEach(t => t.classList.remove('active'));
      tile.classList.add('active');
      const d = await post('/set_builtin_bg', { name: tile.dataset.scene });
      if (d.status === 'ok') {
        $('selected-bg-name').textContent = '✓ ' + d.name;
        showMsg('Background set: ' + d.name);
      }
    });
  });

  // ─── Upload Custom Background ────────────────────────────────────
  $('upload-bg').addEventListener('change', async e => {
    const file = e.target.files[0];
    if (!file) return;
    const form = new FormData();
    form.append('file', file);
    const res = await fetch('/upload_bg', { method: 'POST', body: form });
    const d = await res.json();
    if (d.status === 'ok') {
      document.querySelectorAll('.bg-tile').forEach(t => t.classList.remove('active'));
      $('selected-bg-name').textContent = '✓ ' + d.name;
      showMsg('Custom background uploaded!');
    } else {
      showMsg(d.message, true);
    }
  });

  // ─── Toggle Invisibility ─────────────────────────────────────────
  let running = false;
  $('btn-toggle').addEventListener('click', async () => {
    const d = await post('/toggle', {});
    if (d.status === 'error') { showMsg(d.message, true); return; }
    running = d.running;
    $('btn-toggle').textContent = running ? '⏹ Stop' : '▶ Start';
    $('btn-toggle').className = running ? 'btn btn-danger' : 'btn btn-primary';
    const badge = $('status-badge');
    badge.textContent = running ? 'ON' : 'OFF';
    badge.className = 'badge ' + (running ? 'badge-on' : 'badge-off');
  });

  // ─── Effects ────────────────────────────────────────────────────
  document.querySelectorAll('.effect-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      document.querySelectorAll('.effect-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      await post('/set_effect', { effect: btn.dataset.effect });
    });
  });

  // ─── Click-to-Pick Color ─────────────────────────────────────────
  const videoImg = $('video-feed');
  const tooltip  = $('pick-tooltip');

  videoImg.addEventListener('click', async e => {
    const rect = videoImg.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top)  / rect.height;
    const sens = +$('sensitivity').value;
    const d = await post('/pick_color', { x, y, sensitivity: sens });
    if (d.status === 'ok') {
      applySliders(d);
      // Show color dot in tooltip
      const hue = Math.round(d.hsv[0] * 2); // OpenCV H is 0-179 → CSS hue 0-360
      tooltip.innerHTML = `<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:hsl(${hue},${d.hsv[1]/255*100|0}%,${d.hsv[2]/255*60+20|0}%);vertical-align:middle;margin-right:5px;border:1px solid #aaa"></span>Color picked!`;
      clearTimeout(tooltip._t);
      tooltip._t = setTimeout(() => { tooltip.innerHTML = 'Click to pick color'; }, 3000);
    }
  });

  // ─── Profiles ───────────────────────────────────────────────────
  async function loadProfiles() {
    const profiles = await (await fetch('/profiles')).json();
    renderProfiles(profiles);
  }

  function renderProfiles(profiles) {
    const list = $('profiles-list');
    const names = Object.keys(profiles);
    if (names.length === 0) {
      list.innerHTML = '<span class="no-profiles">No saved profiles yet.</span>';
      return;
    }
    list.innerHTML = names.map(name => `
      <div class="profile-item">
        <span title="${name}">${name}</span>
        <button class="load-btn" data-name="${name}">Load</button>
        <button class="del-btn"  data-name="${name}">✕</button>
      </div>
    `).join('');

    list.querySelectorAll('.load-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const d = await post('/load_profile', { name: btn.dataset.name });
        if (d.status === 'ok') {
          applySliders(d.hsv_min ? {
            h_min: d.hsv_min[0], s_min: d.hsv_min[1], v_min: d.hsv_min[2],
            h_max: d.hsv_max[0], s_max: d.hsv_max[1], v_max: d.hsv_max[2],
          } : {});
          // Set effect button
          document.querySelectorAll('.effect-btn').forEach(b => {
            b.classList.toggle('active', b.dataset.effect === (d.effect || 'none'));
          });
          showMsg(`Profile "${btn.dataset.name}" loaded!`);
        }
      });
    });

    list.querySelectorAll('.del-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const d = await post('/delete_profile', { name: btn.dataset.name });
        if (d.status === 'ok') { renderProfiles(d.profiles); }
      });
    });
  }

  $('btn-save-profile').addEventListener('click', async () => {
    const name = $('profile-name').value.trim();
    if (!name) { showMsg('Enter a profile name first.', true); return; }
    const d = await post('/save_profile', { name });
    if (d.status === 'ok') {
      renderProfiles(d.profiles);
      $('profile-name').value = '';
      showMsg(`Profile "${name}" saved!`);
    }
  });

  // Load profiles on start
  loadProfiles();
})();
