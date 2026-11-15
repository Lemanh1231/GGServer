# Module, player and packet boundaries

Feature code lives together under `game/account`, `game/economy`, `game/social`,
`game/content`, and `game/player`. Each top-level module implements `GameModule`
directly; there are no separate registrar-only wrappers or per-feature layers.
Keep small helpers package-private; expose only operations needed across features.

Declare game command names in `net/CmdId.java`, then reference `CmdId` constants
in modules and packet adapters. Bootstrap and exceptional response mappings live
there too. `resources/schema/schema.json` describes Thrift DTOs only; there is no
external command registry. Schema-only IDs do not imply implemented gameplay.

The composition root is `new GameContext(services).registerModules()` (package
`emu.leman.ggserver.game`). It installs the account, economy, social and
content groups in that order. `modules()` exposes their stable IDs; `commands()`
records the commands actually installed by each module, rather than maintaining
a second hard-coded command list. Registration is idempotent on that context.
Duplicate module IDs and duplicate registry commands are errors. Registration
is startup-only, not transactional: a failing module is not rolled back.

The auth group owns a nested `ProfileModule`. **Do not register it separately**:
`new AccountModule(services).register()` intentionally still installs all 18 legacy
auth/profile/system commands. The four top-level modules collectively install
the same 60 commands, with no duplicate profile bootstrap.

`net.GamePacket(command, request, context)` wraps the existing map-based
request, retains the raw envelope and context, and uses the existing payload
normalization (including the `device_uuid` override). `GameResponse.from(result)`
and `toResult()` retain the existing data/error envelope. Neither introduces
protobuf, new wire fields, authentication rules, or transport serialization.
Envelope maps are shallow read-only copies, not deep serialization clones.

`net.NetHandler` adapts `handle(GamePacket) -> Result` into `net.HandlerRegistry`. Profile
packets live beside their feature in `game/player`: they parse legacy aliases/defaults and call
`Player.profile()`. Other handler groups remain compatible legacy handlers.
HTTP dispatch can construct `GamePacket`, call the registry with `command()`,
`request()`, `context()`, then wrap its result with `GameResponse.from(...)`.

`game.player.Player` owns its identity and `ProfileManager`, not a cached user
document or session. `PlayerManager` supplies player ownership for feature
managers. Every manager read/write obtains a **fresh database snapshot** inside
the existing canonical-account lock. Only the fresh snapshot is saved, preventing
an old player object from overwriting intervening currency/inventory changes.
This is not a replacement concurrency or session system: unrelated direct state
writes must still obey the existing registry locking discipline.

Profile operations preserve legacy behavior: missing accounts are not created,
updates still acknowledge their parsed value, nickname null/empty/zero values
remain explicit, and avatar/title retain truthy-primary/raw-alternate semantics.
Profile projections still include exactly the original fields and zero counters.
No database schema, inventory format or session storage changes are involved.
