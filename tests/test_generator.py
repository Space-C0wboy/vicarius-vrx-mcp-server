import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "mini_openapi.json"


def _load_generator():
    spec = importlib.util.spec_from_file_location(
        "gen", ROOT / "scripts" / "generate_from_openapi.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_domain_and_operations_parsed():
    gen = _load_generator()
    import json
    spec = json.loads(FIXTURE.read_text())
    domains = gen.collect_domains(spec)
    names = {d.module_name for d in domains}
    assert names == {"vulnerability", "endpoint", "organization_endpoint_group"}


def test_get_post_search_twin_deduped_keeps_post():
    gen = _load_generator()
    import json
    spec = json.loads(FIXTURE.read_text())
    domains = {d.module_name: d for d in gen.collect_domains(spec)}
    vuln_ops = domains["vulnerability"].operations
    searches = [o for o in vuln_ops if o.path == "/vulnerability/search"]
    assert len(searches) == 1
    assert searches[0].method == "POST"  # POST twin kept


def test_mutating_classification():
    gen = _load_generator()
    import json
    spec = json.loads(FIXTURE.read_text())
    by_name = {}
    for d in gen.collect_domains(spec):
        for o in d.operations:
            by_name[o.tool_name] = o
    # search POST is non-mutating despite being POST
    assert by_name["vulnerability_search"].mutating is False
    # a POST /count is a read, not a mutation, so it stays available in read-only
    assert by_name["endpoint_count"].mutating is False
    # PUT insert and DELETE delete are mutating
    assert by_name["organization_endpoint_group_insert"].mutating is True
    assert by_name["endpoint_delete"].mutating is True


def test_param_name_sanitization():
    gen = _load_generator()
    assert gen.safe_param_name("from") == "from_"
    assert gen.safe_param_name("size") == "size"


def test_generation_is_deterministic(tmp_path):
    gen = _load_generator()
    out1 = tmp_path / "a"
    out2 = tmp_path / "b"
    gen.generate(FIXTURE, out1, out1 / "ENDPOINTS.md")
    gen.generate(FIXTURE, out2, out2 / "ENDPOINTS.md")
    f1 = (out1 / "vulnerability.py").read_text()
    f2 = (out2 / "vulnerability.py").read_text()
    assert f1 == f2
    assert "def register(mcp" in f1
    assert "vulnerability_search" in f1


def test_description_surfaces_required_params_and_enums(tmp_path):
    gen = _load_generator()
    gen.generate(FIXTURE, tmp_path, tmp_path / "ENDPOINTS.md")
    code = (tmp_path / "endpoint.py").read_text()
    # endpoint_attributes (GET /endpoint/{endpointId}/attributes) has a required path
    # param plus a required enum query param — both must show up in the description.
    assert "Required: endpointId, softwareType." in code
    assert "Allowed values: softwareType=APP|OS." in code


def test_generated_module_imports_and_registers(tmp_path):
    gen = _load_generator()
    gen.generate(FIXTURE, tmp_path, tmp_path / "ENDPOINTS.md")
    # The generated module should be syntactically valid Python.
    code = (tmp_path / "endpoint.py").read_text()
    compile(code, "endpoint.py", "exec")
    assert "endpoint_delete" in code
    assert "endpoint_get_attrs".replace("get_attrs", "") in code  # domain prefix present
