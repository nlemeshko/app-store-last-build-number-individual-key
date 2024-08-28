import sys, os
from datetime import datetime, timedelta
from time import time
import jwt
import requests
import base64

def main():
    output_path = os.environ.get('GITHUB_OUTPUT')

    if len(sys.argv) != 4:
        print("Usage: jwt_encode.py <base64_private_key> <key_id> <app_id>")
        sys.exit(1)

    base64_private_key = sys.argv[1]
    key_id = sys.argv[2]
    app_id = sys.argv[3]

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

    url = f"https://api.appstoreconnect.apple.com/v1/builds?filter[app]={app_id}&limit=1"
    r = requests.get(url, headers=request_headers)

    if r.status_code != 200:
        print(f"Error: {r.status_code}")
        sys.exit(1)

    try:
        response_json = r.json()
        version = response_json["data"][0]["attributes"]["version"]
        print("Last build version is: "+ version)
        if output_path:
            with open(output_path, 'a') as f:
                f.write(f"last_build_number={version}\n")
        if output_path:
            with open(output_path, 'a') as f:
                f.write(f"increment_last_build_number={int(version)+1}\n")
    except (KeyError, IndexError) as e:
        print(f"Error parsing response: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()