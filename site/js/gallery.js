"use strict";

const galleryRoot = document.getElementById("gallery-root");
const lightbox = document.getElementById("lightbox");
const lightboxImg = document.getElementById("lightbox-img");
const lightboxCaption = document.getElementById("lightbox-caption");
const lightboxClose = document.getElementById("lightbox-close");
let galleryLoaded = false;
let galleryLoading = false;

function openLightbox(image) {
    lightboxImg.src = image.preview || image.thumbnail;
    lightboxImg.alt = image.caption;
    lightboxCaption.replaceChildren();

    const captionText = document.createElement("span");
    captionText.textContent = image.caption;
    lightboxCaption.append(captionText);

    lightbox.classList.add("visible");
    lightbox.setAttribute("aria-hidden", "false");
    document.body.classList.add("lightbox-open");
    lightboxClose.focus();
}

function closeLightbox() {
    lightbox.classList.remove("visible");
    lightbox.setAttribute("aria-hidden", "true");
    document.body.classList.remove("lightbox-open");
    window.setTimeout(() => {
        lightboxImg.src = "";
        lightboxImg.alt = "";
        lightboxCaption.replaceChildren();
    }, 300);
}

function makeGalleryItem(image) {
    const item = document.createElement("div");
    item.className = "gallery-item";
    item.tabIndex = 0;
    item.setAttribute("role", "button");
    item.setAttribute("aria-label", `Open ${image.caption}`);
    item.addEventListener("click", () => openLightbox(image));
    item.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            openLightbox(image);
        }
    });

    const img = document.createElement("img");
    img.src = image.thumbnail;
    img.alt = image.caption;
    img.loading = "lazy";
    img.decoding = "async";

    const caption = document.createElement("div");
    caption.className = "caption";
    caption.textContent = image.caption;

    item.append(img, caption);
    return item;
}

function renderGallery(images) {
    galleryRoot.replaceChildren();

    if (!images.length) {
        const empty = document.createElement("p");
        empty.className = "status-message";
        empty.textContent = "No screenshots were found in the generated gallery manifest.";
        galleryRoot.append(empty);
        return;
    }

    const groups = new Map();
    for (const image of images) {
        const key = image.month || "Unknown date";
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(image);
    }

    for (const [month, monthImages] of groups) {
        const heading = document.createElement("h2");
        heading.textContent = month;
        heading.className = "month-heading";

        const grid = document.createElement("div");
        grid.className = "image-gallery";
        for (const image of monthImages) {
            grid.append(makeGalleryItem(image));
        }

        galleryRoot.append(heading, grid);
    }
}

async function ensureGalleryLoaded() {
    if (galleryLoaded || galleryLoading) return;
    galleryLoading = true;

    try {
        const images = await loadJson("./data/images.json");
        renderGallery(Array.isArray(images) ? images : []);
        galleryLoaded = true;
    } catch (error) {
        console.error(error);
        galleryRoot.innerHTML = "<p class='status-message error'>Failed to load the screenshot gallery.</p>";
    } finally {
        galleryLoading = false;
    }
}

document.addEventListener("sitepagechange", (event) => {
    if (event.detail?.page === "images") {
        ensureGalleryLoaded();
    } else if (lightbox.classList.contains("visible")) {
        closeLightbox();
    }
});

lightboxClose.addEventListener("click", closeLightbox);
lightbox.addEventListener("click", (event) => {
    if (event.target === lightbox) closeLightbox();
});
document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && lightbox.classList.contains("visible")) {
        closeLightbox();
    }
});
