# Test context

Antarr has five agreed test seams. Tests should describe behavior through one of
these public interfaces and should not call or patch private helpers.

1. **Authentication HTTP routes** — `/auth/login/`, `/auth/callback/`, and
   `/auth/logout/`. WorkOS is an external system boundary and may be replaced by
   a fake in tests.
2. **Portal HTTP routes** — `/portal/` and its child routes. Observe behavior
   through responses, rendered content, redirects, messages, and downloads.
   Tenant isolation is a required behavior at every route that reads or mutates
   process data.
3. **Private object storage** — `PrivateObjectStorage.get_download_url()` and
   `PrivateObjectStorage.open_signed_download()`. Time and the filesystem are
   external boundaries.
4. **Notification-producing model events** — creating a document, scheduled
   operation, or message is the public event seam. Delivery is observed through
   Django's configured email backend after transaction commit.
5. **Rendered Wagtail pages** — a page URL and its rendered response are the
   public seam. Tests should assert editorial behavior visible to visitors,
   rather than Wagtail internals or template filenames.

For new behavior, work in vertical red → green slices: add one failing behavior
test at an agreed seam, make the smallest production change that passes it, and
then start the next slice. Structural refactoring happens only after the
behavioral cycles are complete.
