package emu.leman.ggserver.server;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.*;
import java.security.cert.*;
import java.security.spec.PKCS8EncodedKeySpec;
import java.util.*;
import java.util.regex.*;
import javax.net.ssl.*;

/** PEM (unencrypted PKCS#8 or RSA PKCS#1) and PKCS#12 server certificates. */
public final class Tls {
    private Tls() {}
    public static SSLContext load(Path file) throws Exception {
        return load(file,System.getenv().getOrDefault("GG_CERT_PASSWORD","changeit"));
    }
    public static SSLContext load(Path file,String configuredPassword) throws Exception {
        char[] password=configuredPassword.toCharArray();
        KeyStore store=KeyStore.getInstance("PKCS12");
        if(file.toString().endsWith(".pem")) {
            store.load(null,password);String pem=Files.readString(file);
            var certs=CertificateFactory.getInstance("X.509").generateCertificates(new ByteArrayInputStream(pem.getBytes(StandardCharsets.US_ASCII)));
            if(certs.isEmpty()) throw new IOException("No certificates in "+file);
            Matcher matcher=Pattern.compile("-----BEGIN (PRIVATE KEY|RSA PRIVATE KEY)-----([\\s\\S]*?)-----END \\1-----").matcher(pem);
            if(!matcher.find()) throw new IOException("Expected unencrypted PRIVATE KEY in "+file);
            byte[] der=Base64.getMimeDecoder().decode(matcher.group(2));
            if(matcher.group(1).equals("RSA PRIVATE KEY")) der=sequence(concat(new byte[]{2,1,0},new byte[]{0x30,0x0d,6,9,0x2a,(byte)0x86,0x48,(byte)0x86,(byte)0xf7,0x0d,1,1,1,5,0},tlv(4,der)));
            PrivateKey key=null;
            for(String algorithm:List.of("RSA","EC","Ed25519")) try { key=KeyFactory.getInstance(algorithm).generatePrivate(new PKCS8EncodedKeySpec(der));break; } catch(GeneralSecurityException ignored) { }
            if(key==null) throw new GeneralSecurityException("Unsupported private key in "+file);
            store.setKeyEntry("server",key,password,certs.toArray(java.security.cert.Certificate[]::new));
        } else try(var in=Files.newInputStream(file)) { store.load(in,password); }
        KeyManagerFactory km=KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm());km.init(store,password);
        SSLContext context=SSLContext.getInstance("TLS");context.init(km.getKeyManagers(),null,null);return context;
    }
    private static byte[] concat(byte[]... arrays) throws IOException { var out=new ByteArrayOutputStream();for(byte[] a:arrays) out.write(a);return out.toByteArray(); }
    private static byte[] sequence(byte[] value) throws IOException { return tlv(0x30,value); }
    private static byte[] tlv(int tag,byte[] value) throws IOException {
        var out=new ByteArrayOutputStream();out.write(tag);int n=value.length;
        if(n<128) out.write(n);else { int count=(32-Integer.numberOfLeadingZeros(n)+7)/8;out.write(0x80|count);for(int i=count-1;i>=0;i--) out.write(n >>> (i*8)); }
        out.write(value);return out.toByteArray();
    }
    public static Path ensureCertificate(Path root) throws Exception {
        return ensureCertificate(root.resolve("data"),System.getenv().getOrDefault("GG_CERT_PASSWORD","changeit"));
    }
    public static Path ensureCertificate(Path dataDirectory,String password) throws Exception {
        Path pem=dataDirectory.resolve("server.pem");if(Files.isRegularFile(pem)) return pem;
        Path file=dataDirectory.resolve("server.p12");if(Files.isRegularFile(file)) return file;
        Files.createDirectories(file.getParent());
        Path keytool=Path.of(System.getProperty("java.home"),"bin","keytool");
        var command=List.of(keytool.toString(),"-genkeypair","-alias","server","-keyalg","RSA","-keysize","2048",
                "-validity","3650","-dname","CN=*.pmang.cloud","-ext",
                "SAN=dns:game.gtgl.pmang.cloud,dns:dl.gtgl.pmang.cloud,dns:*.pmang.cloud,dns:*.neonapi.com,dns:localhost,ip:127.0.0.1",
                "-storetype","PKCS12","-keystore",file.toString(),"-storepass",password,"-keypass",password,"-noprompt");
        Process process=new ProcessBuilder(command).inheritIO().start();
        if(process.waitFor()!=0) throw new IOException("keytool could not generate certificate; supply --cert instead");
        return file;
    }
}
