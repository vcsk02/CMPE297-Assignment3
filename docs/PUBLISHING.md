# Publish the repository and YouTube walkthrough

The finished source, execution evidence, narrated MP4, subtitles and documentation are
included. Publication requires your own authorized GitHub account and YouTube channel.
This delivery does not claim an external URL that has not actually been created.

## GitHub

Install [GitHub CLI](https://cli.github.com/) and authenticate locally with `gh auth login`.
From the repository root, run one of:

```bash
bash scripts/publish_github.sh adk-agent-suite --private
# Or for a publicly readable submission:
bash scripts/publish_github.sh adk-agent-suite --public
```

PowerShell:

```powershell
./scripts/publish_github.ps1 -RepoName adk-agent-suite
# Or: ./scripts/publish_github.ps1 -RepoName adk-agent-suite -Public
```

The script uses your Git identity, commits only if there are staged changes, creates
the repository if no `origin` exists, pushes, and prints the actual URL. If `origin`
already exists, verify it with `git remote -v` before running; the script pushes there.
If your desired name is already taken, choose another name rather than replacing an
existing repository. The MP4 is compressed for direct inclusion; if a regenerated
video exceeds GitHub's single-file limit, put it in a GitHub Release or use Git LFS.

GitHub Actions runs after the push. Confirm its checks before submitting. For private
repositories, grant your instructor access or choose public visibility as required.

## YouTube

### Upload the included file manually

1. Open [YouTube Studio](https://studio.youtube.com/) in the intended channel.
2. Upload `video/adk-agent-suite-walkthrough.mp4`.
3. Use the title and description in `video/youtube-metadata.json`.
4. Add `video/walkthrough.srt` as English subtitles. Copy the chapter timestamps from
   `video/CHAPTERS.md` into the description.
5. Select the appropriate audience/content settings. The video uses disclosed synthetic
   narration and code/terminal visuals; review the actual video against the platform's
   current disclosure prompts.
6. Choose Unlisted if your instructor should access it by link, then copy the actual URL.
7. Add that URL to the README and your submission after the upload succeeds.

### Upload using the provided OAuth helper

Enable YouTube Data API v3 in your Google Cloud project. Create a Desktop OAuth client,
download its client JSON locally, and keep it outside the repository. Configure the
OAuth consent screen/test user as required by your project's publication state.

```bash
uv sync --frozen --extra youtube
uv run --extra youtube python scripts/upload_youtube.py \
  --client-secrets /absolute/path/to/client_secret.json --whoami
```

The helper opens a local browser for Google OAuth and prints channel IDs/titles. Then:

```bash
uv run --extra youtube python scripts/upload_youtube.py \
  --client-secrets /absolute/path/to/client_secret.json \
  --channel-id YOUR_VERIFIED_CHANNEL_ID --privacy unlisted
```

It verifies that the selected OAuth account owns the expected channel, uploads the MP4,
and writes the returned ID and real URL to `video/published.json`. The default privacy
is private; unlisted is explicit above. OAuth credentials stay in memory, not in the
repository. Your API project may restrict upload visibility pending verification/audit;
check the official API response and YouTube Studio instead of assuming publication.
The helper does not automatically upload captions; add the supplied SRT in Studio.

After a successful upload, add the actual URL to README, commit the metadata receipt,
and push again. Include both URLs in your assignment submission. Never paste example
GitHub/YouTube URLs as though they were your completed submission.

## Rebuild the video

Install FFmpeg with the `flite` speech filter, then:

```bash
uv sync --frozen --extra video
uv run agent-suite demo
uv run --extra video python scripts/render_video.py
```

The renderer uses the actual repository code and current artifact outputs. Scene
narration lives in `video/scenes.json`. It generates the MP4, transcript, subtitles,
chapter timestamps and YouTube metadata. Inspect the result before uploading.
