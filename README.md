# Gothic II Classic Revived — GitHub Pages

Static, single-page GitHub Pages version of the Gothic II Classic Revived website.

## Required GitHub Actions secrets

Create both under **Settings → Secrets and variables → Actions → Repository secrets**:

- `YOUTUBE_API_KEY` — YouTube Data API v3 key used only during the build.
- `VPS_IMAGE_MANIFEST_URL` — private build-time URL used to discover the screenshots.

Neither secret is written into the published site.

## `VPS_IMAGE_MANIFEST_URL`

The variable name is kept as `VPS_IMAGE_MANIFEST_URL`, but the loader accepts three source formats so the same secret can point at whichever endpoint is practical on the VPS.

### 1. JSON manifest

```json
[
  "01-08-2026_12-30.jpg",
  "02-08-2026_18-45.jpg"
]
```

or:

```json
{
  "images": [
    "01-08-2026_12-30.jpg",
    "02-08-2026_18-45.jpg"
  ]
}
```

An object may optionally define `base_url`.

### 2. HTTP directory listing

The secret may point directly to a normal Apache/nginx directory index containing links to the image files. The builder extracts the image links automatically.

### 3. Plain-text manifest

A newline-separated list of image filenames/URLs is also accepted. Empty lines and lines starting with `#` are ignored.

Relative paths are resolved against the configured source URL. Image filenames must follow the existing `DD-MM-YYYY_HH-MM` convention, with an optional ` (N)` duplicate suffix.

## Fonts

The stylesheet expects these files in `site/font/`:

- `GothicII.ttf` — default/body text
- `GOTHIC3.TTF` — headings and titles
- `GOTHIC1.TTF` — links, captions, dates and media counters

## Styling

All site styling is in one file:

```text
site/styles/main.css
```

There are no separate page/gallery/video override stylesheets.

## GitHub Pages setup

1. Put the project contents at the repository root.
2. Put the three fonts above in `site/font/`.
3. Add `YOUTUBE_API_KEY` and `VPS_IMAGE_MANIFEST_URL` as repository secrets.
4. Push to `main`.
5. In **Settings → Pages → Build and deployment → Source**, choose **GitHub Actions**.
6. Run the workflow manually or let the push trigger it.

No `gh-pages` branch is required.

## Media build

The build downloads source images temporarily and produces:

- gallery previews: maximum width 1920 px, WebP quality 82
- thumbnails: maximum width 400 px, WebP quality 78

Full originals are not included in the Pages artifact. The public `images.json` contains only generated Pages paths and display metadata, never the source URL.

## Single-page navigation

The public site uses only `site/index.html`. Main, Images and Videos are sections of that document. JavaScript switches between them without changing the URL, hash, query string, or browser history.

If a visitor explicitly arrives through `/index.html`, the frontend canonicalizes that once to the containing directory. Reloading always returns to Main by design.

## Automatic refresh

The workflow runs on pushes to `main`, manually through `workflow_dispatch`, and every six hours. Every run creates a clean `_site/` deployment.
