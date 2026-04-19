from zephyr.models import Architecture

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
  <style>
    body {{
      font-family: system-ui, -apple-system, sans-serif;
      margin: 2rem auto;
      max-width: 1100px;
      background: #f7f8fa;
      color: #1a1a1a;
    }}
    h1 {{ font-size: 1.4rem; margin-bottom: 0.2rem; }}
    .description {{ color: #555; font-size: 0.9rem; margin-bottom: 2rem; }}
    .diagram {{
      background: #fff;
      padding: 2rem;
      border-radius: 8px;
      box-shadow: 0 1px 4px rgba(0,0,0,.08);
      overflow-x: auto;
    }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  {description_block}
  <div class="diagram">
    <div class="mermaid">
{mermaid}
    </div>
  </div>
  <script>mermaid.initialize({{ startOnLoad: true, theme: 'default' }});</script>
  {livereload_script}
</body>
</html>
"""

_LIVERELOAD_SCRIPT = """\
<script>
(function() {
  var last = null;
  setInterval(function() {
    fetch(location.href + '?_t=' + Date.now(), {{cache: 'no-store'}})
      .then(function(r) {{ return r.text(); }})
      .then(function(html) {{
        if (last !== null && html !== last) {{ location.reload(); }}
        last = html;
      }}).catch(function() {{}});
  }, 1000);
})();
</script>"""

_TYPE_TO_CLASS = {
    "actor": "actor",
    "endpoint": "endpoint",
    "identity": "identity",
    "identity-provider": "identity",
    "cloud-identity": "identity",
    "on-prem-identity": "identity",
    "access-gateway": "gateway",
    "remote-access": "gateway",
    "access-policy": "policy",
    "security-control": "policy",
    "device-management": "mgmt",
    "pki": "mgmt",
    "application": "app",
    "on-prem-resource": "app",
}

_CLASS_DEFS = {
    "actor":    "fill:#d4edda,stroke:#28a745,color:#000",
    "endpoint": "fill:#e2e3e5,stroke:#6c757d,color:#000",
    "identity": "fill:#e2d9f3,stroke:#6f42c1,color:#000",
    "gateway":  "fill:#fff3cd,stroke:#fd7e14,color:#000",
    "policy":   "fill:#cce5ff,stroke:#004085,color:#000",
    "mgmt":     "fill:#d1ecf1,stroke:#0c5460,color:#000",
    "app":      "fill:#f8d7da,stroke:#721c24,color:#000",
}


def _node_id(name: str) -> str:
    return name.replace("-", "_").replace(" ", "_")


def _flow_label(label: str, authentication: str, encryption: str) -> str:
    parts = [p for p in [label, authentication, encryption] if p]
    return " | ".join(parts) if parts else ""


def to_mermaid(architecture: Architecture) -> str:
    lines = ["graph TD"]
    lines.append("")

    # classDef blocks
    for class_name, style in _CLASS_DEFS.items():
        lines.append(f"    classDef {class_name} {style}")
    lines.append("")

    # nodes
    class_assignments: list[tuple[str, str]] = []
    for component in architecture.components:
        node_id = _node_id(component.name)
        lines.append(f'    {node_id}["{component.name} ({component.type})"]')
        css_class = _TYPE_TO_CLASS.get(component.type)
        if css_class:
            class_assignments.append((node_id, css_class))

    if class_assignments:
        lines.append("")
        for node_id, css_class in class_assignments:
            lines.append(f"    class {node_id} {css_class}")

    lines.append("")

    # edges
    for flow in architecture.flows:
        source = _node_id(flow.source)
        target = _node_id(flow.target)
        label = _flow_label(flow.label, flow.authentication, flow.encryption)
        if label:
            lines.append(f"    {source} -->|{label}| {target}")
        else:
            lines.append(f"    {source} --> {target}")

    return "\n".join(lines)


def to_html(architecture: Architecture, livereload: bool = False) -> str:
    mermaid = to_mermaid(architecture)
    description_block = (
        f'<p class="description">{architecture.description}</p>'
        if architecture.description
        else ""
    )
    return _HTML_TEMPLATE.format(
        title=architecture.name,
        description_block=description_block,
        mermaid=mermaid,
        livereload_script=_LIVERELOAD_SCRIPT if livereload else "",
    )
