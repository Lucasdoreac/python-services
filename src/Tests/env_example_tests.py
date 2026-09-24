"""O .env.example é o contrato de configuração do deploy: tem de listar
exatamente as variáveis que o código lê (nem faltar, nem sobrar)."""
import ast
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
# Não é importado por nenhum módulo (código morto): suas variáveis não valem.
DEAD_MODULES = {"SLL/sendblue.py"}


def env_vars_read_by_code():
    names = set()
    for path in SRC.rglob("*.py"):
        rel = path.relative_to(SRC).as_posix()
        if rel.startswith("Tests/") or rel in DEAD_MODULES:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            # os.getenv("X") / os.environ.get("X")
            if isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant):
                func = ast.unparse(node.func)
                if func in ("os.getenv", "os.environ.get", "getenv"):
                    names.add(node.args[0].value)
            # os.environ["X"]
            if isinstance(node, ast.Subscript) and ast.unparse(node.value) == "os.environ" \
                    and isinstance(node.slice, ast.Constant):
                names.add(node.slice.value)
            # campos das classes pydantic BaseSettings viram variáveis em maiúsculas
            if isinstance(node, ast.ClassDef) and any(ast.unparse(b) == "BaseSettings" for b in node.bases):
                names |= {s.target.id.upper() for s in node.body
                          if isinstance(s, ast.AnnAssign) and s.target.id != "model_config"}
    return names


def env_example_keys():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    return set(re.findall(r"^([A-Za-z][A-Za-z0-9_]*)=", text, re.MULTILINE))


def test_every_variable_the_code_reads_is_documented():
    # Faltavam MONGO_URI e OFFER_PERIOD_HOURS: quem sobe só pelo exemplo
    # não sabia que existem.
    assert env_vars_read_by_code() - env_example_keys() == set()


def test_example_has_no_variable_the_code_ignores():
    # REACT_APP estava no exemplo mas só o auth_service a lê: configurá-la
    # aqui não muda nada e induz a erro.
    assert env_example_keys() - env_vars_read_by_code() == set()
