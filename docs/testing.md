# Testing

## Repository tests

```bash
python -m pip install -r requirements-dev.txt
ruff check .
pytest
python tools/build_mkp.py
```

The automated tests cover source compilation, package metadata, MKP payload contents, checkman coverage, common secret/lab-data patterns, core check states and collector helper behavior.

## Checkmk-native validation

Install the generated MKP on a clean Checkmk 2.5 test site and run:

```bash
cmk-validate-plugins
cmk -M entra_cloudsync_job
cmk -M entra_cloudsync_execution
cmk -M entra_cloudsync_objects
cmk -M entra_cloudsync_provisioning
cmk -M entra_cloudsync_dropped
cmk -M entra_cloudsync_properties
```

Then configure a logical host and verify discovery returns six services for one `AD2AADProvisioning` job.

## Functional scenarios validated during development

- healthy Active job with successful executions
- disabled/paused Cloud Sync configuration
- stopped Cloud Sync provisioning agent resulting in stale execution data
- object provisioning failure with Graph error details
- later successful provisioning of the same object clearing the unresolved failure
- execution duration and freshness metrics
- property-change reporting with empty-value normalization
- restart provisioning transition through `NotRun` and recovery to Active
- year-0001 sentinel timestamp handling

## Optional Windows local checks

On the Cloud Sync provisioning-agent server, verify the Checkmk agent output contains the local-check services after deployment. If caching is configured, allow the configured cache interval before expecting refreshed output.
