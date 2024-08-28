# App Store Connect Get Last Build Number Action

This GitHub Action retrieves the latest build number for a specified app from App Store Connect. It uses the App Store Connect API to get the build information.

## Inputs

The action requires the following inputs:

- `key` (string): The App Store P8 Key as a string (not a file) in base64. This is used to sign the JWT.
- `key_id` (string): The App Store Key ID. This identifies the key used for signing.
- `app_id` (string): The App Store App ID. This is the ID of the app for which you want to get the build number.

## Outputs

This action does not produce any explicit outputs but writes the build version number to the environment variable `BUILD_VERSION`.

## Usage

Here's a sample GitHub Actions workflow that uses this action:

```yaml
name: 'Get Last Build Number'

on:
  push:
    branches:
      - main

jobs:
  get_build_number:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Get last build number
        id: get_build_number
        uses: nlemeshko/app-store-last-build-number-individual-key-action@1.0.3
        with:
          key: ${{ secrets.APP_STORE_PRIVATE_KEY_BASE64 }}
          key_id: 'XXX'
          app_id: '123'
        # Capture the output from the action
        continue-on-error: true  # Ensure that the step does not fail the workflow

      - name: Set build number as output
        id: set_output
        run: echo "BUILD_VERSION=$(echo "${{ steps.get_build_number.outputs.last_build_number }}")" >> $GITHUB_ENV

      - name: Use build version
        run: |
          echo "The latest build version is $BUILD_VERSION"

You can use last_build_number and increment_last_build_number.