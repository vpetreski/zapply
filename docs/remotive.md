We will implement our 3rd scrapper for Remotive, use existing architecture described in scrapping.md and make this scrapper enabled by default like others.

We have to login first at https://remotive.com/web/login because I use premium account that unlocks more jobs.

Email: vanja@petreski.co
Pass: djq2CUR5gxj.aqr@utd

Update .env .env.example .env.production.example and .env.production on NAS.

We will use Playwright to scrape job listings and job details similar like we do for Working Nomads.

If you open this page: https://remotive.com/remote-jobs/software-development?location=Worldwide%2CLatin+America+%28LATAM%29%2CColombia
Filters will be set:
Location: Worldwide, Latin America (LATAM) and Colombia.
Software Development

There will be a list of jobs, first one will be pinned / sponsored / featured ones
Then after that they will start coming sorted by date - new ones first then older ones.
We can see that by flags like: New, 3d ago, 1d ago, 1wk ago, etc

Similar like for Working Nomads at the bottom is button "More Jobs" that we have to click to load more jobs until jobs with 2wks ago start appearing.
Then we don't have to load more jobs because we are interested in jobs in the last 7 days / 1 week.

So basically in the given page we have to load jobs for the last 7 days with those filters then open each job to get to the job details.

Again, detect and use job details url slug to understand which jobs we already have in the system - those we have to skip and just ingest jobs we don't have.

On the job details page there is a button "Apply for this position" which will open in new window real job page - this is the url we want to store
So that when we click our View Job button it leads to real job page. And we also use that for possible dedup process we have in place.

This will also work in parallel with other scrappers and whos UI logs, etc.

This is enough so you can start implementing - do real testing with real code and iterate until you make scrapper working.

Once done - update scrapping.md to add info about this new scrapper.

Then push, create PR and I will test and review, go!