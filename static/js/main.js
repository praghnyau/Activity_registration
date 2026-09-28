/* ============================================================
   Theme
   ============================================================ */
(function () {
  function applyTheme(pref) {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const resolved = pref === 'system' ? (mq.matches ? 'dark' : 'light') : pref;
    document.documentElement.setAttribute('data-theme', resolved);
  }

  const saved = (() => { try { return localStorage.getItem('theme') || 'system'; } catch { return 'system'; } })();
  applyTheme(saved);

  window.__setTheme = function (pref) {
    try { localStorage.setItem('theme', pref); } catch {}
    applyTheme(pref);
    updateToggleIcon();
  };

  function updateToggleIcon() {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;
    const current = document.documentElement.getAttribute('data-theme');
    btn.setAttribute('aria-label', current === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
    btn.textContent = current === 'dark' ? '☀️' : '🌙';
  }

  document.addEventListener('DOMContentLoaded', function () {
    updateToggleIcon();

    const btn = document.getElementById('theme-toggle');
    if (btn) {
      btn.addEventListener('click', function () {
        const current = document.documentElement.getAttribute('data-theme');
        window.__setTheme(current === 'dark' ? 'light' : 'dark');
      });
    }

    // Follow system if pref is 'system'
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () {
      try { if (localStorage.getItem('theme') === 'system' || !localStorage.getItem('theme')) applyTheme('system'); } catch {}
    });
  });
})();

/* ============================================================
   Sidebar (mobile)
   ============================================================ */
document.addEventListener('DOMContentLoaded', function () {
  const hamburger = document.getElementById('hamburger');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');

  function openSidebar() {
    sidebar && sidebar.classList.add('open');
    overlay && overlay.classList.add('open');
  }
  function closeSidebar() {
    sidebar && sidebar.classList.remove('open');
    overlay && overlay.classList.remove('open');
  }

  hamburger && hamburger.addEventListener('click', openSidebar);
  overlay && overlay.addEventListener('click', closeSidebar);
});

/* ============================================================
   User menu dropdown
   ============================================================ */
document.addEventListener('DOMContentLoaded', function () {
  const btn = document.getElementById('user-menu-btn');
  const dropdown = document.getElementById('user-menu-dropdown');
  if (!btn || !dropdown) return;

  btn.addEventListener('click', function (e) {
    e.stopPropagation();
    dropdown.classList.toggle('open');
  });

  document.addEventListener('click', function () {
    dropdown.classList.remove('open');
  });
});

/* ============================================================
   Flash dismiss
   ============================================================ */
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.flash-close').forEach(function (btn) {
    btn.addEventListener('click', function () {
      btn.closest('.flash').remove();
    });
  });
});

/* ============================================================
   Confirmation dialogs
   ============================================================ */
document.addEventListener('DOMContentLoaded', function () {
  // Open dialog
  document.querySelectorAll('[data-confirm-dialog]').forEach(function (trigger) {
    trigger.addEventListener('click', function (e) {
      e.preventDefault();
      const dialogId = trigger.getAttribute('data-confirm-dialog');
      const dialog = document.getElementById(dialogId);
      if (dialog) dialog.classList.add('open');
    });
  });

  // Cancel dialog
  document.querySelectorAll('[data-dialog-cancel]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      btn.closest('.dialog-overlay').classList.remove('open');
    });
  });

  // Close on overlay click
  document.querySelectorAll('.dialog-overlay').forEach(function (overlay) {
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) overlay.classList.remove('open');
    });
  });
});

/* ============================================================
   Resource link rows (activity form)
   ============================================================ */
document.addEventListener('DOMContentLoaded', function () {
  const container = document.getElementById('resource-links-container');
  const addBtn = document.getElementById('add-resource-link');
  if (!container || !addBtn) return;

  const MAX = 5;

  function updateAddBtn() {
    const rows = container.querySelectorAll('.resource-row');
    addBtn.disabled = rows.length >= MAX;
  }

  addBtn.addEventListener('click', function () {
    const rows = container.querySelectorAll('.resource-row');
    if (rows.length >= MAX) return;
    const idx = rows.length;
    const row = document.createElement('div');
    row.className = 'resource-row';
    row.innerHTML = `
      <input type="text" name="resource_title_${idx}" class="form-control" placeholder="Link title" aria-label="Resource title">
      <input type="url" name="resource_url_${idx}" class="form-control" placeholder="https://..." aria-label="Resource URL">
      <button type="button" class="btn-remove" aria-label="Remove link">Remove</button>
    `;
    row.querySelector('.btn-remove').addEventListener('click', function () {
      row.remove();
      updateAddBtn();
    });
    container.appendChild(row);
    updateAddBtn();
  });

  // Attach remove to existing rows
  container.querySelectorAll('.btn-remove').forEach(function (btn) {
    btn.addEventListener('click', function () {
      btn.closest('.resource-row').remove();
      updateAddBtn();
    });
  });

  updateAddBtn();
});

/* ============================================================
   Password show/hide toggle
   ============================================================ */
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.toggle-pw').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const input = btn.closest('.input-wrap').querySelector('input');
      if (!input) return;
      const isHidden = input.type === 'password';
      input.type = isHidden ? 'text' : 'password';
      btn.textContent = isHidden ? 'Hide' : 'Show';
      btn.setAttribute('aria-label', isHidden ? 'Hide password' : 'Show password');
    });
  });
});

/* ============================================================
   Profile page — theme preference radio
   ============================================================ */
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('input[name="theme_pref"]').forEach(function (radio) {
    radio.addEventListener('change', function () {
      if (radio.checked) window.__setTheme && window.__setTheme(radio.value);
    });
  });
});

/* ============================================================
   Frontend form validation
   ============================================================ */
document.addEventListener('DOMContentLoaded', function () {
  // Login form
  const loginForm = document.getElementById('login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', function (e) {
      let ok = true;
      ['email', 'password'].forEach(function (name) {
        const field = loginForm.querySelector('[name="' + name + '"]');
        const err = loginForm.querySelector('#err-' + name);
        if (field && err) {
          if (!field.value.trim()) {
            err.textContent = 'This field is required.';
            ok = false;
          } else {
            err.textContent = '';
          }
        }
      });
      if (!ok) e.preventDefault();
    });
  }

  // Activity form
  const activityForm = document.getElementById('activity-form');
  if (activityForm) {
    activityForm.addEventListener('submit', function (e) {
      let ok = true;

      function require(name, label) {
        const field = activityForm.querySelector('[name="' + name + '"]');
        const err = activityForm.querySelector('#err-' + name);
        if (field && err && !field.value.trim()) {
          err.textContent = label + ' is required.';
          ok = false;
        } else if (err) {
          err.textContent = '';
        }
      }

      require('title', 'Title');
      require('starts_at', 'Activity date');
      require('registration_deadline', 'Registration deadline');
      require('group_size', 'Group size');

      // Deadline before start
      const start = activityForm.querySelector('[name="starts_at"]');
      const deadline = activityForm.querySelector('[name="registration_deadline"]');
      const errDeadline = activityForm.querySelector('#err-registration_deadline');
      if (start && deadline && errDeadline && start.value && deadline.value) {
        if (new Date(deadline.value) >= new Date(start.value)) {
          errDeadline.textContent = 'Registration deadline must be before the activity start.';
          ok = false;
        }
      }

      // Resource URLs must start with https://
      activityForm.querySelectorAll('input[name^="resource_url_"]').forEach(function (urlInput) {
        const val = urlInput.value.trim();
        if (val && !val.startsWith('https://')) {
          urlInput.setCustomValidity('URL must start with https://');
          urlInput.reportValidity();
          ok = false;
        } else {
          urlInput.setCustomValidity('');
        }
      });

      if (!ok) e.preventDefault();
    });
  }

  // Password change form
  const pwForm = document.getElementById('password-form');
  if (pwForm) {
    pwForm.addEventListener('submit', function (e) {
      let ok = true;
      const cur = pwForm.querySelector('[name="current_password"]');
      const nw = pwForm.querySelector('[name="new_password"]');
      const conf = pwForm.querySelector('[name="confirm_password"]');
      const errCur = pwForm.querySelector('#err-current_password');
      const errNw = pwForm.querySelector('#err-new_password');
      const errConf = pwForm.querySelector('#err-confirm_password');

      if (cur && errCur && !cur.value) { errCur.textContent = 'Current password is required.'; ok = false; }
      else if (errCur) errCur.textContent = '';

      if (nw && errNw) {
        if (!nw.value) { errNw.textContent = 'New password is required.'; ok = false; }
        else if (nw.value.length < 8) { errNw.textContent = 'Password must be at least 8 characters.'; ok = false; }
        else errNw.textContent = '';
      }

      if (conf && errConf && nw) {
        if (conf.value !== nw.value) { errConf.textContent = 'Passwords do not match.'; ok = false; }
        else errConf.textContent = '';
      }

      if (!ok) e.preventDefault();
    });
  }
});
