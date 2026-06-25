import sys, os
from datetime import datetime, timedelta
from time import time
import jwt
import requests
import base64


def format_api_error(response):
    try:
        payload = response.json()
    except ValueError:
        return None

    errors = payload.get("errors")
    if not isinstance(errors, list) or not errors:
        return None

    first_error = errors[0] if isinstance(errors[0], dict) else {}
    code = first_error.get("code")
    detail = first_error.get("detail")

    if code == "FORBIDDEN.REQUIRED_AGREEMENTS_MISSING_OR_EXPIRED":
        message = (
            "App Store Connect rejected the request because a required agreement is missing "
            "or expired for this account. Open App Store Connect -> Agreements, Tax, and Banking "
            "and accept any pending agreements, then rerun the workflow."
        )
        if detail:
            message += f" Apple detail: {detail}"
        return message

    title = first_error.get("title")
    parts = [part for part in [code, title, detail] if part]
    if parts:
        return " | ".join(parts)
    return None


def build_request_url(app_id, app_version=None, cursor=None):
    if cursor:
        return cursor

    query_params = [
        f"filter[app]={app_id}",
        "limit=200",
    ]
    if app_version:
        query_params.append(
            f"filter[preReleaseVersion.version]={requests.utils.quote(app_version)}"
        )
    return f"https://api.appstoreconnect.apple.com/v1/builds?{'&'.join(query_params)}"


def get_highest_build_version(request_headers, app_id, app_version=None):
    versions = []
    next_url = build_request_url(app_id, app_version=app_version)

    while next_url:
        response = requests.get(next_url, headers=request_headers)
        if response.status_code != 200:
            return None, response

        response_json = response.json()
        data = response_json.get("data", []) if isinstance(response_json, dict) else []
        for build in data:
            attributes = build.get("attributes", {})
            version = attributes.get("version")
            if version is not None:
                versions.append(version)

        links = response_json.get("links", {}) if isinstance(response_json, dict) else {}
        next_url = links.get("next")

    if not versions:
        return None, None

    numeric_versions = []
    for version in versions:
        try:
            numeric_versions.append(int(version))
        except (TypeError, ValueError):
            raise ValueError(f"Build version '{version}' is not an integer")

    return str(max(numeric_versions)), None


def main():
    output_path = os.environ.get('GITHUB_OUTPUT')

    if len(sys.argv) < 4:
        print("Usage: jwt_encode.py <base64_private_key> <key_id> <app_id> [app_version]")
        sys.exit(1)

    base64_private_key = sys.argv[1]
    key_id = sys.argv[2]
    app_id = sys.argv[3]
    app_version = None
    if len(sys.argv) >= 5 and sys.argv[4].strip() != "":
        app_version = sys.argv[4].strip()

    # Декодируем Base64 ключ
    try:
        private_key = base64.b64decode(base64_private_key)
    except Exception as e:
        print(f"Error decoding base64 key: {e}")
        sys.exit(1)

    dt = datetime.now() + timedelta(minutes=1)
    headers = {
        "alg": "ES256",
        "kid": key_id,
        "typ": "JWT",
    }
    payload = {
        "sub": "user",
        "iat": int(time()),
        "exp": int(dt.timestamp()),
        "aud": "appstoreconnect-v1",
    }

    try:
        gen_jwt = jwt.encode(payload, private_key, algorithm="ES256", headers=headers)
    except Exception as e:
        print(f"Error generating JWT: {e}")
        sys.exit(1)

    request_headers = {
        "Authorization": f"Bearer {gen_jwt}",
        "Content-Type": "application/json"
    }

    version, error_response = get_highest_build_version(
        request_headers,
        app_id,
        app_version=app_version,
    )

    if error_response is not None:
        formatted_error = format_api_error(error_response)
        try:
            error_body = error_response.text
        except Exception:
            error_body = "<no body>"
        if formatted_error:
            print(f"Error: {error_response.status_code}. {formatted_error}")
        print(f"Response body: {error_body}")
        sys.exit(1)

    try:
        if version is None:
            # Нет билдов по фильтрам — запишем безопасные значения и завершимся успешно
            print("No builds found for the specified app (and version filter, if provided).")
            if output_path:
                with open(output_path, 'a') as f:
                    f.write("last_build_number=0\n")
                    f.write("increment_last_build_number=1\n")
                    f.write("increment_last_build_number_plus=2\n")
            return

        print("Last build version is: " + version)
        if output_path:
            with open(output_path, 'a') as f:
                f.write(f"last_build_number={version}\n")
                f.write(f"increment_last_build_number={int(version) + 1}\n")
                f.write(f"increment_last_build_number_plus={int(version) + 2}\n")
    except (KeyError, IndexError, ValueError) as e:
        print(f"Error parsing response: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
