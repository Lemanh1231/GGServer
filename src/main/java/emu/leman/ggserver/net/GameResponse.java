package emu.leman.ggserver.net;

import java.util.Map;

/** Typed transport boundary retaining the existing Result data/error envelope verbatim. */
public record GameResponse(Object data, Map<String,Object> error) {
    public static GameResponse from(Result result) { return new GameResponse(result.data(),result.error()); }
    public Result toResult() { return new Result(data,error); }
}
