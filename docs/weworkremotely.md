We will now implement our second scrapper for We Work remotely.

We will respect current scrapping architecture that is documented in scrapping.md

I have Pro account on WWR to be able to unlock Apply button for jobs, so here it the login page:

https://weworkremotely.com/job-seekers/account/login

Email: vanja@petreski.co
Password: Ue*T8Um@PiyKzzKqC@cU

So we first have to login.

Also, make sure to update .env .env.example .env.production.example and on nas: .env.production

OK, now - I found that main page with filters doesn't work properly always, filters are not applied properly, etc, so I have another better idea how to approach this.

On this page there is backend jobs listings: https://weworkremotely.com/categories/remote-back-end-programming-jobs
On this page there is fullstack jobs listings: https://weworkremotely.com/categories/remote-full-stack-programming-jobs

But also, there are RSS feeds that could serve us faster / more predictable to fetch job listings:

Backend: https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss
Fullstack: https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss

Seems like both webpages and rss feeds provide all jobs for the last month, so this is good, we will filter manually - like date and location.

First thing I need you do to is to compare webpage and rss feed to make sure that we have all jobs in rss feeds - if that's so:
We will use rss feeds to fetch jobs and filter, if rss feeds have less jobs, then we will scrape html. You have to analyze this deeply first.

Then we will fetch list of jobs from those resources making sure to include jobs only for the last week and location "Anywhere in the world" or something like that, investigate
and also from "Latin America" or something like that - investigate. Idea is to fetvch jobs that can be done from anywhere and in latin america / colombia for the last 7 days.

Also, like for Working Nomads, we will also make sure that we don't scrape details for jobs that were already fetched in our system.
To acomplish that you will also have to have a slug - and this is part of the url on WWR that points to job details page.

If job is still not in our system then we will scrape job details page and convert it to our standard format in our system.

You will notice that there is Apply button or something like that that points to real job url. So this is what we want in our system for View Job.
And this is also what we use for dedup.

Sometimes button to apply will be disabled because it will say "country not supported" or something like this - in that case skip the job.

I think that you have enmough information now to start implementation, if you have questions, ask me along the way to give me input.

Of course - when you start scrapping, both rss and playright scrapping work with real code and test live and iterate until you make it bulletproof and working properly.

Once you implement this, update scrapping.md to include this new scrapped detailed information.