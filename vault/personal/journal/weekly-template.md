<%*
const date = tp.date.now("YYYY-MM-DD");
const year = tp.date.now("YYYY");
const week = tp.date.now("WW");
const folder = `personal/journal/weekly`;
await tp.file.move(`${folder}/${year}-W${week}`);
-%>
# Week <% tp.date.now("WW") %> · <% tp.date.now("YYYY") %>

<% tp.date.now("YYYY-MM-DD") %>

---

## Wins
_What actually moved the needle this week?_

- 

## Wealth
_Net worth change, spending, income. Any financial decisions._

- Current NW: €
- Notable: 

## Business
_LifeOS, consultancy, CloudCast — what progressed?_

- 

## Skills
_What did you learn or practice?_

- 

## Fitness
_Training, weight, energy levels._

- Weight: kg
- Training: 

## Execution
_Deep work hours, focus quality, habits held._

- 

## Knowledge
_Books, frameworks, ideas worth keeping._

- 

## Network
_Conversations, connections, opportunities._

- 

---

## Next Week
_One thing that matters most._

- 

## What to drop or fix
_What wasted time or energy this week?_

- 
