We will implement new scrapper for https://dailyremote.com using Playwright and according to our scrapping.md architecture like for other scrappers.

We will enable it by default and test and iterate implementation using real code until you are sure it works properly.

First, we have to open this link since it will automatically log in for us: https://dailyremote.com/premium/activate?action=reactivate&token=25fe7e53-fe7e-417f-918b-8d3374bdc6c3

We will have to do scrapping 3 times since it's not possible to create Location filter including multiple locations so:

1. https://dailyremote.com/remote-software-development-jobs?page=1&sort_by=time&location_region=Worldwide#main
2. https://dailyremote.com/remote-software-development-jobs?page=1&sort_by=time&location_region=South%20America#main
3. https://dailyremote.com/remote-software-development-jobs?page=1&sort_by=time&location_country=Colombia#main

First one is Worldwide, second one is South America and third one is Colombia.

Job listing will be ordered from recent to older and you will see labels something like:

- 23 hours ago
- Yesterday
- 2 Days Ago
- etc
- 1 Week Ago

At the bottem you will see pagination using pager - 1, 2... so once we go to the bottom of the page (no more jobs) you have to navigate to next page
Until you start seeing "2 Weeks Ago" or similar, so we will take all jobs in the last 7 days.
And repeat the same process for all 3 different locations as described above.

Once you click on the specifric job it will lead you to job page and use that url slug to detect already existing jobs in our system and for dedup.
Also, there is "Apply Now" button that would lead to real job url that we want to store - this is for dedup also and our View Job should lead to that redirected page.

Implement this, iterate, test until it works perfectly and give me the report how many jobs you have found for last week for each give location.