/**
 * helix.js — Helix AI client-side scripts
 *
 * Responsibilities (Milestone 1):
 *  1. Sidebar toggle — mobile open/close + desktop collapse
 *  2. Password visibility toggle
 *  3. Password strength meter (register page)
 *  4. Password match validation (register page)
 *  5. Auto-dismiss flash alerts
 *  6. Active nav link highlighting (fallback for Jinja active class)
 *
 * Future milestones will add:
 *  - Chart.js vitals trend charts (Milestone 3)
 *  - AJAX chat polling for AI Health Companion (Milestone 6)
 *  - Health Score ring animation (Milestone 4)
 *  - Real-time form validation helpers (Milestone 3)
 */

"use strict";

document.addEventListener("DOMContentLoaded", () => {

  // ===========================================================================
  // 1. Sidebar toggle
  // ===========================================================================
  const sidebar         = document.getElementById("helix-sidebar");
  const mobileToggle    = document.getElementById("sidebar-toggle");     // mobile hamburger
  const desktopToggle   = document.getElementById("topbar-toggle");      // desktop collapse
  const backdrop        = document.getElementById("sidebar-backdrop");

  function openSidebar() {
    if (!sidebar) return;
    sidebar.classList.add("open");
    backdrop && backdrop.classList.remove("d-none");
    document.body.style.overflow = "hidden";
  }

  function closeSidebar() {
    if (!sidebar) return;
    sidebar.classList.remove("open");
    backdrop && backdrop.classList.add("d-none");
    document.body.style.overflow = "";
  }

  function toggleDesktopSidebar() {
    if (!sidebar) return;
    const main = document.querySelector(".helix-main");
    sidebar.classList.toggle("collapsed");
    main && main.classList.toggle("sidebar-collapsed");
  }

  mobileToggle  && mobileToggle.addEventListener("click",  openSidebar);
  backdrop      && backdrop.addEventListener("click",       closeSidebar);
  desktopToggle && desktopToggle.addEventListener("click",  toggleDesktopSidebar);

  // Close sidebar on mobile when a nav link is tapped
  if (sidebar) {
    sidebar.querySelectorAll(".nav-link").forEach((link) => {
      link.addEventListener("click", () => {
        if (window.innerWidth < 768) closeSidebar();
      });
    });
  }

  // ===========================================================================
  // 2. Password visibility toggle
  // ===========================================================================
  document.querySelectorAll(".toggle-password").forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = btn.dataset.target;
      const input    = document.getElementById(targetId);
      const icon     = btn.querySelector("i");
      if (!input) return;

      if (input.type === "password") {
        input.type = "text";
        icon && icon.classList.replace("bi-eye", "bi-eye-slash");
      } else {
        input.type = "password";
        icon && icon.classList.replace("bi-eye-slash", "bi-eye");
      }
    });
  });

  // ===========================================================================
  // 3. Password strength meter (register page)
  // ===========================================================================
  const passwordInput   = document.getElementById("password");
  const strengthBar     = document.getElementById("password-strength");
  const strengthFill    = document.getElementById("strength-fill");
  const strengthLabel   = document.getElementById("strength-label");

  if (passwordInput && strengthBar && strengthFill && strengthLabel) {
    passwordInput.addEventListener("input", () => {
      const val = passwordInput.value;
      strengthBar.classList.remove("d-none");

      let score = 0;
      if (val.length >= 8)              score++;
      if (val.length >= 12)             score++;
      if (/[A-Z]/.test(val))            score++;
      if (/[0-9]/.test(val))            score++;
      if (/[^A-Za-z0-9]/.test(val))     score++;

      const levels = [
        { pct: "20%",  color: "#ef4444", label: "Very weak"  },
        { pct: "40%",  color: "#f97316", label: "Weak"       },
        { pct: "60%",  color: "#eab308", label: "Fair"       },
        { pct: "80%",  color: "#22c55e", label: "Good"       },
        { pct: "100%", color: "#15803d", label: "Strong"     },
      ];

      const level = levels[Math.max(0, score - 1)] || levels[0];
      strengthFill.style.width           = val.length ? level.pct : "0%";
      strengthFill.style.backgroundColor = level.color;
      strengthLabel.textContent          = val.length ? level.label : "";
      strengthLabel.style.color          = level.color;
    });
  }

  // ===========================================================================
  // 4. Password match validation (register page)
  // ===========================================================================
  const confirmInput  = document.getElementById("confirm_password");
  const mismatchMsg   = document.getElementById("password-mismatch");

  if (passwordInput && confirmInput && mismatchMsg) {
    function checkMatch() {
      if (confirmInput.value && passwordInput.value !== confirmInput.value) {
        mismatchMsg.classList.remove("d-none");
        confirmInput.classList.add("is-invalid");
      } else {
        mismatchMsg.classList.add("d-none");
        confirmInput.classList.remove("is-invalid");
      }
    }
    confirmInput.addEventListener("input",  checkMatch);
    passwordInput.addEventListener("input", checkMatch);
  }

  // ===========================================================================
  // 5. Auto-dismiss flash alerts after 5 seconds
  // ===========================================================================
  document.querySelectorAll(".flash-container .alert, .auth-flash-container .alert").forEach((alert) => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      bsAlert && bsAlert.close();
    }, 5000);
  });

  // ===========================================================================
  // 6. Active nav link highlighting (JS fallback)
  //    Jinja sets the `active` class server-side; this adds `aria-current` for
  //    screen readers and ensures the active link is scrolled into view.
  // ===========================================================================
  const activeLink = document.querySelector(".sidebar-nav .nav-link.active");
  if (activeLink) {
    activeLink.setAttribute("aria-current", "page");
    activeLink.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }

  // ===========================================================================
  // Future Milestone 3 — Chart.js vitals trend charts
  // TODO: Import Chart.js and initialise line charts for:
  //       blood pressure, blood glucose, heart rate, weight
  // ===========================================================================

  // ===========================================================================
  // Future Milestone 4 — Animate Health Score ring
  // TODO: Read the data-score attribute from .score-fill and tween
  //       stroke-dashoffset to match the score (0-100 mapped to 0-326.73)
  // ===========================================================================

  // ===========================================================================
  // Future Milestone 6 — AI Health Companion chat AJAX
  // TODO: Listen for form submit on #companion-form,
  //       POST to /companion/message, append response to the chat thread,
  //       and scroll the thread to the bottom.
  // ===========================================================================

});
