from routes.upload import _matches_signature


def test_upload_signature_validation(tmp_path) -> None:
    fixtures = {
        "image.jpg": (b"\xff\xd8\xff" + b"\x00" * 9, True),
        "image.png": (b"\x89PNG\r\n\x1a\n" + b"\x00" * 4, True),
        "image.tif": (b"II*\x00" + b"\x00" * 8, True),
        "video.mp4": (b"\x00\x00\x00\x18ftyp" + b"\x00" * 4, True),
        "video.avi": (b"RIFF" + b"\x00" * 4 + b"AVI ", True),
        "fake.jpg": (b"not an image", False),
    }
    for name, (content, expected) in fixtures.items():
        path = tmp_path / name
        path.write_bytes(content)

        assert _matches_signature(path, path.suffix.lower()) is expected
