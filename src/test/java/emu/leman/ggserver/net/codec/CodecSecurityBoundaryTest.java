package emu.leman.ggserver.net.codec;

import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/** Small hostile fixtures only: no load tests or production traffic. */
class CodecSecurityBoundaryTest {
    @Test void rejectsInvalidBase64AndInvalidCompressedStreams() {
        assertThrows(IOException.class,()->Codec.decodeBody("a"));
        assertThrows(IOException.class,()->Codec.decodeBody("bm90LWJ6aXA="));
    }

    @Test void rejectsNegativeAndOversizedCollectionCountsBeforeReadingElements() throws Exception {
        for(int count:new int[]{-1,16_777_217}) {
            var bytes=new ByteArrayOutputStream();
            try(var out=new DataOutputStream(bytes)) {
                out.writeByte(Thrift.LIST);out.writeShort(1);
                out.writeByte(Thrift.BYTE);out.writeInt(count);out.writeByte(Thrift.STOP);
            }
            assertThrows(IOException.class,()->Thrift.readStruct(bytes.toByteArray()));
        }
    }

    @Test void rejectsDeeplyNestedStructsWithCheckedError() throws Exception {
        var bytes=new ByteArrayOutputStream();
        try(var out=new DataOutputStream(bytes)) {
            for(int depth=0;depth<140;depth++) {out.writeByte(Thrift.STRUCT);out.writeShort(1);}
            for(int depth=0;depth<=140;depth++)out.writeByte(Thrift.STOP);
        }
        IOException error=assertThrows(IOException.class,()->Thrift.readStruct(bytes.toByteArray()));
        assertTrue(error.getMessage().contains("nesting limit"));
    }

    @Test void rejectsTruncatedStringsAndUnknownTypes() throws Exception {
        var bytes=new ByteArrayOutputStream();
        try(var out=new DataOutputStream(bytes)) {
            out.writeByte(Thrift.STRING);out.writeShort(1);out.writeInt(100);out.writeByte(Thrift.STOP);
        }
        assertThrows(IOException.class,()->Thrift.readStruct(bytes.toByteArray()));
        assertThrows(IOException.class,()->Thrift.readStruct(new byte[]{99,0,1,0}));
    }
}
