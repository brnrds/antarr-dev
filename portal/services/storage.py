"""
Private object storage with time-limited signed URLs.

The local adapter signs a private Django endpoint. A production S3-compatible
adapter can retain this interface and return a provider presigned URL instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import BinaryIO

from django.conf import settings
from django.core import signing
from django.urls import reverse
from django.utils import timezone


class InvalidDownloadToken(ValueError):
    """The supplied token is invalid or has expired."""


class StoredObjectNotFound(FileNotFoundError):
    """The storage key does not resolve to a readable private file."""


@dataclass(frozen=True)
class SignedDownload:
    url: str
    expires_at: timezone.datetime


@dataclass(frozen=True)
class StoredObject:
    storage_key: str
    stream: BinaryIO
    filename: str


class PrivateObjectStorage:
    """
    Issue and resolve temporary signed URLs for sensitive local files.

    TODO: wire to S3-compatible storage (AWS S3, Cloudflare R2, MinIO).
    """

    default_ttl = timedelta(minutes=15)
    signer_salt = "portal.private-download"

    def __init__(
        self,
        *,
        root: Path | str | None = None,
        ttl: timedelta | None = None,
    ) -> None:
        configured_root = (
            root
            if root is not None
            else getattr(
                settings,
                "PRIVATE_MEDIA_ROOT",
                settings.BASE_DIR / "private-media",
            )
        )
        self.root = Path(configured_root).resolve()
        self.ttl = self.default_ttl if ttl is None else ttl

    def get_download_url(self, storage_key: str) -> SignedDownload:
        expires_at = timezone.now() + self.ttl
        token = self._signer().sign(storage_key)
        url = f"{reverse('portal:signed_file')}?token={token}"
        return SignedDownload(url=url, expires_at=expires_at)

    def open_signed_download(self, token: str) -> StoredObject:
        """Validate a token and safely open its file beneath the private root."""
        try:
            storage_key = self._signer().unsign(
                token,
                max_age=self.ttl.total_seconds(),
            )
        except signing.BadSignature as exc:
            raise InvalidDownloadToken from exc

        file_path = (self.root / storage_key).resolve()
        if self.root not in file_path.parents or not file_path.is_file():
            raise StoredObjectNotFound(storage_key)

        try:
            stream = file_path.open("rb")
        except OSError as exc:
            raise StoredObjectNotFound(storage_key) from exc
        return StoredObject(
            storage_key=storage_key,
            stream=stream,
            filename=file_path.name,
        )

    def _signer(self) -> signing.TimestampSigner:
        return signing.TimestampSigner(salt=self.signer_salt)
