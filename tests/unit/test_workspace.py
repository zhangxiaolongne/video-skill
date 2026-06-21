from artist_portrait_editor.workspace import atomic_write_text


def test_atomic_write_text_replaces_content_without_leaving_tmp_file(tmp_path):
    output = tmp_path / "output" / "report.md"

    atomic_write_text(output, "first\n")
    atomic_write_text(output, "second\n")

    assert output.read_text(encoding="utf-8") == "second\n"
    assert not (output.parent / "report.md.tmp").exists()
