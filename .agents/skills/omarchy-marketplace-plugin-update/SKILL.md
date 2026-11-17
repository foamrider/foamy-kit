---
name: omarchy-marketplace-plugin-update
description: Submit a verified, pushed Foamy/Omarchy plugin commit to the Omarchy marketplace and track the listing until it is published. Use only when the user explicitly asks to publish or update a marketplace listing.
---

# Omarchy marketplace plugin update

Publishing needs explicit approval for the commit, the push, and the marketplace submission.

## Before submitting

1. Identify the plugin checkout (see the plugin list in foamy-kit's `AGENTS.md`), manifest plugin ID, branch, and existing marketplace listing.
   The submission targets `main`: the merge commit of the plugin's release pull request into `main`, never a `dev` commit. Do not offer to move or sync `dev` as part of a release or submission.
2. Run the repository tests, `git diff --check`, `qmllint`/`qmlformat -n` where relevant, and `omarchy plugin validate <checkout>`.
3. Commit only the task's files. After the release pull request is merged into `main`, confirm the local `main` equals `origin/main` and record the merge commit's full 40-character SHA.
4. If local history has commits that are not part of the task, ask before you include them.

## Submit

1. Create or update the listing's verification issue. Use exactly these form headings, in this order:
   `Verification action`, `Plugin ID`, `Repository URL`, `Target commit`, `Verification acknowledgment`, `Standard installation acknowledgment`.
2. Put the full `main` merge SHA in `Target commit`. Put other notes in a separate issue comment. Extra `###` headings make the form validation fail.

## Report

Report the label states `validated`, `review-required` and `approved-and-verified` exactly as they appear. Approval is not publication. Report "published" only after a publication comment or an updated marketplace snapshot confirms it. State any maintainer action that is still necessary.
