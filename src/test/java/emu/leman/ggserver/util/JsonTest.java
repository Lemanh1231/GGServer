package emu.leman.ggserver.util;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.*;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

class JsonTest {
    @TempDir Path temp;
    @Test void wireNamesAndUnicodeSurviveCopy() {
        Map<String,Object> original=obj("u_nick","Lê Mẫn 🎸","area_data",obj("1",obj("s_Gp1","999999999999999999999999999999999")));
        Map<String,Object> cloned=copy(original);
        assertEquals(original,cloned);
        cloned.put("u_nick","changed");
        assertEquals("Lê Mẫn 🎸",original.get("u_nick"));
    }
    @Test void truthinessMatchesPythonForPayloadValues() {
        for(Object value:Arrays.asList(null,false,0,0.0,"",List.of(),Map.of())) assertFalse(truth(value));
        for(Object value:Arrays.asList(true,-1,"0","N",List.of(0),obj("x",0))) assertTrue(truth(value));
        assertEquals("fallback",first("",null,"fallback"));
    }
    @Test void atomicFileReplacementCreatesParent() {
        Path file=temp.resolve("nested/config.json");
        write(file,obj("enabled",true));
        assertEquals(Boolean.TRUE,map(read(file)).get("enabled"));
        write(file,obj("enabled",false));
        assertEquals(Boolean.FALSE,map(read(file)).get("enabled"));
    }
}
