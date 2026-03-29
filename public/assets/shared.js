/**
 * サウジナビ 共通JavaScript
 * ハンバーガーメニュー、ドロップダウン、サイト内検索
 */
(function() {
  "use strict";

  // ===== HAMBURGER MENU =====
  var hamburger = document.getElementById('hamburger');
  var navLinks = document.getElementById('navLinks');

  if (hamburger && navLinks) {
    hamburger.addEventListener('click', function() {
      hamburger.classList.toggle('active');
      navLinks.classList.toggle('open');
    });
    navLinks.querySelectorAll('a').forEach(function(link) {
      link.addEventListener('click', function() {
        hamburger.classList.remove('active');
        navLinks.classList.remove('open');
      });
    });
  }

  // ===== NAV DROPDOWN (その他) =====
  var navMore = document.getElementById('navMore');
  var navMoreBtn = document.getElementById('navMoreBtn');
  if (navMore && navMoreBtn) {
    navMoreBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      navMore.classList.toggle('open');
    });
    document.addEventListener('click', function(e) {
      if (!navMore.contains(e.target)) {
        navMore.classList.remove('open');
      }
    });
  }

  // ===== SEARCH FUNCTIONALITY =====
  var searchToggle = document.getElementById('searchToggle');
  var searchToggleDesktop = document.getElementById('searchToggleDesktop');
  var searchBar = document.getElementById('searchBar');
  var searchInput = document.getElementById('searchInput');
  var searchClear = document.getElementById('searchClear');
  var searchResults = document.getElementById('searchResults');
  var searchResultsContent = document.getElementById('searchResultsContent');
  var searchResultsTitle = document.getElementById('searchResultsTitle');
  var searchResultsClose = document.getElementById('searchResultsClose');

  function openSearch() {
    if (!searchBar) return;
    searchBar.classList.add('open');
    if (searchInput) searchInput.focus();
    if (hamburger) hamburger.classList.remove('active');
    if (navLinks) navLinks.classList.remove('open');
  }

  function closeSearch() {
    if (!searchBar) return;
    searchBar.classList.remove('open');
    if (searchInput) searchInput.value = '';
    if (searchResults) searchResults.classList.remove('visible');
  }

  if (searchToggle) searchToggle.addEventListener('click', openSearch);
  if (searchToggleDesktop) searchToggleDesktop.addEventListener('click', openSearch);
  if (searchClear) searchClear.addEventListener('click', closeSearch);
  if (searchResultsClose) searchResultsClose.addEventListener('click', closeSearch);

  // Keyboard shortcuts
  document.addEventListener('keydown', function(e) {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      openSearch();
    }
    if (e.key === 'Escape') {
      closeSearch();
    }
  });

  // Search logic
  function esc(s) { var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

  if (searchInput && typeof SITE_SEARCH_INDEX !== 'undefined') {
    searchInput.addEventListener('input', function() {
      var q = searchInput.value.trim().toLowerCase();
      if (q.length < 1) {
        if (searchResults) searchResults.classList.remove('visible');
        return;
      }
      var words = q.split(/\s+/).filter(function(w) { return w.length > 0; });
      var matches = SITE_SEARCH_INDEX.filter(function(item) {
        var text = (item.title + ' ' + item.desc + ' ' + item.pageTitle).toLowerCase();
        return words.every(function(w) { return text.includes(w); });
      });
      if (searchResultsTitle) {
        searchResultsTitle.textContent = matches.length ? '検索結果 (' + matches.length + '件)' : '該当なし';
      }
      if (searchResultsContent) {
        searchResultsContent.innerHTML = matches.slice(0, 20).map(function(m) {
          return '<a href="' + esc(m.page) + '" class="sr-item"><div class="sr-page">' +
            esc(m.pageTitle) + '</div><div class="sr-title">' + esc(m.title) +
            '</div><div class="sr-desc">' + esc(m.desc) + '</div></a>';
        }).join('');
      }
      if (searchResults) searchResults.classList.add('visible');
    });
  }
})();
