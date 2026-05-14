from __future__ import annotations

import argparse
from pprint import pprint
import time

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate Omi voice/chat commands against the Codex bridge.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8766")
    parser.add_argument("--token", default="dev-token-change-me")
    parser.add_argument("--uid", default="practice-user")
    parser.add_argument("--run", action="store_true", help="Start the queued job through the bridge API.")
    args = parser.parse_args()

    base = f"/omi/{args.token}"
    transcript_payload = [
        {
            "text": "Hey Omi Codex build a tiny smoke test feature and summarize what changed",
            "speaker": "SPEAKER_00",
            "speakerId": 0,
            "is_user": True,
            "start": 0,
            "end": 5,
        }
    ]

    with httpx.Client(base_url=args.base_url, timeout=30) as client:
        print("Health")
        pprint(client.get("/health").json())

        print("\nManifest tools")
        manifest = client.get(f"{base}/.well-known/omi-tools.json")
        print(manifest.status_code)
        pprint([tool["name"] for tool in manifest.json()["tools"]])

        print("\nBridge status tool")
        response = client.post(
            f"{base}/tools/check_bridge_status",
            json={"uid": args.uid, "app_id": "omi_codex_bridge", "tool_name": "check_bridge_status"},
        )
        print(response.status_code)
        pprint(response.json())

        print("\nRealtime voice command")
        response = client.post(f"{base}/webhooks/realtime", params={"uid": args.uid, "session_id": "sim-codex-1"}, json=transcript_payload)
        print(response.status_code)
        payload = response.json()
        pprint(payload)
        job_id = payload.get("job_id")

        print("\nChat tool command")
        response = client.post(
            f"{base}/tools/start_codex_task",
            json={
                "uid": args.uid,
                "app_id": "omi_codex_bridge",
                "tool_name": "start_codex_task",
                "prompt": "Create a concise implementation plan for improving this project",
            },
        )
        print(response.status_code)
        pprint(response.json())

        print("\nList jobs tool")
        response = client.post(
            f"{base}/tools/list_codex_jobs",
            json={"uid": args.uid, "app_id": "omi_codex_bridge", "tool_name": "list_codex_jobs", "limit": 5},
        )
        print(response.status_code)
        pprint(response.json())

        if args.run and job_id:
            print(f"\nRun {job_id}")
            pprint(
                client.post(
                    f"{base}/tools/run_codex_job",
                    json={"uid": args.uid, "app_id": "omi_codex_bridge", "tool_name": "run_codex_job", "job_id": job_id},
                ).json()
            )
            for _ in range(60):
                job = client.get(f"{base}/api/jobs/{job_id}").json()["job"]
                if job["status"] not in {"pending", "running"}:
                    break
                time.sleep(1)
            pprint(job)
            print("\nOutput tool")
            pprint(
                client.post(
                    f"{base}/tools/get_codex_job_output",
                    json={
                        "uid": args.uid,
                        "app_id": "omi_codex_bridge",
                        "tool_name": "get_codex_job_output",
                        "job_id": job_id,
                    },
                ).json()
            )

        print("\nJobs")
        pprint(client.get(f"{base}/api/jobs").json())

        print("\nEvents")
        pprint(client.get(f"{base}/api/events").json())


if __name__ == "__main__":
    main()
