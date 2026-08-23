# techpicksio.com — Superagent Prompt Library

## How to Use These

Each `.md` file contains a complete system prompt for a specialized AI agent. To use one:

1. Open a **new chat** in Claude (or your preferred AI)
2. Copy the entire content of the agent's `.md` file (everything below the `---` line)
3. Paste it as the first message, OR set it as a custom system prompt / project instruction
4. Then start giving it tasks specific to techpicksio.com

Each agent is designed to work independently, but they complement each other. Use them in this order for a full site improvement cycle:

## The Agents

| # | Agent | File | Use When... |
|---|-------|------|-------------|
| 1 | **UI/UX Design Architect** | `AGENT-1_UI-UX-Designer.md` | You want to improve visual design, readability, mobile experience, or conversion elements (buttons, tables, product cards) |
| 2 | **SEO/GEO/LLMO Strategist** | `AGENT-2_SEO-GEO-LLMO-Strategist.md` | You want to boost organic search traffic, get cited by AI engines, or plan new content targeting specific keywords |
| 3 | **Content Writer** | `AGENT-3_Content-Writer.md` | You need a new article written, or want to expand/improve an existing one — guaranteed to stay within your research-based framing |
| 4 | **Compliance Auditor** | `AGENT-4_Compliance-Auditor.md` | You want to check that FTC disclosures, Amazon Associates rules, IP claims, and privacy policies are all accurate and up to date |
| 5 | **Schema & Structured Data** | `AGENT-5_Schema-Structured-Data.md` | You want to add or fix JSON-LD schema markup for rich snippets and better AI-engine parsing |

## Recommended Workflow

**Before publishing new content:**
1. Use **Agent 3** (Content Writer) to draft the article
2. Use **Agent 4** (Compliance Auditor) to check it for FTC/Amazon/IP issues
3. Use **Agent 5** (Schema) to generate the JSON-LD markup
4. Use **Agent 1** (UI/UX) to review the visual layout and conversion elements

**Monthly maintenance:**
1. Use **Agent 2** (SEO/GEO/LLMO) for a traffic audit and content planning
2. Use **Agent 4** (Compliance) for a full-site compliance sweep
3. Use **Agent 1** (UI/UX) for any design improvements based on what's working

## Important: What All Agents Share

Every agent is built with these non-negotiable constraints baked in:
- **Research-based content only** — no agent will ever write or recommend content that claims hands-on testing
- **Static HTML / GitHub Pages** — no agent will suggest WordPress, JavaScript frameworks, or server-side tools
- **Amazon Associates compliance** — every agent respects the program's operating agreement
- **No fabrication** — no fake reviews, ratings, testimonials, or credentials

These constraints are embedded in each prompt so you don't have to re-explain them every time.
