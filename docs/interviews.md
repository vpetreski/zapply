In the top menu we will Have Interviews link / page after Runs. So Jobs, Runs, Interviews, then the rest..

On the interview page we will be able to add new interview with title and description.

So what is an interview - when recruiter reach out to me either after me applying for job or reaching to me directly via Linkedin or anyhow
And the first meeting is scheduled, I will then create new interview to track the whole process.
Basically in title I plan to add something like company name and title.
And description we need some basic modern editor where I can nicely format description with heading bold, bullet points, etc.
It has to be minimal modern, nice dark theme to fit our app.
So I add interview with title and descritpion. 
We will also track created timestamp and updated timestamp - updated is updated when anything regarding interview updates.

On the page itself we will have a list of interview ordered by last updated descending - so most updated interview comes first.
Then as we scroll - interview load automatically until there is no more..

Also, interview will have status: active (default when we create it), closed.

Editing interview - again title, desription and also status - I can set it to closed (when signed the contract or rejected) and to active again.
We will also show status in interview view listing and modal.

On the listing page we will have status filter by default to active. So first Active, Closed, All.

In the description itself I will sometimes put links so they have to be rendered properly - clickable.

Also I need a way to attach custom cv for that specific job / interview in the case I optimized my default cv for it.
So on interview creation and edit we need a way to attach pdf of custom cv if that's the case and we will store it in DB column.
On interview preview (listing and modal) there will be a pdf icon / link where I can click and download that custom CV to know what I sent to them.
If no custom cv - just show nothning - or "no custom cv" something like that.
When I click to download the pdf it will be named as Resume-Vanja-Petreski.pdf

I think this is enough to start imlementation, once done, push, make PR and I will then test and review and we will iterate.