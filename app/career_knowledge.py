"""Career knowledge base seed. LinkedIn (25-10-2026) is the leading source; the AI-drafted
Codex brief only adds unverified items that must be confirmed before use in applications."""

KNOWLEDGE_BASE_VERSION = 2

LINKEDIN = "LinkedIn profile, 2026-10-25"
BRIEF = "Codex career brief (self-reported, AI-drafted; not leading)"

LINKEDIN_SKILLS = (
    "Python", "SQL", "PostgreSQL", "FastAPI", "Git", "GitHub", "DevOps", "Systems Design",
    "Microsoft Azure", "Microsoft Foundry", "Dify", "n8n", "Generative AI", "AI video tools",
    "Microsoft Power BI", "Microsoft Power Automate", "Microsoft Excel", "Forecasting", "Statistics",
    "Mathematics", "Requirements Analysis", "Product Thinking", "Start-up Ventures",
    "Presentation Skills", "Customer Service", "High-Pressure Environments",
)

FACTS = [
    # Education
    ("education", "Bachelor (in progress)", "BSc Economics and Business Economics, major Information Management, Maastricht University School of Business and Economics, 2024–2027. Degree not yet obtained.", "user_confirmed", LINKEDIN),
    ("education", "Secondary education", "Secondary diploma in Sciences–Mathematics (Wetenschappen-Wiskunde), Stedelijke Humaniora Dilsen, 2016–2022.", "user_confirmed", LINKEDIN),
    # Experience
    ("experience", "ibc group — AI Engineering Intern", "AI Engineering Intern at ibc group, Aachen (hybrid), since September 2026, working with Microsoft Foundry, Microsoft Azure, Dify, generative AI, Python, Git, DevOps and systems design.", "user_confirmed", LINKEDIN),
    ("experience", "Etil — Solution Engineer", "Part-time Solution Engineer at Etil (now part of ibc group), Sittard, since November 2025, working on requirements analysis, SQL, PostgreSQL and Microsoft Power BI.", "user_confirmed", LINKEDIN),
    ("experience", "Event Staff", "Part-time event staff at Beverly Food and Beverage, Belgium, August 2022 – November 2025: customer service in high-pressure environments.", "user_confirmed", LINKEDIN),
    # Projects
    ("project", "Weather-based revenue forecasting", "Co-developed with two fellow students an automated Power BI dashboard that combines weather forecasts with historical sales data to predict daily revenue seven days ahead, using a regression model, Python, Power Query (ETL) and Azure cloud storage.", "user_confirmed", LINKEDIN),
    # Development, volunteering, languages
    ("certification", "Microsoft AI-103", "Preparing for Microsoft certification AI-103 (exam planned November 2026). Not yet obtained.", "user_confirmed", "User, 2026"),
    ("volunteer", "Toastmasters Maastricht", "Member of Toastmasters Maastricht (public speaking), September 2025 – August 2026.", "user_confirmed", LINKEDIN),
    ("volunteer", "KSA scouting leader", "Scouting leader at KSA Nationaal, September 2019 – August 2021.", "user_confirmed", LINKEDIN),
    ("language", "Languages", "Dutch and English; proficiency levels to be confirmed.", "unverified", BRIEF),
    # Self-reported in the brief, not on LinkedIn: confirm before use
    ("project", "KotStart web application", "Worked on a commercial client web application with React, TypeScript, Supabase, Railway and Resend.", "unverified", BRIEF),
    ("project", "Freelance website sales", "Approached local businesses (including cold calling), held discovery conversations and presented website proposals and demos.", "unverified", BRIEF),
    ("project", "Voice-agent prototype", "Built a voice-agent prototype with Synthflow.", "unverified", BRIEF),
    ("project", "Voice-agent call analytics", "Built Power BI dashboards on voice-agent telephone interactions.", "unverified", BRIEF),
    ("skill", "Docker", "Docker", "unverified", BRIEF + "; not listed on LinkedIn"),
    # Conflicts between sources, kept visible until resolved
    ("conflict", "Degree wording", "Brief says specialisation 'Emerging Markets / EMI'; LinkedIn says major Information Management. LinkedIn wording is used.", "unverified", f"{BRIEF} vs {LINKEDIN}"),
    ("conflict", "Etil job title", "Brief says 'Junior Solution Engineer'; LinkedIn says 'Solution Engineer'. LinkedIn title is used.", "unverified", f"{BRIEF} vs {LINKEDIN}"),
    ("conflict", "Event staff employer", "LinkedIn experience says 'Beverly Food and Beverage'; LinkedIn skills page says 'Bevers & Bevers'.", "unverified", LINKEDIN),
    # Superseded entries from the first seed
    ("education", "Current education", "Superseded by 'Bachelor (in progress)'.", "unverified", "Replaced by LinkedIn"),
    ("experience", "Solution engineering", "Superseded by 'Etil — Solution Engineer'.", "unverified", "Replaced by LinkedIn"),
    ("project", "AI applications", "Superseded by specific project and experience entries.", "unverified", "Replaced by LinkedIn"),
]
FACTS += [("skill", skill, skill, "user_confirmed", LINKEDIN) for skill in LINKEDIN_SKILLS]
