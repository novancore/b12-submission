import os
import json
import hmac
import hashlib
import sys
from datetime import datetime, timezone

import urllib.request
import urllib.error


def iso8601_timestamp() -> str:
    now = datetime.now(timezone.utc)
    # Format with milliseconds and a trailing Z
    return now.replace(microsecond=(now.microsecond // 1000) * 1000).isoformat().replace("+00:00", "Z")


def build_payload() -> dict:
    return {
        "timestamp": iso8601_timestamp(),
        "name": os.environ.get("B12_NAME", "Donovan Piper"),
        "email": os.environ.get("B12_EMAIL", "do.piper.eng@outlook.com"),
        "resume_link": os.environ.get("B12_RESUME_LINK", "https://donovan-piper.netlify.app/"),
        "repository_link": os.environ.get("B12_REPOSITORY_LINK", "https://github.com/novancore"),
        "action_run_link": os.environ["B12_ACTION_RUN_LINK"],
    }


def compute_signature(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def main() -> None:
    secret = os.environ.get("B12_SIGNING_SECRET")
    if not secret:
        print("Missing B12_SIGNING_SECRET", file=sys.stderr)
        sys.exit(1)

    try:
        payload = build_payload()
    except KeyError as e:
        print(f"Missing required environment variable: {e}", file=sys.stderr)
        sys.exit(1)

    # Compact, sorted, UTF-8 JSON
    body_str = json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    body_bytes = body_str.encode("utf-8")

    signature = compute_signature(secret, body_bytes)

    req = urllib.request.Request(
        url="https://b12.io/apply/submission",
        data=body_bytes,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "X-Signature-256": signature,
        },
    )

    try:
        with urllib.request.urlopen(req) as resp:
            resp_body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(f"HTTP error: {e.code} {e.reason}", file=sys.stderr)
        try:
            print(e.read().decode("utf-8"), file=sys.stderr)
        except Exception:
            pass
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        parsed = json.loads(resp_body)
    except json.JSONDecodeError:
        print("Invalid JSON response from server", file=sys.stderr)
        print(resp_body, file=sys.stderr)
        sys.exit(1)

    if parsed.get("success") is True and "receipt" in parsed:
        receipt = parsed["receipt"]
        # Print the receipt so you can copy it later
        print(f"Submission receipt: {receipt}")
        sys.exit(0)
    else:
        print("Submission failed or unexpected response", file=sys.stderr)
        print(resp_body, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()