"use strict";

document.addEventListener("DOMContentLoaded", async () => {
    const imageCounter = document.querySelector(".count.images");
    const videoCounter = document.querySelector(".count.videos");

    const [images, videos] = await Promise.allSettled([
        loadJson("./data/images.json"),
        loadJson("./data/videos.json"),
    ]);

    imageCounter.textContent = images.status === "fulfilled" && Array.isArray(images.value)
        ? String(images.value.length)
        : "?";

    videoCounter.textContent = videos.status === "fulfilled" && Array.isArray(videos.value)
        ? String(videos.value.length)
        : "?";
});
