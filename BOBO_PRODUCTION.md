# Bobo production policy — observe, repair, reserve

Zero spending; two distinct eleven-second videos daily remain the target.
Preparation runs before the existing 9 AM and 5 PM Pakistan publication windows.
Additional preparation checks conserve quota when an unreviewed draft exists, a
provider cooldown is active, or four unpublished approved reserve entries exist.
The reserve starts empty. Never report it as ready until actual files are approved.

1. Generate one simple existing-prop interaction, without complicated reveals.
   Generate enough active source footage for eleven seconds; never freeze-pad or
   blindly speed footage to pass duration. Initial dialogue remains provisional.
2. Inspect the entire artifact at least 4 fps and transitions at 8 fps. Observe
   mouth windows, physical contacts, action onset/completion and actual outcomes.
3. Repair the existing artifact first using `bobo_finishing_plan.json` and
   `finish-observed-bobo.yml`. The plan binds episode, artifact_run_id and
   source_sha256; supplies observed_from_full_render=true, observed_actions as
   named [start,end] pairs, purposeful_action_by, speech {text,start,observed_action,
   mouth_window_observed}, captions with observed_action and optional outcome /
   result_visible_at, effects {type,start,duration,observed_action,source,
   material_matched} and an accurate social_caption. The CPU finishing path
   preserves music_variant and resynthesizes only local Piper speech, captions and
   aligned foley. It cannot invent an absent visible action or fix prolonged jaw
   motion. Reject irreparable visual defects; never silently remove speech.
4. Download and re-review the repaired artifact; measure encoded speech, exact
   eleven-second duration and SHA. No waveform-only claim of listening or realism.
5. Approval stages the immutable reviewed artifact in bobo_reserve, preserving its
   pending record. Scheduled publication selects only due approved files, verifies
   all existing quality/SHA/duplicate gates, and caps accepted videos at two per
   Pakistan day. Pending records are removed only after accepted publication or
   deliberate rejection. Approved future entries permit preparing the next draft.
6. Facebook/Instagram and Stories reuse the reviewed file; no extra generation.
   API acceptance must be recorded; no promises of follower growth or exact times.

Do not regenerate merely because captions, voice placement or effects need repair.
Do not label a provisional render as approved. Keep the review enabled.
