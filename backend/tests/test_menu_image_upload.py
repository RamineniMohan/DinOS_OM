import io
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import UploadFile

from app.common.storage import save_image_upload
from app.modules.menu.service import MenuService

@pytest.mark.asyncio
async def test_save_image_upload_local_fallback(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fake_file = UploadFile(
        filename="pizza.png",
        file=io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"),
        headers={"content-type": "image/png"},
    )
    url = await save_image_upload(fake_file, folder="menu_items")
    assert url.startswith("/static/uploads/menu_items/")
    assert url.endswith(".png")

@pytest.mark.asyncio
async def test_menu_service_upload_item_image():
    db = AsyncMock()
    mock_item = MagicMock()
    mock_item.id = uuid.uuid4()
    mock_item.image_url = None

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_item
    db.execute.return_value = mock_result

    updated = await MenuService.upload_item_image(db, mock_item.id, uuid.uuid4(), "/static/uploads/menu_items/test.png")
    assert mock_item.image_url == "/static/uploads/menu_items/test.png"
