"use strict";

const PAGE_TITLES = {
    main: "Gothic II Classic Revived",
    images: "G2ClassicRevived Images",
    videos: "G2ClassicRevived Videos",
};

function canonicalizeIndexUrl() {
    if (!window.history?.replaceState) return;

    const path = window.location.pathname;
    if (!path.endsWith("/index.html")) return;

    const cleanPath = path.slice(0, -"index.html".length);
    window.history.replaceState(null, "", `${cleanPath}${window.location.search}`);
}

function showSitePage(name) {
    const target = document.querySelector(`.site-page[data-page="${name}"]`);
    if (!target) return;

    document.querySelectorAll(".site-page").forEach((page) => {
        const active = page === target;
        page.hidden = !active;
        page.classList.toggle("is-active", active);
        page.setAttribute("aria-hidden", active ? "false" : "true");
    });

    document.querySelectorAll("[data-show-page]").forEach((control) => {
        control.classList.toggle("is-active", control.dataset.showPage === name);
    });

    document.title = PAGE_TITLES[name] || PAGE_TITLES.main;
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });

    document.dispatchEvent(new CustomEvent("sitepagechange", {
        detail: { page: name },
    }));
}

document.addEventListener("DOMContentLoaded", () => {
    canonicalizeIndexUrl();

    document.querySelectorAll("[data-show-page]").forEach((control) => {
        control.addEventListener("click", () => {
            showSitePage(control.dataset.showPage);
        });
    });

    // Main is always the initial state. Page state is deliberately not encoded
    // into the URL, hash, query string, or browser history.
    showSitePage("main");
});
