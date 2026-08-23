"use strict";

document.addEventListener("DOMContentLoaded", () => {
    const year = String(new Date().getFullYear());
    document.querySelectorAll("[data-current-year]").forEach((node) => {
        node.textContent = year;
    });
});

async function loadJson(path) {
    const response = await fetch(path, { cache: "no-cache" });
    if (!response.ok) {
        throw new Error(`HTTP ${response.status} while loading ${path}`);
    }
    return response.json();
}
