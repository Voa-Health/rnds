from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from rnds import __version__
from rnds._mcp import TOOLS

PACKAGE = Path(__file__).resolve().parents[1] / "plugins" / "chatgpt"


def _json(name):
    return json.loads((PACKAGE / name).read_text(encoding="utf-8"))


def test_remote_contract():
    config = _json("mcp.json")
    assert config == {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
        "mcpServers": {
            "rnds": {
                "type": "streamable-http",
                "url": "https://api.voa.health/mcp/rnds/",
                "extensions": {
                    "com.openai": {
                        "auth": {
                            "type": "oauth",
                            "client": {"mode": "cimd"},
                            "baseScopes": ["voa:rnds:read"],
                        }
                    }
                },
            }
        },
    }
    assert not re.search(r"stdio|command|args|env", json.dumps(config), re.IGNORECASE)
    manifest = _json("plugin.json")
    assert manifest["version"] == __version__
    assert manifest["name"] == "rnds"
    assert manifest["$schema"] == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
    assert manifest["author"] == {"name": "Voa Health", "url": "https://voa.health"}
    assert manifest["license"] == "Apache-2.0"
    assert manifest["repository"] == "https://github.com/Voa-Health/rnds"
    assert manifest["homepage"] == "https://github.com/Voa-Health/rnds"
    interface = manifest["extensions"]["com.openai"]["interface"]
    assert interface["developerName"] == "Voa Health"
    assert interface["category"] == "Healthcare"
    assert interface["capabilities"] == []
    assert interface["brandColor"] == "#8236FF"
    assert interface["brandColorDark"] == "#A06AFF"
    urls = {
        "websiteURL": "https://github.com/Voa-Health/rnds",
        "supportURL": "https://github.com/Voa-Health/rnds/issues",
        "privacyPolicyURL": "https://app.voa.health/legal/privacidade",
        "termsOfServiceURL": "https://app.voa.health/legal/termos",
    }
    for key, value in urls.items():
        assert interface[key] == value
        assert interface[key].startswith("https://")
    for key in ("logo", "logoDark", "composerIcon", "composerIconDark"):
        suffix = "-dark" if key.endswith("Dark") else ""
        assert interface[key] == f"./assets/voa-icon{suffix}.png"
        assert (PACKAGE / interface[key]).is_file()


@pytest.mark.parametrize("language", ["en", "pt-BR"])
def test_listing_limits(language):
    manifest = _json("plugin.json")
    openai = manifest["extensions"]["com.openai"]
    listing = (
        openai["interface"] if language == "en" else openai["publication"]["translations"][language]
    )
    for field, limit in (("displayName", 30), ("shortDescription", 30), ("longDescription", 4000)):
        assert isinstance(listing[field], str)
        assert 0 < len(listing[field]) <= limit
    prompts = listing["defaultPrompt"]
    assert isinstance(prompts, list)
    assert 0 < len(prompts) <= 3
    assert all(isinstance(prompt, str) and 0 < len(prompt) <= 128 for prompt in prompts)
    description = manifest["description"] if language == "en" else listing["longDescription"]
    assert all(
        word in description for word in ("CodeSystems", "ValueSets", "CPF/CNS/CNES", "Bundle")
    )


def test_package_boundaries():
    mentioned = set()
    forbidden = re.compile(
        r"\b(?:secrets?|tokens?|Bearer|pfx|certificat\w*|certificad\w*)\b"
        r"|sk-[A-Za-z0-9_-]+|-----BEGIN",
        re.IGNORECASE,
    )
    for path in PACKAGE.rglob("*"):
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            assert path.suffix == ".png"
            continue
        mentioned.update(re.findall(r"rnds_[a-z_]+", content))
        assert not forbidden.search(content), path
    assert mentioned == {"rnds_codigos"}
    assert mentioned <= {tool.name for tool in TOOLS}
    tool = next(tool for tool in TOOLS if tool.name == "rnds_codigos")
    schema = tool.model_dump(by_alias=True)["inputSchema"]
    assert schema["properties"] == {
        field: {"type": "string"} for field in ("sistema", "codigo", "origem")
    }
    assert not schema.get("required")


@pytest.mark.parametrize("group,count,tool", [("positive", 5, "rnds_codigos"), ("negative", 3, "")])
def test_review_cases(group, count, tool):
    review = _json("review-cases.json")
    assert set(review) == {"commerce", "test_cases", "demo_recording_url"}
    assert review["commerce"] is False
    assert review["demo_recording_url"] == ""
    assert set(review["test_cases"]) == {"positive", "negative"}
    cases = review["test_cases"][group]
    assert len(cases) == count
    patterns = (
        r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}[- .]?\d{2}(?!\d)",
        r"(?<!\d)\d{3}[ .]?\d{4}[ .]?\d{4}[ .]?\d{4}(?!\d)",
        r"(?<!\d)\d{7}(?!\d)",
        r"(?<!\d)(?:\+?55[ .-]?)?(?:\(\d{2}\)|\d{2})[ .-]?\d{4,5}[- .]?\d{4}(?!\d)",
    )
    for case in cases:
        assert set(case) == {"description", "prompt", "tools_triggered", "expected_behavior"}
        assert all(isinstance(value, str) for value in case.values())
        assert all(case[key].strip() for key in ("description", "prompt", "expected_behavior"))
        assert case["tools_triggered"] == tool
        text = json.dumps(case, ensure_ascii=False)
        assert not any(re.search(pattern, text) for pattern in patterns)
