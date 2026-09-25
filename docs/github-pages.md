# Balcony privacy screen – owners corporation approval page

A single self-contained web page (`index.html`) with an interactive 3D model, sizes,
materials, drawings and photos of the proposed balcony privacy screen and plant benches.
Everything is built into the file (3D library, model, images), so it needs no build step
and loads nothing from other websites.

## Put it on GitHub Pages

1. Create a new repository on GitHub (for example `balcony-screen`).
2. Upload `index.html` and `.nojekyll` to the root of the repository.
   `.nojekyll` tells GitHub Pages to publish the page as-is instead of running Jekyll.
   (Dotfiles can be hidden in file pickers: in the GitHub web uploader you can instead
   click **Add file > Create new file**, name it `.nojekyll`, and commit it empty.)
3. Go to **Settings > Pages**, set **Source** to *Deploy from a branch*, choose `main`
   and `/ (root)`, and save.
4. After a minute or two the page is live at `https://<your-username>.github.io/balcony-screen/`.

## Add images or update your details

1. Open `https://<your-username>.github.io/balcony-screen/#edit`
   (or open `index.html` directly from your computer or phone).
2. Click **Edit this page** at the bottom, add photos or drawings, captions and your details.
3. Click **Download updated page**. This saves a new `index.html` with everything built in.
4. In the repository, click `index.html` > **...** > **Upload files** (or drag the new file onto
   the repository page) to replace it, then commit. The live site updates within a few minutes;
   refresh with a hard reload if you still see the old version.

Visitors to the normal link don't see the edit option. Anyone who adds `#edit` can only change
their own downloaded copy, never the published site.

## Privacy

The page includes your name and the property address. A GitHub Pages site can be opened by
anyone who has (or guesses) the link. The page asks search engines not to index it, but
that is a request, not a lock. Remove any details you don't want public before uploading.
