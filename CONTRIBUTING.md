# Contributing

Contributions are welcome through pull requests and issues.

Before submitting a change:

```bash
python -m pip install -r requirements-dev.txt
ruff check .
pytest
python tools/build_mkp.py
```

Keep tenant-specific values, credentials, tokens, certificates and customer data out of the repository and test fixtures.

Changes to check plug-ins should also update the matching file in `cmk_addons/plugins/entra_cloudsync/checkman/` when operator-visible behavior changes.
