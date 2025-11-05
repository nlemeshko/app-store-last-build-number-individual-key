import sys, os
from datetime import datetime, timedelta
from time import time
import jwt
import requests
import base64

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

    url = f"https://api.appstoreconnect.apple.com/v1/builds?filter[app]={app_id}&limit=1"
    # Если указана версия приложения, фильтруем по версии предпросмотра (preReleaseVersion.version)
    if app_version:
        url += f"&filter[preReleaseVersion.version]={requests.utils.quote(app_version)}"
    r = requests.get(url, headers=request_headers)

    if r.status_code != 200:
        # Выведем тело ответа для диагностики
        try:
            error_body = r.text
        except Exception:
            error_body = "<no body>"
        print(f"Error: {r.status_code}. Response body: {error_body}")
        sys.exit(1)

    try:
        response_json = r.json()

        data = response_json.get("data", []) if isinstance(response_json, dict) else []
        if not data:
            # Нет билдов по фильтрам — запишем безопасные значения и завершимся успешно
            print("No builds found for the specified app (and version filter, if provided).")
            if output_path:
                with open(output_path, 'a') as f:
                    f.write("last_build_number=0\n")
                    f.write("increment_last_build_number=1\n")
                    f.write("increment_last_build_number_plus=2\n")
            return

        attributes = data[0].get("attributes", {})
        version = attributes.get("version")
        if version is None:
            raise KeyError("'attributes.version' is missing in the API response")

        print("Last build version is: "+ version)
        if output_path:
            with open(output_path, 'a') as f:
                f.write(f"last_build_number={version}\n")
                f.write(f"increment_last_build_number={int(version)+1}\n")
                f.write(f"increment_last_build_number_plus={int(version)+2}\n")
    except (KeyError, IndexError, ValueError) as e:
        print(f"Error parsing response: {e}")
        # Попробуем вывести тело ответа для отладки
        try:
            print(f"Raw response: {r.text}")
        except Exception:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()