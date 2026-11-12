package emu.leman.ggserver.net.codec;

import emu.leman.ggserver.server.Dispatch;
import org.junit.jupiter.api.Test;
import java.io.IOException;
import java.nio.file.*;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

class CodecTest {
    private final Codec codec=new Codec(Path.of("resources"));
    @Test void bzipBlockSizeAndBase64RoundTrip() throws Exception {
        byte[] raw=new byte[]{11,0,1,0,0,0,3,'a','b','c',0};String encoded=Codec.encodeBody(raw);
        byte[] compressed=Base64.getDecoder().decode(encoded);
        assertEquals("BZh3",new String(compressed,0,4,java.nio.charset.StandardCharsets.US_ASCII));
        assertArrayEquals(raw,Codec.decodeBody(" \n"+encoded+"\n"));
        assertEquals("abc",Thrift.readStruct(raw).get(1));
    }
    @Test void namedRequestEnvelopeAndUnknownIds() throws Exception {
        var source=obj("call","userLoad","data",obj("uuid","日本語-🎸"));
        // Some releases place userLoad in another namespace; use schema discovery instead.
        String name=new Dispatch(codec).resolveCommand(obj("call","userLoad"));
        assertNotNull(name);String encoded=codec.encodeResponse(name,source);
        var decoded=codec.decodeRequest(encoded,name);
        assertEquals("userLoad",decoded.named().get("call"));
        assertEquals("日本語-🎸",map(decoded.named().get("data")).get("uuid"));
        assertEquals(7L,codec.idsToNames("not.a.schema",Map.of(99,7L)).get("99"));
    }
    @Test void primitiveClampingBinaryAndNestedContainers() throws Exception {
        var fields=List.of(obj("id",1,"name","tiny","type","I16"),obj("id",2,"name","integer","type","I32"),
                obj("id",3,"name","big","type","I64"),obj("id",4,"name","binary","type","STRING"),
                obj("id",5,"name","rows","type","MAP","key",obj("type","I32"),"val",obj("type","LIST","elem",obj("type","STRUCT","struct","row"))));
        var local=new Codec(obj("test",obj("fields",fields),"row",obj("fields",List.of(obj("id",1,"name","flag","type","BOOL")))));
        var source=obj("tiny",999999,"integer",-999999999999L,"big","99999999999999999999999999999","binary",new byte[]{(byte)255},
                "rows",Map.of(3,List.of(obj("flag",true))));
        var decoded=local.decodeRequest(local.encodeResponse("test",source),"test").named();
        assertEquals(32767,decoded.get("tiny"));assertEquals(Integer.MIN_VALUE,decoded.get("integer"));assertEquals(Long.MAX_VALUE,decoded.get("big"));
        assertArrayEquals(new byte[]{(byte)255},(byte[])decoded.get("binary"));
        assertEquals(true,map(list(((Map<?,?>)decoded.get("rows")).get(3)).getFirst()).get("flag"));
    }
    @Test void referenceGameDataCaptureReencodesToIdenticalThrift() throws Exception {
        String encoded=Files.readString(Path.of("resources/gamedata/getGameDataList.b64"));
        String dto=new Dispatch(codec).returnDtoFor("main.getGameDataList");assertNotNull(dto);
        var decoded=codec.decodeRequest(encoded,dto);
        String regenerated=codec.encodeResponse(dto,decoded.named());
        assertArrayEquals(Codec.decodeBody(encoded),Codec.decodeBody(regenerated));
    }
    @Test void malformedAndOversizedMessagesFail() {
        assertThrows(IOException.class,()->Codec.decodeBody("not a valid stream"));
        assertThrows(IOException.class,()->Thrift.readStruct(new byte[]{11,0,1,127,-1,-1,-1}));
        assertThrows(IOException.class,()->Thrift.readStruct(new byte[]{13,0,1,11,11,-1,-1,-1,-1}));
    }
    @Test void dispatchResolutionSpecialReturnsAndErrors() {
        var d=new Dispatch(codec);
        assertEquals("main.Request",d.resolveCommand(obj("call","Request","mode","userLoad")));
        assertEquals("main.initReturn",d.returnDtoFor("main.Request"));
        assertNotNull(d.returnDtoFor(d.resolveCommand(obj("call","facebookUserJoin"))));
        String command=d.resolveCommand(obj("call","userLoad"));
        var env=d.buildReturn(command,obj("ignored",true),null,"main",obj("code",900,"errmsg","Banned"));
        assertFalse(env.data().containsKey("data"));assertEquals(obj(),env.data().get("maintenance"));
        assertEquals(900,map(env.data().get("error")).get("code"));
    }
}
