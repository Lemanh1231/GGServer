# Guitar Girl (com.neowiz.game.guitargirl) — Server Protocol Analysis

Game: **Guitar Girl** by Neowiz, v8.0.0 (Unity 2022.x, IL2CPP, arm64).
Status: **End of Service** — original servers offline. Goal: build a server emulator.

## 1. Server topology (from metadata)

| Role | Production host | Other envs |
|------|-----------------|-----------|
| Game API server | `game.gtgl.pmang.cloud` | `game.gtgl-dev2/-dq/-review.pmang.cloud` |
| CDN / downloads | `dl.gtgl.pmang.cloud` | `dl.gtgl-dev/-dq/-review.pmang.cloud` |
| Account / platform | `global.neonapi.com`, PmangPlus SDK, AWS API GW (Tokyo) | `qa-*.neonapi.com` |

The client first contacts a **routing server** (`ServerRouterSGT.GetRoutingServerURL`) which
returns the actual API / CDN / web URLs and inspection/update flags. Then all gameplay calls
go to the API server.

## 2. Networking stack

- Engine networking lib namespace: **`blueasa.network`** (Neowiz in-house) on top of Unity `WWWForm` / `UnityWebRequest`.
- RPC payloads are **Apache Thrift** structs (`Thrift.Protocol.*`, `Thrift.Transport.*` present).
- Key classes:
  - `NetworkManagerSGT` — transport (Serialize/Deserialize/SendReq/SendToApiServer/PostWWW).
  - `ApiServerSGT` — 136 `Req*` senders + `OnRecv*` handlers (one per command). *Heavily name-obfuscated (Hangul) but Req/OnRecv/set_*Return are clear.*
  - `ServerRouterSGT` — routing/server discovery, inspection & forced-update flags.

## 3. Wire format (CONFIRMED by disassembly)

### Request body
```
encodedMsg = Base64( BZip2_compress( ThriftBinaryProtocol.Write(requestStruct) ) )
```
- `NetworkManagerSGT.Serialize(TBase)` →
  `MemoryStream(0x19000)` → `TStreamTransport` → **`TBinaryProtocol`** → `struct.Write()` →
  `ToArray()` → **BZip2 compress** (`ICSharpCode.SharpZipLib.BZip2.BZip2.Compress`, blockSize=3) → **`Convert.ToBase64String`**.
- BZip2 stream magic = ASCII `"BZh"`.

### HTTP transport
- `SendReq` → `Serialize(req)` → URL = `Router.<apiUrl@+0x78>` → `SendToApiServer`.
- `SendToApiServer` builds a **`WWWForm`** (multipart/form-data, HTTP POST) and adds fields:
  - **request type name** (C# `Type` name of the request DTO) — the routing key / command id.
  - **the `encodedMsg`** (base64 string above).
  - **access token** (`ApiServerSGT` access-token field).
  - one more constant field.
  - *(exact form field-key strings are runtime-initialised obfuscated statics — easiest to capture live; the server can identify fields generically: the message field base64-decodes to `BZh…`, the command field equals a known DTO type name.)*

### Response body
- `NetworkManagerSGT.Deserialize<T>(string body)`:
  - optionally strips a constant **prefix** (`body.Substring(0,k)==marker` → `body=body.Substring(k)`), else uses body as-is.
  - `Convert.FromBase64String` → `MemoryStream` → **`BZip2InputStream`** (decompress) → `TBinaryProtocol.Read` → `T` (the `<command>RetDataInfo`).
- So response = `[optional prefix] + Base64( BZip2( ThriftBinary( <cmd>RetDataInfo ) ) )`.
- **Emulator can omit the prefix** (client handles both paths).
- No symmetric encryption anywhere — only Thrift + BZip2 + Base64.

## 4. Command surface

- 136 `Req*` methods (full list in `work/idents.txt`), each with a request DTO `<cmd>DataInfo`
  and response DTO `<cmd>RetDataInfo`.
- **691 DTO classes** across feature namespaces (`work/dto_schema.json`):
  `user`(375) `main`(114) `rank`(41) `tour`(39) `music`(35) `store`(33) `eventMode`(26) `post`(22) `multi`(6).
- Thrift `TBinaryProtocol` is **self-describing** (each field = `[type:1][id:2][value]`), so requests
  can be decoded generically without the schema. Responses need each DTO's field-id/type map,
  extractable from its `Read`/`Write` method.

### Boot/login critical chain (first targets for the emulator)
`ServerRouter routing` → `ReqRunLogin` / `ReqPPLogin` (→ `userLogin*`) →
`ReqGetServerTime` → `ReqMain` / `ReqGetGameDataList` → table/cache fetches.

## 5. Artifacts produced
- `work/out/dump.cs` — full symbolicated C# (signatures + RVAs).
- `work/out/script.json` — address↔name map. `work/out/il2cpp.h` — structs.
- `work/dto_schema.json` — all DTO field names by namespace.
- `work/il2dis.py` — Capstone disassembler with symbol/string resolution (usage: `venv/bin/python il2dis.py 0xVA`).
- `work/meta.py` — IL2CPP v31 metadata parser.
