/* ==========================================================================
   Genesis product site — interaction layer
   ==========================================================================

   No dependencies. Everything here is progressive enhancement: with JavaScript
   disabled the page is still complete and readable, because every section's
   content is in the HTML. Keeping it that way matters for a page whose whole
   argument is honest reporting — the risk table, the status table and the
   roadmap are markup, not script.

   Contents:
     1. Theme toggle (dark default, persisted)
     2. Navigation (condense on scroll, mobile drawer)
     3. Reveal on scroll
     4. Risk explorer (the one genuinely interactive explainer)
     5. Budget chart animation
     6. Hash-chain highlight loop
     7. Copy to clipboard
   ========================================================================== */

(function () {
  'use strict';

  try {
  enhance();
  } catch (error) {
    // Fail safe. The scroll-reveal effect hides content until an
    // IntersectionObserver reveals it, so an exception anywhere in this file
    // would otherwise leave the page looking empty. Dropping the `js` marker
    // restores the static document, which is always readable.
    document.documentElement.classList.remove('js');
    if (window.console && console.error) {
      console.error('Genesis site: enhancement failed, showing static content.', error);
    }
  }

  function enhance() {

  var prefersReducedMotion =
    window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------------------------------------------------------------------- */
  /* 1. Theme                                                               */
  /* ---------------------------------------------------------------------- */

  var THEME_KEY = 'genesis_site_theme';

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch (error) {
      /* storage unavailable; the theme still applies for this page view */
    }
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', theme === 'light' ? '#fbfbfc' : '#08090c');
  }

  (function restoreTheme() {
    // The inline attribute on <html> is the default, so there is no flash.
    var stored = null;
    try {
      stored = localStorage.getItem(THEME_KEY);
    } catch (error) {
      /* ignore */
    }
    if (stored === 'light' || stored === 'dark') {
      document.documentElement.setAttribute('data-theme', stored);
      var meta = document.querySelector('meta[name="theme-color"]');
      if (meta) meta.setAttribute('content', stored === 'light' ? '#fbfbfc' : '#08090c');
      return;
    }
    // No stored preference: respect the OS if it asks for light.
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
      document.documentElement.setAttribute('data-theme', 'light');
    }
  })();

  var themeToggle = document.getElementById('theme-toggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', function () {
      var next =
        document.documentElement.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
      applyTheme(next);
    });
  }

  /* ---------------------------------------------------------------------- */
  /* 2. Navigation                                                          */
  /* ---------------------------------------------------------------------- */

  var nav = document.getElementById('nav');
  var burger = document.getElementById('nav-burger');
  var drawer = document.getElementById('nav-drawer');

  if (nav) {
    var onScroll = function () {
      nav.classList.toggle('is-stuck', window.scrollY > 8);
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  if (burger && drawer) {
    var setDrawer = function (open) {
      drawer.hidden = !open;
      drawer.classList.toggle('is-open', open);
      burger.setAttribute('aria-expanded', String(open));
      burger.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    };

    burger.addEventListener('click', function () {
      setDrawer(drawer.hidden);
    });

    drawer.addEventListener('click', function (event) {
      if (event.target.tagName === 'A') setDrawer(false);
    });

    // A drawer left open behind a widened viewport is a common bug; close it.
    window.addEventListener('resize', function () {
      if (window.innerWidth > 1024 && !drawer.hidden) setDrawer(false);
    });
  }

  /* ---------------------------------------------------------------------- */
  /* 3. Reveal on scroll                                                    */
  /* ---------------------------------------------------------------------- */

  var revealables = Array.prototype.slice.call(document.querySelectorAll('.reveal'));

  if (prefersReducedMotion || !('IntersectionObserver' in window)) {
    revealables.forEach(function (node) {
      node.classList.add('is-visible');
    });
  } else {
    var revealObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.classList.add('is-visible');
          revealObserver.unobserve(entry.target);
        });
      },
      { rootMargin: '0px 0px -8% 0px', threshold: 0.08 }
    );
    revealables.forEach(function (node) {
      revealObserver.observe(node);
    });
  }

  /* ---------------------------------------------------------------------- */
  /* 4. Risk explorer                                                       */
  /* ---------------------------------------------------------------------- */

  /* Derived from genesis/governance/policy.py and risk.py. The examples are the
     capability names actually declared in the registry, so the section cannot
     drift into describing behaviour the engine does not have without the pair
     failing a review. */
  var RISKS = {
    R0: {
      title: 'Read-only, or data you already own',
      rule: 'disposition: allow',
      body:
        'No state changes and nothing leaves your boundary. Reading the Mind’s own memory, ' +
        'running a reflection pass, or fetching public data. These run without asking, so a ' +
        'being does not need permission to think.',
      examples: ['search_memory', 'reflect_on_progress', 'search_web'],
      demo: {
        decision: 'allow',
        rows: [
          ['Action', 'search web'],
          ['Risk', 'R0'],
          ['Policy decision', 'allow'],
          ['Reason code', 'read_only_allowed'],
          ['Receipt', 'not required'],
        ],
      },
    },
    R1: {
      title: 'Reversible, inside the Mind’s own workspace',
      rule: 'disposition: allow_with_receipt',
      body:
        'It changes something, but only inside the Mind’s isolated workspace, and it can be ' +
        'undone. It runs — and a receipt is written, because "allowed" still has to be ' +
        'answerable later.',
      examples: ['add_memory', 'create_task', 'schedule_action', 'save_note'],
      demo: {
        decision: 'allow_with_receipt',
        rows: [
          ['Action', 'create task'],
          ['Risk', 'R1'],
          ['Policy decision', 'allow_with_receipt'],
          ['Reason code', 'reversible_internal_allowed'],
          ['Receipt', 'written'],
        ],
      },
    },
    R2: {
      title: 'Changes something outside the workspace',
      rule: 'disposition: require_approval',
      body:
        'It reaches outside the Mind’s own boundary. Approval is required, unless your ' +
        'organisation has explicitly pre-approved this named capability — a standing grant can ' +
        'cover recurring low-risk work, but it must name the capability.',
      examples: ['write to a shared file', 'update a third-party record'],
      demo: {
        decision: 'require_approval',
        rows: [
          ['Action', 'update shared record'],
          ['Risk', 'R2'],
          ['Policy decision', 'require_approval'],
          ['Reason code', 'external_change_requires_approval'],
          ['Standing grant', 'may apply if scoped'],
        ],
      },
    },
    R3: {
      title: 'External communication, deployment, purchase, admin',
      rule: 'disposition: require_approval — configuration cannot lower this',
      body:
        'Sending email, publishing, spending money, deploying, granting privilege, or deleting ' +
        'data. These are consequential and usually irreversible. No setting can auto-approve ' +
        'them; a human decision is always required.',
      examples: ['send_email', 'post_publicly', 'make_purchase', 'deploy_service', 'delete_data'],
      demo: {
        decision: 'require_approval',
        rows: [
          ['Action', 'send email'],
          ['Risk', 'R3'],
          ['Policy decision', 'require_approval'],
          ['Human required', 'no — owner or delegate'],
          ['Reversible', 'not reversible'],
        ],
      },
    },
    R4: {
      title: 'Legal, medical, financial, employment, safety, or physical',
      rule: 'disposition: require_approval — human approver only',
      body:
        'Regulated domains and anything with physical-world effect. A responsible human owner ' +
        'must approve, and the approval service refuses an approval whose actor is the Mind ' +
        'itself. This is the tier where "the agent decided" stops being an acceptable answer.',
      examples: ['give_medical_advice', 'give_legal_advice', 'actuate_robot'],
      demo: {
        decision: 'require_approval',
        rows: [
          ['Action', 'actuate robot'],
          ['Risk', 'R4'],
          ['Policy decision', 'require_approval'],
          ['Human required', 'yes'],
          ['Agent can approve', 'refused'],
        ],
      },
    },
    R5: {
      title: 'Prohibited',
      rule: 'disposition: deny, or emergency_stop',
      body:
        'Constitutionally disallowed: harming humans, modifying core constraints, disabling ' +
        'safety, hiding actions, malware, phishing. Denied outright — and if the attempt is ' +
        'catastrophic, the emergency stop latches and only a human can release it.',
      examples: ['harm_humans', 'bypass_safety', 'execute_exploit', 'spread_malware'],
      demo: {
        decision: 'emergency_stop',
        rows: [
          ['Action', 'bypass safety'],
          ['Risk', 'R5'],
          ['Policy decision', 'emergency_stop'],
          ['Reason code', 'constitution_prohibited'],
          ['Emergency stop', 'latched by policy'],
        ],
      },
    },
  };

  var riskDetail = document.getElementById('risk-detail');
  var riskDemo = document.getElementById('risk-demo');
  var riskTabs = Array.prototype.slice.call(document.querySelectorAll('.risk-tab'));

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, function (character) {
      return {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
      }[character];
    });
  }

  function renderRisk(level) {
    var data = RISKS[level];
    if (!data || !riskDetail || !riskDemo) return;

    riskDetail.style.setProperty('--risk-color', 'var(--risk-' + level.toLowerCase() + ')');

    riskDetail.innerHTML =
      '<h3><span class="risk-badge" data-risk="' + level + '">' + level + '</span>' +
      escapeHtml(data.title) + '</h3>' +
      '<p class="risk-rule">' + escapeHtml(data.rule) + '</p>' +
      '<p>' + escapeHtml(data.body) + '</p>' +
      '<p class="risk-disposition">→ ' + escapeHtml(data.demo.decision) + '</p>' +
      '<div class="risk-examples">' +
      data.examples
        .map(function (name) {
          return '<span>' + escapeHtml(name) + '</span>';
        })
        .join('') +
      '</div>';

    riskDemo.innerHTML =
      '<div class="demo-card"><div class="demo-head">' +
      '<span class="demo-title">Action receipt</span>' +
      '<span class="risk-badge" data-risk="' + level + '">' + level + '</span>' +
      '</div>' +
      data.demo.rows
        .map(function (row) {
          return (
            '<div class="demo-row"><span>' +
            escapeHtml(row[0]) +
            '</span><b>' +
            escapeHtml(row[1]) +
            '</b></div>'
          );
        })
        .join('') +
      '</div>';
  }

  riskTabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      riskTabs.forEach(function (other) {
        other.classList.remove('is-active');
        other.setAttribute('aria-selected', 'false');
      });
      tab.classList.add('is-active');
      tab.setAttribute('aria-selected', 'true');
      renderRisk(tab.getAttribute('data-risk'));
    });

    // Left/right arrows move between tiers, as a tablist should.
    tab.addEventListener('keydown', function (event) {
      if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return;
      var index = riskTabs.indexOf(tab);
      var next = event.key === 'ArrowRight' ? index + 1 : index - 1;
      if (next < 0) next = riskTabs.length - 1;
      if (next >= riskTabs.length) next = 0;
      riskTabs[next].click();
      riskTabs[next].focus();
    });
  });

  if (riskDetail) renderRisk('R0');

  /* ---------------------------------------------------------------------- */
  /* 5. Budget chart                                                        */
  /* ---------------------------------------------------------------------- */

  var budgetChart = document.querySelector('.budget-chart');
  if (budgetChart && 'IntersectionObserver' in window) {
    var chartObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.classList.add('is-visible');
          chartObserver.unobserve(entry.target);
        });
      },
      { threshold: 0.3 }
    );
    chartObserver.observe(budgetChart);
  } else if (budgetChart) {
    budgetChart.classList.add('is-visible');
  }

  /* ---------------------------------------------------------------------- */
  /* 6. Hash chain highlight                                                */
  /* ---------------------------------------------------------------------- */

  var chainRows = Array.prototype.slice.call(
    document.querySelectorAll('#chain-rows .chain-row')
  );

  if (chainRows.length && !prefersReducedMotion && 'IntersectionObserver' in window) {
    var chainIndex = 0;
    var chainTimer = null;

    var stepChain = function () {
      chainRows.forEach(function (row) {
        row.classList.remove('is-flash');
      });
      // Walk oldest -> newest, because that is the direction the chain is built.
      chainRows[chainRows.length - 1 - chainIndex].classList.add('is-flash');
      chainIndex = (chainIndex + 1) % chainRows.length;
    };

    var chainObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting && !chainTimer) {
            stepChain();
            chainTimer = window.setInterval(stepChain, 900);
          } else if (!entry.isIntersecting && chainTimer) {
            window.clearInterval(chainTimer);
            chainTimer = null;
          }
        });
      },
      { threshold: 0.25 }
    );

    var chainContainer = document.getElementById('chain-rows');
    if (chainContainer) chainObserver.observe(chainContainer);
  }

  /* ---------------------------------------------------------------------- */
  /* 7. Copy to clipboard                                                   */
  /* ---------------------------------------------------------------------- */

  var copyButton = document.getElementById('copy-install');
  var installCode = document.getElementById('install-code');

  if (copyButton && installCode) {
    copyButton.addEventListener('click', function () {
      var text = installCode.innerText;
      var done = function () {
        copyButton.textContent = 'Copied';
        copyButton.classList.add('is-done');
        window.setTimeout(function () {
          copyButton.textContent = 'Copy';
          copyButton.classList.remove('is-done');
        }, 1600);
      };
      var failed = function () {
        copyButton.textContent = 'Press Ctrl+C';
        window.setTimeout(function () {
          copyButton.textContent = 'Copy';
        }, 2200);
      };

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done).catch(failed);
        return;
      }

      // Fallback for non-secure contexts, where the async clipboard is blocked.
      try {
        var range = document.createRange();
        range.selectNodeContents(installCode);
        var selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        var ok = document.execCommand('copy');
        selection.removeAllRanges();
        ok ? done() : failed();
      } catch (error) {
        failed();
      }
    });
  }

  } /* end enhance() */
})();
