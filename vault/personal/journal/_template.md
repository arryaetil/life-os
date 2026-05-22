<%*
const date = tp.date.now("YYYY-MM-DD");
const year = tp.date.now("YYYY");
const month = tp.date.now("MM");
const targetFolder = `personal/journal/${year}/${month}`;
await tp.file.move(`${targetFolder}/${date}`);
-%>
# <% tp.date.now("YYYY-MM-DD") %>

## Today
_What happened. What you did._

- 

## Money
_Any notable spending, earning, or financial decisions today._

- 

## Energy
_How did the day feel? High/medium/low and why._


## Tomorrow
_One thing that matters._

- 
