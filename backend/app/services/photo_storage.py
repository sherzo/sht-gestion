"""Almacenamiento de las fotos de productos (FR-008, research R9).

- `SupabasePhotoStorage`: bucket público de Supabase Storage, por su API REST con la
  clave secreta del proyecto, que nunca llega al navegador (principio IV).
- `LocalPhotoStorage`: disco local para desarrollo y pruebas; la API lo sirve en
  `/media` solo en esos ambientes.
"""

from pathlib import Path
from typing import Protocol

import httpx

from app.core.config import Settings, get_settings
from app.core.errors import ApiError


class PhotoStorage(Protocol):
    def save(self, path: str, data: bytes, content_type: str) -> None: ...

    def delete(self, path: str) -> None: ...

    def public_url(self, path: str) -> str: ...


class LocalPhotoStorage:
    def __init__(self, root: str, base_url: str) -> None:
        self.root = Path(root)
        self.base_url = base_url.rstrip("/")

    def _file(self, path: str) -> Path:
        target = (self.root / path).resolve()
        if not target.is_relative_to(self.root.resolve()):
            raise ValueError("Ruta de foto inválida")
        return target

    def save(self, path: str, data: bytes, content_type: str) -> None:
        target = self._file(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def delete(self, path: str) -> None:
        self._file(path).unlink(missing_ok=True)

    def public_url(self, path: str) -> str:
        return f"{self.base_url}/{path}"


class SupabasePhotoStorage:
    def __init__(self, url: str, key: str, bucket: str) -> None:
        self.url = url.rstrip("/")
        self.key = key
        self.bucket = bucket

    def _object_url(self, path: str) -> str:
        return f"{self.url}/storage/v1/object/{self.bucket}/{path}"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.key}", "apikey": self.key}

    def save(self, path: str, data: bytes, content_type: str) -> None:
        try:
            response = httpx.post(
                self._object_url(path),
                content=data,
                headers={**self._headers(), "Content-Type": content_type, "x-upsert": "false"},
                timeout=30,
            )
        except httpx.HTTPError as exc:
            raise _storage_unavailable() from exc
        if response.status_code >= 300:
            raise _storage_unavailable()

    def delete(self, path: str) -> None:
        try:
            response = httpx.delete(self._object_url(path), headers=self._headers(), timeout=30)
        except httpx.HTTPError as exc:
            raise _storage_unavailable() from exc
        # Un objeto que ya no existe no es un error: el resultado es el mismo.
        if response.status_code >= 300 and response.status_code != 404:
            raise _storage_unavailable()

    def public_url(self, path: str) -> str:
        return f"{self.url}/storage/v1/object/public/{self.bucket}/{path}"


def _storage_unavailable() -> ApiError:
    return ApiError(
        503, "photo_storage_unavailable", "No se pudo guardar la foto. Intenta de nuevo"
    )


def build_photo_storage(settings: Settings) -> PhotoStorage:
    if settings.photo_storage == "supabase":
        assert settings.supabase_url and settings.supabase_storage_key
        return SupabasePhotoStorage(
            settings.supabase_url,
            settings.supabase_storage_key.get_secret_value(),
            settings.photo_bucket,
        )
    return LocalPhotoStorage(settings.photo_local_dir, settings.photo_local_base_url)


def get_photo_storage() -> PhotoStorage:
    return build_photo_storage(get_settings())
