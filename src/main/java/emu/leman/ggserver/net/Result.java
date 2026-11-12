package emu.leman.ggserver.net;
import java.util.Map;
import static emu.leman.ggserver.util.Json.obj;
public record Result(Object data, Map<String,Object> error) {
    public static Result ok(Object data) { return new Result(data,obj("code",0,"errmsg","")); }
    public static Result error(int code,String message) { return new Result(obj(),obj("code",code,"errmsg",message)); }
}
