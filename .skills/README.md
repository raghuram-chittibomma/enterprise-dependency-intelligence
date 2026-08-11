# Project Skill Overlay

This directory holds **this project's own** domain-specific checklists — served via the `list_project_skills` / `get_project_skill` MCP tools, resolved against `paths.project_skills` in `sdlc.project.yaml`.

Do **not** put generic, reusable-across-projects skills here — those belong upstream in the `enterprise-sdlc-mcp` catalog (`enterprise_sdlc_mcp/catalog/skills/`) so every consuming project benefits. Add a file here only when a checklist genuinely only makes sense for this project's specific domain (e.g. a checklist for reviewing changes to this project's own pricing model, a proprietary integration, or a bespoke compliance rule).

## Format

Same shape as a catalog skill:

```markdown
# Skill: <Name>

Used by: <Agent Role(s)>.

## Checklist

- [ ] <item>
```

`{{project.*}}` placeholders work the same way here as in catalog skills.

Empty by default — delete this note once the project has its first real overlay skill.
