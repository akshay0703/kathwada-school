"""
Phase 0.11 — S3-compatible storage.

This test proves the django-storages + boto3 upload/download code path is
correct by mocking AWS's S3 API with `moto` (no real network, no real bucket).
It intentionally does NOT hit a live MinIO/S3 endpoint — moto's HTTP
interception is keyed to AWS's own default endpoints, so for this test only
we drop the custom AWS_S3_ENDPOINT_URL override and let boto3 talk to the
(mocked) default AWS endpoint instead. This is a scope difference worth being
explicit about, not something to gloss over.

What IS verified here (automatically, in CI): the storage backend
configuration is wired correctly, and a save() -> exists() -> open() -> read()
-> delete() cycle round-trips bytes correctly through django-storages' S3
backend and boto3's S3 client.

What is NOT yet verified here (needs `docker compose up` with the real minio
+ minio-init services from docker/docker-compose.yml, which this sandbox
cannot run): that the concrete MinIO container starts, that the
kathwada-documents bucket actually gets created by minio-init, and that the
app container can reach it over the Docker network at the real
AWS_S3_ENDPOINT_URL=http://minio:9000. That is called out explicitly in the
Phase 0 report as the one sub-item still requiring your local verification.
"""

import pytest
from django.core.files.base import ContentFile
from django.test import override_settings
from moto import mock_aws


@mock_aws
@override_settings(AWS_S3_ENDPOINT_URL=None)  # see module docstring
@pytest.mark.django_db
def test_s3_storage_round_trip():
    import boto3
    from django.core.files.storage import storages

    # moto intercepts this — no real AWS account/credentials touched.
    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="kathwada-documents")

    storage = storages["default"]
    file_name = "documents/test-round-trip.txt"
    content = b"Kathwada High School - Phase 0 storage round-trip test"

    saved_name = storage.save(file_name, ContentFile(content))
    assert storage.exists(saved_name)

    with storage.open(saved_name) as f:
        read_back = f.read()
    assert read_back == content

    storage.delete(saved_name)
    assert not storage.exists(saved_name)
