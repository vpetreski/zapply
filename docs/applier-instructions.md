These are instructions how we will implement together (Claude Code + me - human) and test and iterate Applier component.

So, you will first mark all failed and applied jobs to matched, so we start clean.

They we will go through full list of matched jobs and process them one by one like this:

You will show browser in this approach so I can see what's going on.

You start filling the form and before trying to submit yuu will ask in claude code console for my input where I can give me feedback about form filling 
for that job. So we might either fix issues on form filling or I can tell you to press the button to apply. Then you will again ask me for feedback what I see.

So basically we will go job by job, step by step - form filling, button pressing, verification, fixes, iteration.

Only when we fix existing job or decide to skip fixing for it - we will continue to next job.

Idea with this is that we don't guess, but work together to fix issues efficiently and once and for all.

USE REAL APPLIER CODE NOT SOME DUMB THING FOR TESTING WE WANT TO ITERATE AND MODIFY REAL CODE

Also this should be additive process, like fixing things with every iteration but not breaking what's already working.
Idea is to iterate and build robust system with 99% success rate for apply!

START!