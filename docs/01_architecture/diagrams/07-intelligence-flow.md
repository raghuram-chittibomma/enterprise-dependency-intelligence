# 07 — Intelligence flow

Deterministic analytics over the same graph; optional narrative is presentation-only.

```mermaid
flowchart TB
  subgraph inputs [Graph inputs]
    Entity[Entity + neighbors]
    Owners[Ownership]
    Caps[Capabilities]
    Meta[Criticality · lifecycle · technology]
  end

  subgraph compute [Deterministic engines]
    Risk[Change risk score FR23]
    WhatIf[Retirement what-if FR24]
    Drift[Drift signals FR25]
    Rat[Tech rationalization FR26]
  end

  subgraph present [Presentation]
    Panels[Entity / team panels]
    Pages[Drift · Rationalize pages]
    Narr[Optional LLM narrative FR27<br/>factors only — no new facts]
  end

  Entity --> Risk
  Owners --> Risk
  Caps --> Risk
  Meta --> Risk
  Entity --> WhatIf
  Meta --> Drift
  Entity --> Drift
  Meta --> Rat

  Risk --> Panels
  WhatIf --> Panels
  Drift --> Pages
  Rat --> Pages
  Risk --> Narr
  WhatIf --> Narr
```

**Team pages:** risk is a **rollup over owned systems**, not a score of the Team node itself.

What-if is **read-only**—it never mutates Neo4j (`ADR-0008`).
