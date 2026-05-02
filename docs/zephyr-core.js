// zephyr-core.js — pure JS port of Zephyr Workbench logic
// No dependencies. Runs in browser.

const ZephyrCore = (() => {

  // ── Data model enums ──────────────────────────────────────────────────────
  const DOMAINS = ["business", "application", "data", "technology"];
  const COMPONENT_TYPES = [
    "access-gateway","access-policy","actor","application","cloud-identity",
    "device-management","endpoint","identity","identity-provider",
    "on-prem-identity","on-prem-resource","pki","remote-access","security-control",
  ];
  const SEVERITIES = ["low","medium","high","critical"];
  const LIKELIHOODS = ["low","medium","high"];
  const IMPACTS = ["low","medium","high"];
  const CONTROL_TYPES = ["policy","technical","process"];
  const STAKEHOLDER_ROLES = ["owner","user","operator","security"];
  const ENVIRONMENTS = ["prod","test","dev"];
  const CRITICALITIES = ["low","medium","high","mission-critical"];
  const EXPOSURES = ["internal","external"];
  const LIFECYCLES = ["planned","active","deprecated"];
  const FLOW_DIRECTIONS = ["inbound","outbound","bidirectional"];
  const AUTH_TYPES = ["none","password","mfa","certificate"];
  const ENCRYPTION_TYPES = ["none","tls","ipsec"];

  // ── Validation ────────────────────────────────────────────────────────────
  function validate(data) {
    const errors = [];
    const warnings = [];

    // Required top-level
    for (const f of ["name","components","flows"]) {
      if (!(f in data)) errors.push(`missing required field: ${f}`);
    }
    if (errors.length) return { errors, warnings };

    if (typeof data.name !== "string") errors.push("'name' must be a string");

    const components = Array.isArray(data.components) ? data.components : [];
    const flows = Array.isArray(data.flows) ? data.flows : [];
    const risks = Array.isArray(data.risks) ? data.risks : [];
    const controls = Array.isArray(data.controls) ? data.controls : [];
    const stakeholders = Array.isArray(data.stakeholders) ? data.stakeholders : [];

    if (!Array.isArray(data.components) || data.components.length === 0)
      errors.push("'components' must be a non-empty list");

    // Components
    const componentNames = new Set();
    const componentTypes = {};
    for (let i = 0; i < components.length; i++) {
      const c = components[i];
      const loc = `components[${i+1}]`;
      if (typeof c !== "object" || !c) { errors.push(`${loc} must be a mapping`); continue; }
      if (!c.name) errors.push(`${loc}.name is required`);
      else if (componentNames.has(c.name)) errors.push(`duplicate component name: ${c.name}`);
      else componentNames.add(c.name);
      if (!c.type) errors.push(`${loc}.type is required`);
      else if (!COMPONENT_TYPES.includes(c.type)) errors.push(`${loc}.type '${c.type}' is invalid`);
      if (c.domain && !DOMAINS.includes(c.domain)) errors.push(`${loc}.domain '${c.domain}' is invalid`);
      if (c.criticality && !CRITICALITIES.includes(c.criticality)) errors.push(`${loc}.criticality '${c.criticality}' is invalid`);
      if (c.exposure && !EXPOSURES.includes(c.exposure)) errors.push(`${loc}.exposure '${c.exposure}' is invalid`);
      if (c.lifecycle && !LIFECYCLES.includes(c.lifecycle)) errors.push(`${loc}.lifecycle '${c.lifecycle}' is invalid`);
      if (c.name && c.type) componentTypes[c.name] = c.type;
    }

    // Flows
    for (let i = 0; i < flows.length; i++) {
      const f = flows[i];
      const loc = `flows[${i+1}]`;
      if (typeof f !== "object" || !f) { errors.push(`${loc} must be a mapping`); continue; }
      if (!f.from) errors.push(`${loc}.from is required`);
      else if (!componentNames.has(f.from)) errors.push(`${loc}.from '${f.from}' does not match any component`);
      if (!f.to) errors.push(`${loc}.to is required`);
      else if (!componentNames.has(f.to)) errors.push(`${loc}.to '${f.to}' does not match any component`);
      if (f.authentication && !AUTH_TYPES.includes(f.authentication)) errors.push(`${loc}.authentication '${f.authentication}' is invalid`);
      if (f.encryption && !ENCRYPTION_TYPES.includes(f.encryption)) errors.push(`${loc}.encryption '${f.encryption}' is invalid`);
      if (f.direction && !FLOW_DIRECTIONS.includes(f.direction)) errors.push(`${loc}.direction '${f.direction}' is invalid`);
      // endpoint-to-endpoint warning
      if (componentTypes[f.from] === "endpoint" && componentTypes[f.to] === "endpoint")
        warnings.push(`endpoint-to-endpoint flow detected (${f.from} → ${f.to})`);
    }

    // Risks
    const riskIds = new Set();
    for (let i = 0; i < risks.length; i++) {
      const r = risks[i];
      const loc = `risks[${i+1}]`;
      if (typeof r !== "object" || !r) { errors.push(`${loc} must be a mapping`); continue; }
      if (!r.id) errors.push(`${loc}.id is required`);
      else if (riskIds.has(r.id)) errors.push(`duplicate risk id: ${r.id}`);
      else riskIds.add(r.id);
      if (!r.title) errors.push(`${loc}.title is required`);
      if (!r.severity) errors.push(`${loc}.severity is required`);
      else if (!SEVERITIES.includes(r.severity)) errors.push(`${loc}.severity '${r.severity}' is invalid`);
      if (r.likelihood && !LIKELIHOODS.includes(r.likelihood)) errors.push(`${loc}.likelihood '${r.likelihood}' is invalid`);
      if (r.impact && !IMPACTS.includes(r.impact)) errors.push(`${loc}.impact '${r.impact}' is invalid`);
    }

    // Controls
    for (let i = 0; i < controls.length; i++) {
      const c = controls[i];
      const loc = `controls[${i+1}]`;
      if (typeof c !== "object" || !c) { errors.push(`${loc} must be a mapping`); continue; }
      if (!c.name) errors.push(`${loc}.name is required`);
      if (!c.type) errors.push(`${loc}.type is required`);
      else if (!CONTROL_TYPES.includes(c.type)) errors.push(`${loc}.type '${c.type}' is invalid`);
      if (!c.applies_to) errors.push(`${loc}.applies_to is required`);
      else if (Array.isArray(c.applies_to)) {
        for (const t of c.applies_to) {
          if (!componentNames.has(t)) errors.push(`${loc}.applies_to '${t}' does not match any component`);
        }
      }
    }

    // Stakeholders
    for (let i = 0; i < stakeholders.length; i++) {
      const s = stakeholders[i];
      const loc = `stakeholders[${i+1}]`;
      if (!s.name) errors.push(`${loc}.name is required`);
      if (!s.role) errors.push(`${loc}.role is required`);
      else if (!STAKEHOLDER_ROLES.includes(s.role)) errors.push(`${loc}.role '${s.role}' is invalid`);
    }

    // Warnings
    const gateways = Object.entries(componentTypes).filter(([,t]) => t === "access-gateway");
    if (gateways.length === 1) warnings.push(`only one access-gateway detected (${gateways[0][0]}) — single point of failure`);

    const identityTypes = new Set(["identity","identity-provider","cloud-identity","on-prem-identity"]);
    for (const f of flows) {
      if (f.authentication === "mfa" && f.to && !identityTypes.has(componentTypes[f.to]))
        warnings.push(`MFA flow target should be an identity component (${f.from} → ${f.to})`);
    }

    return { errors, warnings };
  }

  // ── Summary ───────────────────────────────────────────────────────────────
  function summarize(data) {
    return {
      name: data.name || "",
      description: data.description || "",
      components: (data.components || []).length,
      flows: (data.flows || []).length,
      risks: (data.risks || []).length,
      controls: (data.controls || []).length,
      stakeholders: (data.stakeholders || []).length,
      riskDetails: (data.risks || []),
      controlDetails: (data.controls || []),
      stakeholderDetails: (data.stakeholders || []),
      componentDetails: (data.components || []),
      flowDetails: (data.flows || []),
      meta: data.meta || {},
    };
  }

  // ── Mermaid diagram ───────────────────────────────────────────────────────
  const TYPE_TO_CLASS = {
    "actor":"actor","endpoint":"endpoint",
    "identity":"identity","identity-provider":"identity",
    "cloud-identity":"identity","on-prem-identity":"identity",
    "access-gateway":"gateway","remote-access":"gateway",
    "access-policy":"policy","security-control":"policy",
    "device-management":"mgmt","pki":"mgmt",
    "application":"app","on-prem-resource":"app",
  };
  const CLASS_DEFS = {
    actor:    "fill:#d4edda,stroke:#28a745,color:#111",
    endpoint: "fill:#e2e3e5,stroke:#6c757d,color:#111",
    identity: "fill:#e2d9f3,stroke:#6f42c1,color:#111",
    gateway:  "fill:#fff3cd,stroke:#fd7e14,color:#111",
    policy:   "fill:#cce5ff,stroke:#004085,color:#111",
    mgmt:     "fill:#d1ecf1,stroke:#0c5460,color:#111",
    app:      "fill:#f8d7da,stroke:#721c24,color:#111",
  };

  function nodeId(name) {
    return name.replace(/[-\s]/g, "_");
  }

  function toMermaid(data) {
    if (!data || !data.components) return "graph TD\n    A[No architecture loaded]";
    const lines = ["graph TD", ""];
    for (const [cls, style] of Object.entries(CLASS_DEFS)) {
      lines.push(`    classDef ${cls} ${style}`);
    }
    lines.push("");
    const assignments = [];
    for (const c of data.components) {
      const id = nodeId(c.name);
      lines.push(`    ${id}["${c.name}<br/><small>${c.type}</small>"]`);
      const cls = TYPE_TO_CLASS[c.type];
      if (cls) assignments.push([id, cls]);
    }
    if (assignments.length) {
      lines.push("");
      for (const [id, cls] of assignments) lines.push(`    class ${id} ${cls}`);
    }
    lines.push("");
    for (const f of (data.flows || [])) {
      const src = nodeId(f.from);
      const tgt = nodeId(f.to);
      const parts = [f.label, f.authentication, f.encryption].filter(Boolean);
      const label = parts.join(" · ");
      lines.push(label ? `    ${src} -->|${label}| ${tgt}` : `    ${src} --> ${tgt}`);
    }
    return lines.join("\n");
  }

  // ── Diff ──────────────────────────────────────────────────────────────────
  function diffArchitectures(a, b) {
    const result = { components: [], flows: [], risks: [] };

    const byName = (arr, key="name") => Object.fromEntries((arr||[]).map(x => [x[key], x]));

    // Components
    const ac = byName(a.components); const bc = byName(b.components);
    const allC = new Set([...Object.keys(ac), ...Object.keys(bc)]);
    for (const n of allC) {
      if (!ac[n]) result.components.push({ op: "added", item: bc[n] });
      else if (!bc[n]) result.components.push({ op: "removed", item: ac[n] });
      else {
        const changes = fieldDiff(ac[n], bc[n], ["type","description","domain","criticality","exposure","lifecycle"]);
        if (changes.length) result.components.push({ op: "modified", name: n, changes });
      }
    }

    // Flows
    const fKey = f => `${f.from}→${f.to}`;
    const af = byName(a.flows.map(f => ({...f, name: fKey(f)})));
    const bf = byName(b.flows.map(f => ({...f, name: fKey(f)})));
    const allF = new Set([...Object.keys(af), ...Object.keys(bf)]);
    for (const n of allF) {
      if (!af[n]) result.flows.push({ op: "added", item: bf[n] });
      else if (!bf[n]) result.flows.push({ op: "removed", item: af[n] });
      else {
        const changes = fieldDiff(af[n], bf[n], ["label","protocol","authentication","encryption","direction"]);
        if (changes.length) result.flows.push({ op: "modified", name: n, changes });
      }
    }

    // Risks
    const ar = byName(a.risks || [], "id"); const br = byName(b.risks || [], "id");
    const allR = new Set([...Object.keys(ar), ...Object.keys(br)]);
    for (const n of allR) {
      if (!ar[n]) result.risks.push({ op: "added", item: br[n] });
      else if (!br[n]) result.risks.push({ op: "removed", item: ar[n] });
      else {
        const changes = fieldDiff(ar[n], br[n], ["title","severity","likelihood","impact","mitigation"]);
        if (changes.length) result.risks.push({ op: "modified", id: n, changes });
      }
    }

    return result;
  }

  function fieldDiff(a, b, fields) {
    return fields.filter(f => (a[f]||"") !== (b[f]||"")).map(f => ({ field: f, from: a[f]||"", to: b[f]||"" }));
  }

  // ── Templates ─────────────────────────────────────────────────────────────
  const TEMPLATES = {
    minimal: {
      _description: "Smallest valid model — one actor, one app, one flow, one risk.",
      name: "my-architecture",
      description: "",
      meta: { version: "v1" },
      domains: ["business","application","data","technology"],
      components: [
        { name: "user", type: "actor", domain: "business", criticality: "low", exposure: "internal", lifecycle: "active" },
        { name: "app", type: "application", domain: "application", criticality: "medium", exposure: "internal", lifecycle: "active" },
      ],
      flows: [{ from: "user", to: "app", label: "uses", direction: "outbound" }],
      risks: [{ id: "R1", title: "Access control not defined", severity: "medium", likelihood: "medium", impact: "medium" }],
      controls: [], stakeholders: [],
    },
    "hybrid-identity": {
      _description: "Cloud identity + on-prem AD — Entra ID, Conditional Access, VPN, PKI.",
      name: "hybrid-identity",
      description: "Hybrid identity architecture with cloud and on-prem integration.",
      meta: { version: "v1", owner: "", environment: ["prod"], criticality: "high" },
      domains: ["business","application","data","technology"],
      components: [
        { name: "user", type: "actor", domain: "business", criticality: "low", exposure: "internal", lifecycle: "active" },
        { name: "endpoint", type: "endpoint", domain: "technology", criticality: "high", exposure: "internal", lifecycle: "active" },
        { name: "entra-id", type: "cloud-identity", domain: "application", criticality: "mission-critical", exposure: "external", lifecycle: "active" },
        { name: "conditional-access", type: "access-policy", domain: "application", criticality: "high", exposure: "external", lifecycle: "active" },
        { name: "on-prem-ad", type: "on-prem-identity", domain: "data", criticality: "mission-critical", exposure: "internal", lifecycle: "active" },
        { name: "vpn", type: "remote-access", domain: "technology", criticality: "high", exposure: "external", lifecycle: "active" },
        { name: "pki", type: "pki", domain: "technology", criticality: "high", exposure: "internal", lifecycle: "active" },
        { name: "internal-resource", type: "on-prem-resource", domain: "data", criticality: "medium", exposure: "internal", lifecycle: "active" },
      ],
      flows: [
        { from: "user", to: "endpoint", label: "signs in", direction: "outbound" },
        { from: "endpoint", to: "entra-id", label: "authenticates", protocol: "https", authentication: "mfa", encryption: "tls", direction: "outbound" },
        { from: "entra-id", to: "conditional-access", label: "evaluate policy", protocol: "https", encryption: "tls", direction: "outbound" },
        { from: "endpoint", to: "vpn", label: "connect", protocol: "ipsec", authentication: "certificate", encryption: "ipsec", direction: "outbound" },
        { from: "endpoint", to: "pki", label: "obtain certificate", protocol: "https", authentication: "certificate", encryption: "tls", direction: "outbound" },
        { from: "vpn", to: "internal-resource", label: "access", authentication: "certificate", encryption: "tls", direction: "outbound" },
      ],
      risks: [
        { id: "R1", title: "Single VPN gateway creates availability risk", severity: "high", likelihood: "medium", impact: "high", mitigation: "Deploy redundant VPN gateways across availability zones." },
        { id: "R2", title: "Trust boundary between cloud and on-prem identity unclear", severity: "high", likelihood: "high", impact: "high", mitigation: "Implement Entra ID Kerberos and enforce Conditional Access for on-prem resource access." },
        { id: "R3", title: "Certificate expiry may silently break access", severity: "medium", likelihood: "medium", impact: "high", mitigation: "Configure auto-renewal via SCEP and alert on upcoming expirations." },
      ],
      controls: [
        { name: "enforce-mfa", type: "technical", applies_to: ["entra-id","conditional-access"], description: "Require MFA for all cloud identity authentication flows." },
        { name: "cert-renewal", type: "process", applies_to: ["pki","endpoint"], description: "Quarterly certificate review with automated SCEP renewal." },
      ],
      stakeholders: [
        { name: "platform-team", role: "owner" },
        { name: "it-security", role: "security" },
      ],
    },
    "zero-trust": {
      _description: "Never trust, always verify — identity-first access with MFA and policy enforcement.",
      name: "zero-trust",
      description: "Zero-trust architecture: all access is authenticated, authorised, and encrypted.",
      meta: { version: "v1", owner: "", environment: ["prod"], criticality: "mission-critical" },
      domains: ["business","application","data","technology"],
      components: [
        { name: "user", type: "actor", domain: "business", criticality: "low", exposure: "external", lifecycle: "active" },
        { name: "device", type: "endpoint", domain: "technology", criticality: "high", exposure: "external", lifecycle: "active" },
        { name: "device-management", type: "device-management", domain: "application", criticality: "high", exposure: "external", lifecycle: "active" },
        { name: "identity-provider", type: "identity-provider", domain: "application", criticality: "mission-critical", exposure: "external", lifecycle: "active" },
        { name: "mfa-service", type: "security-control", domain: "application", criticality: "mission-critical", exposure: "external", lifecycle: "active" },
        { name: "access-gateway", type: "access-gateway", domain: "technology", criticality: "mission-critical", exposure: "external", lifecycle: "active" },
        { name: "access-policy", type: "access-policy", domain: "application", criticality: "high", exposure: "external", lifecycle: "active" },
        { name: "protected-resource", type: "application", domain: "application", criticality: "high", exposure: "internal", lifecycle: "active" },
      ],
      flows: [
        { from: "user", to: "device", label: "operates", direction: "outbound" },
        { from: "device", to: "device-management", label: "enroll and attest", protocol: "https", authentication: "certificate", encryption: "tls", direction: "outbound" },
        { from: "device", to: "identity-provider", label: "authenticate", protocol: "https", authentication: "mfa", encryption: "tls", direction: "outbound" },
        { from: "identity-provider", to: "mfa-service", label: "verify second factor", protocol: "https", encryption: "tls", direction: "outbound" },
        { from: "identity-provider", to: "access-policy", label: "evaluate trust signal", protocol: "https", encryption: "tls", direction: "outbound" },
        { from: "device", to: "access-gateway", label: "request access", protocol: "https", authentication: "certificate", encryption: "tls", direction: "outbound" },
        { from: "access-gateway", to: "protected-resource", label: "forward authorised request", protocol: "https", encryption: "tls", direction: "outbound" },
      ],
      risks: [
        { id: "R1", title: "Identity provider is a single point of trust failure", severity: "critical", likelihood: "low", impact: "high", mitigation: "Deploy identity provider in high-availability configuration with failover." },
        { id: "R2", title: "Device attestation not enforced at access gateway", severity: "high", likelihood: "medium", impact: "high", mitigation: "Require device compliance signal from device-management before forwarding requests." },
        { id: "R3", title: "Access policy gaps may allow lateral movement", severity: "high", likelihood: "medium", impact: "high", mitigation: "Apply least-privilege policies per resource and review quarterly." },
      ],
      controls: [
        { name: "continuous-verification", type: "technical", applies_to: ["identity-provider","access-gateway","access-policy"], description: "Re-verify identity and device posture on every request, not just at login." },
        { name: "least-privilege-policy", type: "policy", applies_to: ["access-policy","protected-resource"], description: "Grant minimum required permissions per resource; no standing access." },
        { name: "access-review", type: "process", applies_to: ["access-policy"], description: "Quarterly review of all access policies and permission grants." },
      ],
      stakeholders: [
        { name: "security-team", role: "security" },
        { name: "platform-team", role: "owner" },
        { name: "end-users", role: "user" },
      ],
    },
  };

  function getTemplate(name) {
    const t = TEMPLATES[name];
    if (!t) return null;
    return Object.fromEntries(Object.entries(t).filter(([k]) => !k.startsWith("_")));
  }

  function templateNames() {
    return Object.entries(TEMPLATES).map(([name, t]) => ({
      name,
      description: t._description || "",
    }));
  }

  // ── YAML serialisation (simple, no dependency) ────────────────────────────
  function toYaml(obj, indent=0) {
    const pad = "  ".repeat(indent);
    if (obj === null || obj === undefined) return "null";
    if (typeof obj === "boolean") return obj ? "true" : "false";
    if (typeof obj === "number") return String(obj);
    if (typeof obj === "string") {
      if (obj.includes("\n") || obj.includes(":") || obj.includes("#") || obj.startsWith(" "))
        return `>-\n${pad}  ` + obj.replace(/\n/g, `\n${pad}  `);
      return obj;
    }
    if (Array.isArray(obj)) {
      if (obj.length === 0) return "[]";
      if (obj.every(x => typeof x === "string" || typeof x === "number"))
        return "[" + obj.map(x => toYaml(x)).join(", ") + "]";
      return "\n" + obj.map(x => `${pad}- ${toYaml(x, indent+1).trimStart()}`).join("\n");
    }
    if (typeof obj === "object") {
      const keys = Object.keys(obj).filter(k => obj[k] !== undefined && obj[k] !== "" && !(Array.isArray(obj[k]) && obj[k].length===0));
      if (keys.length === 0) return "{}";
      return "\n" + keys.map(k => {
        const v = obj[k];
        const rendered = toYaml(v, indent+1);
        if (rendered.startsWith("\n")) return `${pad}${k}:${rendered}`;
        return `${pad}${k}: ${rendered}`;
      }).join("\n");
    }
    return String(obj);
  }

  function objToYaml(obj) {
    return toYaml(obj, 0).trim();
  }

  return {
    validate,
    summarize,
    toMermaid,
    diffArchitectures,
    getTemplate,
    templateNames,
    objToYaml,
    COMPONENT_TYPES,
    CRITICALITIES,
    EXPOSURES,
    LIFECYCLES,
    AUTH_TYPES,
    ENCRYPTION_TYPES,
    FLOW_DIRECTIONS,
    SEVERITIES,
    DOMAINS,
  };
})();

// Export to window
window.ZephyrCore = ZephyrCore;
