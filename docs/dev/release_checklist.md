# Release Checklist

This document is intended for app maintainers and outlines the steps to perform when releasing a new version of the app.

!!! important
    This project uses a **main-only branching strategy** with **beta releases** for testing before stable releases.

    Before starting, make sure your **local** `main` branch is up to date:

    ```bash
    git fetch
    git switch main && git pull
    ```

## Release Strategy

This project follows a streamlined release process:

1. **Feature development** → Merge to `main` via squash merge (PR required)
2. **Beta release** → Tag `1.0.0b1`, `1.0.0b2`, etc. from `main`
3. **Testing period** → Let beta "cook" with real-world usage
4. **Stable release** → Tag `1.0.0` from `main`

Choose your path:

- **Beta release** (for testing)? Continue with [Beta Releases](#beta-releases)
- **Stable release** (production-ready)? Continue with [Stable Releases](#stable-releases)
- **LTM/Backport release**? Jump to [LTM Releases](#ltm-releases)

---

## Beta Releases

Beta releases allow early adopters to test new features before they reach stable. Users can install with `pip install --pre nautobot-ai-ops`.

### 1. Verify CI Build Status

Ensure that continuous integration testing on the `main` branch is completing successfully.

### 2. Update Version to Beta

Update the package version to a beta version using `poetry version`:

```bash
# First beta of version 1.0.0
poetry version 1.0.0b1

# Or bump from current beta
poetry version prerelease  # e.g., 1.0.0b1 → 1.0.0b2
```

### 3. Commit Version Bump

```bash
git add pyproject.toml
git commit -m "chore: bump version to 1.0.0b1"
```

### 4. Tag and Push

```bash
git tag 1.0.0b1
git push origin main --tags
```

!!! success "Automatic Deployment"
    Once the tag is pushed, the GitHub Actions workflow will automatically:
    
    - Build the package
    - Publish to PyPI (as a pre-release)
    - Create a GitHub pre-release with auto-generated notes

### 5. Monitor Deployment

Check the [Publish to PyPI workflow](https://github.com/kvncampos/nautobot-ai-ops/actions/workflows/publish-pypi.yml) to ensure it completes successfully.

### 6. Test Beta Release

Install and test the beta in a non-production environment:

```bash
pip install --pre nautobot-ai-ops
```

### 7. Iterate If Needed

If issues are found, fix them, merge to `main`, and release another beta:

```bash
poetry version prerelease  # 1.0.0b1 → 1.0.0b2
git add pyproject.toml
git commit -m "chore: bump version to 1.0.0b2"
git tag 1.0.0b2
git push origin main --tags
```

---

## Stable Releases

Stable releases should only be created after adequate beta testing.

### 1. Verify CI Build Status

Ensure that continuous integration testing on the `main` branch is completing successfully.

### 2. Update Requirements (Minor/Major Releases Only)

For minor or major version releases, refresh `poetry.lock`:

```bash
# Review available updates
poetry update --dry-run

# Update specific packages
poetry update <package>

# Install and test
poetry install
poetry run invoke tests
```

If a package requires updating to a new version outside current constraints in `pyproject.toml`, update it manually.

### 3. Update Documentation (Minor/Major Releases Only)

- Update the compatibility matrix if needed
- Verify installation and upgrade steps still accurate
- Update any new configuration examples

### 4. Consolidate Changelog Fragments

Run towncrier to consolidate all changelog fragments:

```bash
# Towncrier will use the version from pyproject.toml
invoke generate-release-notes --version 1.0.0
```

This will:
- Generate/update `docs/admin/release_notes/version_1.0.md`
- Delete all processed fragments from `changes/`
- Stage the changes in git

!!! note
    For new major/minor versions, manually add a `Release Overview` section to the generated release notes file with a user-friendly summary of notable changes.

### 5. Update Version to Stable

```bash
poetry version 1.0.0
```

### 6. Commit Release Changes

```bash
git add .
git commit -m "chore: release 1.0.0"
```

### 7. Tag and Push

```bash
git tag 1.0.0
git push origin main --tags
```

!!! success "Automatic Deployment"
    Once the tag is pushed, the GitHub Actions workflow will automatically:
    
    - Verify changelog fragments are cleared
    - Build the package
    - Publish to PyPI (as a stable release)
    - Create a GitHub release with auto-generated notes

### 8. Verify Deployment

Check the following:

1. [Publish to PyPI workflow](https://github.com/kvncampos/nautobot-ai-ops/actions/workflows/publish-pypi.yml) completed successfully
2. Package appears on [PyPI](https://pypi.org/project/nautobot-ai-ops/) as a stable release
3. GitHub release created with correct tag and notes
4. Documentation built and deployed

---

## Poetry Version Commands Quick Reference

```bash
# Display current version
poetry version

# Beta releases
poetry version 1.0.0b1           # Set specific beta version
poetry version prerelease        # Bump beta: 1.0.0b1 → 1.0.0b2

# Stable releases
poetry version patch             # 1.0.0 → 1.0.1
poetry version minor             # 1.0.1 → 1.1.0
poetry version major             # 1.1.0 → 2.0.0

# Convert beta to stable
poetry version 1.0.0             # 1.0.0b2 → 1.0.0
```

---
## LTM Releases

For projects maintaining a Nautobot LTM compatible release, all development and release management is done through the `ltm-x.y` branch. The `x.y` relates to the LTM version of Nautobot it's compatible with, for example `1.6`.

The process is similar to stable releases, but you release directly from the LTM branch:

### 1. Verify CI Status

Make sure your `ltm-1.6` branch is passing CI.

### 2. Create Release Branch

```bash
git switch -c release-1.2.3 ltm-1.6
```

### 3. Update Version

Choose the appropriate version bump based on the changes:

```bash
# For bug fixes only (patch release: 1.2.3 → 1.2.4)
poetry version patch

# For backported features (minor release: 1.2.3 → 1.3.0)
poetry version minor
```

### 4. Generate Release Notes

```bash
invoke generate-release-notes --version 1.2.3
```

Move the release notes from `docs/admin/release_notes/version_X.Y.md` to `docs/admin/release_notes/version_1.2.md`.

### 5. Commit and Tag

```bash
git add .
git commit -m "chore: release 1.2.3"
git tag 1.2.3
git push origin release-1.2.3 --tags
```

### 6. Create PR to LTM Branch

Open a PR against `ltm-1.6`. Once CI is passing:

!!! important
    Select `Create a merge commit` when merging (don't squash!).

### 7. Create GitHub Release

Follow the same steps as [Stable Releases - Verify Deployment](#8-verify-deployment).

### 8. Sync to Main (Optional)

Open a separate PR against `main` to synchronize LTM release changelogs for visibility in the latest docs.

---

## Troubleshooting

### Deleting a Bad Tag

If you tagged the wrong version:

```bash
# Delete local tag
git tag -d 1.0.0

# Delete remote tag
git push origin :refs/tags/1.0.0
```

### Changelog Fragments Still Exist

The workflow will fail for stable releases if fragments remain in `changes/`. This is intentional - run `towncrier build` first.

### Failed PyPI Deployment

Check the [Actions tab](https://github.com/kvncampos/nautobot-ai-ops/actions/workflows/publish-pypi.yml) for error details. Common issues:

- Version already exists on PyPI (can't republish same version)
- Authentication issues (check repository secrets)
- Build failures (check package integrity)

---

## Summary

**For Beta Releases:**
1. `poetry version 1.0.0b1` → `git commit` → `git tag 1.0.0b1` → `git push --tags`

**For Stable Releases:**
1. `invoke generate-release-notes --version 1.0.0`
2. `poetry version 1.0.0` → `git commit` → `git tag 1.0.0` → `git push --tags`

**Key Points:**
- All PRs must include changelog fragments in `changes/`
- Beta releases keep fragments; stable releases consolidate them
- All merges to `main` use squash merge
- GitHub Actions handles PyPI publishing automatically
