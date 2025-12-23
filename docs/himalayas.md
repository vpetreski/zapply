You will implement https://himalayas.app/api scrapper, follow our architecture from docs/scrapping.md, but this one will be using API.
It's public and provides all job, although you have to use pagination pause between requests to get all jobs in the last 7 days in batches of 20.

Enable this scrapper by default and I think we can't use cross scrapper dedup since this will give us job page with apply button protected
So I will have to open their job page when logged in myself and get the real job page myself, but that's ok.

Wha you have to do is to understand how api works, if we can filter Software Engineering jobs and location: real remote, Colombia, LATAM / South America
Or we will have to filter them manually.

So test and iterate scrapper until it gets us what we want: last 7 days software engineering jobs real remote or south america / latam, colombia.

Use also url slug for this scrapper dedup.

Then test and give me number of jobs in last 7 days that we are interested in. I want to lknow if this scrapper is actually valuable before i merge it.

Update docs/scrapping.md with this scrapper details.

Then push, create PR.

Additional comments from Claude:

Himalayas stands out as the only major board with timezone filtering Mev in its API, making it invaluable for identifying positions compatible with Colombia's UTC-5 timezone.
CriterionAssessmentUpdate frequencyDaily updates, jobs sorted by recencyTrue remote filtering✅ locationRestrictions array shows exact countries acceptedLATAM filtering✅ Timezone filtering via timezoneRestriction field with UTC offsetsDate filtering✅ pubDate and expiryDate fields in APICategory filtering✅ category and parentCategories arraysScraping feasibility✅ Excellent — Free JSON API + RSS feed
Technical details:

API endpoint: https://himalayas.app/jobs/api Himalayashimalayas
RSS feed: https://himalayas.app/jobs/rss Himalayashimalayas (100 most recent) HimalayasHimalayas
Pagination: ?limit=20&offset=10 (max 20 per request) Himalayashimalayas
Rate limiting: 429 errors if exceeded; himalayas implement 1-2 second delays Himalayas
No authentication required

Quality assessment: Curated listings from verified companies with detailed profiles showing tech stacks, benefits, and culture. The 100,000+ registered remote workers Himalayas suggests strong employer interest in the platform. Himalayas
Limitations: Recent API changes reduced max results to 20 per request (previously higher). Plan for pagination loops. Terms prohibit submitting to Google Jobs, LinkedIn, or Jooble