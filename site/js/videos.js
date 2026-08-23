"use strict";

const videoGallery = document.getElementById("video-gallery");
let videosLoaded = false;
let videosLoading = false;

function renderVideos(videos) {
    videoGallery.replaceChildren();

    if (!videos.length) {
        const empty = document.createElement("p");
        empty.className = "status-message";
        empty.textContent = "No videos are present in the generated video manifest.";
        videoGallery.append(empty);
        return;
    }

    for (const video of videos) {
        const item = document.createElement("div");
        item.className = "video-item";

        const frame = document.createElement("iframe");
        frame.src = `https://www.youtube.com/embed/${encodeURIComponent(video.id)}`;
        frame.title = video.title || video.date || "Gothic II Classic Revived video";
        frame.loading = "lazy";
        frame.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
        frame.allowFullscreen = true;
        frame.referrerPolicy = "strict-origin-when-cross-origin";

        const caption = document.createElement("div");
        caption.className = "caption";
        caption.textContent = video.date;

        item.append(frame, caption);
        videoGallery.append(item);
    }
}

async function ensureVideosLoaded() {
    if (videosLoaded || videosLoading) return;
    videosLoading = true;

    try {
        const videos = await loadJson("./data/videos.json");
        renderVideos(Array.isArray(videos) ? videos : []);
        videosLoaded = true;
    } catch (error) {
        console.error(error);
        videoGallery.innerHTML = "<p class='status-message error'>Failed to load the video gallery.</p>";
    } finally {
        videosLoading = false;
    }
}

document.addEventListener("sitepagechange", (event) => {
    if (event.detail?.page === "videos") {
        ensureVideosLoaded();
    }
});
