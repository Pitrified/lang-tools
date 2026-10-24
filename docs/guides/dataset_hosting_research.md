# Hosting Large Static Datasets via GitHub Releases

When a static file (like a word database) exceeds 50MB, standard frontend hosts (Vercel, Netlify, GitHub Pages) often fail or penalize your build times. Additionally, **Git LFS has a strict 1 GB free monthly bandwidth cap**, which can be exhausted by just a few users downloading a 200MB file.

Using **GitHub Releases** bypasses these limits entirely, keeping repository sizes light while providing predictable, fast, and free downloads.

---

## 1. Free Hosting Options Comparison

| Option | Free Storage Limit | Monthly Bandwidth | Best For | Pros & Cons |
| --- | --- | --- | --- | --- |
| **GitHub Releases** | 2 GB per file | Unlimited (reasonable use) | Open-source or public app assets. | **Pros:** No CC required; built-in versioning.<br>

<br>**Cons:** Asset files must be public. |
| **Cloudflare R2** | 10 GB | **Unlimited ($0 Egress)** | Production apps needing a global CDN. | **Pros:** Zero bandwidth fees; S3 API compatible.<br>

<br>**Cons:** Requires a Credit Card for identity verification. |
| **Hugging Face** | 10 GB+ | Unlimited | Structured data (JSON, CSV, SQLite). | **Pros:** Designed for large assets; great web UI.<br>

<br>**Cons:** Public by default; requires tokens for private data. |
| **Backblaze B2** | 10 GB | 30 GB / month | Simple cloud object storage. | **Pros:** Completely free up to 10GB; S3 compatible.<br>

<br>**Cons:** Strictly capped bandwidth (~150 downloads/mo for 200MB). |

---

## 2. Managing Releases via GitHub CLI (`gh`)

The official GitHub CLI is the fastest way to interact with your releases programmatically from your local terminal. Make sure you are authenticated using `gh auth login`.

### Create a Brand New Release & Upload the File

To create a new release container and push your curated file straight from your computer:

```bash
gh release create v1.0.0 ./path/to/your/dataset.json --title "Dataset v1.0.0" --notes "Initial word database release."
```

### Update an Existing Release (The Overwrite/"Clobber" Trick)

If you want to update your database file without creating a new tag or changing the download URL, upload it to the existing release and use the `--clobber` flag to overwrite the old asset:

```bash
gh release upload v1.0.0 ./path/to/your/dataset.json --clobber
```

---

## 3. Removing a Release and its Git Tag

If you need to completely wipe out a release and remove its underlying Git historical marker (the tag), run this command in your terminal:

```bash
gh release delete v1.0.0 --cleanup-tag -y
```

* **`--cleanup-tag`**: Deletes both the release container *and* the Git tag from GitHub.
* **`-y`**: Skips the interactive "Are you sure?" confirmation prompt, making it suitable for automated scripts.

---

## 4. The Permanent Download URL

GitHub generates a predictable public URL for every release asset.

### URL Structure:

```text
https://github.com/[USERNAME_OR_ORG]/[REPO_NAME]/releases/download/[TAG_NAME]/[FILE_NAME]
```

### Real-World Example:

If your username is `worddev`, your repository is `word-db`, your release tag is `v1.0.0`, and your file is `dataset.json`, the exact public link is:

```text
https://github.com/worddev/word-db/releases/download/v1.0.0/dataset.json
```

> 💡 **Architectural Advantage:** If you use the `--clobber` command shown in Section 2, you can update your file under the same `v1.0.0` tag endlessly. The URL never changes, meaning you can safely hardcode it into your applications without fearing broken links when data updates.

---

## 5. Critical Best Practices for Migrating from Git LFS

Because you are moving away from Git LFS to stop hitting your monthly bandwidth cap, you **must** safely purge the old file out of your Git history, or your repository will remain bloated.

### Step 1: Untrack the file from LFS

Stop Git LFS from watching your database file:

```bash
git lfs untrack "path/to/your/dataset.json"
```

### Step 2: Update your `.gitignore`

Add your local dataset to your `.gitignore` so your terminal never accidentally tries to upload it to the main repository code again:

```text
# .gitignore
path/to/your/dataset.json
```

### Step 3: Clear Client-Side Cache (For your App's Users)

Your code should check if the database exists locally first; if it does, load it instantly from local storage, and only hit the GitHub Release URL if a user forces a manual refresh.
