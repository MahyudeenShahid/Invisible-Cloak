(() => {
  const $ = id => document.getElementById(id);

  const sliderIds = ['h_min', 'h_max', 's_min', 's_max', 'v_min', 'v_max'];
  let debounceTimer = null;
  let currentRangeIdx = 0;

  // ─── Utility ────────────────────────────────────────────────────
  function showMsg(text, isError = false) {
    const el = $('action-msg');
    el.textContent = text;
    el.className = 'msg' + (isError ? ' error' : '');
    clearTimeout(el._t);
    el._t = setTimeout(() => { el.innerHTML = ''; }, 3000);
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
    if (!slider || !lbl) return;
    slider.addEventListener('input', () => {
      lbl.textContent = slider.value;
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(pushHSV, 200);
    });
  });

  function pushHSV() {
    post('/set_hsv', {
      idx: currentRangeIdx,
      h_min: +$('h_min').value, h_max: +$('h_max').value,
      s_min: +$('s_min').value, s_max: +$('s_max').value,
      v_min: +$('v_min').value, v_max: +$('v_max').value,
    });
  }

  function applySliders(data) {
    ['h_min','h_max','s_min','s_max','v_min','v_max'].forEach(k => {
      if (data[k] !== undefined) {
        if ($(k)) $(k).value = data[k];
        if ($('lbl-' + k)) $('lbl-' + k).textContent = data[k];
      }
    });
  }

  // ─── Multi-Color Cloak ────────────────────────────────────────────
  function hsvToHsl(h, s, v) {
    // OpenCV HSV (h 0-179, s 0-255, v 0-255) to CSS hsl string for swatches
    const hDeg = h * 2;
    const sSat = s / 255;
    const vPct = v / 255;
    const l = vPct * (1 - sSat / 2);
    const sHsl = (l === 0 || l === 1) ? 0 : (vPct - l) / Math.min(l, 1 - l);
    return `hsl(${hDeg}, ${Math.round(sHsl * 100)}%, ${Math.max(20, Math.round(l * 100))}%)`;
  }

  function renderColorRanges(ranges, activeIdx) {
    currentRangeIdx = activeIdx;
    const container = $('color-chips');
    container.innerHTML = ranges.map((cr, i) => {
      const hMid = (cr.hsv_min[0] + cr.hsv_max[0]) / 2;
      const sMid = (cr.hsv_min[1] + cr.hsv_max[1]) / 2;
      const vMid = (cr.hsv_min[2] + cr.hsv_max[2]) / 2;
      const swatch = hsvToHsl(hMid, sMid, vMid);
      return `
        <div class="color-chip${i === activeIdx ? ' active' : ''}" data-idx="${i}" title="Color ${i + 1} — click to edit sliders">
          <div class="chip-swatch" style="background:${swatch}"></div>
          <span>Color ${i + 1}</span>
          ${ranges.length > 1 ? `<button class="chip-del" data-idx="${i}" title="Remove">×</button>` : ''}
        </div>`;
    }).join('');

    container.querySelectorAll('.color-chip').forEach(chip => {
      chip.addEventListener('click', async e => {
        if (e.target.classList.contains('chip-del')) return;
        const idx = +chip.dataset.idx;
        const d = await post('/set_active_range', { idx });
        if (d.status === 'ok') {
          currentRangeIdx = d.active_idx;
          container.querySelectorAll('.color-chip').forEach(c =>
            c.classList.toggle('active', +c.dataset.idx === idx));
          applySliders({
            h_min: d.hsv_min[0], s_min: d.hsv_min[1], v_min: d.hsv_min[2],
            h_max: d.hsv_max[0], s_max: d.hsv_max[1], v_max: d.hsv_max[2],
          });
        }
      });
    });

    container.querySelectorAll('.chip-del').forEach(btn => {
      btn.addEventListener('click', async e => {
        e.stopPropagation();
        const idx = +btn.dataset.idx;
        const d = await post('/delete_color_range', { idx });
        if (d.status === 'ok') {
          renderColorRanges(d.ranges, d.active_idx);
          const ar = d.ranges[d.active_idx];
          applySliders({
            h_min: ar.hsv_min[0], s_min: ar.hsv_min[1], v_min: ar.hsv_min[2],
            h_max: ar.hsv_max[0], s_max: ar.hsv_max[1], v_max: ar.hsv_max[2],
          });
          showMsg('Color slot removed.');
        }
      });
    });
  }

  $('btn-add-color').addEventListener('click', async () => {
    const d = await post('/add_color_range', {});
    if (d.status === 'ok') {
      renderColorRanges(d.ranges, d.active_idx);
      applySliders({ h_min: 0, h_max: 179, s_min: 0, s_max: 255, v_min: 0, v_max: 255 });
      showMsg(`Color ${d.active_idx + 1} added — click the new cloak color on the video!`);
    } else {
      showMsg(d.message, true);
    }
  });

  async function initColorRanges() {
    const d = await (await fetch('/color_ranges')).json();
    renderColorRanges(d.ranges, d.active_idx);
    const ar = d.ranges[d.active_idx];
    applySliders({
      h_min: ar.hsv_min[0], s_min: ar.hsv_min[1], v_min: ar.hsv_min[2],
      h_max: ar.hsv_max[0], s_max: ar.hsv_max[1], v_max: ar.hsv_max[2],
    });
  }

  // Sensitivity label
  $('sensitivity').addEventListener('input', () => {
    $('sens-val').textContent = $('sensitivity').value;
  });

  // ─── Capture Background ─────────────────────────────────────────
  $('btn-capture').addEventListener('click', async () => {
    const originalHtml = $('btn-capture').innerHTML;
    $('btn-capture').innerHTML = '<span>⏳</span> Analyzing Scene...';
    const d = await post('/capture_background', {});
    $('btn-capture').innerHTML = originalHtml;
    showMsg(d.message || 'Scene Base Captured!', d.status !== 'ok');
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
      $('panel-smart').style.display     = currentMode === 'smart'     ? '' : 'none';
      // stop if running
      if (running) {
        running = false;
        $('toggle-icon').textContent = '▶';
        $('toggle-text').textContent = 'Initialize System';
        $('btn-toggle').className = 'btn btn-primary';
        const badge = $('status-badge');
        badge.textContent = 'System Standby'; 
        badge.className = 'badge badge-off';
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
        const target = tile.closest('.smart-subpanel') ? 'selected-bg-name-smart' : 'selected-bg-name';
        $(target).textContent = 'Selected: ' + d.name;
        showMsg('Target set: ' + d.name);
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

  // ─── Smart BG Mode ───────────────────────────────────────────────
  let currentSmartType = 'blur';

  // Smart type toggle (Blur / Scene / Color)
  document.querySelectorAll('.smart-type-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      document.querySelectorAll('.smart-type-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentSmartType = btn.dataset.stype;
      $('smart-panel-blur').style.display    = currentSmartType === 'blur'    ? '' : 'none';
      $('smart-panel-virtual').style.display = currentSmartType === 'virtual' ? '' : 'none';
      $('smart-panel-solid').style.display   = currentSmartType === 'solid'   ? '' : 'none';
      await post('/set_smart_bg_type', { type: currentSmartType });
    });
  });

  // Blur amount slider
  $('blur-amount').addEventListener('input', () => {
    const v = $('blur-amount').value;
    $('lbl-blur').textContent = v;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      post('/set_smart_bg_type', { type: currentSmartType, blur_amount: +v });
    }, 150);
  });

  // Smart scene tiles (inside smart panel)
  document.querySelectorAll('.smart-scene-tile').forEach(tile => {
    tile.addEventListener('click', async () => {
      document.querySelectorAll('.smart-scene-tile').forEach(t => t.classList.remove('active'));
      tile.classList.add('active');
      const d = await post('/set_builtin_bg', { name: tile.dataset.scene });
      if (d.status === 'ok') {
        $('selected-bg-name-smart').textContent = '✓ ' + d.name;
        showMsg('Smart background set: ' + d.name);
      }
    });
  });

  // Smart upload
  $('upload-bg-smart').addEventListener('change', async e => {
    const file = e.target.files[0];
    if (!file) return;
    const form = new FormData();
    form.append('file', file);
    const res = await fetch('/upload_bg', { method: 'POST', body: form });
    const d = await res.json();
    if (d.status === 'ok') {
      document.querySelectorAll('.smart-scene-tile').forEach(t => t.classList.remove('active'));
      $('selected-bg-name-smart').textContent = '✓ ' + d.name;
      showMsg('Custom background uploaded!');
    } else {
      showMsg(d.message, true);
    }
  });

  // Solid color presets
  document.querySelectorAll('.color-preset').forEach(btn => {
    btn.addEventListener('click', async () => {
      document.querySelectorAll('.color-preset').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const r = +btn.dataset.r, g = +btn.dataset.g, b = +btn.dataset.b;
      const hex = '#' + [r,g,b].map(x => x.toString(16).padStart(2,'0')).join('');
      $('solid-color-picker').value = hex;
      $('solid-color-name').textContent = btn.title;
      await post('/set_solid_color', { r, g, b });
    });
  });

  // Custom color picker
  $('solid-color-picker').addEventListener('input', async () => {
    const hex = $('solid-color-picker').value;
    const r = parseInt(hex.slice(1,3), 16);
    const g = parseInt(hex.slice(3,5), 16);
    const b = parseInt(hex.slice(5,7), 16);
    document.querySelectorAll('.color-preset').forEach(p => p.classList.remove('active'));
    $('solid-color-name').textContent = hex;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => post('/set_solid_color', { r, g, b }), 150);
  });

  // ─── Fullscreen ──────────────────────────────────────────────────
  const videoWrapper  = $('video-wrapper');
  const fsIconEnter   = $('fs-icon-enter');
  const fsIconExit    = $('fs-icon-exit');

  $('btn-fullscreen').addEventListener('click', () => {
    if (!document.fullscreenElement) {
      (videoWrapper.requestFullscreen
        || videoWrapper.webkitRequestFullscreen
        || videoWrapper.mozRequestFullScreen
        || videoWrapper.msRequestFullscreen
      ).call(videoWrapper);
    } else {
      (document.exitFullscreen
        || document.webkitExitFullscreen
        || document.mozCancelFullScreen
        || document.msExitFullscreen
      ).call(document);
    }
  });

  function onFsChange() {
    const isFs = !!document.fullscreenElement;
    fsIconEnter.style.display = isFs ? 'none' : '';
    fsIconExit.style.display  = isFs ? ''     : 'none';
  }
  document.addEventListener('fullscreenchange',       onFsChange);
  document.addEventListener('webkitfullscreenchange', onFsChange);
  document.addEventListener('mozfullscreenchange',    onFsChange);
  document.addEventListener('MSFullscreenChange',     onFsChange);

  // ─── Toggle Invisibility ─────────────────────────────────────────
  let running = false;
  $('btn-toggle').addEventListener('click', async () => {
    const d = await post('/toggle', {});
    if (d.status === 'error') { showMsg(d.message, true); return; }
    running = d.running;
    $('toggle-icon').textContent = running ? '⏹' : '▶';
    $('toggle-text').textContent = running ? 'Terminate Feed' : 'Initialize System';
    $('btn-toggle').className = running ? 'btn btn-danger' : 'btn btn-primary';
    const badge = $('status-badge');
    badge.textContent = running ? 'Active Feed' : 'System Standby';
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
      // Refresh the chip swatch for the active color slot
      (async () => {
        const rd = await (await fetch('/color_ranges')).json();
        renderColorRanges(rd.ranges, rd.active_idx);
      })();
      // Show color dot in tooltip
      const hue = Math.round(d.hsv[0] * 2); // OpenCV H is 0-179 → CSS hue 0-360
      tooltip.innerHTML = `<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:hsl(${hue},${d.hsv[1]/255*100|0}%,${d.hsv[2]/255*60+20|0}%);vertical-align:middle;margin-right:5px;border:1px solid #aaa"></span>Color ${currentRangeIdx + 1} picked!`;
      clearTimeout(tooltip._t);
      tooltip._t = setTimeout(() => { tooltip.innerHTML = '🎯 Aim & Click to Select Color'; }, 3000);
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
      list.innerHTML = '<span class="no-profiles">No presets saved.</span>';
      return;
    }
    list.innerHTML = names.map(name => `
      <div class="profile-item">
        <span title="${name}">${name}</span>
        <div class="profile-actions">
          <button class="load-btn" data-name="${name}">Load</button>
          <button class="del-btn"  data-name="${name}">✕</button>
        </div>
      </div>
    `).join('');

    list.querySelectorAll('.load-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const d = await post('/load_profile', { name: btn.dataset.name });
        if (d.status === 'ok') {
          if (d.color_ranges) {
            renderColorRanges(d.color_ranges, d.active_idx || 0);
            const ar = d.color_ranges[d.active_idx || 0];
            applySliders({
              h_min: ar.hsv_min[0], s_min: ar.hsv_min[1], v_min: ar.hsv_min[2],
              h_max: ar.hsv_max[0], s_max: ar.hsv_max[1], v_max: ar.hsv_max[2],
            });
          } else if (d.hsv_min) {
            applySliders({
              h_min: d.hsv_min[0], s_min: d.hsv_min[1], v_min: d.hsv_min[2],
              h_max: d.hsv_max[0], s_max: d.hsv_max[1], v_max: d.hsv_max[2],
            });
          }
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

  // Load initial state
  initColorRanges();
  loadProfiles();
})();
