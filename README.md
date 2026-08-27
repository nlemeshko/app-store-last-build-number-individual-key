# App Store Connect Get Last Build Number Action

This GitHub Action retrieves the highest build number for an app from App Store Connect and exposes incremented values for a subsequent iOS build.

## Inputs

- `key` (required): Base64-encoded App Store Connect P8 private key.
- `key_id` (required): App Store Connect API key ID.
- `app_id` (required): Numeric App Store Connect app ID.
- `app_version` (optional): Explicit pre-release version used to filter builds, for example `3.2.0`.
- `target_name` (optional): Xcode target whose resolved `MARKETING_VERSION` should be used, for example `Monix`. This mode requires a macOS runner with Xcode.
- `project_path` (optional): Path to the `.xcodeproj`. When omitted, the action expects exactly one `.xcodeproj` in the repository root.
- `configuration` (optional): Xcode build configuration used when resolving the target version. Defaults to `Release`.

`app_version` and `target_name` are mutually exclusive. When neither is provided, the action considers builds from all app versions.

## Outputs

- `app_version`: The explicit or target-derived marketing version. Empty when no version filter is used.
- `last_build_number`: Highest build number returned by App Store Connect.
- `increment_last_build_number`: Highest build number plus one.
- `increment_last_build_number_plus`: Highest build number plus two.

## Usage with an Xcode target

```yaml
- name: Get last build number
  id: get_build_number
  uses: nlemeshko/app-store-last-build-number-individual-key@1.0.7
  with:
    key: ${{ secrets.APP_STORE_PRIVATE_KEY_BASE64 }}
    key_id: ${{ secrets.APP_STORE_KEY_ID }}
    app_id: ${{ secrets.APP_ID }}
    target_name: Monix
    project_path: Monix.xcodeproj
    configuration: Release

- name: Show resolved values
  run: |
    echo "App version: ${{ steps.get_build_number.outputs.app_version }}"
    echo "Next build: ${{ steps.get_build_number.outputs.increment_last_build_number }}"
```

## Usage with an explicit version

```yaml
- name: Get last build number
  id: get_build_number
  uses: nlemeshko/app-store-last-build-number-individual-key@1.0.7
  with:
    key: ${{ secrets.APP_STORE_PRIVATE_KEY_BASE64 }}
    key_id: ${{ secrets.APP_STORE_KEY_ID }}
    app_id: ${{ secrets.APP_ID }}
    app_version: 3.2.0
```

## Troubleshooting

If the action fails with `FORBIDDEN.REQUIRED_AGREEMENTS_MISSING_OR_EXPIRED`, the App Store Connect API key is still valid, but Apple is blocking API access until someone with the right permissions accepts pending agreements in App Store Connect under **Agreements, Tax, and Banking**.
