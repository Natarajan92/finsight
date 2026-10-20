import json


def test_audit_command_uses_selected_local_corpus(data_dir, capsys):
    from finsight.financebench.__main__ import main

    assert main(["audit", "--data-dir", str(data_dir), "--company", "Other Corp", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["company"] == "Other Corp"
    assert report["question_count"] == 1
    assert report["ok"] is True


def test_audit_command_returns_failure_for_missing_pdf(data_dir, capsys):
    from finsight.financebench.__main__ import main

    (data_dir / "pdfs" / "AMD_2022_10K.pdf").unlink()
    assert main(["audit", "--data-dir", str(data_dir)]) == 1
    assert "missing_pdf" in capsys.readouterr().out


def test_command_reports_unknown_company_without_a_traceback(data_dir, capsys):
    from finsight.financebench.__main__ import main

    assert main(["audit", "--data-dir", str(data_dir), "--company", "Missing"]) == 2
    assert "Unknown company" in capsys.readouterr().err
