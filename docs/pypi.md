# Publishing Genesis to PyPI

This guide covers publishing new versions of the `genesis-minds` package to PyPI.

## Prerequisites

1. **PyPI Account**: Create accounts on both:
   - [PyPI](https://pypi.org/account/register/) (production)
   - [TestPyPI](https://test.pypi.org/account/register/) (testing)

2. **API Tokens**: Generate API tokens for both:
   - PyPI: https://pypi.org/manage/account/token/
   - TestPyPI: https://test.pypi.org/manage/account/token/

3. **Required Packages**:
   ```bash
   pip install --upgrade build twine
   ```

## Configuration

Create/update `~/.pypirc` with your API tokens:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR-PRODUCTION-TOKEN-HERE

[testpypi]
username = __token__
password = pypi-YOUR-TEST-TOKEN-HERE
repository = https://test.pypi.org/legacy/
```

## Publishing Process

### Step 1: Update Version

Edit `pyproject.toml` and increment the version:

```toml
[project]
name = "genesis-minds"
version = "0.1.4"  # ← Increment this
```

**Version Numbering:**
- **Patch** (0.1.x): Bug fixes, minor improvements
- **Minor** (0.x.0): New features, backward compatible
- **Major** (x.0.0): Breaking changes

### Step 2: Update Changelog

Document changes in `README.md` or `CHANGELOG.md`:

```markdown
## v0.1.4 (2026-01-XX)
- Added: New feature X
- Fixed: Bug Y
- Improved: Performance of Z
```

### Step 3: Clean Previous Builds

Remove old build artifacts:

```bash
# PowerShell (Windows)
Remove-Item -Recurse -Force dist, build, *.egg-info

# Bash (Linux/Mac)
rm -rf dist build *.egg-info
```

### Step 4: Build Distribution

Build both source and wheel distributions:

```bash
python -m build
```

This creates:
- `dist/genesis-minds-0.1.4.tar.gz` (source distribution)
- `dist/genesis_minds-0.1.4-py3-none-any.whl` (wheel distribution)

### Step 5: Test on TestPyPI (Optional but Recommended)

Upload to TestPyPI first:

```bash
python -m twine upload --repository testpypi dist/*
```

Test installation from TestPyPI:

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ genesis-minds
```

### Step 6: Upload to PyPI

Once testing is successful, upload to production PyPI:

```bash
python -m twine upload dist/*
```

You'll see output like:
```
Uploading distributions to https://upload.pypi.org/legacy/
Uploading genesis_minds-0.1.4-py3-none-any.whl
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 150.0/150.0 kB • 00:01
Uploading genesis-minds-0.1.4.tar.gz
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 120.0/120.0 kB • 00:01

View at:
https://pypi.org/project/genesis-minds/0.1.4/
```

### Step 7: Verify Installation

Test that users can install the new version:

```bash
pip install --upgrade genesis-minds
python -c "import genesis; print(genesis.__version__)"
```

### Step 8: Create Git Tag

Tag the release in Git:

```bash
git add pyproject.toml README.md
git commit -m "Release v0.1.4"
git tag v0.1.4
git push origin main --tags
```

### Step 9: GitHub Release (Optional)

Create a GitHub release:
1. Go to https://github.com/shaik-shahansha/genesis-agi/releases
2. Click "Draft a new release"
3. Select tag `v0.1.4`
4. Add release notes
5. Publish release

## Quick Command Reference

**Complete release process (copy-paste):**

```bash
# 1. Clean old builds
Remove-Item -Recurse -Force dist, build, *.egg-info

# 2. Build distributions
python -m build

# 3. Upload to TestPyPI (optional)
python -m twine upload --repository testpypi dist/*

# 4. Upload to PyPI
python -m twine upload dist/*

# 5. Git tag and push
git add .
git commit -m "Release v0.1.4"
git tag v0.1.4
git push origin main --tags
```

## Troubleshooting

### "File already exists" Error
If you get an error that the version already exists on PyPI:
- You cannot overwrite existing versions
- Increment the version number and rebuild

### Build Fails
Check that all required files are present:
- `pyproject.toml`
- `README.md`
- `LICENSE`
- `genesis/__init__.py`

### Import Errors After Installation
Make sure dependencies are correctly listed in `pyproject.toml` under `dependencies`.

### Authentication Errors
- Verify your API token is correct in `~/.pypirc`
- Make sure you're using `__token__` as username
- Token should start with `pypi-`

## Package Metadata

Current package info (from `pyproject.toml`):

- **Name**: `genesis-minds`
- **Current Version**: `0.1.4`
- **Python**: `>=3.11`
- **License**: MIT
- **PyPI**: https://pypi.org/project/genesis-minds/

## Important Notes

1. **Versions are permanent**: Once uploaded, you cannot delete or replace a version
2. **Test first**: Always test on TestPyPI before production
3. **Semantic versioning**: Follow [semver.org](https://semver.org) guidelines
4. **Keep README updated**: PyPI displays README.md on the package page
5. **Security**: Never commit API tokens to Git

## Resources

- [Python Packaging Guide](https://packaging.python.org/)
- [setuptools Documentation](https://setuptools.pypa.io/)
- [Twine Documentation](https://twine.readthedocs.io/)
- [PyPI Help](https://pypi.org/help/)
