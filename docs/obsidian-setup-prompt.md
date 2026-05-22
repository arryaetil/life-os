# Obsidian Setup Prompt for LifeOS

Paste everything below the line into a fresh Claude conversation.

---

I'm setting up Obsidian as the personal layer of my LifeOS system. Here's the context:

**What LifeOS is:**
A personal AI operating system I'm building. The core is a finance tracker with a Telegram bot that acts as my Tim Grover-style financial coach. The coach has access to my real financial data (net worth, spending, budget) and uses conversation memory stored in this vault.

**The vault folder:**
The `vault/` folder inside my `finance-lifeos` repo IS my Obsidian vault. I open it directly in Obsidian. The AI reads and writes to these files.

**Current vault structure (don't change these — AI-maintained):**
```
vault/
  context/           ← system context, AI reads this
    LifeOS.md
    Current_Priorities.md
    User_Profile.md
    Operating_Rules.md
  hubs/              ← domain knowledge
    Finance.md
    Architecture.md
    Agent_Control.md
  sessions/          ← session logs + coach memory
    coach-memory.md  ← AI updates this every 10 messages
    recent-sessions.md
  projects/          ← project tracking
  decisions/         ← architecture decisions
  commands/          ← command reference
  personal/          ← my personal notes (new)
    goals.md
    values.md
    journal/
      template.md
```

**What I need you to do:**

1. **Recommend the exact Obsidian settings** I should configure (core plugins, appearance, editor settings) for a clean, fast, distraction-free experience that works well for both quick daily notes and reading AI-generated context files.

2. **Recommend community plugins** — only the ones that genuinely add value for this use case. I want:
   - Easy daily journaling
   - Being able to see my goals and coach memory at a glance
   - Linking between notes where it makes sense
   - Nothing bloated or over-engineered

3. **Write me a Dataview query** (if you recommend Dataview) that shows me a dashboard of: recent journal entries, current goals, and a link to coach-memory.md — all on one page.

4. **Set up a Home note** (`vault/Home.md`) that acts as my dashboard when I open Obsidian. It should show what matters, link to the right places, and be minimal.

5. **Set up a proper daily note template** that works with the Templater plugin. Each daily note should have: date, a space for what happened, money notes (notable spending/decisions), energy level, and one priority for tomorrow. It should auto-create in `vault/personal/journal/YYYY/MM/` so they stay organised.

6. **Give me a weekly review template** that I can fill in each Sunday. It should cover: what I accomplished, financial week summary (I'll fill in numbers), what drained me, what I want to do differently, and one goal to focus on next week.

**My style:**
- Minimal. Clean. Dark theme.
- I don't want to spend more than 5 minutes a day in Obsidian — it's a capture and review tool, not a project manager.
- The AI coach does the analysis. Obsidian is where I reflect.
- Short entries are fine. I'm not writing essays.

After setting this up, the coach in Telegram will be able to read my goals and values and use them to give me better advice. So the more honest I am in those files, the better the coaching gets.

Please give me everything as copy-paste ready content — the Home.md file, the templates, the plugin list with install names, and the exact settings to change. Keep it practical.
