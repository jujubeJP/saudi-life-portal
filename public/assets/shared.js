/**
 * サウジナビ 共通JavaScript
 * ハンバーガーメニュー、ドロップダウン
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

})();
