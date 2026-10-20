"""Execute a learning notebook with a local kernel and outbound networking blocked."""

import argparse
import json
import os
import sys
from pathlib import Path

import nbformat
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
from nbclient import NotebookClient
from nbformat import NotebookNode

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks/01_financebench_data_audit.ipynb"
OFFLINE_GUARD = """\
import socket
import urllib.request

_original_connect = socket.socket.connect
def _local_connect(self, address):
    if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "::1", "localhost"}:
        raise RuntimeError("Outbound networking is blocked during notebook verification")
    return _original_connect(self, address)

def _no_http(*args, **kwargs):
    raise RuntimeError("HTTP is blocked during notebook verification")

socket.socket.connect = _local_connect
urllib.request.urlopen = _no_http
"""


def execute_notebook(data_dir: Path, output: Path, *, notebook: Path = NOTEBOOK) -> NotebookNode:
    """Run the actual notebook against a warm cache, leaving the source output-free."""
    output = output.resolve()
    source = notebook.resolve()
    if output == source or (output.exists() and source.exists() and output.samefile(source)):
        raise ValueError("Output must differ from the source notebook")
    output.parent.mkdir(parents=True, exist_ok=True)
    runtime = output.parent / "notebook-runtime"
    kernel_root = runtime / "kernels"
    spec_dir = kernel_root / "finsight"
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "kernel.json").write_text(
        json.dumps(
            {
                "argv": [
                    sys.executable,
                    "-Xfrozen_modules=off",
                    "-m",
                    "ipykernel_launcher",
                    "-f",
                    "{connection_file}",
                ],
                "display_name": "Python (finsight)",
                "language": "python",
                "metadata": {"supported_encryption": ["curve"]},
            }
        ),
        encoding="utf-8",
    )
    manager = KernelSpecManager(kernel_dirs=[str(kernel_root)], ensure_native_kernel=False)
    kernel = KernelManager(
        kernel_name="finsight",
        kernel_spec_manager=manager,
        connection_file=str(runtime / "connection.json"),
        transport_encryption="auto",
    )
    notebook = nbformat.read(source, as_version=4)
    notebook.cells.insert(0, nbformat.v4.new_code_cell(OFFLINE_GUARD))
    env = os.environ.copy()
    env.update(
        {
            "FINSIGHT_DATA_DIR": str(data_dir.resolve()),
            "IPYTHONDIR": str(runtime / "ipython"),
            "JUPYTER_RUNTIME_DIR": str(runtime),
            "JUPYTER_DATA_DIR": str(runtime / "data"),
        }
    )
    executed = NotebookClient(
        notebook,
        km=kernel,
        kernel_name="finsight",
        timeout=90,
        resources={"metadata": {"path": str(ROOT)}},
    ).execute(env=env, cleanup_kc=True)
    nbformat.write(executed, output)
    return executed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/financebench")
    parser.add_argument("--notebook", type=Path, default=NOTEBOOK)
    parser.add_argument(
        "--output",
        type=Path,
        help="Executed copy (default: .artifacts/<notebook-stem>.executed.ipynb)",
    )
    args = parser.parse_args()
    output = args.output or ROOT / f".artifacts/{args.notebook.stem}.executed.ipynb"
    executed = execute_notebook(args.data_dir, output, notebook=args.notebook)
    count = sum(cell.cell_type == "code" for cell in executed.cells)
    print(f"Executed {count} code cells offline. Output: {output.resolve()}")


if __name__ == "__main__":
    main()
