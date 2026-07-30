# Bug fixes

This file records fixes that were verified against decoded emulator captures and, where noted, from the Android client.

## Fixed

### Login event was hidden and could not be claimed

**Cause:** the server always returned `status = N` for `setAttendance(check)` and automatically credited the daily reward while constructing `getEventRewardList`. The client therefore considered the login event completed before the player saw it.

**Fix:**

- `setAttendance(check)` now returns `Y` when today's reward has not been claimed.
- `setAttendance(add)` performs the normal one-time claim, updates attendance state, and grants the configured reward.
- `getEventRewardList` no longer auto-claims a daily reward.
- A second claim on the same day is rejected without a duplicate reward.

**Verified:** clean-profile capture showed `check = Y`, followed by `add = Y`; the client displayed the 7-day login event and the reward popup.

### CP and Candy were incorrectly seeded with huge free balances

**Cause:** new users received 1,000,000 CP and 100,000 Candy, making purchases effectively free.

**Fix:** new profiles now start with `u_cp = 0`, `u_candy = 0`, and `u_free_cp = 0`. Existing profiles containing the old 1,000,000 `u_free_cp` seed are migrated to zero on full login.

### Skill upgrades appeared to fail

**Cause:** `state.save_user()` removed fields from the live inventory objects. `buyContents` had already put the same object into its response, so the client received `{}` instead of the upgraded skill.

**Fix:** persistence now works from copies and never mutates handler response objects.

**Verified:** the starter skill upgraded from level 1 to level 2 in the Android client.

### Skills were pre-opened before their level gate

**Cause:** the default profile injected an extra skill at creation/login.

**Fix:** only the starter skill is returned below level 10. The formerly pre-opened skill is added only once a character has reached level 10. Other game-defined locks remain client-visible.

### Star Pass used fabricated subscriptions and fabricated rewards

**Cause:** `setSubscribe` returned 100 invented subscription IDs and `setPassReward` always granted a mock reward.

**Fix:**

- Free Star Pass rewards are read from `SubscribePassReward` and `reward_group` in `game_data.json`.
- Claims are idempotent: retrying a claimed step returns no reward.
- The paid/Gold Star Card is never seeded, returned, or claimable. Only the Free Pass is available by design.
- Legacy saves that contain the previous unlock-all paid subscription list are cleared at login.

**Verified:** temporary-state tests confirm that Free Pass claims grant the configured reward while Gold Pass claims return an empty reward list. The client login capture returns an empty `user_subscribe_list` for the paid track.

### Furniture and music upgrade flow

**Verified:** Android testing upgraded the starter music and the `Bàn kệ đầu giường` furniture item from level 1 to level 2, with the displayed currency deduction and level change.

## Testing rule

After any server-code change, clear the Android app data before a clean-client test:

```bash
adb -s <device> shell pm clear com.neowiz.game.guitargirl
```

On a newly cleared app, accept all Terms of Game Service checkboxes, tap **Agree and Play**, and dismiss the optional Google Play Games profile sheet by tapping outside it. Grant app permissions when requested.
