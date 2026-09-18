(function () {
  "use strict";

  var storageKey = "feed-form-flow-theme";
  var choices = ["system", "light", "dark"];
  var media = window.matchMedia("(prefers-color-scheme: dark)");
  var preference = "system";

  try {
    var saved = window.localStorage.getItem(storageKey);
    if (choices.indexOf(saved) !== -1) preference = saved;
  } catch (error) {
    preference = "system";
  }

  function resolvedTheme() {
    if (preference === "system") return media.matches ? "dark" : "light";
    return preference;
  }

  function applyTheme() {
    document.documentElement.dataset.theme = resolvedTheme();
    document.documentElement.dataset.themePreference = preference;

    document.querySelectorAll("[data-theme-choice]").forEach(function (button) {
      button.setAttribute(
        "aria-pressed",
        String(button.dataset.themeChoice === preference)
      );
    });
  }

  function closeThemeMenus(returnFocus) {
    document.querySelectorAll(".fff-theme-menu").forEach(function (menu) {
      var trigger = menu.querySelector(".fff-theme-trigger");
      var control = menu.querySelector(".fff-theme-control");
      if (!trigger || !control || control.hidden) return;
      control.hidden = true;
      trigger.setAttribute("aria-expanded", "false");
      if (returnFocus) trigger.focus();
    });
  }

  function chooseTheme(choice) {
    if (choices.indexOf(choice) === -1) return;
    preference = choice;
    try {
      window.localStorage.setItem(storageKey, choice);
    } catch (error) {
      // The theme still applies for this page when storage is unavailable.
    }
    applyTheme();
    closeThemeMenus(false);
  }

  applyTheme();

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".fff-theme-menu").forEach(function (menu) {
      var trigger = menu.querySelector(".fff-theme-trigger");
      var control = menu.querySelector(".fff-theme-control");
      if (!trigger || !control) return;

      trigger.addEventListener("click", function () {
        var willOpen = control.hidden;
        closeThemeMenus(false);
        control.hidden = !willOpen;
        trigger.setAttribute("aria-expanded", String(willOpen));
        if (willOpen) {
          var selected = control.querySelector('[aria-pressed="true"]');
          if (selected) selected.focus();
        }
      });
    });

    document.querySelectorAll("[data-theme-choice]").forEach(function (button) {
      button.addEventListener("click", function () {
        chooseTheme(button.dataset.themeChoice);
      });
    });

    document.addEventListener("click", function (event) {
      if (!event.target.closest(".fff-theme-menu")) closeThemeMenus(false);
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closeThemeMenus(true);
    });

    applyTheme();
  });

  function followSystemTheme() {
    if (preference === "system") applyTheme();
  }

  if (media.addEventListener) media.addEventListener("change", followSystemTheme);
  else media.addListener(followSystemTheme);
})();
