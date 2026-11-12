package emu.leman.ggserver.server;

import com.sun.net.httpserver.HttpServer;
import java.net.*;
import java.net.http.*;
import java.nio.file.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

class DownloadTest {
    @TempDir Path root;
    private HttpServer server;
    private URI uri;
    private final HttpClient client=HttpClient.newHttpClient();
    @BeforeEach void start() throws Exception {
        Path apk=root.resolve("fixture.apk");Files.writeString(apk,"0123456789");
        server=HttpServer.create(new InetSocketAddress("127.0.0.1",0),0);
        server.createContext("/",exchange->HttpSupport.sendFile(exchange,apk,"fixture.apk","application/vnd.android.package-archive"));
        server.start();uri=URI.create("http://127.0.0.1:"+server.getAddress().getPort()+"/");
    }
    @AfterEach void stop() { server.stop(0); }
    private HttpResponse<String> request(String method,String range) throws Exception {
        var builder=HttpRequest.newBuilder(uri).method(method,HttpRequest.BodyPublishers.noBody());
        if(range!=null) builder.header("Range",range);
        return client.send(builder.build(),HttpResponse.BodyHandlers.ofString());
    }
    @Test void wholeFileAndHeadHaveRealLength() throws Exception {
        var get=request("GET",null);assertEquals(200,get.statusCode());assertEquals("0123456789",get.body());
        var head=request("HEAD",null);assertEquals("",head.body());assertEquals("10",head.headers().firstValue("Content-Length").orElseThrow());
    }
    @Test void boundedOpenAndSuffixRanges() throws Exception {
        var bounded=request("GET","bytes=2-4");assertEquals(206,bounded.statusCode());assertEquals("234",bounded.body());
        assertEquals("bytes 2-4/10",bounded.headers().firstValue("Content-Range").orElseThrow());
        assertEquals("789",request("GET","bytes=7-").body());
        assertEquals("89",request("GET","bytes=-2").body());
        assertEquals("0123456789",request("GET","bytes=-100").body());
        assertEquals("89",request("GET","bytes=8-100").body());
    }
    @Test void unsatisfiableOrMalformedRangesDoNotStreamFile() throws Exception {
        for(String range:new String[]{"bytes=10-","bytes=4-1","bytes=-0","bytes=-","bytes=bogus","bytes=999999999999999999999999-"}) {
            var response=request("GET",range);assertEquals(416,response.statusCode(),range);assertEquals("",response.body());
            assertEquals("bytes */10",response.headers().firstValue("Content-Range").orElseThrow());
        }
    }
    @Test void unsupportedMultipleRangesAndUnitsUseFullResponse() throws Exception {
        assertEquals(200,request("GET","bytes=0-1,3-4").statusCode());
        assertEquals(200,request("GET","items=0-1").statusCode());
    }
    @Test void landingPageNamesJavaAndDoesNotPromiseLosslessUninstall() {
        String html=Download.getDownloadHtml();assertTrue(html.contains("Java Server"));
        assertTrue(html.contains("kotorin.dev"));assertFalse(html.contains("100%"));
        assertTrue(html.contains("Không gỡ game"));
    }
}
