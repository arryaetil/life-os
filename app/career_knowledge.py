"""Career knowledge base seed. LinkedIn (25-10-2026) is the leading source; the AI-drafted
Codex brief only adds unverified items that must be confirmed before use in applications."""

KNOWLEDGE_BASE_VERSION = 3

LINKEDIN = "LinkedIn profile, 2026-10-25"
BRIEF = "Codex career brief (self-reported, AI-drafted; not leading)"
REVIEW = "User, CV review 2026-10-25"

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
    ("experience", "ibc group — AI Engineering Intern", "Full-time AI Engineering Intern at ibc group (formerly Etil), Aachen (hybrid), since September 2026. Builds AI prototypes end-to-end, from requirements to working demo, with code reviewed by senior developers; develops generative-AI applications and agents in Python with Microsoft Foundry, Azure and Dify, using Git and DevOps practices.", "user_confirmed", REVIEW),
    ("experience", "Etil — Solution Engineer", "Part-time Solution Engineer at Etil (now part of ibc group), Sittard, November 2025 – August 2026. Analysed client requirements and translated them into data and software solutions, and presented solution demos and prototypes to clients and colleagues.", "user_confirmed", REVIEW),
    ("experience", "Etil — data and BI", "Early in the Etil role (from November 2025) built data models and reports with SQL, PostgreSQL and Microsoft Power BI. Use only for vacancies where data or BI is relevant.", "user_confirmed", REVIEW),
    ("experience", "Event Staff", "Part-time event staff at Beverly Food and Beverage (also known as Bevers & Bevers), Belgium, August 2022 – November 2025: customer service in high-pressure environments.", "user_confirmed", REVIEW),
    # Projects (describe what a tool does; internal names mean nothing to recruiters)
    ("project", "Multilingual sales assistant", "At ibc group, built a multilingual (EN/NL/DE) proof of concept in which sales teams capture a client's business context through a guided conversation and get answers grounded in approved company documents (FastAPI, Azure AI Foundry). Internal name: SIP.", "user_confirmed", REVIEW + "; github.com/arryaetil/sip-poc"),
    ("project", "Lead finder", "Worked on a lead-finding feature in the sales assistant that searches public sources and job postings for potential clients. Use for sales and business-development vacancies.", "user_confirmed", REVIEW),
    ("project", "Public-source research tools", "At Etil, built research tools that collect and check public information on companies and people, for customer due diligence and negative-news screening, with a human reviewer making the final call (Python, FastAPI, LangGraph). Internal names: KYC4etil, KYCX.", "user_confirmed", REVIEW + "; github.com/arryaetil/KYC4etil"),
    ("project", "AI voice agents", "At Etil, configured and tested AI voice agents built with Synthflow that handle customer phone calls.", "user_confirmed", REVIEW),
    ("project", "Weather-based revenue forecasting", "Co-developed with two fellow students an automated Power BI dashboard that combines weather forecasts with historical sales data to predict daily revenue seven days ahead, using a regression model, Python, Power Query (ETL) and Azure cloud storage.", "user_confirmed", LINKEDIN),
    # Development, volunteering, languages
    ("certification", "Microsoft AI-103", "Preparing for Microsoft certification AI-103 (exam planned November 2026). Not yet obtained.", "user_confirmed", "User, 2026"),
    ("volunteer", "Toastmasters Maastricht", "Member of Toastmasters Maastricht (public speaking), September 2025 – August 2026.", "user_confirmed", LINKEDIN),
    ("volunteer", "KSA scouting leader", "Scouting leader at KSA Nationaal, September 2019 – August 2021.", "user_confirmed", LINKEDIN),
    ("language", "Languages", "Dutch and English; proficiency levels to be confirmed.", "unverified", BRIEF),
    # Self-reported in the brief, not on LinkedIn: confirm before use
    ("project", "KotStart web application", "Worked on a commercial client web application with React, TypeScript, Supabase, Railway and Resend.", "unverified", BRIEF),
    ("project", "Freelance website sales", "Approached local businesses (including cold calling), held discovery conversations and presented website proposals and demos.", "unverified", BRIEF),
    ("project", "Voice-agent prototype", "Superseded by 'AI voice agents'.", "unverified", "Replaced in CV review"),
    ("project", "Voice-agent call analytics", "Superseded by 'Etil — data and BI'.", "unverified", "Replaced in CV review"),
    ("skill", "Docker", "Docker", "unverified", BRIEF + "; not listed on LinkedIn"),
    # Conflicts between sources, resolved in the CV review
    ("conflict", "Degree wording", "Resolved: the major is Information Management. 'Emerging Markets / EMI' in the brief was wrong.", "user_confirmed", REVIEW),
    ("conflict", "Etil job title", "Resolved: use 'Solution Engineer (part-time)', not 'Junior Solution Engineer' or 'Working Student'.", "user_confirmed", REVIEW),
    ("conflict", "Event staff employer", "Resolved: 'Beverly Food and Beverage' and 'Bevers & Bevers' are the same employer; use Beverly Food and Beverage.", "user_confirmed", REVIEW),
    # Goals and writing rules for generated CVs
    ("career_goal", "Return to Etil", "Plans to return to Etil / ibc group as Junior AI Solution Engineer after the internship. A goal, not a current position: never list it as a job.", "user_confirmed", REVIEW),
    ("cv_guideline", "Describe what tools do", "Describe what a tool or project does instead of its internal name (no 'KYC4etil', 'SIP' or 'KYCX' as titles).", "user_confirmed", REVIEW),
    ("cv_guideline", "No client names", "Do not name clients (such as voice-agent clients) on CVs or letters without explicit permission.", "user_confirmed", REVIEW),
    ("cv_guideline", "Developer-built parts", "JavaScript and C# parts of team projects are built by developers; do not list them as own skills. Python is the main own language.", "user_confirmed", REVIEW),
    # Superseded entries from the first seed
    ("education", "Current education", "Superseded by 'Bachelor (in progress)'.", "unverified", "Replaced by LinkedIn"),
    ("experience", "Solution engineering", "Superseded by 'Etil — Solution Engineer'.", "unverified", "Replaced by LinkedIn"),
    ("project", "AI applications", "Superseded by specific project and experience entries.", "unverified", "Replaced by LinkedIn"),
]
FACTS += [("skill", skill, skill, "user_confirmed", LINKEDIN) for skill in LINKEDIN_SKILLS]
