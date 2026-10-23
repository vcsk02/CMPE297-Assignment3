"""Upload only to an explicitly verified channel using the caller's local OAuth consent."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-secrets", required=True)
    parser.add_argument("--whoami", action="store_true")
    parser.add_argument("--channel-id")
    parser.add_argument("--privacy", choices=["private", "unlisted", "public"], default="private")
    parser.add_argument("--video", default="video/adk-agent-suite-walkthrough.mp4")
    args = parser.parse_args()
    if not args.whoami and not args.channel_id:
        parser.error("--channel-id is required for upload; use --whoami to inspect your channel")
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    credentials = InstalledAppFlow.from_client_secrets_file(
        args.client_secrets,
        scopes=[
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.readonly",
        ],
    ).run_local_server(port=0)
    service = build("youtube", "v3", credentials=credentials)
    channels = service.channels().list(part="id,snippet", mine=True).execute().get("items", [])
    identities = [{"id": item["id"], "title": item["snippet"]["title"]} for item in channels]
    if args.whoami:
        print(json.dumps(identities, indent=2))
        return
    if args.channel_id not in {item["id"] for item in identities}:
        raise ValueError("OAuth account does not own the expected channel; nothing uploaded")
    video = Path(args.video)
    if not video.is_file():
        raise FileNotFoundError(video)
    metadata = json.loads(Path("video/youtube-metadata.json").read_text())
    request = service.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": metadata["title"],
                "description": metadata["description"],
                "tags": metadata["tags"],
                "categoryId": "28",
            },
            "status": {"privacyStatus": args.privacy, "selfDeclaredMadeForKids": False},
        },
        media_body=MediaFileUpload(str(video), mimetype="video/mp4", resumable=True),
    )
    response = None
    while response is None:
        progress, response = request.next_chunk()
        if progress:
            print(f"Uploaded {progress.progress():.0%}")
    if response.get("snippet", {}).get("channelId") not in {None, args.channel_id}:
        raise RuntimeError("Unexpected channel in upload response; inspect YouTube Studio")
    receipt = {
        "video_id": response["id"],
        "url": "https://www.youtube.com/watch?v=" + response["id"],
        "channel_id": args.channel_id,
        "requested_privacy": args.privacy,
        "returned_status": response.get("status", {}),
    }
    Path("video/published.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["url"])


if __name__ == "__main__":
    main()
