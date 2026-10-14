# Sharing a memory: item grants and a replaceable front door

Status: **architectural design, not implemented**. There is no guest-share
command, share-management interface or public guest gateway in this design update.
No public listener is enabled and no trust/configuration is changed.

Future Crash + LOOK is a personal computing environment spanning a person's
devices. Files, Notes, media and commands are useful surfaces within it. Sharing
adds one boundary: an owner may grant another person access to a particular item
without giving that person general access to the environment.

## Existing mechanisms and their limits

- Fabric trust authorizes paired nodes. A guest link must not create a peer,
  grant node trust, or authorize general node APIs.
- Signal has short-lived, process-local media tickets tied to particular media
  requests. These are playback mechanisms, not durable email-ready share grants.
- Existing media routes support source delivery and browser presentation.
  A source responding successfully does not prove browser playback works.
- Tailscale Serve is private to the tailnet. Funnel can expose a local service
  publicly. Public reachability alone does not authenticate a guest.

These facts do not imply that guest sharing is already available. Verify the
current implementation and live discovery before reporting operational capability.

## The smallest useful boundary

An **item grant** describes owner intent independently of network transport:

| Part | Meaning |
|---|---|
| Owner | Existing local/Fabric authority allowed to share the item |
| Item | One explicitly selected resource and its source identity |
| Representation | Original file or an explicitly identified browser rendition |
| Guest policy | Anyone holding the link, or a separately verified recipient |
| Lifetime | Creation, expiry and revocation state |
| Rights | Read/stream the selected representation; no browsing or mutation |

Reuse existing item identities and Fabric locators. A locator such as
`@node:/path` identifies a location, not permission. Before implementation,
resolve how moved/replaced files are identified: a share must not silently begin
serving a different file that happens to occupy the same path. Content digests
can pin a representation where available; do not invent a second Fabric namespace.

A human-readable title is presentation, never authority. A random grant/link
identifier must not expose local paths, node credentials or internal API URLs.
Treat a link secret as bearer authority, store a verifier rather than a reusable
plaintext secret where feasible, and avoid writing it to access logs.

## Guest delivery boundary

The public-facing service should offer only a small share page and bounded
read/stream routes. It validates the grant and serves its selected item through
existing private owner-authorized facilities. Guests cannot choose arbitrary
nodes, paths, catalog IDs or internal API operations.

Tailscale Funnel is a possible first **reachability adapter**. Alternatives can
publish the same guest service without owning grant policy, recipient identity
or Fabric trust. Keep provider addresses separate from the resource/grant;
transport replacement may change a URL without changing who owns the item.
Do not publish the ordinary Unified Node, Signal/Albert control APIs, or a whole
directory merely to share one video.

No gateway, adapter interface, grant schema or endpoint is implemented here.
Define those only when a concrete sharing feature is approved.

## Contracts a future implementation must demonstrate

1. Explicit item selection and review precede publication. Selecting a file or
   previewing a note never creates a share.
2. Every guest content request, including HEAD and byte-range requests, checks
   the grant, representation, expiry and revocation. A signed token alone cannot
   provide immediate revocation without authoritative state or a bounded expiry.
3. Revocation denies subsequent requests. Define treatment of an already-open
   stream honestly; it cannot retrieve bytes already delivered to a recipient.
4. Anyone-with-link shares can be forwarded. Recipient-restricted shares need
   actual recipient verification; an email address in a grant is not verification.
5. Browser video delivery preserves seeking and reports preparation/failure.
   MP4/MOV filenames alone do not prove that the contained codecs are supported.
6. Sharing read access cannot guarantee prevention of copying or screen recording.
7. An unavailable owner or source produces an honest unavailable response, not
   invented access or silent substitution of unrelated media.
8. Publishing, changing lifetime/access, and revoking are separate owner actions
   with observable receipts. Opening a share grants no further authority.

## How assistants should use this document

This is a design reference, not an executable tool definition. LO, Albert and
Signal may explain it when retrieved, but must not claim they can create guest
shares, generate working public links or revoke them. Do not advertise a
`share.create` capability until a registered, authorized implementation exists.

The content is included in the generated installed `look/docs/REFERENCE.md`,
available through existing file-reading tools and `lk doc` / `lk help all`.
Source documentation and runtime evidence have different roles: docs describe
contracts; registered tools and live observations establish what can run now.
