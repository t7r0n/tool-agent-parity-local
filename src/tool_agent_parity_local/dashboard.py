from __future__ import annotations

from jinja2 import Template

from .models import SuiteSummary

HTML = Template(
    """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tool Agent Parity Local</title>
<style>
:root{color-scheme:light dark;--bg:#f7f9fc;--fg:#172033;--muted:#65718a;--card:#fff;--line:#dce4ef;--a:#236f84;--b:#6e8f37;--w:#a55f17}
@media (prefers-color-scheme: dark){:root{--bg:#10141a;--fg:#eef4f8;--muted:#a7b2c0;--card:#181f28;--line:#2d3847;--a:#80c8dd;--b:#b2d06a;--w:#efb25d}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
header,main{max-width:1180px;margin:auto;padding:28px}h1{margin:0;font-size:clamp(2rem,4vw,4rem);letter-spacing:0}h2{margin:0 0 14px;font-size:1.05rem}p{color:var(--muted);max-width:780px;line-height:1.45}
.grid{display:grid;gap:16px}.metrics{grid-template-columns:repeat(4,minmax(0,1fr))}.cols{grid-template-columns:1fr 1fr}.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:18px;box-shadow:0 10px 24px rgba(20,31,50,.06)}
.metric strong{display:block;font-size:2rem;color:var(--a)}.metric span{color:var(--muted)}.bar{height:12px;border-radius:999px;overflow:hidden;background:color-mix(in srgb,var(--line),var(--card) 35%)}.bar i{display:block;height:100%;background:var(--b)}
table{width:100%;border-collapse:collapse;font-size:.9rem}th,td{text-align:left;padding:10px 8px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--muted)}code{color:var(--a);white-space:nowrap}.ok{color:var(--b);font-weight:700}.warn{color:var(--w);font-weight:700}
@media(max-width:820px){header,main{padding:20px}.metrics,.cols{grid-template-columns:1fr}table{font-size:.82rem}}
</style></head>
<body><header><h1>Tool Agent Parity Local</h1><p>Deterministic schema lift, description synthesis, and record/replay parity checks for migrating tool bundles into agent metadata.</p></header>
<main class="grid">
<section class="grid metrics">
<div class="card metric"><strong>{{ summary.bundle_count }}</strong><span>Bundles</span></div>
<div class="card metric"><strong>{{ "%.0f"|format(summary.parity_pass_rate*100) }}%</strong><span>Parity pass rate</span></div>
<div class="card metric"><strong>{{ "%.0f"|format(summary.tool_selection_accuracy*100) }}%</strong><span>Tool selection</span></div>
<div class="card metric"><strong>{{ summary.median_added_lines }}</strong><span>Median added lines</span></div>
</section>
<section class="grid cols"><div class="card"><h2>Migration Gates</h2>
{% for label,value,target in gates %}<div style="margin-bottom:14px"><div style="display:flex;justify-content:space-between;margin-bottom:6px"><span>{{ label }}</span><span class="{{ 'ok' if value >= target else 'warn' }}">{{ value }}</span></div><div class="bar"><i style="width:{{ [100,(value/target*100)|int]|min }}%"></i></div></div>{% endfor %}
</div><div class="card"><h2>Run Summary</h2><p>Scenarios: <strong>{{ summary.scenario_count }}</strong></p><p>Build-to-demo: <strong>{{ summary.build_to_demo_minutes }} min</strong></p><p>P95 eval latency: <strong>{{ summary.p95_eval_latency_ms }} ms</strong></p><p>Status: <span class="{{ 'ok' if summary.pass_gates else 'warn' }}">{{ 'PASS' if summary.pass_gates else 'FAIL' }}</span></p></div></section>
<section class="card"><h2>Bundle Samples</h2><table><thead><tr><th>Bundle</th><th>Scenarios</th><th>Parity</th><th>Tool Accuracy</th><th>Added Lines</th></tr></thead><tbody>
{% for row in details[:12] %}<tr><td><code>{{ row.summary.bundle_id }}</code></td><td>{{ row.summary.scenarios }}</td><td class="{{ 'ok' if row.summary.parity_pass_rate >= 0.95 else 'warn' }}">{{ row.summary.parity_pass_rate }}</td><td>{{ row.summary.tool_selection_accuracy }}</td><td>{{ row.summary.estimated_added_lines }}</td></tr>{% endfor %}
</tbody></table></section>
</main></body></html>"""
)


def render_dashboard(summary: SuiteSummary, details: list[dict[str, object]]) -> str:
    gates = [
        ("Parity pass rate", summary.parity_pass_rate, 0.95),
        ("Tool selection", summary.tool_selection_accuracy, 0.85),
        ("Line budget headroom", round(max(0.0, 1 - summary.median_added_lines / 31), 3), 0.03),
    ]
    return HTML.render(summary=summary, details=details, gates=gates)
