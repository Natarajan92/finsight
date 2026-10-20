import json

import pytest


def test_learning_notebook_executes_offline_with_synthetic_data(data_dir, tmp_path):
    from scripts.verify_notebook import execute_notebook

    output = tmp_path / "executed.ipynb"
    executed = execute_notebook(data_dir, output)
    assert output.is_file()
    code_cells = [cell for cell in executed.cells if cell.cell_type == "code"]
    assert all(cell.execution_count is not None for cell in code_cells)
    assert not any(out.output_type == "error" for cell in code_cells for out in cell.outputs)
    last_output = "".join(out.get("text", "") for out in code_cells[-1].outputs)
    summary = json.loads(last_output)
    assert summary == {
        "company": "AMD",
        "questions": 2,
        "documents": 1,
        "evidence_annotations": 3,
        "unique_evidence_pages": 2,
        "missing_reasoning_labels": 1,
        "annotation_audit_ok": True,
        "provenance_verified": False,
    }


@pytest.mark.parametrize("missing_source", [False, True])
def test_verification_closes_its_kernel_on_success_and_failure(
    data_dir,
    tmp_path,
    monkeypatch,
    missing_source,
):
    from jupyter_client import KernelManager
    from nbclient.exceptions import CellExecutionError

    from scripts import verify_notebook

    managers = []

    def real_manager(**kwargs):
        manager = KernelManager(**kwargs)
        managers.append(manager)
        return manager

    monkeypatch.setattr(verify_notebook, "KernelManager", real_manager)
    selected = tmp_path / "missing" if missing_source else data_dir
    try:
        if missing_source:
            with pytest.raises(CellExecutionError, match="fetch"):
                verify_notebook.execute_notebook(selected, tmp_path / "output.ipynb")
        else:
            verify_notebook.execute_notebook(selected, tmp_path / "output.ipynb")
        assert not managers[0].has_kernel
    finally:
        for manager in managers:
            if manager.has_kernel:
                manager.shutdown_kernel(now=True)
