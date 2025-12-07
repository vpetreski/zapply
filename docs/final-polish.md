We will now do final polishing before I finally start using this tool.

1. Completely remove Dashboard from UI and backend, our initial page will now be Jobs page.
2. Remove status New from UI - filter in Jobs page and other places because job will either be matched or rejected, since matching is now part of pipeline, we can keep it internally though
3. On the right side of Status filter on Jobs page add new filter "Auto" or "Manual" or "Both" (which will be first and default in the list) which will indicate if matching was done by AI (what we are currently doing) or manual override (which we will add later). So for all existing jobs currently, we have to set that new flag to auto, since what we currently have was all matched automatically.
4. Remove Sort By filter and always sort first by date (newest first) then additionally by score
5. Remove Min Score filter
6. Add new filter to allow filtering by date scrapped we have. First and default in the list is "Last 7 Days", then "Last 15 days", then "Last 30 days", then "All"
7. On both job listing page and page details dialog add button to manually mark job as matched if it is rejected and button to mark job as rejected if it is matched. This will allow us to override matching status manually and in those cases we have to set newly added flag to manual instead of auto. When these actions are taken, make sure to update the UI to match and respect currently set filters.
8. On both job listing page and page details dialog, for job that is not applied yet - add a button to mark it as applied
9. Remove statistics page from UI and backend if needed
10. Modify Daily scheduler that currently runs 9pm Colombian time if enabled to run 6am Colombian time
11. Remove Database Cleanup completely from Admin page

Go - implement all this!