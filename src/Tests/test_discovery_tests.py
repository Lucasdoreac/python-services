"""`pytest` puro (CI e dev-local) tem de achar todo arquivo de teste.
Os arquivos daqui se chamam *_tests.py, que o pytest não descobre por
padrão: sem configuração, só 25 dos 83 testes rodavam."""
import fnmatch
import pathlib
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[2]
# Teste antigo quebrado (usa DAL.index, que não existe mais); fica fora de
# propósito até alguém decidir consertar ou apagar.
KNOWN_BROKEN = {"dal.py"}


def test_every_test_file_is_discovered_by_plain_pytest():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    options = config.get("tool", {}).get("pytest", {}).get("ini_options", {})
    patterns = options.get("python_files", ["test_*.py", "*_test.py"])

    test_files = [p.name for p in (ROOT / "src" / "Tests").glob("*.py")
                  if "\ndef test" in p.read_text(encoding="utf-8") or "\n    def test" in p.read_text(encoding="utf-8")]
    missed = [name for name in test_files if name not in KNOWN_BROKEN and not any(fnmatch.fnmatch(name, pat) for pat in patterns)]

    assert options.get("testpaths") == ["src/Tests"]
    assert missed == []
